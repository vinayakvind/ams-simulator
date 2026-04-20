"""
DesignIndex Agent - Indexed design step registry for reproducibility.

Records every design step in a structured, indexed format so that
any design can be reproduced, audited, or used as a template for
future designs. Serves as the "memory" of the chip design agent.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


@dataclass
class IndexedStep:
    """A single indexed design step."""
    index: int
    chip_name: str
    phase: str
    description: str
    timestamp: float
    data: dict[str, Any] = field(default_factory=dict)
    status: str = "completed"
    duration_s: Optional[float] = None


class DesignIndex:
    """Maintains an indexed registry of all design steps.

    Provides persistence, querying, and template generation for
    reproducible chip design flows.

    Usage:
        idx = DesignIndex()
        idx.record_step("lin_asic", "architecture", {"blocks": [...]})
        idx.save("designs/lin_asic/design_index.json")

        # Later: reproduce or create a template
        template = idx.get_template("lin_asic")
    """

    def __init__(self):
        self._steps: list[IndexedStep] = []
        self._counter = 0
        self._templates: dict[str, list[dict]] = {}

    def record_step(self, chip_name: str, phase: str,
                    data: dict[str, Any],
                    description: str = "") -> IndexedStep:
        """Record a design step."""
        self._counter += 1
        step = IndexedStep(
            index=self._counter,
            chip_name=chip_name,
            phase=phase,
            description=description or f"{phase} for {chip_name}",
            timestamp=time.time(),
            data=data,
        )
        self._steps.append(step)
        return step

    def get_steps(self, chip_name: Optional[str] = None,
                  phase: Optional[str] = None) -> list[IndexedStep]:
        """Query design steps by chip name and/or phase."""
        results = self._steps
        if chip_name:
            results = [s for s in results if s.chip_name == chip_name]
        if phase:
            results = [s for s in results if s.phase == phase]
        return results

    def get_template(self, chip_name: str) -> list[dict[str, Any]]:
        """Generate a design template from recorded steps.

        Returns a list of steps that can be used to reproduce
        or create a similar design.
        """
        steps = self.get_steps(chip_name=chip_name)
        return [
            {
                "index": s.index,
                "phase": s.phase,
                "description": s.description,
                "data_keys": list(s.data.keys()),
            }
            for s in steps
        ]

    def save(self, filepath: str | Path) -> None:
        """Save the design index to a JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": "1.0",
            "total_steps": len(self._steps),
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "steps": [asdict(s) for s in self._steps],
            "templates": self._templates,
        }
        filepath.write_text(json.dumps(data, indent=2, default=str))

    def load(self, filepath: str | Path) -> None:
        """Load a design index from a JSON file."""
        filepath = Path(filepath)
        if not filepath.exists():
            return

        data = json.loads(filepath.read_text())
        self._steps = []
        for s in data.get("steps", []):
            self._steps.append(IndexedStep(**s))
        self._counter = len(self._steps)
        self._templates = data.get("templates", {})

    def register_template(self, name: str,
                          steps: list[dict[str, Any]]) -> None:
        """Register a reusable design template."""
        self._templates[name] = steps

    def list_templates(self) -> list[str]:
        """List available design templates."""
        return list(self._templates.keys())

    def summary(self) -> dict[str, Any]:
        """Get index summary."""
        chips = set(s.chip_name for s in self._steps)
        phases = set(s.phase for s in self._steps)
        return {
            "total_steps": len(self._steps),
            "chips_designed": list(chips),
            "phases_covered": list(phases),
            "templates_available": list(self._templates.keys()),
        }


# ── Pre-defined Design Templates ──────────────────────────────

DESIGN_TEMPLATES = {
    "mixed_signal_asic": [
        {"phase": "spec_capture", "description": "Capture chip specifications",
         "actions": ["define_supply", "define_io", "define_blocks", "define_interfaces"]},
        {"phase": "architecture", "description": "Define chip architecture",
         "actions": ["power_domains", "block_hierarchy", "signal_routing"]},
        {"phase": "bandgap_design", "description": "Design bandgap reference",
         "actions": ["topology_select", "sizing", "simulation", "verify_tempco"]},
        {"phase": "ldo_design", "description": "Design LDO regulators",
         "actions": ["error_amp", "pass_transistor", "compensation", "verify_regulation"]},
        {"phase": "transceiver_design", "description": "Design bus transceiver",
         "actions": ["driver", "receiver", "slew_control", "esd_protection"]},
        {"phase": "digital_design", "description": "Design digital controller",
         "actions": ["rtl_coding", "synthesis", "register_file", "verification"]},
        {"phase": "integration", "description": "Top-level chip integration",
         "actions": ["instantiation", "wiring", "power_routing", "io_assignment"]},
        {"phase": "verification", "description": "Full-chip verification",
         "actions": ["dc_analysis", "transient", "corners", "temperature"]},
        {"phase": "signoff", "description": "Design sign-off",
         "actions": ["drc", "lvs", "power_analysis", "report_generation"]},
    ],
    "lin_protocol_asic": [
        {"phase": "spec_capture", "description": "LIN ASIC specifications per ISO 17987"},
        {"phase": "architecture", "description": "LIN ASIC architecture with analog/digital partitioning"},
        {"phase": "bandgap", "description": "1.2V Brokaw bandgap reference"},
        {"phase": "ldo_analog", "description": "3.3V LDO for analog circuits"},
        {"phase": "ldo_digital", "description": "1.8V LDO for digital core"},
        {"phase": "ldo_lin", "description": "5V LDO for LIN transceiver"},
        {"phase": "lin_transceiver", "description": "LIN analog TX/RX per ISO 17987-4"},
        {"phase": "spi_controller", "description": "SPI slave for register access"},
        {"phase": "lin_controller", "description": "LIN protocol state machine"},
        {"phase": "register_file", "description": "Configuration register file"},
        {"phase": "control_logic", "description": "Power sequencing and clock management"},
        {"phase": "integration", "description": "Top-level LIN ASIC assembly"},
        {"phase": "verification", "description": "Full verification suite"},
    ],
}
