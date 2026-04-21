"""Hierarchical block symbols for schematic hierarchy views."""

from __future__ import annotations

import math

from simulator.components.base import (
    Component,
    ComponentProperty,
    ComponentType,
    Pin,
    PinType,
    PropertyType,
)


class HierarchicalBlock(Component):
    """Symbolic analog/digital/mixed-signal sub-block used in hierarchy tabs."""

    def __init__(
        self,
        block_name: str,
        ports: list[str],
        domain: str = "mixed",
        instance_name: str | None = None,
        model_name: str | None = None,
    ):
        self._ref_prefix = "X"
        self._block_name = block_name
        self._ports = list(ports)
        self._domain = (domain or "mixed").upper()
        self._instance_name = instance_name or block_name
        self._model_name = model_name or block_name
        self._body_width = 150
        self._pin_span = max(5, math.ceil(len(self._ports) / 2))
        self._body_height = max(70, min(320, 32 + self._pin_span * 18))
        super().__init__()

    @property
    def component_type(self) -> ComponentType:
        return ComponentType.SUBCIRCUIT

    @property
    def display_name(self) -> str:
        return self._block_name

    @property
    def symbol_path(self) -> list[tuple]:
        half_h = self._body_height / 2
        x0 = -self._body_width / 2
        y0 = -half_h
        cmds: list[tuple] = [
            ("rect", x0, y0, self._body_width, self._body_height),
            ("text", x0 + 10, y0 + 18, self._domain, 8),
            ("text", x0 + 10, y0 + 36, self._shorten(self._block_name, 18), 10),
            ("text", x0 + 10, y0 + self._body_height - 8, self._shorten(self._instance_name, 22), 7),
        ]

        for pin in self._pins:
            label = self._shorten(pin.name, 16)
            if pin.x_offset < 0:
                cmds.append(("line", pin.x_offset, pin.y_offset, x0, pin.y_offset))
                cmds.append(("text", x0 + 4, pin.y_offset - 2, label, 7))
            else:
                cmds.append(("line", x0 + self._body_width, pin.y_offset, pin.x_offset, pin.y_offset))
                cmds.append(("text", x0 + self._body_width - 58, pin.y_offset - 2, label, 7))

        return cmds

    def _init_pins(self):
        left_names = self._ports[: self._pin_span]
        right_names = self._ports[self._pin_span :]
        self._pins = []

        left_step = self._pin_spacing(len(left_names))
        right_step = self._pin_spacing(len(right_names))

        left_start = -left_step * (len(left_names) - 1) / 2 if left_names else 0
        right_start = -right_step * (len(right_names) - 1) / 2 if right_names else 0

        for idx, name in enumerate(left_names):
            self._pins.append(Pin(name, self._guess_pin_type(name), -95, left_start + idx * left_step))
        for idx, name in enumerate(right_names):
            self._pins.append(Pin(name, self._guess_pin_type(name), 95, right_start + idx * right_step))

    def _init_properties(self):
        self._properties = {
            "domain": ComponentProperty(
                name="domain",
                display_name="Domain",
                property_type=PropertyType.STRING,
                default_value=self._domain,
                readonly=True,
            ),
            "instance_name": ComponentProperty(
                name="instance_name",
                display_name="Instance",
                property_type=PropertyType.STRING,
                default_value=self._instance_name,
                readonly=True,
            ),
            "model": ComponentProperty(
                name="model",
                display_name="Model",
                property_type=PropertyType.STRING,
                default_value=self._model_name,
                readonly=True,
            ),
            "port_count": ComponentProperty(
                name="port_count",
                display_name="Ports",
                property_type=PropertyType.INTEGER,
                default_value=len(self._ports),
                readonly=True,
            ),
        }

    def get_spice_model(self) -> str:
        nets = [pin.connected_net or pin.name for pin in self._pins]
        return f"X{self.reference} {' '.join(nets)} {self._model_name}".strip()

    def _pin_spacing(self, count: int) -> float:
        if count <= 1:
            return 18.0
        usable_height = self._body_height - 30
        return max(14.0, usable_height / (count - 1))

    def _guess_pin_type(self, name: str) -> PinType:
        upper = name.upper()
        if upper in {"0", "GND", "VSS", "VGND"} or "GND" in upper:
            return PinType.GROUND
        if upper.startswith("VDD") or upper.startswith("VIN") or upper.startswith("VBAT"):
            return PinType.POWER
        if any(token in upper for token in ("CLK", "RST", "EN", "CS", "WR", "RD", "ADDR", "WDATA", "MOSI", "SCLK", "TXD")):
            return PinType.INPUT
        if any(token in upper for token in ("MISO", "IRQ", "OUT", "RDATA", "RXD", "POR_N")):
            return PinType.OUTPUT
        if self._domain == "DIGITAL":
            return PinType.DIGITAL
        if self._domain == "ANALOG":
            return PinType.ANALOG
        return PinType.BIDIRECTIONAL

    @staticmethod
    def _shorten(text: str, max_len: int) -> str:
        if len(text) <= max_len:
            return text
        return text[: max_len - 3] + "..."