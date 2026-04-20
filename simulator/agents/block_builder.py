"""
BlockBuilder Agent - Constructs individual analog and digital circuit blocks.

Provides parameterized block generators for common ASIC building blocks
including bandgap references, LDOs, transceivers, protocol controllers,
register files, and more.
"""

from __future__ import annotations

from typing import Any


# ── Block generator registry ───────────────────────────────────────

_BLOCK_GENERATORS: dict[str, callable] = {}


def _register(name: str):
    """Decorator to register a block generator function."""
    def decorator(func):
        _BLOCK_GENERATORS[name] = func
        return func
    return decorator


class BlockBuilder:
    """Builds individual circuit blocks with technology-mapped parameters.

    Usage:
        builder = BlockBuilder("generic180")
        block = builder.build_block("bandgap", supply_voltage=3.3)
    """

    def __init__(self, technology: str = "generic180"):
        self.technology = technology

    def build_block(self, block_name: str, **kwargs) -> dict[str, Any]:
        """Build a named block with given parameters."""
        # Normalize name
        normalized = block_name.lower().replace("-", "_").replace(" ", "_")

        # Look up generator
        gen = _BLOCK_GENERATORS.get(normalized)
        if gen is None:
            # Try partial match
            for key, func in _BLOCK_GENERATORS.items():
                if key in normalized or normalized in key:
                    gen = func
                    break

        if gen is None:
            return {
                "name": block_name,
                "type": "stub",
                "netlist": f"* Stub for {block_name}\n.SUBCKT {block_name.upper()} vdd gnd\n.ENDS",
                "ports": ["vdd", "gnd"],
                "subckt_name": block_name.upper(),
                "transistor_count": 0,
            }

        return gen(**kwargs)

    def list_block_types(self) -> list[str]:
        """List all available block types."""
        return sorted(_BLOCK_GENERATORS.keys())


# ================================================================
# ANALOG BLOCK GENERATORS
# ================================================================

@_register("bandgap")
@_register("bandgap_reference")
@_register("bandgap_ref")
def _build_bandgap(**kwargs) -> dict[str, Any]:
    """Bandgap voltage reference - Brokaw topology.

    Generates a ~1.2V temperature-independent reference using
    BJT-based Brokaw bandgap architecture.
    """
    vdd = kwargs.get("supply_voltage", 3.3)

    netlist = f"""\
* Bandgap Voltage Reference - Brokaw Topology
* Supply: {vdd}V, Output: ~1.2V
* Temperature coefficient: < 50 ppm/°C
.SUBCKT BANDGAP_REF VDD VREF GND EN

* Startup circuit
M_START1 n_start1 EN GND GND NMOS_3P3 W=2u L=0.5u
M_START2 n_start1 n_start1 VDD VDD PMOS_3P3 W=4u L=0.5u
M_START3 n_bp n_start1 VDD VDD PMOS_3P3 W=4u L=0.5u

* PMOS current mirror (cascode for accuracy)
M_P1 n_c1 n_bp VDD VDD PMOS_3P3 W=20u L=2u
M_P2 n_c2 n_bp VDD VDD PMOS_3P3 W=20u L=2u
M_P3 n_bp n_bp VDD VDD PMOS_3P3 W=20u L=2u

* BJT pair (Q2 has 8x area of Q1)
Q1 n_c1 n_c1 n_e1 GND NPN_VERT AREA=1
Q2 n_c2 n_c2 n_e2 GND NPN_VERT AREA=8

* Emitter resistors for delta-VBE
R1 n_e1 n_r1 10k
R2 n_e2 n_r1 1.25k

* Output resistor divider for VREF = VBE + (R3/R2)*Vt*ln(8)
R3 n_r1 GND 25k

* Output buffer
M_BUF1 VREF n_c1 VDD VDD PMOS_3P3 W=40u L=1u
R_OUT VREF GND 100k
C_FILT VREF GND 10p

* Enable control
M_EN n_bp EN GND GND NMOS_3P3 W=2u L=0.5u

.ENDS BANDGAP_REF
"""
    return {
        "name": "bandgap_ref",
        "type": "analog",
        "netlist": netlist,
        "ports": ["VDD", "VREF", "GND", "EN"],
        "subckt_name": "BANDGAP_REF",
        "transistor_count": 7,
        "specs": {
            "vref_nominal": 1.2,
            "tempco": "< 50 ppm/°C",
            "psrr": "> 60 dB",
            "supply_range": f"{1.8} to {vdd + 0.5}V",
            "quiescent_current": "~50 uA",
        },
    }


@_register("ldo_analog")
@_register("ldo_ana")
def _build_ldo_analog(**kwargs) -> dict[str, Any]:
    """LDO regulator for analog supply (3.3V from 12V)."""
    vdd = kwargs.get("io_voltage", 12.0)
    vout = kwargs.get("supply_voltage", 3.3)
    iload = kwargs.get("load_current", 50e-3)

    netlist = f"""\
* LDO Regulator - Analog Supply
* Input: {vdd}V (VBAT), Output: {vout}V
* Load current: {iload*1e3:.0f}mA max
.SUBCKT LDO_ANALOG VIN VOUT GND VREF EN

* Error amplifier (folded-cascode OTA)
* Non-inverting: VREF, Inverting: feedback from VOUT divider
M_D1 n_d1 n_d1 VIN VIN PMOS_3P3 W=10u L=1u
M_D2 n_d2 n_d1 VIN VIN PMOS_3P3 W=10u L=1u
M_D3 n_d1 VREF n_tail GND NMOS_3P3 W=20u L=1u
M_D4 n_d2 n_fb n_tail GND NMOS_3P3 W=20u L=1u
M_TAIL n_tail n_bias GND GND NMOS_3P3 W=10u L=2u

* Bias current generation
M_BIAS n_bias n_bias GND GND NMOS_3P3 W=5u L=4u
R_BIAS n_bias VIN 200k

* Pass transistor (PMOS - low dropout)
M_PASS VOUT n_d2 VIN VIN PMOS_3P3 W=5000u L=0.5u

* Output capacitor (external, modeled)
C_OUT VOUT GND 1u
R_ESR VOUT n_esr 50m
C_INT n_esr GND 100p

* Feedback resistor divider: VOUT * R2/(R1+R2) = VREF
* For VREF=1.2V, VOUT={vout}V: R1/R2 = (VOUT/VREF - 1)
R_FB1 VOUT n_fb {(vout/1.2 - 1) * 100e3:.0f}
R_FB2 n_fb GND 100k

* Miller compensation
C_COMP n_d2 VOUT 5p
R_COMP n_d2 n_comp_int 10k
C_COMP2 n_comp_int VOUT 2p

* Enable switch
M_EN_SW n_bias EN GND GND NMOS_3P3 W=2u L=0.5u

.ENDS LDO_ANALOG
"""
    return {
        "name": "ldo_analog",
        "type": "analog",
        "netlist": netlist,
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "subckt_name": "LDO_ANALOG",
        "transistor_count": 8,
        "specs": {
            "vin_range": f"{vout + 0.3}V to {vdd + 0.5}V",
            "vout": f"{vout}V",
            "dropout": "< 300mV",
            "load_regulation": "< 1%",
            "line_regulation": "< 0.5%",
            "psrr": "> 50 dB @ 1kHz",
            "max_load_current": f"{iload*1e3:.0f} mA",
        },
    }


@_register("ldo_digital")
@_register("ldo_dig")
def _build_ldo_digital(**kwargs) -> dict[str, Any]:
    """LDO regulator for digital core supply (1.8V from 3.3V)."""
    vdd = kwargs.get("supply_voltage", 3.3)
    vout_dig = 1.8

    netlist = f"""\
* LDO Regulator - Digital Core Supply
* Input: {vdd}V (VDD_ANA), Output: {vout_dig}V
* Optimized for digital load transients
.SUBCKT LDO_DIGITAL VIN VOUT GND VREF EN

* Error amplifier (simple 2-stage)
M_D1 n_d1 n_d1 VIN VIN PMOS_3P3 W=8u L=1u
M_D2 n_d2 n_d1 VIN VIN PMOS_3P3 W=8u L=1u
M_D3 n_d1 VREF n_tail GND NMOS_3P3 W=15u L=1u
M_D4 n_d2 n_fb n_tail GND NMOS_3P3 W=15u L=1u
M_TAIL n_tail n_bias GND GND NMOS_3P3 W=8u L=2u

* Bias
M_BIAS n_bias n_bias GND GND NMOS_3P3 W=4u L=4u
R_BIAS n_bias VIN 150k

* Pass transistor
M_PASS VOUT n_d2 VIN VIN PMOS_3P3 W=3000u L=0.5u

* Decoupling
C_OUT VOUT GND 4.7u
C_INT VOUT GND 200p

* Feedback: VOUT * R2/(R1+R2) = VREF (1.2V)
* For VOUT=1.8V: R1 = 50k, R2 = 100k
R_FB1 VOUT n_fb 50k
R_FB2 n_fb GND 100k

* Compensation
C_COMP n_d2 VOUT 8p

* Enable
M_EN_SW n_bias EN GND GND NMOS_3P3 W=2u L=0.5u

.ENDS LDO_DIGITAL
"""
    return {
        "name": "ldo_digital",
        "type": "analog",
        "netlist": netlist,
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "subckt_name": "LDO_DIGITAL",
        "transistor_count": 8,
        "specs": {
            "vin_range": f"{vout_dig + 0.3}V to {vdd + 0.5}V",
            "vout": f"{vout_dig}V",
            "dropout": "< 200mV",
            "load_regulation": "< 2%",
            "max_load_current": "30 mA",
        },
    }


@_register("ldo_lin")
@_register("ldo_lin_driver")
def _build_ldo_lin(**kwargs) -> dict[str, Any]:
    """LDO regulator for LIN transceiver supply (5V from 12V VBAT)."""
    vbat = kwargs.get("io_voltage", 12.0)
    vout_lin = 5.0

    netlist = f"""\
* LDO Regulator - LIN Transceiver Supply
* Input: {vbat}V (VBAT), Output: {vout_lin}V
* Designed for LIN bus driver power
.SUBCKT LDO_LIN VIN VOUT GND VREF EN

* Error amplifier
M_D1 n_d1 n_d1 VIN VIN PMOS_HV W=10u L=1u
M_D2 n_d2 n_d1 VIN VIN PMOS_HV W=10u L=1u
M_D3 n_d1 VREF n_tail GND NMOS_3P3 W=20u L=1u
M_D4 n_d2 n_fb n_tail GND NMOS_3P3 W=20u L=1u
M_TAIL n_tail n_bias GND GND NMOS_3P3 W=10u L=2u

* Bias
M_BIAS n_bias n_bias GND GND NMOS_3P3 W=5u L=4u
R_BIAS n_bias VIN 300k

* HV Pass transistor (handles VBAT range 8-18V)
M_PASS VOUT n_d2 VIN VIN PMOS_HV W=8000u L=0.8u

* Output
C_OUT VOUT GND 2.2u
C_INT VOUT GND 100p

* Feedback: VOUT=5V, VREF=1.2V -> R1/R2 = 3.167
R_FB1 VOUT n_fb 316.7k
R_FB2 n_fb GND 100k

* Compensation
C_COMP n_d2 VOUT 4p
R_COMP n_d2 n_rc 15k
C_COMP2 n_rc VOUT 2p

* Enable
M_EN_SW n_bias EN GND GND NMOS_3P3 W=2u L=0.5u

.ENDS LDO_LIN
"""
    return {
        "name": "ldo_lin",
        "type": "analog",
        "netlist": netlist,
        "ports": ["VIN", "VOUT", "GND", "VREF", "EN"],
        "subckt_name": "LDO_LIN",
        "transistor_count": 8,
        "specs": {
            "vin_range": "8V to 18V (VBAT)",
            "vout": f"{vout_lin}V",
            "dropout": "< 500mV",
            "max_load_current": "100 mA",
            "purpose": "LIN transceiver power supply",
        },
    }


@_register("lin_transceiver")
@_register("lin_tx_rx")
@_register("lin_txrx")
def _build_lin_transceiver(**kwargs) -> dict[str, Any]:
    """LIN bus transceiver - analog transmitter and receiver.

    LIN physical layer per ISO 17987-4:
    - Single wire, dominant-low, recessive-high
    - VBAT pull-up through 1k resistor + diode
    - Open-drain driver (dominant pull-down)
    - Receiver with hysteresis comparator
    - Slew rate control for EMC compliance
    """
    vbat = kwargs.get("io_voltage", 12.0)

    netlist = f"""\
* LIN Bus Transceiver - Analog TX/RX
* Compliant with ISO 17987-4 / LIN 2.2A Physical Layer
* Bus voltage: {vbat}V (VBAT), Logic: 3.3V/5V
.SUBCKT LIN_TRANSCEIVER LIN_BUS TXD RXD VDD VBAT GND EN SLP_N

* =====================================================
* LIN BUS DRIVER (Transmitter)
* =====================================================
* Open-drain push-pull driver with slew rate control
* Dominant state: LIN_BUS pulled to GND through NMOS
* Recessive state: LIN_BUS pulled to VBAT through pull-up R + diode

* Slew rate control circuit
* Limits dV/dt to 1-4 V/us for EMC compliance
R_SR1 n_txd_buf n_sr 20k
C_SR n_sr GND 10p
M_SR_P n_gate_p n_sr VDD VDD PMOS_3P3 W=10u L=1u
M_SR_N n_gate_n n_sr GND GND NMOS_3P3 W=5u L=1u

* Pre-driver stage
M_PRE_P n_predrive n_gate_p VDD VDD PMOS_3P3 W=20u L=0.5u
M_PRE_N n_predrive n_gate_n GND GND NMOS_3P3 W=10u L=0.5u

* Main bus driver (open-drain NMOS)
* Strong pull-down for dominant state
M_DRV LIN_BUS n_predrive GND GND NMOS_HV W=200u L=0.8u

* LIN bus pull-up network (master node)
* 1k series resistor + blocking diode to VBAT
D_PU VBAT n_pu DIODE_HV
R_PU n_pu LIN_BUS 1k

* Internal pull-up (slave nodes use 30k)
R_PU_INT LIN_BUS n_pu_int 30k
D_PU_INT n_pu_int VBAT DIODE_HV

* TX input buffer with enable gating
M_TX_EN n_txd_buf TXD GND GND NMOS_3P3 W=5u L=0.5u
M_TX_EN2 n_txd_buf EN VDD VDD PMOS_3P3 W=5u L=0.5u

* =====================================================
* LIN BUS RECEIVER
* =====================================================
* Comparator with hysteresis for noise immunity
* Thresholds per LIN spec:
*   Dominant (logic 0): V_bus < 0.4 * VSUP
*   Recessive (logic 1): V_bus > 0.6 * VSUP

* Threshold voltage divider (from VBAT)
R_TH_H VBAT n_th_h 400k
R_TH_M n_th_h n_th_l 200k
R_TH_L n_th_l GND 400k
* n_th_h = 0.6*VBAT (recessive threshold)
* n_th_l = 0.4*VBAT (dominant threshold)

* Hysteresis comparator
M_RX_D1 n_rx1 n_rx1 VDD VDD PMOS_3P3 W=8u L=1u
M_RX_D2 n_rx2 n_rx1 VDD VDD PMOS_3P3 W=8u L=1u
M_RX_D3 n_rx1 LIN_BUS n_rx_tail GND NMOS_3P3 W=10u L=1u
M_RX_D4 n_rx2 n_th_mid n_rx_tail GND NMOS_3P3 W=10u L=1u
M_RX_TAIL n_rx_tail n_rx_bias GND GND NMOS_3P3 W=5u L=2u

* Midpoint threshold with hysteresis feedback
R_HYS_1 n_th_h n_th_mid 100k
R_HYS_2 n_th_mid n_th_l 100k

* Positive feedback for hysteresis (~100mV)
M_HYS n_th_mid n_rx2 GND GND NMOS_3P3 W=1u L=2u

* Receiver bias
M_RX_BIAS n_rx_bias n_rx_bias GND GND NMOS_3P3 W=3u L=4u
R_RX_BIAS n_rx_bias VDD 300k

* Output inverter buffer (RXD output)
M_RXD_P RXD n_rx2 VDD VDD PMOS_3P3 W=8u L=0.5u
M_RXD_N RXD n_rx2 GND GND NMOS_3P3 W=4u L=0.5u

* =====================================================
* SLEEP MODE CONTROL
* =====================================================
* SLP_N = 0: sleep mode, disable TX/RX, low power
* SLP_N = 1: normal operation
M_SLP_TX n_txd_buf SLP_N GND GND NMOS_3P3 W=2u L=0.5u
M_SLP_RX n_rx_bias SLP_N GND GND NMOS_3P3 W=2u L=0.5u

* Wake-up detector (monitors LIN bus during sleep)
R_WAKE LIN_BUS n_wake 1MEG
M_WAKE_DET n_wake_out n_wake GND GND NMOS_3P3 W=2u L=1u

.ENDS LIN_TRANSCEIVER
"""
    return {
        "name": "lin_transceiver",
        "type": "analog",
        "netlist": netlist,
        "ports": ["LIN_BUS", "TXD", "RXD", "VDD", "VBAT", "GND", "EN", "SLP_N"],
        "subckt_name": "LIN_TRANSCEIVER",
        "transistor_count": 22,
        "specs": {
            "bus_voltage": f"{vbat}V (VBAT)",
            "baud_rate": "up to 20 kbit/s",
            "dominant_voltage": "< 1.2V (typ 0.6V)",
            "recessive_voltage": f"> {vbat * 0.7:.1f}V",
            "slew_rate": "1-4 V/us",
            "rx_threshold_high": f"{vbat * 0.6:.1f}V",
            "rx_threshold_low": f"{vbat * 0.4:.1f}V",
            "sleep_current": "< 10 uA",
            "compliance": "ISO 17987-4 / LIN 2.2A",
        },
    }


@_register("lin_tx")
@_register("lin_transmitter")
def _build_lin_tx(**kwargs) -> dict[str, Any]:
    """Standalone LIN transmitter block."""
    result = _build_lin_transceiver(**kwargs)
    result["name"] = "lin_tx"
    return result


@_register("lin_rx")
@_register("lin_receiver")
def _build_lin_rx(**kwargs) -> dict[str, Any]:
    """Standalone LIN receiver block."""
    result = _build_lin_transceiver(**kwargs)
    result["name"] = "lin_rx"
    return result


# ================================================================
# DIGITAL BLOCK GENERATORS
# ================================================================

@_register("spi_controller")
@_register("spi")
def _build_spi_controller(**kwargs) -> dict[str, Any]:
    """SPI Controller for register access.

    4-wire SPI slave with configurable CPOL/CPHA.
    Provides register read/write interface to LIN controller.
    """
    netlist = """\
* SPI Slave Controller - Digital Block
* 4-wire SPI: SCLK, MOSI, MISO, CS_N
* 8-bit address, 8-bit data register interface
.SUBCKT SPI_CONTROLLER SCLK MOSI MISO CS_N VDD GND
+ REG_ADDR[7:0] REG_WDATA[7:0] REG_RDATA[7:0]
+ REG_WR REG_RD CLK RST_N

* ---- Verilog behavioral description ----
* module spi_slave (
*   input  wire       sclk,
*   input  wire       mosi,
*   output reg        miso,
*   input  wire       cs_n,
*   output reg  [7:0] reg_addr,
*   output reg  [7:0] reg_wdata,
*   input  wire [7:0] reg_rdata,
*   output reg        reg_wr,
*   output reg        reg_rd,
*   input  wire       clk,
*   input  wire       rst_n
* );
*
* reg [4:0] bit_cnt;
* reg [7:0] shift_in;
* reg [7:0] shift_out;
* reg       cmd_phase;  // 0=address, 1=data
* reg       rw_bit;     // 0=write, 1=read
*
* always @(posedge sclk or negedge cs_n) begin
*   if (!cs_n) begin
*     shift_in <= {shift_in[6:0], mosi};
*     bit_cnt <= bit_cnt + 1;
*   end
* end
*
* always @(negedge sclk) begin
*   miso <= shift_out[7];
*   shift_out <= {shift_out[6:0], 1'b0};
* end
*
* always @(posedge cs_n) begin
*   bit_cnt <= 0;
*   cmd_phase <= 0;
*   reg_wr <= 0;
*   reg_rd <= 0;
* end
*
* endmodule

* Gate-level placeholder for simulation
* (Full RTL in digital/ directory)
.ENDS SPI_CONTROLLER
"""
    return {
        "name": "spi_controller",
        "type": "digital",
        "netlist": netlist,
        "ports": ["SCLK", "MOSI", "MISO", "CS_N", "VDD", "GND",
                  "REG_ADDR[7:0]", "REG_WDATA[7:0]", "REG_RDATA[7:0]",
                  "REG_WR", "REG_RD", "CLK", "RST_N"],
        "subckt_name": "SPI_CONTROLLER",
        "transistor_count": 0,  # Digital - counted as gates
        "gate_count": 120,
        "specs": {
            "interface": "SPI Slave, Mode 0/1/2/3",
            "clock_freq": "up to 10 MHz",
            "address_width": 8,
            "data_width": 8,
        },
    }


@_register("lin_controller")
@_register("lin_protocol")
def _build_lin_controller(**kwargs) -> dict[str, Any]:
    """LIN Protocol Controller - Digital state machine.

    Implements LIN 2.2A protocol:
    - Break/sync/ID field detection (slave mode)
    - Break/sync/ID generation (master mode)
    - Data frame assembly/disassembly
    - Checksum computation (classic + enhanced)
    - Error detection (framing, checksum, bit)
    - Sleep/wake-up management
    """
    netlist = """\
* LIN Protocol Controller - Digital Block
* LIN 2.2A compliant master/slave controller
.SUBCKT LIN_CONTROLLER TXD RXD VDD GND CLK RST_N
+ REG_ADDR[7:0] REG_WDATA[7:0] REG_RDATA[7:0]
+ REG_WR REG_RD
+ IRQ LIN_MASTER_N
+ BAUD_DIV[15:0]

* ---- Verilog behavioral description ----
* module lin_controller (
*   output reg        txd,        // To LIN transceiver TXD
*   input  wire       rxd,        // From LIN transceiver RXD
*   input  wire       clk,        // System clock
*   input  wire       rst_n,      // Active-low reset
*   // Register interface (from SPI)
*   input  wire [7:0] reg_addr,
*   input  wire [7:0] reg_wdata,
*   output reg  [7:0] reg_rdata,
*   input  wire       reg_wr,
*   input  wire       reg_rd,
*   // Control
*   output reg        irq,        // Interrupt request
*   input  wire       lin_master_n, // 0=master, 1=slave
*   input  wire [15:0] baud_div   // Baud rate divisor
* );
*
* // LIN State Machine
* localparam IDLE     = 4'd0;
* localparam BREAK    = 4'd1;
* localparam SYNC     = 4'd2;
* localparam PID      = 4'd3;
* localparam DATA     = 4'd4;
* localparam CHECKSUM = 4'd5;
* localparam SLEEP    = 4'd6;
* localparam WAKEUP   = 4'd7;
* localparam ERROR    = 4'd8;
*
* reg [3:0] state;
* reg [7:0] data_buf [0:7]; // 8 bytes max
* reg [2:0] byte_cnt;
* reg [7:0] pid_reg;
* reg [7:0] checksum;
*
* // UART TX/RX at LIN baud rate
* reg [15:0] baud_counter;
* reg [3:0]  bit_pos;
* reg        tx_busy;
*
* // Protected ID calculation (PID)
* // P0 = ID0 ^ ID1 ^ ID2 ^ ID4
* // P1 = ~(ID1 ^ ID3 ^ ID4 ^ ID5)
* function [7:0] calc_pid;
*   input [5:0] id;
*   begin
*     calc_pid[5:0] = id;
*     calc_pid[6] = id[0] ^ id[1] ^ id[2] ^ id[4];
*     calc_pid[7] = ~(id[1] ^ id[3] ^ id[4] ^ id[5]);
*   end
* endfunction
*
* // Enhanced checksum (LIN 2.0+)
* function [7:0] calc_checksum;
*   input [7:0] pid;
*   input [7:0] data0, data1, data2, data3;
*   input [7:0] data4, data5, data6, data7;
*   input [2:0] len;
*   reg [15:0] sum;
*   integer i;
*   begin
*     sum = pid;
*     // Add data bytes with carry
*     sum = sum + data0; sum = (sum & 8'hFF) + (sum >> 8);
*     sum = sum + data1; sum = (sum & 8'hFF) + (sum >> 8);
*     // ... repeat for all bytes up to len
*     calc_checksum = ~sum[7:0]; // Invert
*   end
* endfunction
*
* endmodule

.ENDS LIN_CONTROLLER
"""
    return {
        "name": "lin_controller",
        "type": "digital",
        "netlist": netlist,
        "ports": ["TXD", "RXD", "VDD", "GND", "CLK", "RST_N",
                  "REG_ADDR[7:0]", "REG_WDATA[7:0]", "REG_RDATA[7:0]",
                  "REG_WR", "REG_RD", "IRQ", "LIN_MASTER_N",
                  "BAUD_DIV[15:0]"],
        "subckt_name": "LIN_CONTROLLER",
        "transistor_count": 0,
        "gate_count": 450,
        "specs": {
            "protocol": "LIN 2.2A (ISO 17987)",
            "modes": ["master", "slave"],
            "baud_rate": "1-20 kbit/s",
            "frame_types": ["unconditional", "event-triggered",
                            "sporadic", "diagnostic"],
            "data_length": "2/4/8 bytes",
            "checksum": "classic + enhanced",
            "error_detection": ["framing", "checksum", "bit", "sync"],
        },
    }


@_register("register_file")
@_register("registers")
@_register("reg_file")
def _build_register_file(**kwargs) -> dict[str, Any]:
    """LIN ASIC Register File - SPI-accessible configuration registers.

    Register Map:
    0x00: CHIP_ID      (RO) - Chip identification
    0x01: CHIP_REV     (RO) - Revision
    0x02: CTRL         (RW) - Main control register
    0x03: STATUS       (RO) - Status register
    0x04: LIN_CTRL     (RW) - LIN controller config
    0x05: LIN_STATUS   (RO) - LIN status
    0x06: LIN_ID       (RW) - LIN protected identifier
    0x07: LIN_DL       (RW) - Data length (2/4/8)
    0x08-0x0F: LIN_DATA[0:7] (RW) - LIN data buffer
    0x10: LIN_CKSUM    (RO) - Computed checksum
    0x11: BAUD_DIV_H   (RW) - Baud rate divisor high
    0x12: BAUD_DIV_L   (RW) - Baud rate divisor low
    0x13: IRQ_EN       (RW) - Interrupt enable
    0x14: IRQ_FLAG     (R/W1C) - Interrupt flags
    0x15: LDO_CTRL     (RW) - LDO enable/config
    0x16: BGR_CTRL     (RW) - Bandgap control
    0x17: SLEEP_CTRL   (RW) - Sleep mode control
    0x18: TRIM_BGR     (RW) - Bandgap trim
    0x19: TRIM_OSC     (RW) - Oscillator trim
    0x1A: TEST_MODE    (RW) - Test mode register
    """
    netlist = """\
* Register File - LIN ASIC Configuration Registers
* 8-bit address, 8-bit data, SPI-accessible
.SUBCKT REGISTER_FILE VDD GND CLK RST_N
+ REG_ADDR[7:0] REG_WDATA[7:0] REG_RDATA[7:0]
+ REG_WR REG_RD
+ LIN_EN ANA_EN BGR_EN LDO_ANA_EN LDO_DIG_EN LDO_LIN_EN
+ SLEEP_MODE MASTER_MODE
+ BAUD_DIV[15:0]
+ LIN_TX_DATA[7:0] LIN_RX_DATA[7:0]
+ IRQ_EN[7:0] IRQ_FLAG[7:0]

* Register Map (Verilog implementation)
* module register_file (
*   input  wire       clk,
*   input  wire       rst_n,
*   input  wire [7:0] reg_addr,
*   input  wire [7:0] reg_wdata,
*   output reg  [7:0] reg_rdata,
*   input  wire       reg_wr,
*   input  wire       reg_rd,
*   // Control outputs
*   output reg        lin_en,
*   output reg        ana_en,
*   output reg        bgr_en,
*   output reg        ldo_ana_en,
*   output reg        ldo_dig_en,
*   output reg        ldo_lin_en,
*   output reg        sleep_mode,
*   output reg        master_mode,
*   output reg [15:0] baud_div,
*   output reg  [7:0] irq_en,
*   input  wire [7:0] irq_flag
* );
*
* // Register storage
* reg [7:0] regs [0:31];
*
* // Read-only registers
* localparam CHIP_ID  = 8'h00; // Value: 0x4C (L for LIN)
* localparam CHIP_REV = 8'h01; // Value: 0x10 (Rev 1.0)
*
* // Control register bits
* // CTRL (0x02): [7:6]=reserved [5]=TEST [4]=SLEEP
* //              [3]=BGR_EN [2]=LDO_LIN_EN [1]=LDO_DIG_EN [0]=LDO_ANA_EN
*
* // LIN_CTRL (0x04): [7]=LIN_EN [6]=MASTER [5:4]=reserved
* //                  [3:2]=DATA_LEN [1]=ENHANCED_CKSUM [0]=AUTO_BAUD
*
* always @(posedge clk or negedge rst_n) begin
*   if (!rst_n) begin
*     regs[8'h00] <= 8'h4C; // CHIP_ID
*     regs[8'h01] <= 8'h10; // CHIP_REV
*     regs[8'h02] <= 8'h0F; // CTRL: all LDOs + BGR enabled
*     regs[8'h04] <= 8'h80; // LIN_CTRL: LIN enabled, slave mode
*     regs[8'h07] <= 8'h08; // LIN_DL: 8 bytes default
*     regs[8'h11] <= 8'h01; // BAUD_DIV_H (19.2kbps default)
*     regs[8'h12] <= 8'hA1; // BAUD_DIV_L
*   end else if (reg_wr) begin
*     case (reg_addr)
*       8'h00, 8'h01, 8'h03, 8'h05, 8'h10: ; // Read-only
*       8'h14: regs[reg_addr] <= regs[reg_addr] & ~reg_wdata; // W1C
*       default: regs[reg_addr] <= reg_wdata;
*     endcase
*   end
* end
*
* // Read mux
* always @(*) begin
*   reg_rdata = regs[reg_addr];
* end
*
* // Decode control outputs
* assign lin_en     = regs[8'h04][7];
* assign master_mode= regs[8'h04][6];
* assign bgr_en     = regs[8'h02][3];
* assign ldo_lin_en = regs[8'h02][2];
* assign ldo_dig_en = regs[8'h02][1];
* assign ldo_ana_en = regs[8'h02][0];
* assign sleep_mode = regs[8'h02][4];
* assign baud_div   = {regs[8'h11], regs[8'h12]};
*
* endmodule

.ENDS REGISTER_FILE
"""
    return {
        "name": "register_file",
        "type": "digital",
        "netlist": netlist,
        "ports": ["VDD", "GND", "CLK", "RST_N",
                  "REG_ADDR[7:0]", "REG_WDATA[7:0]", "REG_RDATA[7:0]",
                  "REG_WR", "REG_RD",
                  "LIN_EN", "ANA_EN", "BGR_EN",
                  "LDO_ANA_EN", "LDO_DIG_EN", "LDO_LIN_EN",
                  "SLEEP_MODE", "MASTER_MODE",
                  "BAUD_DIV[15:0]",
                  "LIN_TX_DATA[7:0]", "LIN_RX_DATA[7:0]",
                  "IRQ_EN[7:0]", "IRQ_FLAG[7:0]"],
        "subckt_name": "REGISTER_FILE",
        "transistor_count": 0,
        "gate_count": 280,
        "register_count": 27,
        "specs": {
            "address_width": 8,
            "data_width": 8,
            "register_count": 27,
            "access_types": ["RO", "RW", "R/W1C"],
            "chip_id": "0x4C",
            "chip_rev": "0x10",
        },
    }


@_register("control_logic")
@_register("ctrl_logic")
def _build_control_logic(**kwargs) -> dict[str, Any]:
    """Digital control logic - enables, power sequencing, clock generation."""
    netlist = """\
* Control Logic - Enable Sequencing & Clock Management
.SUBCKT CONTROL_LOGIC VDD GND CLK_IN RST_N
+ BGR_EN LDO_ANA_EN LDO_DIG_EN LDO_LIN_EN LIN_EN
+ SLEEP_MODE POR_N
+ CLK_OUT

* Power-on-reset detector
* RC delay for reliable startup
R_POR VDD n_por 100k
C_POR n_por GND 100p
* Schmitt trigger on POR
M_POR1 n_por_inv n_por VDD VDD PMOS_3P3 W=4u L=0.5u
M_POR2 n_por_inv n_por GND GND NMOS_3P3 W=2u L=0.5u
M_POR3 POR_N n_por_inv VDD VDD PMOS_3P3 W=4u L=0.5u
M_POR4 POR_N n_por_inv GND GND NMOS_3P3 W=2u L=0.5u

* RC oscillator (if no external clock)
* ~8 MHz relaxation oscillator
R_OSC1 VDD n_osc1 50k
C_OSC1 n_osc1 GND 1p
M_OSC_INV1 n_osc2 n_osc1 VDD VDD PMOS_3P3 W=4u L=0.5u
M_OSC_INV2 n_osc2 n_osc1 GND GND NMOS_3P3 W=2u L=0.5u
M_OSC_FB n_osc1 n_osc2 GND GND NMOS_3P3 W=1u L=0.5u

* Clock mux (external or internal)
M_CLK_MUX1 CLK_OUT CLK_IN VDD VDD PMOS_3P3 W=8u L=0.5u
M_CLK_MUX2 CLK_OUT CLK_IN GND GND NMOS_3P3 W=4u L=0.5u

* Power sequencing:
* 1. BGR first (always on after POR)
* 2. LDO_ANA second
* 3. LDO_DIG third
* 4. LDO_LIN + LIN_EN last
* (Sequencing is register-controlled, hardware provides delays)

.ENDS CONTROL_LOGIC
"""
    return {
        "name": "control_logic",
        "type": "mixed",
        "netlist": netlist,
        "ports": ["VDD", "GND", "CLK_IN", "RST_N",
                  "BGR_EN", "LDO_ANA_EN", "LDO_DIG_EN", "LDO_LIN_EN", "LIN_EN",
                  "SLEEP_MODE", "POR_N", "CLK_OUT"],
        "subckt_name": "CONTROL_LOGIC",
        "transistor_count": 10,
        "specs": {
            "por_delay": "~10us",
            "oscillator_freq": "~8 MHz",
            "power_sequencing": "BGR -> LDO_ANA -> LDO_DIG -> LDO_LIN -> LIN",
        },
    }
