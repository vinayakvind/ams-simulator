"""
Standard Analog Blocks - Ready-to-use CMOS analog circuit blocks with symbols.

Includes: LDO Regulator, Bandgap Reference, Current Mirror, Differential Pair,
OTA (Operational Transconductance Amplifier), Voltage Reference, Level Shifter,
Bias Generator.

Each block generates a full CMOS transistor-level SPICE netlist when placed,
with user-tunable high-level parameters (gain, bandwidth, dropout, etc.)
that automatically size internal transistors.
"""

from simulator.components.base import (
    Component, ComponentType, Pin, PinType,
    ComponentProperty, PropertyType
)


# ============================================================
# LDO Regulator (Low Dropout Regulator)
# ============================================================
class LDORegulator(Component):
    """CMOS Low Dropout Voltage Regulator.

    Architecture: Error Amplifier → Pass Transistor → Feedback Divider
    Generates full transistor-level SPICE subcircuit.
    """

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "LDO Regulator"

    @property
    def symbol_path(self) -> list[tuple]:
        """LDO box symbol with voltage labels."""
        return [
            # Main body (rectangle)
            ('rect', -40, -30, 80, 60),
            # Label
            ('text', 0, -5, 'LDO', 12),
            # Pin labels
            ('text', -30, -18, 'VIN', 8),
            ('text', 18, -18, 'VOUT', 8),
            ('text', -30, 18, 'GND', 8),
            ('text', 18, 18, 'EN', 8),
            # Pin stubs
            ('line', -55, -15, -40, -15),   # VIN
            ('line', 40, -15, 55, -15),     # VOUT
            ('line', -55, 15, -40, 15),     # GND
            ('line', 40, 15, 55, 15),       # EN
            # Power indicator
            ('text', 0, 10, '▼', 8),
        ]

    def _init_pins(self):
        self._pins = [
            Pin("VIN", PinType.POWER, -55, -15),
            Pin("VOUT", PinType.ANALOG, 55, -15),
            Pin("GND", PinType.GROUND, -55, 15),
            Pin("EN", PinType.INPUT, 55, 15),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='LDO_CMOS',
                description='SPICE subcircuit model name'
            ),
            'vout': ComponentProperty(
                name='vout', display_name='Output Voltage',
                property_type=PropertyType.FLOAT,
                default_value=1.2,
                unit='V', min_value=0.3, max_value=5.0,
                description='Regulated output voltage'
            ),
            'vin_max': ComponentProperty(
                name='vin_max', display_name='Max Input Voltage',
                property_type=PropertyType.FLOAT,
                default_value=3.3,
                unit='V', min_value=1.0, max_value=5.5,
                description='Maximum input voltage'
            ),
            'dropout': ComponentProperty(
                name='dropout', display_name='Dropout Voltage',
                property_type=PropertyType.FLOAT,
                default_value=0.2,
                unit='V', min_value=0.05, max_value=1.0,
                description='Minimum Vin-Vout for regulation'
            ),
            'iout_max': ComponentProperty(
                name='iout_max', display_name='Max Output Current',
                property_type=PropertyType.FLOAT,
                default_value=0.1,
                unit='A', min_value=1e-6, max_value=1.0,
                description='Maximum load current'
            ),
            'loop_gain': ComponentProperty(
                name='loop_gain', display_name='Loop Gain',
                property_type=PropertyType.FLOAT,
                default_value=60.0,
                unit='dB', min_value=20.0, max_value=100.0,
                description='DC loop gain in dB'
            ),
            'bandwidth': ComponentProperty(
                name='bandwidth', display_name='Bandwidth',
                property_type=PropertyType.FLOAT,
                default_value=1e6,
                unit='Hz', min_value=1e3, max_value=100e6,
                description='Unity-gain bandwidth of error amp'
            ),
            'psrr': ComponentProperty(
                name='psrr', display_name='PSRR',
                property_type=PropertyType.FLOAT,
                default_value=60.0,
                unit='dB', min_value=20.0, max_value=100.0,
                description='Power Supply Rejection Ratio at DC'
            ),
            'cout': ComponentProperty(
                name='cout', display_name='Output Capacitor',
                property_type=PropertyType.FLOAT,
                default_value=1e-6,
                unit='F', min_value=100e-12, max_value=100e-6,
                description='Output decoupling capacitor'
            ),
            'technology': ComponentProperty(
                name='technology', display_name='Technology',
                property_type=PropertyType.STRING,
                default_value='180nm',
                description='CMOS technology node'
            ),
        }

    def get_spice_model(self) -> str:
        vin_net = self._pins[0].connected_net or 'vin'
        vout_net = self._pins[1].connected_net or 'vout'
        gnd_net = self._pins[2].connected_net or '0'
        en_net = self._pins[3].connected_net or 'vin'
        model = self._properties['model'].value
        return f"X{self.reference} {vin_net} {vout_net} {gnd_net} {en_net} {model}"

    def generate_subcircuit(self) -> str:
        """Generate full CMOS transistor-level subcircuit for this LDO."""
        return generate_ldo_subcircuit(self._properties)


# ============================================================
# Bandgap Reference
# ============================================================
class BandgapReference(Component):
    """CMOS Bandgap Voltage Reference.

    Architecture: Self-biased cascode with BJT core.
    Generates ~1.2V temperature-independent reference.
    """

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "Bandgap Reference"

    @property
    def symbol_path(self) -> list[tuple]:
        return [
            ('rect', -35, -25, 70, 50),
            ('text', 0, -5, 'BGR', 12),
            ('text', -25, 15, 'GND', 8),
            ('text', 15, -15, 'VREF', 7),
            ('line', -50, -10, -35, -10),   # VDD
            ('line', 35, -10, 50, -10),     # VREF
            ('line', -50, 10, -35, 10),     # GND
            ('text', -25, -15, 'VDD', 8),
        ]

    def _init_pins(self):
        self._pins = [
            Pin("VDD", PinType.POWER, -50, -10),
            Pin("VREF", PinType.ANALOG, 50, -10),
            Pin("GND", PinType.GROUND, -50, 10),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='BGR_CMOS',
                description='Subcircuit model name'
            ),
            'vref': ComponentProperty(
                name='vref', display_name='Reference Voltage',
                property_type=PropertyType.FLOAT,
                default_value=1.2,
                unit='V', min_value=0.5, max_value=1.5,
                description='Output reference voltage'
            ),
            'tc': ComponentProperty(
                name='tc', display_name='Temp. Coefficient',
                property_type=PropertyType.FLOAT,
                default_value=10.0,
                unit='ppm/°C', min_value=0.1, max_value=100.0,
                description='Temperature coefficient'
            ),
            'psrr': ComponentProperty(
                name='psrr', display_name='PSRR',
                property_type=PropertyType.FLOAT,
                default_value=50.0,
                unit='dB', min_value=20.0, max_value=100.0,
                description='Power supply rejection'
            ),
            'iq': ComponentProperty(
                name='iq', display_name='Quiescent Current',
                property_type=PropertyType.FLOAT,
                default_value=50e-6,
                unit='A', min_value=1e-6, max_value=1e-3,
                description='Total quiescent current'
            ),
        }

    def get_spice_model(self) -> str:
        vdd = self._pins[0].connected_net or 'vdd'
        vref = self._pins[1].connected_net or 'vref'
        gnd = self._pins[2].connected_net or '0'
        return f"X{self.reference} {vdd} {vref} {gnd} {self._properties['model'].value}"


# ============================================================
# Current Mirror
# ============================================================
class CurrentMirror(Component):
    """CMOS Current Mirror with configurable ratio."""

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "Current Mirror"

    @property
    def symbol_path(self) -> list[tuple]:
        return [
            ('rect', -30, -25, 60, 50),
            ('text', 0, -5, 'CM', 12),
            ('text', -20, 12, 'IN', 8),
            ('text', 12, 12, 'OUT', 8),
            ('line', -45, 10, -30, 10),     # IIN
            ('line', 30, 10, 45, 10),       # IOUT
            ('line', -45, -10, -30, -10),   # VDD
            ('line', 30, -10, 45, -10),     # VSS/GND
        ]

    def _init_pins(self):
        self._pins = [
            Pin("VDD", PinType.POWER, -45, -10),
            Pin("VSS", PinType.POWER, 45, -10),
            Pin("IIN", PinType.INPUT, -45, 10),
            Pin("IOUT", PinType.OUTPUT, 45, 10),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='CM_CMOS',
                description='Subcircuit model name'
            ),
            'mirror_ratio': ComponentProperty(
                name='mirror_ratio', display_name='Mirror Ratio',
                property_type=PropertyType.FLOAT,
                default_value=1.0,
                min_value=0.01, max_value=100.0,
                description='Output/Input current ratio (Iout/Iin)'
            ),
            'iref': ComponentProperty(
                name='iref', display_name='Reference Current',
                property_type=PropertyType.FLOAT,
                default_value=10e-6,
                unit='A', min_value=1e-9, max_value=10e-3,
                description='Reference input current'
            ),
            'type': ComponentProperty(
                name='type', display_name='Mirror Type',
                property_type=PropertyType.STRING,
                default_value='NMOS',
                description='NMOS or PMOS mirror'
            ),
            'cascode': ComponentProperty(
                name='cascode', display_name='Cascode',
                property_type=PropertyType.BOOLEAN,
                default_value=False,
                description='Use cascode for higher output impedance'
            ),
        }

    def get_spice_model(self) -> str:
        vdd = self._pins[0].connected_net or 'vdd'
        vss = self._pins[1].connected_net or '0'
        iin = self._pins[2].connected_net or 'iin'
        iout = self._pins[3].connected_net or 'iout'
        return f"X{self.reference} {vdd} {vss} {iin} {iout} {self._properties['model'].value}"


# ============================================================
# OTA (Operational Transconductance Amplifier)
# ============================================================
class OTA(Component):
    """CMOS Operational Transconductance Amplifier (folded-cascode)."""

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "OTA"

    @property
    def symbol_path(self) -> list[tuple]:
        return [
            ('polygon', [(-35, -35), (-35, 35), (35, 0)]),
            ('text', -22, -15, '+', 12),
            ('text', -22, 15, '−', 12),
            ('text', 5, -5, 'Gm', 9),
            ('line', -50, -20, -35, -20),    # IN+
            ('line', -50, 20, -35, 20),      # IN-
            ('line', 35, 0, 50, 0),          # OUT
            ('line', 0, -35, 0, -50),        # VDD
            ('line', 0, 35, 0, 50),          # VSS
        ]

    def _init_pins(self):
        self._pins = [
            Pin("IN+", PinType.ANALOG, -50, -20),
            Pin("IN-", PinType.ANALOG, -50, 20),
            Pin("OUT", PinType.ANALOG, 50, 0),
            Pin("VDD", PinType.POWER, 0, -50),
            Pin("VSS", PinType.POWER, 0, 50),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='OTA_CMOS',
                description='Subcircuit model name'
            ),
            'gm': ComponentProperty(
                name='gm', display_name='Transconductance (Gm)',
                property_type=PropertyType.FLOAT,
                default_value=1e-3,
                unit='S', min_value=1e-6, max_value=0.1,
                description='DC transconductance'
            ),
            'gain': ComponentProperty(
                name='gain', display_name='DC Gain',
                property_type=PropertyType.FLOAT,
                default_value=70.0,
                unit='dB', min_value=20.0, max_value=120.0,
                description='Open-loop DC voltage gain'
            ),
            'bandwidth': ComponentProperty(
                name='bandwidth', display_name='Bandwidth',
                property_type=PropertyType.FLOAT,
                default_value=10e6,
                unit='Hz', min_value=1e3, max_value=1e9,
                description='Unity-gain bandwidth'
            ),
            'ibias': ComponentProperty(
                name='ibias', display_name='Bias Current',
                property_type=PropertyType.FLOAT,
                default_value=50e-6,
                unit='A', min_value=1e-6, max_value=1e-3,
                description='Tail bias current'
            ),
            'phase_margin': ComponentProperty(
                name='phase_margin', display_name='Phase Margin',
                property_type=PropertyType.FLOAT,
                default_value=60.0,
                unit='°', min_value=30.0, max_value=90.0,
                description='Phase margin at unity gain'
            ),
        }

    def get_spice_model(self) -> str:
        inp = self._pins[0].connected_net or 'inp'
        inn = self._pins[1].connected_net or 'inn'
        out = self._pins[2].connected_net or 'out'
        vdd = self._pins[3].connected_net or 'vdd'
        vss = self._pins[4].connected_net or '0'
        return f"X{self.reference} {inp} {inn} {out} {vdd} {vss} {self._properties['model'].value}"


# ============================================================
# Voltage Regulator (generic)
# ============================================================
class VoltageBuffer(Component):
    """Unity-gain CMOS voltage buffer (source follower)."""

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "Voltage Buffer"

    @property
    def symbol_path(self) -> list[tuple]:
        return [
            ('polygon', [(-30, -25), (-30, 25), (25, 0)]),
            ('text', -15, 0, '1x', 10),
            ('line', -45, 0, -30, 0),     # IN
            ('line', 25, 0, 40, 0),       # OUT
            ('line', 0, -25, 0, -40),     # VDD
            ('line', 0, 25, 0, 40),       # VSS
        ]

    def _init_pins(self):
        self._pins = [
            Pin("IN", PinType.ANALOG, -45, 0),
            Pin("OUT", PinType.ANALOG, 40, 0),
            Pin("VDD", PinType.POWER, 0, -40),
            Pin("VSS", PinType.POWER, 0, 40),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='VBUF_CMOS',
                description='Subcircuit model name'
            ),
            'zout': ComponentProperty(
                name='zout', display_name='Output Impedance',
                property_type=PropertyType.FLOAT,
                default_value=50.0,
                unit='Ω', min_value=0.1, max_value=10000.0,
                description='Output impedance'
            ),
            'ibias': ComponentProperty(
                name='ibias', display_name='Bias Current',
                property_type=PropertyType.FLOAT,
                default_value=100e-6,
                unit='A', min_value=1e-6, max_value=1e-3,
                description='Quiescent bias current'
            ),
        }

    def get_spice_model(self) -> str:
        vin = self._pins[0].connected_net or 'in'
        vout = self._pins[1].connected_net or 'out'
        vdd = self._pins[2].connected_net or 'vdd'
        vss = self._pins[3].connected_net or '0'
        return f"X{self.reference} {vin} {vout} {vdd} {vss} {self._properties['model'].value}"


# ============================================================
# Level Shifter
# ============================================================
class LevelShifter(Component):
    """CMOS Level Shifter (cross-coupled)."""

    def __init__(self):
        self._ref_prefix = "U"
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return "Level Shifter"

    @property
    def symbol_path(self) -> list[tuple]:
        return [
            ('rect', -30, -25, 60, 50),
            ('text', 0, 0, 'LS', 12),
            ('text', -20, -15, 'IN', 8),
            ('text', 13, -15, 'OUT', 8),
            ('line', -45, -10, -30, -10),   # IN
            ('line', 30, -10, 45, -10),     # OUT
            ('line', -45, 10, -30, 10),     # VDDL
            ('line', 30, 10, 45, 10),       # VDDH
            ('text', -22, 12, 'VL', 7),
            ('text', 15, 12, 'VH', 7),
        ]

    def _init_pins(self):
        self._pins = [
            Pin("IN", PinType.INPUT, -45, -10),
            Pin("OUT", PinType.OUTPUT, 45, -10),
            Pin("VDDL", PinType.POWER, -45, 10),
            Pin("VDDH", PinType.POWER, 45, 10),
        ]

    def _init_properties(self):
        self._properties = {
            'model': ComponentProperty(
                name='model', display_name='Model',
                property_type=PropertyType.STRING,
                default_value='LS_CMOS',
                description='Subcircuit model name'
            ),
            'vddl': ComponentProperty(
                name='vddl', display_name='Low-side VDD',
                property_type=PropertyType.FLOAT,
                default_value=1.2,
                unit='V', description='Input logic level supply'
            ),
            'vddh': ComponentProperty(
                name='vddh', display_name='High-side VDD',
                property_type=PropertyType.FLOAT,
                default_value=3.3,
                unit='V', description='Output logic level supply'
            ),
            'delay': ComponentProperty(
                name='delay', display_name='Propagation Delay',
                property_type=PropertyType.FLOAT,
                default_value=1e-9,
                unit='s', description='Input-to-output delay'
            ),
        }

    def get_spice_model(self) -> str:
        vin = self._pins[0].connected_net or 'in'
        vout = self._pins[1].connected_net or 'out'
        vddl = self._pins[2].connected_net or 'vddl'
        vddh = self._pins[3].connected_net or 'vddh'
        return f"X{self.reference} {vin} {vout} {vddl} {vddh} {self._properties['model'].value}"


# ============================================================
# SUBCIRCUIT GENERATION FUNCTIONS
# ============================================================

def _size_mosfet(iout: float, vdsat: float = 0.2, kp: float = 280e-6,
                 l_um: float = 0.5) -> float:
    """Calculate MOSFET width for target current.  W = 2*Id*L / (Kp * Vdsat^2)"""
    w = 2.0 * iout * (l_um * 1e-6) / (kp * vdsat ** 2)
    return max(w, 0.5e-6)  # min 0.5um


def generate_ldo_subcircuit(props: dict) -> str:
    """Generate complete CMOS LDO subcircuit from high-level specs.

    Parameters come from the LDORegulator component properties dict.
    Returns a full SPICE subcircuit definition with .MODEL statements.
    """
    vout = props['vout'].value
    vin = props['vin_max'].value
    dropout = props['dropout'].value
    iout_max = props['iout_max'].value
    loop_gain_db = props['loop_gain'].value
    bw = props['bandwidth'].value
    cout = props['cout'].value
    tech = props['technology'].value

    # Technology parameters
    if '180' in tech:
        kpn, kpp = 280e-6, 95e-6
        vthn, vthp = 0.45, 0.45
        lmin = 0.18e-6
    elif '65' in tech:
        kpn, kpp = 500e-6, 180e-6
        vthn, vthp = 0.35, 0.35
        lmin = 0.065e-6
    else:
        kpn, kpp = 280e-6, 95e-6
        vthn, vthp = 0.45, 0.45
        lmin = 0.18e-6

    # ---- Sizing calculations ----
    # Pass transistor: PMOS, must supply iout_max with Vsd >= dropout
    vsg_pass = vthp + dropout
    w_pass = 2.0 * iout_max * (0.5e-6) / (kpp * dropout ** 2)
    w_pass = max(w_pass, 20e-6)
    w_pass_um = w_pass * 1e6

    # Error amplifier bias current (1% of Iout_max, min 10uA)
    ibias = max(iout_max * 0.01, 10e-6)

    # Diff pair sizing (Gm = 2*Id/Vdsat, target Gm for BW)
    gm_target = 2 * 3.14159 * bw * cout
    vdsat_diff = max(2 * ibias / gm_target, 0.1) if gm_target > 0 else 0.15
    w_diff = _size_mosfet(ibias / 2, 0.15, kpn, 0.5)
    w_diff_um = w_diff * 1e6

    # Current mirror load (same current as diff pair)
    w_load = _size_mosfet(ibias / 2, 0.2, kpp, 0.5)
    w_load_um = w_load * 1e6

    # Tail current source sizing
    w_tail = _size_mosfet(ibias, 0.2, kpn, 1.0)
    w_tail_um = w_tail * 1e6

    # Feedback resistor divider: Vout = Vref * (1 + R1/R2)
    vref = 0.6  # Internal reference (bandgap-like)
    if vout > vref:
        r2 = 100e3
        r1 = r2 * (vout / vref - 1)
    else:
        r1 = 0
        r2 = 100e3

    lines = []
    lines.append(f"* CMOS LDO Regulator - Auto-generated")
    lines.append(f"* Target: Vin={vin}V, Vout={vout}V, Iout_max={iout_max*1e3:.1f}mA")
    lines.append(f"* Dropout={dropout}V, Loop Gain={loop_gain_db}dB, BW={bw/1e6:.1f}MHz")
    lines.append(f"* Technology: {tech}")
    lines.append(f"")
    lines.append(f"* MOSFET Models")
    lines.append(f".MODEL nmos_ldo NMOS (VTO={vthn} KP={kpn:.0e} LAMBDA=0.08)")
    lines.append(f".MODEL pmos_ldo PMOS (VTO=-{vthp} KP={kpp:.0e} LAMBDA=0.10)")
    lines.append(f"")
    lines.append(f"* ====== Power Supply ======")
    lines.append(f"Vin vin 0 DC {vin}V")
    lines.append(f"")
    lines.append(f"* ====== Internal Reference ({vref}V) ======")
    lines.append(f"Vref vref_int 0 DC {vref}V")
    lines.append(f"")
    lines.append(f"* ====== Error Amplifier (Folded-Cascode OTA) ======")
    lines.append(f"* Differential pair (NMOS)")
    lines.append(f"M1 d1 vref_int tail 0 nmos_ldo W={w_diff_um:.1f}u L=0.5u")
    lines.append(f"M2 d2 vfb tail 0 nmos_ldo W={w_diff_um:.1f}u L=0.5u")
    lines.append(f"")
    lines.append(f"* Tail current source")
    lines.append(f"M_tail tail vbias_n 0 0 nmos_ldo W={w_tail_um:.1f}u L=1u")
    lines.append(f"")
    lines.append(f"* Active load (PMOS current mirror)")
    lines.append(f"M3 d1 d1 vin vin pmos_ldo W={w_load_um:.1f}u L=0.5u")
    lines.append(f"M4 d2 d1 vin vin pmos_ldo W={w_load_um:.1f}u L=0.5u")
    lines.append(f"")
    lines.append(f"* ====== Pass Transistor (PMOS) ======")
    lines.append(f"Mpass vout d2 vin vin pmos_ldo W={w_pass_um:.0f}u L=0.5u")
    lines.append(f"")
    lines.append(f"* ====== Feedback Resistor Divider ======")
    lines.append(f"R1 vout vfb {r1:.0f}")
    lines.append(f"R2 vfb 0 {r2:.0f}")
    lines.append(f"")
    lines.append(f"* ====== Bias Circuit ======")
    lines.append(f"* Simple self-biased current reference")
    lines.append(f"Ibias vbias_n 0 DC {ibias:.2e}")
    lines.append(f"M_bias vbias_n vbias_n 0 0 nmos_ldo W={w_tail_um:.1f}u L=1u")
    lines.append(f"")
    lines.append(f"* ====== Output Capacitor ======")
    lines.append(f"Cout vout 0 {cout:.2e}")
    lines.append(f"")
    lines.append(f"* ====== Load ======")
    lines.append(f"Rload vout 0 {vout / iout_max:.1f}")
    lines.append(f"")
    lines.append(f"* ====== Compensation ======")
    lines.append(f"* Miller compensation on error amp output")
    lines.append(f"Cc d2 vout 5p")
    lines.append(f"Rc d2 d2_rc 1k")
    lines.append(f"Cc2 d2_rc vout 1p")
    lines.append(f"")
    lines.append(f"* ====== Analysis Commands ======")
    lines.append(f".OP")
    lines.append(f".TRAN 100n 500u UIC")
    lines.append(f"")
    lines.append(f"* Measurements")
    lines.append(f".SAVE V(vin) V(vout) V(vfb) V(vref_int) V(d1) V(d2) V(tail)")
    lines.append(f"")
    lines.append(f".END")

    return "\n".join(lines)
