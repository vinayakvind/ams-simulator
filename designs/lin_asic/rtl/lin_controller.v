// =================================================================
// LIN Protocol Controller - Verilog RTL
// Part of LIN Protocol ASIC
// =================================================================
// LIN 2.2A compliant master/slave protocol controller.
// Handles break detection, sync, PID, data framing, and checksum.
// =================================================================

module lin_controller (
    // LIN transceiver interface
    output reg        txd,         // To LIN transceiver TXD input
    input  wire       rxd,         // From LIN transceiver RXD output

    // Register interface (from SPI controller)
    input  wire [7:0] reg_addr,
    input  wire [7:0] reg_wdata,
    output reg  [7:0] reg_rdata,
    input  wire       reg_wr,
    input  wire       reg_rd,

    // Control
    output reg        irq,
    input  wire       lin_en,
    input  wire       master_mode,  // 1 = master, 0 = slave
    input  wire [15:0] baud_div,    // Baud rate divisor

    // System
    input  wire       clk,
    input  wire       rst_n
);

    // ── LIN State Machine States ──
    localparam [3:0]
        ST_IDLE     = 4'd0,
        ST_BREAK_TX = 4'd1,
        ST_BREAK_RX = 4'd2,
        ST_SYNC     = 4'd3,
        ST_PID      = 4'd4,
        ST_DATA     = 4'd5,
        ST_CHECKSUM = 4'd6,
        ST_SLEEP    = 4'd7,
        ST_WAKEUP   = 4'd8,
        ST_ERROR    = 4'd9,
        ST_RESPONSE = 4'd10;

    reg [3:0]  state, next_state;

    // ── UART TX/RX ──
    reg [15:0] baud_cnt;
    reg        baud_tick;
    reg [3:0]  tx_bit_cnt;
    reg [3:0]  rx_bit_cnt;
    reg [9:0]  tx_shift;   // start + 8 data + stop
    reg [7:0]  rx_shift;
    reg        tx_busy;
    reg        rx_done;
    reg [7:0]  rx_byte;

    // ── LIN Protocol State ──
    reg [7:0]  pid_reg;
    reg [7:0]  data_buf [0:7];
    reg [2:0]  byte_cnt;
    reg [2:0]  data_len;       // 2, 4, or 8 bytes
    reg [7:0]  checksum_reg;
    reg        enhanced_cksum; // 1 = enhanced (LIN 2.0+)

    // ── Break Detection ──
    reg [4:0]  break_cnt;      // Count consecutive dominant bits
    reg        break_detected;
    reg        rxd_d1;

    // ── IRQ Flags ──
    reg [7:0]  irq_flags;
    // Bit 0: TX complete
    // Bit 1: RX complete
    // Bit 2: Error (checksum/framing)
    // Bit 3: Break detected
    // Bit 4: Wakeup
    reg [7:0]  irq_enable;

    // ── Baud Rate Generator ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            baud_cnt  <= 16'd0;
            baud_tick <= 1'b0;
        end else begin
            if (baud_cnt >= baud_div) begin
                baud_cnt  <= 16'd0;
                baud_tick <= 1'b1;
            end else begin
                baud_cnt  <= baud_cnt + 16'd1;
                baud_tick <= 1'b0;
            end
        end
    end

    // ── RXD Synchronization ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            rxd_d1 <= 1'b1;
        else
            rxd_d1 <= rxd;
    end

    // ── Break Detection (13+ dominant bits) ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            break_cnt      <= 5'd0;
            break_detected <= 1'b0;
        end else if (baud_tick) begin
            if (!rxd_d1) begin
                // Dominant bit
                if (break_cnt < 5'd20)
                    break_cnt <= break_cnt + 5'd1;
                if (break_cnt >= 5'd13)
                    break_detected <= 1'b1;
            end else begin
                break_cnt      <= 5'd0;
                break_detected <= 1'b0;
            end
        end
    end

    // ── UART Transmitter ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            txd        <= 1'b1;  // Recessive
            tx_busy    <= 1'b0;
            tx_shift   <= 10'h3FF;
            tx_bit_cnt <= 4'd0;
        end else if (tx_busy && baud_tick) begin
            txd      <= tx_shift[0];
            tx_shift <= {1'b1, tx_shift[9:1]};
            tx_bit_cnt <= tx_bit_cnt + 4'd1;
            if (tx_bit_cnt >= 4'd9) begin
                tx_busy <= 1'b0;
                txd     <= 1'b1;
            end
        end
    end

    // ── UART Receiver ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rx_shift   <= 8'h00;
            rx_bit_cnt <= 4'd0;
            rx_done    <= 1'b0;
            rx_byte    <= 8'h00;
        end else if (baud_tick) begin
            rx_done <= 1'b0;
            if (rx_bit_cnt == 4'd0) begin
                // Wait for start bit
                if (!rxd_d1)
                    rx_bit_cnt <= 4'd1;
            end else if (rx_bit_cnt >= 4'd1 && rx_bit_cnt <= 4'd8) begin
                rx_shift   <= {rxd_d1, rx_shift[7:1]};
                rx_bit_cnt <= rx_bit_cnt + 4'd1;
            end else if (rx_bit_cnt == 4'd9) begin
                // Stop bit
                rx_byte    <= rx_shift;
                rx_done    <= 1'b1;
                rx_bit_cnt <= 4'd0;
            end
        end
    end

    // ── Protected ID Calculation ──
    // P0 = ID0 ^ ID1 ^ ID2 ^ ID4
    // P1 = ~(ID1 ^ ID3 ^ ID4 ^ ID5)
    function [7:0] calc_pid;
        input [5:0] id;
        begin
            calc_pid[5:0] = id;
            calc_pid[6]   = id[0] ^ id[1] ^ id[2] ^ id[4];
            calc_pid[7]   = ~(id[1] ^ id[3] ^ id[4] ^ id[5]);
        end
    endfunction

    // ── Enhanced Checksum (LIN 2.0+) ──
    // Sum all data bytes + PID with carry wrap-around, then invert
    reg [8:0] cksum_acc;

    task compute_checksum;
        input [7:0] pid;
        integer i;
        begin
            cksum_acc = enhanced_cksum ? {1'b0, pid} : 9'd0;
            for (i = 0; i < data_len; i = i + 1) begin
                cksum_acc = cksum_acc + {1'b0, data_buf[i]};
                if (cksum_acc[8])
                    cksum_acc = {1'b0, cksum_acc[7:0]} + 9'd1;
            end
            checksum_reg = ~cksum_acc[7:0];
        end
    endtask

    // ── Main State Machine ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= ST_IDLE;
            pid_reg   <= 8'd0;
            byte_cnt  <= 3'd0;
            data_len  <= 3'd0;
            irq_flags <= 8'd0;
            irq       <= 1'b0;
        end else if (!lin_en) begin
            state <= ST_SLEEP;
        end else begin
            irq <= |(irq_flags & irq_enable);

            case (state)
                ST_IDLE: begin
                    if (master_mode) begin
                        // Master: initiate break
                        state <= ST_BREAK_TX;
                    end else begin
                        // Slave: wait for break
                        if (break_detected) begin
                            state <= ST_SYNC;
                            irq_flags[3] <= 1'b1;
                        end
                    end
                end

                ST_BREAK_TX: begin
                    // Transmit break (13 dominant bits + delimiter)
                    if (baud_tick) begin
                        if (break_cnt < 5'd14) begin
                            txd <= 1'b0;  // Dominant
                        end else begin
                            txd   <= 1'b1;  // Delimiter
                            state <= ST_SYNC;
                        end
                    end
                end

                ST_SYNC: begin
                    // Sync byte: 0x55
                    if (master_mode) begin
                        tx_shift <= {1'b1, 8'h55, 1'b0};
                        tx_busy  <= 1'b1;
                        state    <= ST_PID;
                    end else if (rx_done) begin
                        if (rx_byte == 8'h55)
                            state <= ST_PID;
                        else
                            state <= ST_ERROR;
                    end
                end

                ST_PID: begin
                    if (master_mode && !tx_busy) begin
                        // Send PID
                        tx_shift <= {1'b1, pid_reg, 1'b0};
                        tx_busy  <= 1'b1;
                        state    <= ST_DATA;
                        byte_cnt <= 3'd0;
                    end else if (!master_mode && rx_done) begin
                        pid_reg  <= rx_byte;
                        state    <= ST_DATA;
                        byte_cnt <= 3'd0;
                        // Determine data length from PID bits 5:4
                        case (rx_byte[5:4])
                            2'b00: data_len <= 3'd2;
                            2'b01: data_len <= 3'd2;
                            2'b10: data_len <= 3'd4;
                            2'b11: data_len <= 3'd8;
                        endcase
                    end
                end

                ST_DATA: begin
                    if (rx_done) begin
                        data_buf[byte_cnt] <= rx_byte;
                        byte_cnt <= byte_cnt + 3'd1;
                        if (byte_cnt >= data_len - 1)
                            state <= ST_CHECKSUM;
                    end
                end

                ST_CHECKSUM: begin
                    if (rx_done) begin
                        // Verify checksum
                        compute_checksum(pid_reg);
                        if (rx_byte == checksum_reg) begin
                            irq_flags[1] <= 1'b1;  // RX complete
                            state <= ST_IDLE;
                        end else begin
                            irq_flags[2] <= 1'b1;  // Checksum error
                            state <= ST_ERROR;
                        end
                    end
                end

                ST_ERROR: begin
                    state <= ST_IDLE;
                end

                ST_SLEEP: begin
                    // Wait for wakeup (dominant pulse > 250us)
                    if (!rxd_d1 && break_cnt >= 5'd5) begin
                        irq_flags[4] <= 1'b1;
                        state <= ST_IDLE;
                    end
                end

                ST_WAKEUP: begin
                    // Send wakeup pulse
                    txd   <= 1'b0;
                    state <= ST_IDLE;
                end

                default: state <= ST_IDLE;
            endcase
        end
    end

    // ── Register Read Interface ──
    // Allows SPI controller to read LIN controller status
    always @(*) begin
        case (reg_addr)
            8'h04: reg_rdata = {lin_en, master_mode, 2'b00,
                                data_len[1:0], enhanced_cksum, 1'b0};
            8'h05: reg_rdata = {4'd0, state};
            8'h06: reg_rdata = pid_reg;
            8'h07: reg_rdata = {5'd0, data_len};
            8'h08: reg_rdata = data_buf[0];
            8'h09: reg_rdata = data_buf[1];
            8'h0A: reg_rdata = data_buf[2];
            8'h0B: reg_rdata = data_buf[3];
            8'h0C: reg_rdata = data_buf[4];
            8'h0D: reg_rdata = data_buf[5];
            8'h0E: reg_rdata = data_buf[6];
            8'h0F: reg_rdata = data_buf[7];
            8'h10: reg_rdata = checksum_reg;
            8'h13: reg_rdata = irq_enable;
            8'h14: reg_rdata = irq_flags;
            default: reg_rdata = 8'h00;
        endcase
    end

    // ── Register Write Interface ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            irq_enable    <= 8'h00;
            enhanced_cksum <= 1'b1;  // Default: enhanced checksum
        end else if (reg_wr) begin
            case (reg_addr)
                8'h06: pid_reg <= reg_wdata;
                8'h07: data_len <= reg_wdata[2:0];
                8'h08: data_buf[0] <= reg_wdata;
                8'h09: data_buf[1] <= reg_wdata;
                8'h0A: data_buf[2] <= reg_wdata;
                8'h0B: data_buf[3] <= reg_wdata;
                8'h0C: data_buf[4] <= reg_wdata;
                8'h0D: data_buf[5] <= reg_wdata;
                8'h0E: data_buf[6] <= reg_wdata;
                8'h0F: data_buf[7] <= reg_wdata;
                8'h13: irq_enable <= reg_wdata;
                8'h14: irq_flags <= irq_flags & ~reg_wdata;  // W1C
            endcase
        end
    end

endmodule
