// =================================================================
// Register File - SystemVerilog RTL
// Part of LIN Protocol ASIC
// =================================================================
// SPI-visible control and status register bank for the LIN ASIC.
// Provides power-enable sequencing controls, LIN mode control, baud-rate
// configuration, IRQ mask handling, and payload staging registers.
// =================================================================

module register_file (
    input  wire       clk,
    input  wire       rst_n,
    input  wire [7:0] reg_addr,
    input  wire [7:0] reg_wdata,
    output reg  [7:0] reg_rdata,
    input  wire       reg_wr,
    input  wire       reg_rd,
    output reg        lin_en,
    output reg        ana_en,
    output reg        bgr_en,
    output reg        ldo_ana_en,
    output reg        ldo_dig_en,
    output reg        ldo_lin_en,
    output reg        sleep_mode,
    output reg        master_mode,
    output reg [15:0] baud_div,
    output reg  [7:0] lin_tx_data,
    input  wire [7:0] lin_rx_data,
    output reg  [7:0] irq_en,
    input  wire [7:0] irq_flag
);

    localparam [7:0]
        CHIP_ID_ADDR   = 8'h00,
        CHIP_REV_ADDR  = 8'h01,
        CTRL_ADDR      = 8'h02,
        STATUS_ADDR    = 8'h03,
        LIN_CTRL_ADDR  = 8'h04,
        LIN_STAT_ADDR  = 8'h05,
        PID_ADDR       = 8'h06,
        LIN_DL_ADDR    = 8'h07,
        LIN_TX0_ADDR   = 8'h08,
        BAUD_DIV_HADDR = 8'h11,
        BAUD_DIV_LADDR = 8'h12,
        IRQ_EN_ADDR    = 8'h13,
        IRQ_FLAG_ADDR  = 8'h14;

    reg [7:0] chip_id_reg;
    reg [7:0] chip_rev_reg;
    reg [7:0] ctrl_reg;
    reg [7:0] status_reg;
    reg [7:0] lin_ctrl_reg;
    reg [7:0] lin_stat_reg;
    reg [7:0] pid_reg;
    reg [7:0] lin_dl_reg;
    reg [7:0] lin_tx0_reg;
    reg [7:0] baud_div_h_reg;
    reg [7:0] baud_div_l_reg;
    reg [7:0] irq_en_reg;
    reg [7:0] irq_flag_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            chip_id_reg    <= 8'h4C;
            chip_rev_reg   <= 8'h10;
            ctrl_reg       <= 8'h0F;
            status_reg     <= 8'h00;
            lin_ctrl_reg   <= 8'h80;
            lin_stat_reg   <= 8'h00;
            pid_reg        <= 8'h00;
            lin_dl_reg     <= 8'h08;
            lin_tx0_reg    <= 8'h00;
            baud_div_h_reg <= 8'h01;
            baud_div_l_reg <= 8'hA1;
            irq_en_reg     <= 8'h00;
            irq_flag_reg   <= 8'h00;
        end else begin
            status_reg   <= {3'b000, ctrl_reg[4], ctrl_reg[0], lin_ctrl_reg[7], lin_ctrl_reg[6], 1'b1};
            lin_stat_reg <= {5'b00000, lin_rx_data[2:0]};
            irq_flag_reg <= irq_flag;

            if (reg_wr) begin
                case (reg_addr)
                    CTRL_ADDR:      ctrl_reg <= reg_wdata;
                    LIN_CTRL_ADDR:  lin_ctrl_reg <= reg_wdata;
                    PID_ADDR:       pid_reg <= reg_wdata;
                    LIN_DL_ADDR:    lin_dl_reg <= reg_wdata;
                    LIN_TX0_ADDR:   lin_tx0_reg <= reg_wdata;
                    BAUD_DIV_HADDR: baud_div_h_reg <= reg_wdata;
                    BAUD_DIV_LADDR: baud_div_l_reg <= reg_wdata;
                    IRQ_EN_ADDR:    irq_en_reg <= reg_wdata;
                    IRQ_FLAG_ADDR:  irq_flag_reg <= irq_flag & ~reg_wdata;
                    default: begin end
                endcase
            end
        end
    end

    always @(*) begin
        reg_rdata   = 8'h00;
        lin_en      = lin_ctrl_reg[7];
        master_mode = lin_ctrl_reg[6];
        bgr_en      = ctrl_reg[3];
        ldo_lin_en  = ctrl_reg[2];
        ldo_dig_en  = ctrl_reg[1];
        ldo_ana_en  = ctrl_reg[0];
        ana_en      = ctrl_reg[0];
        sleep_mode  = ctrl_reg[4];
        baud_div    = {baud_div_h_reg, baud_div_l_reg};
        lin_tx_data = lin_tx0_reg;
        irq_en      = irq_en_reg;

        if (reg_rd) begin
            case (reg_addr)
                CHIP_ID_ADDR:   reg_rdata = chip_id_reg;
                CHIP_REV_ADDR:  reg_rdata = chip_rev_reg;
                CTRL_ADDR:      reg_rdata = ctrl_reg;
                STATUS_ADDR:    reg_rdata = status_reg;
                LIN_CTRL_ADDR:  reg_rdata = lin_ctrl_reg;
                LIN_STAT_ADDR:  reg_rdata = lin_stat_reg;
                PID_ADDR:       reg_rdata = pid_reg;
                LIN_DL_ADDR:    reg_rdata = lin_dl_reg;
                LIN_TX0_ADDR:   reg_rdata = lin_tx0_reg;
                BAUD_DIV_HADDR: reg_rdata = baud_div_h_reg;
                BAUD_DIV_LADDR: reg_rdata = baud_div_l_reg;
                IRQ_EN_ADDR:    reg_rdata = irq_en_reg;
                IRQ_FLAG_ADDR:  reg_rdata = irq_flag_reg;
                default:        reg_rdata = 8'h00;
            endcase
        end
    end

endmodule
