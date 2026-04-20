"""
Base component classes for the AMS Simulator.
Defines the fundamental building blocks for all circuit components.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional, Callable
import uuid


class PinType(Enum):
    """Type of component pin."""
    INPUT = auto()
    OUTPUT = auto()
    BIDIRECTIONAL = auto()
    POWER = auto()
    GROUND = auto()
    ANALOG = auto()
    DIGITAL = auto()


class ComponentType(Enum):
    """Category of component."""
    PASSIVE = auto()
    TRANSISTOR = auto()
    DIODE = auto()
    SOURCE = auto()
    PROBE = auto()
    DIGITAL_GATE = auto()
    DIGITAL_SEQUENTIAL = auto()
    AMPLIFIER = auto()
    MIXED_SIGNAL = auto()
    SUBCIRCUIT = auto()


class PropertyType(Enum):
    """Type of component property."""
    FLOAT = auto()
    INTEGER = auto()
    STRING = auto()
    BOOLEAN = auto()
    ENUM = auto()
    EXPRESSION = auto()


@dataclass
class ComponentProperty:
    """Defines a property of a component that can be edited."""
    name: str
    display_name: str
    property_type: PropertyType
    default_value: Any
    value: Any = None
    unit: str = ""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: list[str] = field(default_factory=list)
    description: str = ""
    readonly: bool = False
    
    def __post_init__(self):
        if self.value is None:
            self.value = self.default_value
    
    def validate(self) -> tuple[bool, str]:
        """Validate the property value."""
        if self.property_type == PropertyType.FLOAT:
            try:
                val = float(self.value)
                if self.min_value is not None and val < self.min_value:
                    return False, f"{self.display_name} must be >= {self.min_value}"
                if self.max_value is not None and val > self.max_value:
                    return False, f"{self.display_name} must be <= {self.max_value}"
            except (TypeError, ValueError):
                return False, f"{self.display_name} must be a number"
        elif self.property_type == PropertyType.INTEGER:
            try:
                val = int(self.value)
                if self.min_value is not None and val < self.min_value:
                    return False, f"{self.display_name} must be >= {self.min_value}"
                if self.max_value is not None and val > self.max_value:
                    return False, f"{self.display_name} must be <= {self.max_value}"
            except (TypeError, ValueError):
                return False, f"{self.display_name} must be an integer"
        elif self.property_type == PropertyType.ENUM:
            if self.value not in self.enum_values:
                return False, f"{self.display_name} must be one of: {', '.join(self.enum_values)}"
        return True, ""
    
    def get_display_value(self) -> str:
        """Get the value formatted for display."""
        if self.property_type == PropertyType.FLOAT:
            val = float(self.value)
            # Use engineering notation for very large/small values
            if abs(val) >= 1e6:
                return f"{val/1e6:.3g}M{self.unit}"
            elif abs(val) >= 1e3:
                return f"{val/1e3:.3g}k{self.unit}"
            elif abs(val) >= 1:
                return f"{val:.3g}{self.unit}"
            elif abs(val) >= 1e-3:
                return f"{val*1e3:.3g}m{self.unit}"
            elif abs(val) >= 1e-6:
                return f"{val*1e6:.3g}µ{self.unit}"
            elif abs(val) >= 1e-9:
                return f"{val*1e9:.3g}n{self.unit}"
            elif abs(val) >= 1e-12:
                return f"{val*1e12:.3g}p{self.unit}"
            else:
                return f"{val:.3e}{self.unit}"
        return f"{self.value}{self.unit}"


@dataclass
class Pin:
    """Represents a connection point on a component."""
    name: str
    pin_type: PinType
    x_offset: float  # Offset from component center
    y_offset: float
    connected_net: Optional[str] = None
    connected_wire: Optional[str] = None
    
    def __post_init__(self):
        self.id = str(uuid.uuid4())[:8]
    
    @property
    def is_connected(self) -> bool:
        return self.connected_net is not None or self.connected_wire is not None
    
    def connect(self, net_name: str):
        """Connect this pin to a net."""
        self.connected_net = net_name
    
    def disconnect(self):
        """Disconnect this pin from any net."""
        self.connected_net = None
        self.connected_wire = None


@dataclass
class Point:
    """A 2D point."""
    x: float
    y: float
    
    def __add__(self, other: Point) -> Point:
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: Point) -> Point:
        return Point(self.x - other.x, self.y - other.y)
    
    def distance_to(self, other: Point) -> float:
        """Calculate distance to another point."""
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


class Component(ABC):
    """
    Abstract base class for all circuit components.
    
    Each component has:
    - A unique identifier
    - A reference designator (e.g., R1, C2, M3)
    - Position and rotation
    - Pins for connections
    - Properties that can be edited
    """
    
    # Class-level counters for reference designators
    _instance_counters: dict[str, int] = {}
    
    def __init__(self):
        self.id: str = str(uuid.uuid4())
        # Only set _ref_prefix to default if subclass hasn't set it
        if not hasattr(self, '_ref_prefix') or self._ref_prefix is None:
            self._ref_prefix: str = "X"
        self._ref_number: int = self._get_next_ref_number()
        
        # Position and orientation
        self.x: float = 0.0
        self.y: float = 0.0
        self.rotation: int = 0  # 0, 90, 180, 270 degrees
        self.mirror_h: bool = False
        self.mirror_v: bool = False
        
        # Pins and properties
        self._pins: list[Pin] = []
        self._properties: dict[str, ComponentProperty] = {}
        
        # Selection state
        self.selected: bool = False
        
        # Initialize component-specific pins and properties
        self._init_pins()
        self._init_properties()
    
    def _get_next_ref_number(self) -> int:
        """Get the next reference number for this component type."""
        prefix = self._ref_prefix
        if prefix not in Component._instance_counters:
            Component._instance_counters[prefix] = 0
        Component._instance_counters[prefix] += 1
        return Component._instance_counters[prefix]
    
    @classmethod
    def reset_counters(cls):
        """Reset all reference designator counters."""
        cls._instance_counters.clear()
    
    @property
    def reference(self) -> str:
        """Get the reference designator (e.g., R1, C2)."""
        return f"{self._ref_prefix}{self._ref_number}"
    
    @reference.setter
    def reference(self, value: str):
        """Set the reference designator."""
        # Parse prefix and number from value
        import re
        match = re.match(r'([A-Za-z]+)(\d+)', value)
        if match:
            self._ref_prefix = match.group(1)
            self._ref_number = int(match.group(2))
    
    @property
    @abstractmethod
    def component_type(self) -> ComponentType:
        """Get the component category."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Get the display name of the component."""
        pass
    
    @property
    @abstractmethod
    def symbol_path(self) -> list[tuple]:
        """
        Get the drawing path for the component symbol.
        Returns a list of drawing commands:
        - ('line', x1, y1, x2, y2)
        - ('rect', x, y, width, height)
        - ('circle', cx, cy, radius)
        - ('arc', cx, cy, radius, start_angle, end_angle)
        - ('text', x, y, text, size)
        - ('polygon', [(x1,y1), (x2,y2), ...])
        """
        pass
    
    @abstractmethod
    def _init_pins(self):
        """Initialize the component pins."""
        pass
    
    @abstractmethod
    def _init_properties(self):
        """Initialize the component properties."""
        pass
    
    @property
    def pins(self) -> list[Pin]:
        """Get all pins."""
        return self._pins
    
    def get_pin(self, name: str) -> Optional[Pin]:
        """Get a pin by name."""
        for pin in self._pins:
            if pin.name == name:
                return pin
        return None
    
    def get_pin_position(self, pin: Pin) -> Point:
        """Get the absolute position of a pin, accounting for rotation and mirroring."""
        import math
        
        # Apply mirroring
        x_off = -pin.x_offset if self.mirror_h else pin.x_offset
        y_off = -pin.y_offset if self.mirror_v else pin.y_offset
        
        # Apply rotation
        angle = math.radians(self.rotation)
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        
        rotated_x = x_off * cos_a - y_off * sin_a
        rotated_y = x_off * sin_a + y_off * cos_a
        
        return Point(self.x + rotated_x, self.y + rotated_y)
    
    @property
    def properties(self) -> dict[str, ComponentProperty]:
        """Get all properties."""
        return self._properties
    
    def get_property(self, name: str) -> Optional[ComponentProperty]:
        """Get a property by name."""
        return self._properties.get(name)
    
    def set_property(self, name: str, value: Any) -> tuple[bool, str]:
        """Set a property value. Returns (success, error_message)."""
        prop = self._properties.get(name)
        if prop is None:
            return False, f"Property '{name}' not found"
        if prop.readonly:
            return False, f"Property '{name}' is read-only"
        
        old_value = prop.value
        prop.value = value
        
        valid, error = prop.validate()
        if not valid:
            prop.value = old_value
            return False, error
        
        return True, ""
    
    def move(self, dx: float, dy: float):
        """Move the component by the given offset."""
        self.x += dx
        self.y += dy
    
    def move_to(self, x: float, y: float):
        """Move the component to the given position."""
        self.x = x
        self.y = y
    
    def rotate(self, angle: int = 90):
        """Rotate the component by the given angle (90 degree increments)."""
        self.rotation = (self.rotation + angle) % 360
    
    def flip_horizontal(self):
        """Flip the component horizontally."""
        self.mirror_h = not self.mirror_h
    
    def flip_vertical(self):
        """Flip the component vertically."""
        self.mirror_v = not self.mirror_v
    
    def get_bounding_box(self) -> tuple[float, float, float, float]:
        """Get the bounding box of the component (x_min, y_min, x_max, y_max)."""
        # Default bounding box based on symbol path
        x_min = y_min = float('inf')
        x_max = y_max = float('-inf')
        
        for cmd in self.symbol_path:
            if cmd[0] == 'line':
                _, x1, y1, x2, y2 = cmd
                x_min = min(x_min, x1, x2)
                x_max = max(x_max, x1, x2)
                y_min = min(y_min, y1, y2)
                y_max = max(y_max, y1, y2)
            elif cmd[0] == 'rect':
                _, x, y, w, h = cmd
                x_min = min(x_min, x)
                x_max = max(x_max, x + w)
                y_min = min(y_min, y)
                y_max = max(y_max, y + h)
            elif cmd[0] == 'circle':
                _, cx, cy, r = cmd
                x_min = min(x_min, cx - r)
                x_max = max(x_max, cx + r)
                y_min = min(y_min, cy - r)
                y_max = max(y_max, cy + r)
        
        # Add pin positions
        for pin in self._pins:
            x_min = min(x_min, pin.x_offset)
            x_max = max(x_max, pin.x_offset)
            y_min = min(y_min, pin.y_offset)
            y_max = max(y_max, pin.y_offset)
        
        # Transform to world coordinates
        return (
            self.x + x_min,
            self.y + y_min,
            self.x + x_max,
            self.y + y_max
        )
    
    def contains_point(self, x: float, y: float, margin: float = 5.0) -> bool:
        """Check if a point is within the component's bounding box."""
        x_min, y_min, x_max, y_max = self.get_bounding_box()
        return (x_min - margin <= x <= x_max + margin and
                y_min - margin <= y <= y_max + margin)
    
    @abstractmethod
    def get_spice_model(self) -> str:
        """Get the SPICE model/netlist line for this component."""
        pass
    
    def to_dict(self) -> dict:
        """Serialize component to dictionary."""
        return {
            'type': self.__class__.__name__,
            'id': self.id,
            'reference': self.reference,
            'x': self.x,
            'y': self.y,
            'rotation': self.rotation,
            'mirror_h': self.mirror_h,
            'mirror_v': self.mirror_v,
            'properties': {
                name: prop.value for name, prop in self._properties.items()
            },
            'pin_connections': {
                pin.name: pin.connected_net for pin in self._pins
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Component:
        """Deserialize component from dictionary."""
        component = cls()
        component.id = data['id']
        component.reference = data['reference']
        component.x = data['x']
        component.y = data['y']
        component.rotation = data['rotation']
        component.mirror_h = data['mirror_h']
        component.mirror_v = data['mirror_v']
        
        for name, value in data.get('properties', {}).items():
            component.set_property(name, value)
        
        for pin_name, net_name in data.get('pin_connections', {}).items():
            pin = component.get_pin(pin_name)
            if pin and net_name:
                pin.connect(net_name)
        
        return component
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.reference}, pos=({self.x}, {self.y}))"
