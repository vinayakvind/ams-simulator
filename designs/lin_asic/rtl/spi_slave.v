// =================================================================
// SPI Slave Controller - Verilog RTL
// Part of LIN Protocol ASIC
// =================================================================
// 4-wire SPI slave with 8-bit address, 8-bit data register access.
// Supports SPI Mode 0 (CPOL=0, CPHA=0).
// Protocol: [R/W bit][7-bit addr][8-bit data]
// =================================================================

module spi_slave (
    // SPI interface
    input  wire       sclk,
    input  wire       mosi,
    output reg        miso,
    input  wire       cs_n,

    // Register interface
    output reg  [7:0] reg_addr,
    output reg  [7:0] reg_wdata,
    input  wire [7:0] reg_rdata,
    output reg        reg_wr,
    output reg        reg_rd,

    // System
    input  wire       clk,
    input  wire       rst_n
);

    // ── Internal signals ──
    reg [4:0]  bit_cnt;
    reg [15:0] shift_in;
    reg [7:0]  shift_out;
    reg        rw_bit;       // 0 = write, 1 = read
    reg        sclk_d1, sclk_d2;
    reg        cs_n_d1, cs_n_d2;
    wire       sclk_posedge;
    wire       sclk_negedge;
    wire       cs_n_posedge;
    wire       cs_n_negedge;

    // ── Edge detection (synchronized to clk domain) ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk_d1 <= 1'b0;
            sclk_d2 <= 1'b0;
            cs_n_d1 <= 1'b1;
            cs_n_d2 <= 1'b1;
        end else begin
            sclk_d1 <= sclk;
            sclk_d2 <= sclk_d1;
            cs_n_d1 <= cs_n;
            cs_n_d2 <= cs_n_d1;
        end
    end

    assign sclk_posedge = sclk_d1 & ~sclk_d2;
    assign sclk_negedge = ~sclk_d1 & sclk_d2;
    assign cs_n_posedge = cs_n_d1 & ~cs_n_d2;
    assign cs_n_negedge = ~cs_n_d1 & cs_n_d2;

    // ── Shift-in on SCLK rising edge ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_in <= 16'h0000;
            bit_cnt  <= 5'd0;
        end else if (cs_n_negedge) begin
            // CS asserted - reset counter
            shift_in <= 16'h0000;
            bit_cnt  <= 5'd0;
        end else if (!cs_n_d2 && sclk_posedge) begin
            shift_in <= {shift_in[14:0], mosi};
            bit_cnt  <= bit_cnt + 5'd1;
        end
    end

    // ── Decode command after 16 bits received ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            reg_addr  <= 8'h00;
            reg_wdata <= 8'h00;
            rw_bit    <= 1'b0;
            reg_wr    <= 1'b0;
            reg_rd    <= 1'b0;
        end else if (cs_n_posedge) begin
            // CS de-asserted - complete transaction
            reg_wr <= 1'b0;
            reg_rd <= 1'b0;
        end else if (bit_cnt == 5'd8 && sclk_posedge && !cs_n_d2) begin
            // First 8 bits: R/W + 7-bit address
            rw_bit   <= shift_in[7];
            reg_addr <= {1'b0, shift_in[6:0]};
            if (shift_in[7]) begin
                // Read: load shift_out with register data
                reg_rd <= 1'b1;
            end
        end else if (bit_cnt == 5'd16 && sclk_posedge && !cs_n_d2) begin
            // Second 8 bits: data
            if (!rw_bit) begin
                // Write operation
                reg_wdata <= shift_in[7:0];
                reg_wr    <= 1'b1;
            end
        end else begin
            reg_wr <= 1'b0;
            reg_rd <= 1'b0;
        end
    end

    // ── Shift-out on SCLK falling edge (for reads) ──
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            shift_out <= 8'h00;
            miso      <= 1'b0;
        end else if (reg_rd) begin
            shift_out <= reg_rdata;
        end else if (!cs_n_d2 && sclk_negedge && bit_cnt > 5'd8) begin
            miso      <= shift_out[7];
            shift_out <= {shift_out[6:0], 1'b0};
        end
    end

endmodule
