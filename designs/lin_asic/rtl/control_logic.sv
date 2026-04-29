// =================================================================
// Control Logic - SystemVerilog RTL
// Part of LIN Protocol ASIC
// =================================================================
// Power-on sequencing, POR generation, and simple sleep-aware clock gating.
// The sequence implemented here matches the intended ASIC bring-up order:
//   1. Bandgap
//   2. Analog LDO
//   3. Digital LDO
//   4. LIN LDO and LIN enable
// =================================================================

module control_logic (
    input  wire clk_in,
    input  wire rst_n,
    input  wire sleep_mode,
    input  wire bgr_req,
    input  wire ldo_ana_req,
    input  wire ldo_dig_req,
    input  wire ldo_lin_req,
    input  wire lin_req,
    output reg  bgr_en,
    output reg  ldo_ana_en,
    output reg  ldo_dig_en,
    output reg  ldo_lin_en,
    output reg  lin_en,
    output reg  por_n,
    output reg  clk_out
);

    reg [3:0] por_count;

    always @(posedge clk_in or negedge rst_n) begin
        if (!rst_n) begin
            por_count   <= 4'd0;
            bgr_en      <= 1'b0;
            ldo_ana_en  <= 1'b0;
            ldo_dig_en  <= 1'b0;
            ldo_lin_en  <= 1'b0;
            lin_en      <= 1'b0;
            por_n       <= 1'b0;
            clk_out     <= 1'b0;
        end else begin
            if (por_count < 4'd10)
                por_count <= por_count + 4'd1;

            clk_out <= sleep_mode ? 1'b0 : clk_in;

            if (por_count >= 4'd1 && bgr_req)
                bgr_en <= 1'b1;
            if (por_count >= 4'd3 && ldo_ana_req)
                ldo_ana_en <= 1'b1;
            if (por_count >= 4'd5 && ldo_dig_req)
                ldo_dig_en <= 1'b1;
            if (por_count >= 4'd7 && ldo_lin_req)
                ldo_lin_en <= 1'b1;
            if (por_count >= 4'd8) begin
                por_n <= 1'b1;
                if (lin_req && !sleep_mode)
                    lin_en <= 1'b1;
            end

            if (sleep_mode)
                lin_en <= 1'b0;
        end
    end

endmodule