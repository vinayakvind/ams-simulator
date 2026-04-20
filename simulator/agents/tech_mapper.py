"""
TechMapper Agent - Technology-specific parameter mapping.

Maps generic design parameters to technology-specific values
for different process nodes (180nm, 130nm, 65nm, etc.).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TechParams:
    """Technology parameters for a specific process node."""
    name: str
    node_nm: int
    vdd_nominal: float
    vdd_io: float
    nmos_vth: float
    pmos_vth: float
    nmos_kp: float  # uA/V^2
    pmos_kp: float
    cox: float  # fF/um^2
    min_length: float  # um
    min_width: float  # um
    metal_layers: int
    poly_res: float  # ohm/sq
    nwell_res: float  # ohm/sq
    mim_cap: float  # fF/um^2
    hv_nmos_vth: float = 0.7
    hv_pmos_vth: float = -0.7
    hv_max_voltage: float = 20.0
    npn_bf: float = 100.0  # BJT forward gain
    description: str = ""


# ── Technology Library ──────────────────────────────────────

TECH_LIBRARY: dict[str, TechParams] = {
    "generic180": TechParams(
        name="generic180",
        node_nm=180,
        vdd_nominal=1.8,
        vdd_io=3.3,
        nmos_vth=0.5,
        pmos_vth=-0.5,
        nmos_kp=170.0,
        pmos_kp=60.0,
        cox=8.5,
        min_length=0.18,
        min_width=0.22,
        metal_layers=6,
        poly_res=7.5,
        nwell_res=900.0,
        mim_cap=2.0,
        hv_nmos_vth=0.7,
        hv_pmos_vth=-0.8,
        hv_max_voltage=20.0,
        npn_bf=100.0,
        description="Generic 180nm CMOS with HV options (automotive)",
    ),
    "generic130": TechParams(
        name="generic130",
        node_nm=130,
        vdd_nominal=1.2,
        vdd_io=3.3,
        nmos_vth=0.4,
        pmos_vth=-0.4,
        nmos_kp=250.0,
        pmos_kp=90.0,
        cox=12.0,
        min_length=0.13,
        min_width=0.16,
        metal_layers=8,
        poly_res=8.0,
        nwell_res=800.0,
        mim_cap=2.5,
        hv_nmos_vth=0.6,
        hv_pmos_vth=-0.7,
        hv_max_voltage=16.0,
        npn_bf=120.0,
        description="Generic 130nm CMOS",
    ),
    "generic65": TechParams(
        name="generic65",
        node_nm=65,
        vdd_nominal=1.0,
        vdd_io=2.5,
        nmos_vth=0.35,
        pmos_vth=-0.35,
        nmos_kp=400.0,
        pmos_kp=150.0,
        cox=20.0,
        min_length=0.06,
        min_width=0.09,
        metal_layers=9,
        poly_res=10.0,
        nwell_res=700.0,
        mim_cap=3.0,
        hv_nmos_vth=0.5,
        hv_pmos_vth=-0.6,
        hv_max_voltage=5.5,
        npn_bf=80.0,
        description="Generic 65nm CMOS (low-power)",
    ),
    "bcd180": TechParams(
        name="bcd180",
        node_nm=180,
        vdd_nominal=1.8,
        vdd_io=5.0,
        nmos_vth=0.5,
        pmos_vth=-0.5,
        nmos_kp=170.0,
        pmos_kp=60.0,
        cox=8.5,
        min_length=0.18,
        min_width=0.22,
        metal_layers=6,
        poly_res=7.5,
        nwell_res=900.0,
        mim_cap=2.0,
        hv_nmos_vth=0.8,
        hv_pmos_vth=-0.9,
        hv_max_voltage=40.0,
        npn_bf=150.0,
        description="BCD 180nm - Bipolar/CMOS/DMOS for automotive HV",
    ),
}


class TechMapper:
    """Maps design intent to technology-specific parameters.

    Usage:
        mapper = TechMapper("generic180")
        params = mapper.get_params()
        sized = mapper.size_transistor("nmos", ids=100e-6, vds=0.9)
    """

    def __init__(self, technology: str = "generic180"):
        self.technology = technology
        if technology not in TECH_LIBRARY:
            raise ValueError(
                f"Unknown technology '{technology}'. "
                f"Available: {list(TECH_LIBRARY.keys())}"
            )
        self.params = TECH_LIBRARY[technology]

    def get_params(self) -> dict[str, Any]:
        """Get all technology parameters as a dictionary."""
        return {
            "name": self.params.name,
            "node_nm": self.params.node_nm,
            "vdd_nominal": self.params.vdd_nominal,
            "vdd_io": self.params.vdd_io,
            "nmos_vth": self.params.nmos_vth,
            "pmos_vth": self.params.pmos_vth,
            "nmos_kp": self.params.nmos_kp,
            "pmos_kp": self.params.pmos_kp,
            "min_length": self.params.min_length,
            "min_width": self.params.min_width,
            "metal_layers": self.params.metal_layers,
            "hv_max_voltage": self.params.hv_max_voltage,
            "description": self.params.description,
        }

    def size_transistor(self, mos_type: str, ids: float,
                        vds: float, vgs_od: float = 0.2) -> dict[str, float]:
        """Calculate W/L for a desired drain current.

        Args:
            mos_type: 'nmos' or 'pmos'
            ids: Target drain current (A)
            vds: Drain-source voltage (V)
            vgs_od: Gate-source overdrive (V)

        Returns:
            Dictionary with W, L, and gm values
        """
        if mos_type.lower() == "nmos":
            kp = self.params.nmos_kp * 1e-6  # Convert to A/V^2
        else:
            kp = self.params.pmos_kp * 1e-6

        l = self.params.min_length * 2  # Use 2x minimum for analog
        # In saturation: Ids = (kp/2) * (W/L) * Vov^2
        w_over_l = (2 * abs(ids)) / (kp * vgs_od ** 2)
        w = w_over_l * l

        # Ensure minimum width
        w = max(w, self.params.min_width)

        # Transconductance
        gm = 2 * abs(ids) / vgs_od

        return {
            "W": round(w, 3),
            "L": round(l, 3),
            "W_um": f"{w:.2f}u",
            "L_um": f"{l:.2f}u",
            "gm": gm,
            "ids": ids,
        }

    def get_model_cards(self) -> str:
        """Generate SPICE model cards for the technology."""
        p = self.params
        return f"""\
* Technology: {p.name} ({p.node_nm}nm)
* {p.description}

.model NMOS_3P3 NMOS (LEVEL=1 VTO={p.nmos_vth} KP={p.nmos_kp}u
+  LAMBDA=0.04 PHI=0.65 GAMMA=0.5 TOX={10/p.cox:.1f}n)

.model PMOS_3P3 PMOS (LEVEL=1 VTO={p.pmos_vth} KP={p.pmos_kp}u
+  LAMBDA=0.05 PHI=0.65 GAMMA=0.6 TOX={10/p.cox:.1f}n)

.model NMOS_HV NMOS (LEVEL=1 VTO={p.hv_nmos_vth} KP={p.nmos_kp*0.6:.0f}u
+  LAMBDA=0.02 PHI=0.65 GAMMA=0.7 TOX=20n)

.model PMOS_HV PMOS (LEVEL=1 VTO={p.hv_pmos_vth} KP={p.pmos_kp*0.5:.0f}u
+  LAMBDA=0.03 PHI=0.65 GAMMA=0.8 TOX=20n)

.model NPN_VERT NPN (BF={p.npn_bf} IS=1e-16 VAF=80
+  TF=0.3n TR=5n CJC=0.5p CJE=0.8p)

.model DIODE_HV D (IS=1e-14 BV={p.hv_max_voltage} RS=10 N=1.05)
"""

    @staticmethod
    def list_technologies() -> list[dict[str, Any]]:
        """List all available technologies."""
        return [
            {
                "name": t.name,
                "node": f"{t.node_nm}nm",
                "vdd": t.vdd_nominal,
                "description": t.description,
            }
            for t in TECH_LIBRARY.values()
        ]
