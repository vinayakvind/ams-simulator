"""
Schematic Editor - The main canvas for drawing circuits.
"""

from __future__ import annotations
import json
import math
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum, auto

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem,
    QGraphicsLineItem, QGraphicsRectItem, QGraphicsEllipseItem,
    QGraphicsTextItem, QGraphicsPathItem, QMenu, QApplication
)
from PyQt6.QtCore import (
    Qt, QPointF, QRectF, QLineF, pyqtSignal, QMimeData
)
from PyQt6.QtGui import (
    QPen, QBrush, QColor, QPainter, QPainterPath,
    QTransform, QFont, QKeyEvent, QMouseEvent, QWheelEvent
)

from simulator.components.base import Component, Pin, PinType, Point
from simulator.components.hierarchy import HierarchicalBlock


class EditorMode(Enum):
    """Editor interaction modes."""
    SELECT = auto()
    COMPONENT_PLACE = auto()
    WIRE_DRAW = auto()
    PAN = auto()


@dataclass
class Wire:
    """Represents a wire connection."""
    id: str
    points: List[QPointF] = field(default_factory=list)
    net_name: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'points': [(p.x(), p.y()) for p in self.points],
            'net_name': self.net_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> Wire:
        wire = cls(id=data['id'])
        wire.points = [QPointF(p[0], p[1]) for p in data['points']]
        wire.net_name = data.get('net_name')
        return wire


class ComponentGraphicsItem(QGraphicsItem):
    """Graphics item representing a circuit component."""
    
    def __init__(self, component: Component):
        super().__init__()
        self.component = component
        
        # Enable selection and movement
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        
        # Set position
        self.setPos(component.x, component.y)
        self.setRotation(component.rotation)
        
        # Visual properties
        self._pen = QPen(QColor("#333333"), 2)
        self._pen_selected = QPen(QColor("#0066cc"), 2)
        self._brush = QBrush(Qt.BrushStyle.NoBrush)
        self._pin_pen = QPen(QColor("#555555"), 1.5)
        self._pin_brush = QBrush(QColor("#ffffff"))
    
    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the component."""
        margin = 10
        x_min, y_min, x_max, y_max = -50, -50, 50, 50
        
        # Calculate from symbol path
        for cmd in self.component.symbol_path:
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
        
        # Include pins
        for pin in self.component.pins:
            x_min = min(x_min, pin.x_offset)
            x_max = max(x_max, pin.x_offset)
            y_min = min(y_min, pin.y_offset)
            y_max = max(y_max, pin.y_offset)
        
        return QRectF(x_min - margin, y_min - margin,
                      x_max - x_min + 2*margin, y_max - y_min + 2*margin)
    
    def paint(self, painter: QPainter, option, widget):
        """Paint the component."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set pen based on selection state
        if self.isSelected():
            painter.setPen(self._pen_selected)
        else:
            painter.setPen(self._pen)
        painter.setBrush(self._brush)
        
        # Apply mirroring
        transform = QTransform()
        if self.component.mirror_h:
            transform.scale(-1, 1)
        if self.component.mirror_v:
            transform.scale(1, -1)
        painter.setTransform(transform, True)
        
        # Draw symbol
        for cmd in self.component.symbol_path:
            self._draw_command(painter, cmd)
        
        # Draw pins
        for pin in self.component.pins:
            self._draw_pin_marker(painter, pin)
        
        # Draw reference designator
        painter.setPen(self._pen if not self.isSelected() else self._pen_selected)
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.drawText(QPointF(0, -40), self.component.reference)
    
    def _draw_command(self, painter: QPainter, cmd: tuple):
        """Draw a single symbol command."""
        if cmd[0] == 'line':
            _, x1, y1, x2, y2 = cmd
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        
        elif cmd[0] == 'rect':
            _, x, y, w, h = cmd
            painter.drawRect(QRectF(x, y, w, h))
        
        elif cmd[0] == 'circle':
            _, cx, cy, r = cmd
            painter.drawEllipse(QPointF(cx, cy), r, r)
        
        elif cmd[0] == 'arc':
            _, cx, cy, r, start, end = cmd
            rect = QRectF(cx - r, cy - r, 2*r, 2*r)
            painter.drawArc(rect, int(start * 16), int((end - start) * 16))
        
        elif cmd[0] == 'polygon':
            _, points = cmd
            path = QPainterPath()
            path.moveTo(points[0][0], points[0][1])
            for p in points[1:]:
                path.lineTo(p[0], p[1])
            path.closeSubpath()
            painter.drawPath(path)
        
        elif cmd[0] == 'text':
            _, x, y, text, size = cmd
            font = QFont("Arial", size)
            painter.setFont(font)
            painter.drawText(QPointF(x, y), text)

    @staticmethod
    def _pin_color(pin_type: PinType) -> QColor:
        """Return a stable color per pin type so hierarchy ports stay readable."""
        palette = {
            PinType.INPUT: QColor("#1f77b4"),
            PinType.OUTPUT: QColor("#ff7f0e"),
            PinType.BIDIRECTIONAL: QColor("#00a398"),
            PinType.POWER: QColor("#2ca02c"),
            PinType.GROUND: QColor("#444444"),
            PinType.ANALOG: QColor("#d62728"),
            PinType.DIGITAL: QColor("#7f7f7f"),
        }
        return palette.get(pin_type, QColor("#cc0000"))

    def _draw_pin_marker(self, painter: QPainter, pin: Pin) -> None:
        """Draw a pin marker whose shape and color reflect the pin role."""
        x = pin.x_offset
        y = pin.y_offset
        size = 5.0
        color = self._pin_color(pin.pin_type)
        fill = color if pin.is_connected else QColor("#ffffff")
        toward_body = 1 if x < 0 else -1

        painter.save()
        painter.setPen(QPen(color.darker(120), 1.5))
        painter.setBrush(QBrush(fill))

        if pin.pin_type in {PinType.INPUT, PinType.OUTPUT}:
            pointing_toward_body = pin.pin_type == PinType.INPUT
            tip_x = x + (toward_body * size if pointing_toward_body else -toward_body * size)
            base_x = x - (toward_body * size if pointing_toward_body else -toward_body * size)
            marker = QPainterPath()
            marker.moveTo(tip_x, y)
            marker.lineTo(base_x, y - size)
            marker.lineTo(base_x, y + size)
            marker.closeSubpath()
            painter.drawPath(marker)
        elif pin.pin_type == PinType.POWER:
            marker = QPainterPath()
            marker.moveTo(x, y - size)
            marker.lineTo(x + size, y)
            marker.lineTo(x, y + size)
            marker.lineTo(x - size, y)
            marker.closeSubpath()
            painter.drawPath(marker)
        elif pin.pin_type == PinType.GROUND:
            marker = QPainterPath()
            marker.moveTo(x - size, y - size / 2)
            marker.lineTo(x + size, y - size / 2)
            marker.lineTo(x, y + size)
            marker.closeSubpath()
            painter.drawPath(marker)
        elif pin.pin_type == PinType.DIGITAL:
            painter.drawRect(QRectF(x - size, y - size, size * 2, size * 2))
        elif pin.pin_type == PinType.BIDIRECTIONAL:
            painter.drawEllipse(QPointF(x, y), size, size)
            painter.drawLine(QPointF(x - size, y), QPointF(x + size, y))
        else:
            painter.drawEllipse(QPointF(x, y), size, size)

        painter.restore()
    
    def itemChange(self, change, value):
        """Handle item changes."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            # Update component position
            pos = value
            self.component.x = pos.x()
            self.component.y = pos.y()
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.component.selected = value
        return super().itemChange(change, value)


class WireGraphicsItem(QGraphicsPathItem):
    """Graphics item representing a wire."""
    
    def __init__(self, wire: Wire):
        super().__init__()
        self.wire = wire
        
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        
        self._pen = QPen(QColor("#006600"), 2)
        self._pen_selected = QPen(QColor("#00cc00"), 3)
        self.setPen(self._pen)
        
        self._update_path()
    
    def _update_path(self):
        """Update the path from wire points."""
        if len(self.wire.points) < 2:
            return
        
        path = QPainterPath()
        path.moveTo(self.wire.points[0])
        for point in self.wire.points[1:]:
            path.lineTo(point)
        self.setPath(path)
    
    def add_point(self, point: QPointF):
        """Add a point to the wire."""
        self.wire.points.append(point)
        self._update_path()
    
    def paint(self, painter: QPainter, option, widget):
        """Paint the wire."""
        if self.isSelected():
            self.setPen(self._pen_selected)
        else:
            self.setPen(self._pen)
        super().paint(painter, option, widget)
        
        # Draw junction dots at wire points
        painter.setBrush(QBrush(QColor("#006600")))
        for point in self.wire.points:
            painter.drawEllipse(point, 4, 4)


class SchematicEditor(QGraphicsView):
    """
    Schematic editor widget for drawing and editing circuits.
    """
    
    # Signals
    selection_changed = pyqtSignal(object)  # Component or None
    cursor_moved = pyqtSignal(float, float)
    zoom_changed = pyqtSignal(float)
    mode_changed = pyqtSignal(str)
    schematic_modified = pyqtSignal()
    hierarchy_descend_requested = pyqtSignal(object)
    hierarchy_ascend_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # Create scene
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-5000, -5000, 10000, 10000)
        self.setScene(self.scene)
        
        # Editor state
        self._mode = EditorMode.SELECT
        self._zoom = 1.0
        self._grid_size = 10
        self._grid_visible = True
        self._snap_to_grid = True
        
        # Data storage
        self._components: Dict[str, Component] = {}
        self._component_items: Dict[str, ComponentGraphicsItem] = {}
        self._wires: Dict[str, Wire] = {}
        self._wire_items: Dict[str, WireGraphicsItem] = {}
        self._net_counter = 0
        
        # Interaction state
        self._placing_component: Optional[Component] = None
        self._placing_item: Optional[ComponentGraphicsItem] = None
        self._drawing_wire: Optional[Wire] = None
        self._drawing_wire_item: Optional[WireGraphicsItem] = None
        self._last_mouse_pos = QPointF()
        self._pan_start = QPointF()
        
        # Undo/redo stacks
        self._undo_stack: List[dict] = []
        self._redo_stack: List[dict] = []
        
        # Clipboard
        self._clipboard: List[dict] = []
        
        # Auto-wire state
        self._auto_wire_enabled = True
        self._dragging_from_pin: Optional[tuple] = None  # (component_id, pin)
        self._auto_wire_preview: Optional[QGraphicsPathItem] = None

        # Hierarchy navigation state
        self._navigation_tab_name: str = ""
        self._navigation_parent_tab_name: Optional[str] = None
        self._navigation_root_tab_name: Optional[str] = None
        
        # Setup view
        self._setup_view()
        
        # Draw grid
        self._draw_grid()

    def configure_hierarchy_navigation(
        self,
        tab_name: str,
        parent_tab_name: Optional[str] = None,
        root_tab_name: Optional[str] = None,
    ) -> None:
        """Attach parent/root tab targets for right-click hierarchy navigation."""
        self._navigation_tab_name = tab_name
        self._navigation_parent_tab_name = parent_tab_name
        self._navigation_root_tab_name = root_tab_name or tab_name
    
    def _setup_view(self):
        """Setup view properties."""
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        
        # Background
        self.setBackgroundBrush(QBrush(QColor("#f5f5f5")))
    
    def _draw_grid(self):
        """Draw the background grid."""
        if not self._grid_visible:
            return
        
        # Grid is drawn in drawBackground
        self.viewport().update()
    
    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Draw the background with grid."""
        super().drawBackground(painter, rect)
        
        if not self._grid_visible:
            return
        
        # Calculate grid bounds
        left = int(rect.left()) - (int(rect.left()) % self._grid_size)
        top = int(rect.top()) - (int(rect.top()) % self._grid_size)
        
        # Draw minor grid
        painter.setPen(QPen(QColor("#e0e0e0"), 0.5))
        
        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += self._grid_size
        
        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += self._grid_size
        
        # Draw major grid (every 10 units)
        painter.setPen(QPen(QColor("#cccccc"), 1))
        major_grid = self._grid_size * 10
        
        left = int(rect.left()) - (int(rect.left()) % major_grid)
        top = int(rect.top()) - (int(rect.top()) % major_grid)
        
        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += major_grid
        
        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += major_grid
    
    def _snap_to_grid_point(self, point: QPointF) -> QPointF:
        """Snap a point to the grid."""
        if not self._snap_to_grid:
            return point
        
        x = round(point.x() / self._grid_size) * self._grid_size
        y = round(point.y() / self._grid_size) * self._grid_size
        return QPointF(x, y)
    
    # Component operations
    def start_component_placement(self, component_class: type):
        """Start placing a new component."""
        self._mode = EditorMode.COMPONENT_PLACE
        self.mode_changed.emit("Place Component")
        
        # Create component instance
        self._placing_component = component_class()
        self._placing_item = ComponentGraphicsItem(self._placing_component)
        self._placing_item.setOpacity(0.5)
        self.scene.addItem(self._placing_item)
        
        self.setCursor(Qt.CursorShape.CrossCursor)
    
    def _finish_component_placement(self, pos: QPointF):
        """Finish placing a component."""
        if self._placing_component is None:
            return
        
        # Save state for undo
        self._save_undo_state()
        
        # Snap to grid
        snapped = self._snap_to_grid_point(pos)
        
        # Update component position
        self._placing_component.x = snapped.x()
        self._placing_component.y = snapped.y()
        
        # Create final item
        final_item = ComponentGraphicsItem(self._placing_component)
        final_item.setPos(snapped)
        self.scene.addItem(final_item)
        
        # Store in data structures
        self._components[self._placing_component.id] = self._placing_component
        self._component_items[self._placing_component.id] = final_item
        
        # Remove preview item
        self.scene.removeItem(self._placing_item)
        
        # Reset placement state
        self._placing_component = None
        self._placing_item = None
        self._mode = EditorMode.SELECT
        self.mode_changed.emit("Select")
        self.setCursor(Qt.CursorShape.ArrowCursor)
        
        self.schematic_modified.emit()
    
    def add_component(self, component: Component):
        """Add an existing component to the schematic."""
        self._save_undo_state()
        
        item = ComponentGraphicsItem(component)
        item.setPos(component.x, component.y)
        self.scene.addItem(item)
        
        self._components[component.id] = component
        self._component_items[component.id] = item
        
        self.schematic_modified.emit()
    
    def remove_component(self, component_id: str):
        """Remove a component from the schematic."""
        if component_id not in self._components:
            return
        
        self._save_undo_state()
        
        # Remove from scene
        item = self._component_items[component_id]
        self.scene.removeItem(item)
        
        # Remove from data
        del self._components[component_id]
        del self._component_items[component_id]
        
        self.schematic_modified.emit()
    
    def update_component(self, component: Component):
        """Update a component's display after property changes."""
        if component.id in self._component_items:
            self._component_items[component.id].update()
    
    # Wire operations
    def _start_wire_draw(self, pos: QPointF):
        """Start drawing a wire."""
        self._mode = EditorMode.WIRE_DRAW
        self.mode_changed.emit("Draw Wire")
        
        import uuid
        self._drawing_wire = Wire(id=str(uuid.uuid4())[:8])
        self._drawing_wire.points.append(self._snap_to_grid_point(pos))
        
        self._drawing_wire_item = WireGraphicsItem(self._drawing_wire)
        self.scene.addItem(self._drawing_wire_item)
    
    def _continue_wire_draw(self, pos: QPointF):
        """Continue drawing a wire."""
        if self._drawing_wire is None:
            return
        
        snapped = self._snap_to_grid_point(pos)
        last_point = self._drawing_wire.points[-1]
        
        # Create orthogonal routing
        if abs(snapped.x() - last_point.x()) > abs(snapped.y() - last_point.y()):
            # Horizontal first
            mid_point = QPointF(snapped.x(), last_point.y())
        else:
            # Vertical first
            mid_point = QPointF(last_point.x(), snapped.y())
        
        if mid_point != last_point:
            self._drawing_wire_item.add_point(mid_point)
        if snapped != mid_point:
            self._drawing_wire_item.add_point(snapped)
    
    def _finish_wire_draw(self):
        """Finish drawing a wire."""
        if self._drawing_wire is None:
            return
        
        if len(self._drawing_wire.points) >= 2:
            self._save_undo_state()
            
            # Assign net name
            self._net_counter += 1
            self._drawing_wire.net_name = f"net{self._net_counter}"
            
            # Check for pin connections at endpoints
            self._connect_wire_to_pins(self._drawing_wire)
            
            # Store wire
            self._wires[self._drawing_wire.id] = self._drawing_wire
            self._wire_items[self._drawing_wire.id] = self._drawing_wire_item
            
            self.schematic_modified.emit()
        else:
            # Remove wire if too short
            self.scene.removeItem(self._drawing_wire_item)
        
        self._drawing_wire = None
        self._drawing_wire_item = None
        self._mode = EditorMode.SELECT
        self.mode_changed.emit("Select")
    
    def _connect_wire_to_pins(self, wire: Wire):
        """Connect wire endpoints to nearby pins."""
        if not wire.points:
            return
        
        start_point = wire.points[0]
        end_point = wire.points[-1]
        
        threshold = 15  # Distance threshold for auto-connection
        
        for comp_id, comp in self._components.items():
            for pin in comp.pins:
                # Calculate absolute pin position
                pin_pos = QPointF(comp.x + pin.x_offset, comp.y + pin.y_offset)
                
                # Check start point
                if self._distance(start_point, pin_pos) < threshold:
                    pin.connect(wire.net_name)
                
                # Check end point
                if self._distance(end_point, pin_pos) < threshold:
                    pin.connect(wire.net_name)
    
    def _distance(self, p1: QPointF, p2: QPointF) -> float:
        """Calculate distance between two points."""
        dx = p1.x() - p2.x()
        dy = p1.y() - p2.y()
        return (dx * dx + dy * dy) ** 0.5
    
    def _find_pin_at(self, pos: QPointF, threshold: float = 15) -> Optional[tuple]:
        """Find a pin at or near the given position. Returns (component_id, pin) or None."""
        for comp_id, comp in self._components.items():
            for pin in comp.pins:
                # Calculate absolute pin position (accounting for rotation)
                pin_pos = QPointF(comp.x + pin.x_offset, comp.y + pin.y_offset)
                if self._distance(pos, pin_pos) < threshold:
                    return (comp_id, pin, pin_pos)
        return None
    
    def _create_auto_wire(self, start_pos: QPointF, end_pos: QPointF):
        """Create an automatic orthogonal wire between two points."""
        import uuid
        
        wire = Wire(id=str(uuid.uuid4())[:8])
        
        # Start point
        wire.points.append(start_pos)
        
        # Create orthogonal routing
        mid_x = (start_pos.x() + end_pos.x()) / 2
        
        # Use L-shaped or Z-shaped routing
        if abs(end_pos.x() - start_pos.x()) > abs(end_pos.y() - start_pos.y()):
            # Horizontal first
            wire.points.append(QPointF(mid_x, start_pos.y()))
            wire.points.append(QPointF(mid_x, end_pos.y()))
        else:
            # Vertical first
            mid_y = (start_pos.y() + end_pos.y()) / 2
            wire.points.append(QPointF(start_pos.x(), mid_y))
            wire.points.append(QPointF(end_pos.x(), mid_y))
        
        # End point
        wire.points.append(end_pos)
        
        return wire
    
    def set_auto_wire_enabled(self, enabled: bool):
        """Enable or disable auto-wire feature."""
        self._auto_wire_enabled = enabled
    
    def _cancel_wire_draw(self):
        """Cancel current wire drawing."""
        if self._drawing_wire_item:
            self.scene.removeItem(self._drawing_wire_item)
        self._drawing_wire = None
        self._drawing_wire_item = None
        self._mode = EditorMode.SELECT
        self.mode_changed.emit("Select")
    
    # Selection operations
    def delete_selected(self):
        """Delete selected items."""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        self._save_undo_state()
        
        for item in selected:
            if isinstance(item, ComponentGraphicsItem):
                self.remove_component(item.component.id)
            elif isinstance(item, WireGraphicsItem):
                if item.wire.id in self._wires:
                    del self._wires[item.wire.id]
                    del self._wire_items[item.wire.id]
                self.scene.removeItem(item)
    
    def select_all(self):
        """Select all items."""
        for item in self.scene.items():
            if isinstance(item, (ComponentGraphicsItem, WireGraphicsItem)):
                item.setSelected(True)
    
    def rotate_selected(self, angle: int):
        """Rotate selected components."""
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentGraphicsItem):
                item.component.rotate(angle)
                item.setRotation(item.component.rotation)
                self.schematic_modified.emit()
    
    def flip_selected_horizontal(self):
        """Flip selected components horizontally."""
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentGraphicsItem):
                item.component.flip_horizontal()
                item.update()
                self.schematic_modified.emit()
    
    def flip_selected_vertical(self):
        """Flip selected components vertically."""
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentGraphicsItem):
                item.component.flip_vertical()
                item.update()
                self.schematic_modified.emit()
    
    # Undo/Redo
    def _save_undo_state(self):
        """Save current state to undo stack."""
        state = self._serialize_state()
        self._undo_stack.append(state)
        self._redo_stack.clear()
        
        # Limit undo stack size
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
    
    def _serialize_state(self) -> dict:
        """Serialize current state."""
        return {
            'components': {
                cid: comp.to_dict() 
                for cid, comp in self._components.items()
            },
            'wires': {
                wid: wire.to_dict()
                for wid, wire in self._wires.items()
            }
        }
    
    def undo(self):
        """Undo last action."""
        if not self._undo_stack:
            return
        
        # Save current state to redo
        self._redo_stack.append(self._serialize_state())
        
        # Restore previous state
        state = self._undo_stack.pop()
        self._restore_state(state)
    
    def redo(self):
        """Redo last undone action."""
        if not self._redo_stack:
            return
        
        # Save current state to undo
        self._undo_stack.append(self._serialize_state())
        
        # Restore redo state
        state = self._redo_stack.pop()
        self._restore_state(state)
    
    def _restore_state(self, state: dict):
        """Restore state from serialized data."""
        # Clear current items
        for item in list(self._component_items.values()):
            self.scene.removeItem(item)
        for item in list(self._wire_items.values()):
            self.scene.removeItem(item)
        
        self._components.clear()
        self._component_items.clear()
        self._wires.clear()
        self._wire_items.clear()
        
        # Restore components
        from simulator.gui.component_library import COMPONENT_REGISTRY
        for cid, cdata in state.get('components', {}).items():
            comp_class = COMPONENT_REGISTRY.get(cdata['type'])
            if comp_class:
                comp = comp_class.from_dict(cdata)
                self.add_component(comp)
        
        # Restore wires
        for wid, wdata in state.get('wires', {}).items():
            wire = Wire.from_dict(wdata)
            wire_item = WireGraphicsItem(wire)
            self.scene.addItem(wire_item)
            self._wires[wire.id] = wire
            self._wire_items[wire.id] = wire_item
    
    # Clipboard
    def cut(self):
        """Cut selected items."""
        self.copy()
        self.delete_selected()
    
    def copy(self):
        """Copy selected items."""
        self._clipboard.clear()
        for item in self.scene.selectedItems():
            if isinstance(item, ComponentGraphicsItem):
                self._clipboard.append({
                    'type': 'component',
                    'data': item.component.to_dict()
                })
            elif isinstance(item, WireGraphicsItem):
                self._clipboard.append({
                    'type': 'wire',
                    'data': item.wire.to_dict()
                })
    
    def paste(self):
        """Paste from clipboard."""
        if not self._clipboard:
            return
        
        self._save_undo_state()
        
        # Deselect all
        for item in self.scene.selectedItems():
            item.setSelected(False)
        
        # Offset for pasted items
        offset = QPointF(20, 20)
        
        from simulator.components import COMPONENT_REGISTRY
        for clip_item in self._clipboard:
            if clip_item['type'] == 'component':
                data = clip_item['data'].copy()
                comp_class = COMPONENT_REGISTRY.get(data['type'])
                if comp_class:
                    # Generate new ID
                    import uuid
                    data['id'] = str(uuid.uuid4())
                    data['x'] += offset.x()
                    data['y'] += offset.y()
                    
                    comp = comp_class.from_dict(data)
                    self.add_component(comp)
                    self._component_items[comp.id].setSelected(True)
    
    # Zoom operations
    def zoom_in(self):
        """Zoom in."""
        self._zoom *= 1.25
        self.setTransform(QTransform().scale(self._zoom, self._zoom))
        self.zoom_changed.emit(self._zoom)
    
    def zoom_out(self):
        """Zoom out."""
        self._zoom *= 0.8
        self.setTransform(QTransform().scale(self._zoom, self._zoom))
        self.zoom_changed.emit(self._zoom)
    
    def zoom_fit(self):
        """Fit all items in view."""
        items_rect = self.scene.itemsBoundingRect()
        if items_rect.isEmpty():
            return
        self.fitInView(items_rect, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)
    
    def set_grid_visible(self, visible: bool):
        """Set grid visibility."""
        self._grid_visible = visible
        self.viewport().update()
    
    # Mouse events
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        scene_pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.MouseButton.LeftButton:
            if self._mode == EditorMode.COMPONENT_PLACE:
                self._finish_component_placement(scene_pos)
            elif self._mode == EditorMode.WIRE_DRAW:
                self._continue_wire_draw(scene_pos)
            else:
                # Check if clicking on a pin for auto-wire
                if self._auto_wire_enabled:
                    pin_info = self._find_pin_at(scene_pos)
                    if pin_info:
                        self._dragging_from_pin = pin_info
                        self._start_wire_draw(pin_info[2])  # Start from pin position
                        return
                
                # Check if starting wire with Ctrl
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self._start_wire_draw(scene_pos)
                else:
                    super().mousePressEvent(event)
        
        elif event.button() == Qt.MouseButton.RightButton:
            if self._mode == EditorMode.COMPONENT_PLACE:
                # Cancel placement
                if self._placing_item:
                    self.scene.removeItem(self._placing_item)
                self._placing_component = None
                self._placing_item = None
                self._mode = EditorMode.SELECT
                self.mode_changed.emit("Select")
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._mode == EditorMode.WIRE_DRAW:
                self._finish_wire_draw()
                self._dragging_from_pin = None
            else:
                # Context menu
                self._show_context_menu(event.pos())
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._mode = EditorMode.PAN
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        scene_pos = self.mapToScene(event.pos())
        self._last_mouse_pos = scene_pos
        
        # Emit cursor position
        self.cursor_moved.emit(scene_pos.x(), scene_pos.y())
        
        if self._mode == EditorMode.COMPONENT_PLACE and self._placing_item:
            snapped = self._snap_to_grid_point(scene_pos)
            self._placing_item.setPos(snapped)
        
        elif self._mode == EditorMode.WIRE_DRAW and self._drawing_wire_item:
            # Update wire preview to mouse position
            if self._auto_wire_preview:
                self.scene.removeItem(self._auto_wire_preview)
                self._auto_wire_preview = None
            
            # Check if hovering over a pin
            target_pin = self._find_pin_at(scene_pos)
            
            # Draw preview wire to target
            if self._drawing_wire and len(self._drawing_wire.points) > 0:
                preview_path = QPainterPath()
                start = self._drawing_wire.points[0]
                preview_path.moveTo(start)
                
                snapped = self._snap_to_grid_point(scene_pos)
                if target_pin:
                    snapped = target_pin[2]  # Snap to pin position
                
                # Orthogonal routing preview
                last_point = self._drawing_wire.points[-1] if len(self._drawing_wire.points) > 1 else start
                if abs(snapped.x() - last_point.x()) > abs(snapped.y() - last_point.y()):
                    mid_point = QPointF(snapped.x(), last_point.y())
                else:
                    mid_point = QPointF(last_point.x(), snapped.y())
                
                preview_path.lineTo(mid_point)
                preview_path.lineTo(snapped)
                
                self._auto_wire_preview = QGraphicsPathItem(preview_path)
                pen = QPen(QColor("#00aa00" if target_pin else "#888888"), 2, Qt.PenStyle.DashLine)
                self._auto_wire_preview.setPen(pen)
                self.scene.addItem(self._auto_wire_preview)
        
        elif self._mode == EditorMode.PAN:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        scene_pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.MouseButton.LeftButton:
            # Check for auto-wire completion
            if self._mode == EditorMode.WIRE_DRAW and self._dragging_from_pin:
                target_pin = self._find_pin_at(scene_pos)
                if target_pin and target_pin[0] != self._dragging_from_pin[0]:
                    # Connect to target pin - finish wire at pin position
                    self._continue_wire_draw(target_pin[2])
                    self._finish_wire_draw()
                    
                    # Connect both pins to the wire
                    if self._wires:
                        last_wire = list(self._wires.values())[-1]
                        self._dragging_from_pin[1].connect(last_wire.net_name)
                        target_pin[1].connect(last_wire.net_name)
                
                self._dragging_from_pin = None
                
                # Remove preview
                if self._auto_wire_preview:
                    self.scene.removeItem(self._auto_wire_preview)
                    self._auto_wire_preview = None
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            self._mode = EditorMode.SELECT
            self.mode_changed.emit("Select")
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)
        
        # Update selection
        selected = self.scene.selectedItems()
        if selected and isinstance(selected[0], ComponentGraphicsItem):
            self.selection_changed.emit(selected[0].component)
        else:
            self.selection_changed.emit(None)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Handle double click."""
        scene_pos = self.mapToScene(event.pos())
        item = self.scene.itemAt(scene_pos, QTransform())
        
        if isinstance(item, ComponentGraphicsItem):
            # Edit component properties
            self.selection_changed.emit(item.component)
        
        super().mouseDoubleClickEvent(event)
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            super().wheelEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press."""
        if event.key() == Qt.Key.Key_Escape:
            if self._mode == EditorMode.COMPONENT_PLACE:
                if self._placing_item:
                    self.scene.removeItem(self._placing_item)
                self._placing_component = None
                self._placing_item = None
                self._mode = EditorMode.SELECT
                self.mode_changed.emit("Select")
                self.setCursor(Qt.CursorShape.ArrowCursor)
            elif self._mode == EditorMode.WIRE_DRAW:
                self._cancel_wire_draw()
        
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        
        elif event.key() == Qt.Key.Key_R:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.rotate_selected(-90)
            else:
                self.rotate_selected(90)
        
        elif event.key() == Qt.Key.Key_H:
            self.flip_selected_horizontal()
        
        elif event.key() == Qt.Key.Key_V:
            self.flip_selected_vertical()
        
        elif event.key() == Qt.Key.Key_W:
            # Start wire mode
            self._start_wire_draw(self._last_mouse_pos)
        
        else:
            super().keyPressEvent(event)
    
    def _show_context_menu(self, pos):
        """Show context menu."""
        menu = QMenu(self)

        component_item = self._component_item_at_view_pos(pos)
        if component_item and not component_item.isSelected():
            for selected_item in self.scene.selectedItems():
                selected_item.setSelected(False)
            component_item.setSelected(True)
            self.selection_changed.emit(component_item.component)

        if component_item and isinstance(component_item.component, HierarchicalBlock):
            block_name = component_item.component.display_name
            action_label = f"Descend Into {block_name}"
            if component_item.component.domain == "DIGITAL":
                action_label = f"Descend Into {block_name} / Open RTL Source"
            menu.addAction(
                action_label,
                lambda comp=component_item.component: self.hierarchy_descend_requested.emit(comp),
            )

        if self._navigation_parent_tab_name:
            target_label = "Ascend To Parent"
            if self._navigation_root_tab_name == self._navigation_parent_tab_name:
                target_label = "Ascend To Top Level"
            menu.addAction(target_label, self.hierarchy_ascend_requested.emit)

        if component_item or self._navigation_parent_tab_name:
            menu.addSeparator()
        
        menu.addAction("Cut", self.cut)
        menu.addAction("Copy", self.copy)
        menu.addAction("Paste", self.paste)
        menu.addSeparator()
        menu.addAction("Delete", self.delete_selected)
        menu.addSeparator()
        menu.addAction("Rotate CW", lambda: self.rotate_selected(90))
        menu.addAction("Rotate CCW", lambda: self.rotate_selected(-90))
        menu.addAction("Flip Horizontal", self.flip_selected_horizontal)
        menu.addAction("Flip Vertical", self.flip_selected_vertical)
        
        menu.exec(self.mapToGlobal(pos))

    def _component_item_at_view_pos(self, pos) -> Optional[ComponentGraphicsItem]:
        """Return the component item under a viewport position, if any."""
        scene_pos = self.mapToScene(pos)
        item = self.scene.itemAt(scene_pos, QTransform())
        while item is not None and not isinstance(item, ComponentGraphicsItem):
            item = item.parentItem()
        if isinstance(item, ComponentGraphicsItem):
            return item
        return None
    
    # Netlist generation
    # Default SPICE .MODEL definitions for NgSpice compatibility
    _DEFAULT_MODELS: dict[str, str] = {
        'NMOS_DEFAULT': '.MODEL NMOS_DEFAULT NMOS (VTO=0.4 KP=120u LAMBDA=0.01)',
        'PMOS_DEFAULT': '.MODEL PMOS_DEFAULT PMOS (VTO=-0.4 KP=40u LAMBDA=0.01)',
        'PMOS_BUCK': '.MODEL PMOS_BUCK PMOS (VTO=-0.7 KP=80u LAMBDA=0.02)',
        'NPN_DEFAULT': '.MODEL NPN_DEFAULT NPN (BF=100 IS=1e-14 VAF=100)',
        'PNP_DEFAULT': '.MODEL PNP_DEFAULT PNP (BF=100 IS=1e-14 VAF=100)',
        'D1N4148': '.MODEL D1N4148 D (IS=2.52e-9 N=1.752 BV=100 RS=0.568)',
        'BZX79C5V1': '.MODEL BZX79C5V1 D (IS=1e-14 BV=5.1 IBV=5e-3 RS=10)',
        'DFAST': '.MODEL DFAST D (IS=1e-14 N=1.0 BV=100 RS=0.1)',
    }

    def generate_netlist(self) -> str:
        """Generate SPICE netlist from the schematic.
        
        Includes .MODEL definitions for any transistor/diode models
        referenced by components so the netlist is self-contained and
        works with external simulators like NgSpice.
        """
        lines: list[str] = []
        lines.append("* AMS Simulator Netlist")
        lines.append("* Generated automatically")
        lines.append("")
        
        # Collect model names that need definitions
        referenced_models: set[str] = set()
        
        # Components
        for comp in self._components.values():
            spice_line = comp.get_spice_model()
            if spice_line:
                lines.append(spice_line)
            # Collect model names from transistors and diodes
            if hasattr(comp, '_properties') and 'model' in comp._properties:
                model_name = comp._properties['model'].value
                if model_name:
                    referenced_models.add(model_name.upper())
        
        # Emit .MODEL definitions for referenced models
        if referenced_models:
            lines.append("")
            lines.append("* Model definitions")
            for model_name in sorted(referenced_models):
                # Use built-in default if available
                model_upper = model_name.upper()
                if model_upper in self._DEFAULT_MODELS:
                    lines.append(self._DEFAULT_MODELS[model_upper])
                else:
                    # Try to guess type from element prefix in the netlist
                    # NMOS/PMOS if referenced by M-line, NPN/PNP by Q-line, D by D-line
                    for comp in self._components.values():
                        if (hasattr(comp, '_properties')
                                and 'model' in comp._properties
                                and comp._properties['model'].value.upper() == model_upper):
                            ctype = type(comp).__name__
                            if ctype == 'NMOS':
                                lines.append(f".MODEL {model_name} NMOS (VTO=0.7 KP=110u LAMBDA=0.04)")
                            elif ctype == 'PMOS':
                                lines.append(f".MODEL {model_name} PMOS (VTO=-0.7 KP=40u LAMBDA=0.05)")
                            elif ctype == 'NPN':
                                lines.append(f".MODEL {model_name} NPN (BF=100 IS=1e-14 VAF=100)")
                            elif ctype == 'PNP':
                                lines.append(f".MODEL {model_name} PNP (BF=100 IS=1e-14 VAF=100)")
                            elif ctype in ('Diode', 'Zener', 'LED'):
                                lines.append(f".MODEL {model_name} D (IS=1e-14 N=1.0 BV=100 RS=0.1)")
                            break
        
        lines.append("")
        lines.append(".END")
        
        return "\n".join(lines)
    
    # File operations
    def save_to_file(self, filename: str):
        """Save schematic to file."""
        state = self._serialize_state()
        with open(filename, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_from_file(self, filename: str):
        """Load schematic from file."""
        with open(filename, 'r') as f:
            state = json.load(f)
        self._restore_state(state)
    
    def load_from_netlist(self, netlist_text: str, preserve_hierarchy: bool = False):
        """Parse a SPICE netlist and create visual schematic components.
        
        Maps SPICE element prefixes to component classes and places them
        with auto-layout on the canvas. Wires are created to represent 
        net connections between pins.
        
        Args:
            netlist_text: SPICE netlist content as a string.
            preserve_hierarchy: When True, keep X-subcircuit instances as
                symbolic hierarchical blocks instead of flattening them.
        """
        import re
        from simulator.components.passive import Resistor, Capacitor, Inductor
        from simulator.components.transistors import NMOS, PMOS, NPN, PNP
        from simulator.components.sources import (
            VoltageSource, CurrentSource, PulseSource, SineSource, Ground
        )
        from simulator.components.diodes import Diode
        
        # Clear current schematic
        for item in list(self._component_items.values()):
            self.scene.removeItem(item)
        for item in list(self._wire_items.values()):
            self.scene.removeItem(item)
        self._components.clear()
        self._component_items.clear()
        self._wires.clear()
        self._wire_items.clear()
        
        # Reset reference counters for clean loading
        from simulator.components.base import Component
        Component.reset_counters()
        
        # SPICE prefix -> component class mapping
        prefix_map = {
            'R': Resistor,
            'C': Capacitor,
            'L': Inductor,
            'V': VoltageSource,  # Will specialize for PULSE/SIN
            'I': CurrentSource,
            'E': VoltageSource,  # VCVS displayed as voltage source
            'G': CurrentSource,  # VCCS displayed as current source
            'M': NMOS,           # Will check for PMOS model
            'Q': NPN,            # Will check for PNP model
            'D': Diode,
        }
        
        lines = netlist_text.strip().split('\n')

        # ── Phase 1: Collect .SUBCKT definitions ──
        subcircuits: dict[str, tuple[list[str], list[str]]] = {}
        _in_subckt = False
        _subckt_name = ''
        _subckt_ports: list[str] = []
        _subckt_body: list[str] = []
        element_lines: list[str] = []

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith('*'):
                continue
            upper = stripped.upper()

            if upper.startswith('.SUBCKT'):
                toks = stripped.split()
                _subckt_name = toks[1] if len(toks) > 1 else ''
                _subckt_ports = toks[2:]
                _subckt_body = []
                _in_subckt = True
                continue
            if upper.startswith('.ENDS'):
                if _in_subckt and _subckt_name:
                    subcircuits[_subckt_name] = (_subckt_ports, _subckt_body)
                _in_subckt = False
                continue
            if _in_subckt:
                if not stripped.startswith('.'):
                    _subckt_body.append(stripped)
                continue
            if stripped.startswith('.'):
                continue
            element_lines.append(stripped)

        # ── Phase 1.5: For pure-SUBCKT files (block hierarchy view) ──
        # When the file contains only .SUBCKT/.ENDS definitions with no top-level
        # element lines (e.g. a block cell file), flatten the first SUBCKT body so
        # the schematic editor can render the internal circuit.
        if not element_lines and subcircuits:
            _, first_body = next(iter(subcircuits.values()))
            element_lines = [ln for ln in first_body if not ln.strip().startswith('.')]

        # ── Phase 1.6: Preserve hierarchy for top-level ASIC views ──
        if preserve_hierarchy:
            symbolic_instances = []
            for eline in element_lines:
                toks = eline.split()
                if not toks or toks[0][0].upper() != 'X' or len(toks) < 3:
                    continue
                subckt_ref = toks[-1]
                ports = subcircuits.get(subckt_ref, (toks[1:-1], []))[0]
                symbolic_instances.append({
                    'instance_name': toks[0],
                    'block_name': subckt_ref,
                    'ports': ports or [f'P{i + 1}' for i in range(len(toks) - 2)],
                    'nets': toks[1:-1],
                    'domain': self._guess_block_domain(subckt_ref),
                })
            if symbolic_instances:
                self._render_symbolic_blocks(symbolic_instances, grouped_layout=True)
                return

        # ── Phase 2: Expand X_ subcircuit instances inline ──
        expanded_lines: list[str] = []
        for eline in element_lines:
            toks = eline.split()
            if not toks:
                continue
            if toks[0][0].upper() == 'X' and len(toks) >= 3:
                subckt_ref = toks[-1]
                port_nets = toks[1:-1]
                if subckt_ref in subcircuits:
                    sub_ports, sub_body = subcircuits[subckt_ref]
                    net_map: dict[str, str] = {}
                    for mi, sp in enumerate(sub_ports):
                        if mi < len(port_nets):
                            net_map[sp] = port_nets[mi]
                    inst_prefix = toks[0][2:] if toks[0].startswith('X_') else toks[0][1:]
                    for sub_line in sub_body:
                        exp = self._expand_subckt_line(sub_line, inst_prefix, net_map)
                        if exp:
                            expanded_lines.append(exp)
                    continue
            expanded_lines.append(eline)

        # ── Phase 3: Parse element lines into components ──
        parsed_elements = []
        net_connections: dict = {}

        for line in expanded_lines:
            tokens = line.split()
            if not tokens:
                continue

            ref = tokens[0]
            prefix = ref[0].upper()

            if prefix not in prefix_map:
                continue

            comp_class = prefix_map[prefix]
            nets = []
            value_str = None

            try:
                if prefix in ('R', 'C', 'L'):
                    # R/C/L name node1 node2 value [params]
                    if len(tokens) >= 4:
                        nets = [tokens[1], tokens[2]]
                        value_str = tokens[3]

                elif prefix == 'V':
                    # V name node+ node- [DC val] [AC mag [phase]] [PULSE(...)] [SIN(...)]
                    if len(tokens) >= 3:
                        nets = [tokens[1], tokens[2]]
                        rest = ' '.join(tokens[3:])
                        if 'PULSE' in rest.upper():
                            comp_class = PulseSource
                        elif 'SIN' in rest.upper():
                            comp_class = SineSource
                        dc_match = re.search(r'(?:DC\s+)?([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*V?', rest, re.I)
                        if dc_match:
                            value_str = dc_match.group(1)

                elif prefix == 'I':
                    # I name node+ node- value
                    if len(tokens) >= 4:
                        nets = [tokens[1], tokens[2]]
                        value_str = tokens[3]

                elif prefix == 'E':
                    # VCVS: E name out+ out- [VCVS] ctl+ ctl- gain
                    if len(tokens) >= 3:
                        nets = [tokens[1], tokens[2]]
                        value_str = tokens[-1] if len(tokens) > 3 else None

                elif prefix == 'G':
                    # VCCS: G name out+ out- ctl+ ctl- transconductance
                    if len(tokens) >= 3:
                        nets = [tokens[1], tokens[2]]
                        value_str = tokens[-1] if len(tokens) > 3 else None

                elif prefix == 'M':
                    # M name drain gate source bulk model [W=... L=...]
                    if len(tokens) >= 6:
                        nets = [tokens[1], tokens[2], tokens[3], tokens[4]]
                        model_name = tokens[5] if len(tokens) > 5 else ''
                        if 'PMOS' in model_name.upper():
                            comp_class = PMOS

                elif prefix == 'Q':
                    # Q name collector base emitter model
                    if len(tokens) >= 5:
                        nets = [tokens[1], tokens[2], tokens[3]]
                        model_name = tokens[4] if len(tokens) > 4 else ''
                        if 'PNP' in model_name.upper():
                            comp_class = PNP

                elif prefix == 'D':
                    # D name anode cathode model
                    if len(tokens) >= 3:
                        nets = [tokens[1], tokens[2]]

            except (IndexError, ValueError):
                continue

            if not nets:
                continue

            parsed_elements.append({
                'ref': ref,
                'comp_class': comp_class,
                'nets': nets,
                'value_str': value_str,
                'line': line,
            })

            # Track net connections
            elem_idx = len(parsed_elements) - 1
            for pin_idx, net_name in enumerate(nets):
                if net_name not in net_connections:
                    net_connections[net_name] = []
                net_connections[net_name].append((elem_idx, pin_idx))
        
        if not parsed_elements:
            if subcircuits:
                subckt_name, (ports, _) = next(iter(subcircuits.items()))
                self._render_symbolic_blocks([
                    {
                        'instance_name': subckt_name,
                        'block_name': subckt_name,
                        'ports': ports,
                        'nets': ports,
                        'domain': self._guess_block_domain(subckt_name),
                    }
                ])
            return
        
        self._render_parsed_elements(parsed_elements, net_connections)

    def _render_parsed_elements(self, parsed_elements: list[dict], net_connections: dict):
        """Render parsed primitive elements using the existing grid layout."""
        from simulator.components.sources import Ground

        grid_spacing_x = 200
        grid_spacing_y = 180
        cols = max(3, int(len(parsed_elements) ** 0.5) + 1)
        start_x = -((cols - 1) * grid_spacing_x) / 2
        start_y = -((len(parsed_elements) // cols) * grid_spacing_y) / 2

        created_components = []
        for i, elem in enumerate(parsed_elements):
            comp = elem['comp_class']()
            comp.reference = elem['ref']

            if elem['value_str'] is not None:
                val = self._parse_spice_value(elem['value_str'])
                if val is not None:
                    prop_map = {
                        'Resistor': 'resistance',
                        'Capacitor': 'capacitance',
                        'Inductor': 'inductance',
                        'VoltageSource': 'voltage',
                        'CurrentSource': 'current',
                        'PulseSource': 'voltage',
                        'SineSource': 'voltage',
                    }
                    prop_name = prop_map.get(comp.__class__.__name__)
                    if prop_name and prop_name in comp.properties:
                        comp.set_property(prop_name, val)

            row = i // cols
            col = i % cols
            comp.x = start_x + col * grid_spacing_x
            comp.y = start_y + row * grid_spacing_y

            for pin_idx, net_name in enumerate(elem['nets']):
                if pin_idx < len(comp.pins):
                    comp.pins[pin_idx].connect(net_name)

            item = ComponentGraphicsItem(comp)
            item.setPos(comp.x, comp.y)
            self.scene.addItem(item)
            self._components[comp.id] = comp
            self._component_items[comp.id] = item
            created_components.append(comp)

        self._render_net_wires(created_components, net_connections)

        if '0' in net_connections:
            gnd = Ground()
            gnd.x = 0
            gnd.y = start_y + ((len(parsed_elements) // cols) + 1) * grid_spacing_y
            gnd.pins[0].connect('0')

            gnd_item = ComponentGraphicsItem(gnd)
            gnd_item.setPos(gnd.x, gnd.y)
            self.scene.addItem(gnd_item)
            self._components[gnd.id] = gnd
            self._component_items[gnd.id] = gnd_item

        self.zoom_fit()
        self.schematic_modified.emit()

    def _render_symbolic_blocks(self, symbolic_instances: list[dict], grouped_layout: bool = False):
        """Render hierarchical instances as symbolic block components."""
        domain_columns = {'ANALOG': -320, 'MIXED': 0, 'DIGITAL': 320}
        domain_counters = {'ANALOG': 0, 'MIXED': 0, 'DIGITAL': 0}
        created_components = []
        net_connections: dict[str, list[tuple[int, int]]] = {}

        for i, inst in enumerate(symbolic_instances):
            domain = (inst.get('domain') or 'MIXED').upper()
            if grouped_layout:
                x_pos = domain_columns.get(domain, 0)
                y_pos = -220 + domain_counters.get(domain, 0) * 150
                domain_counters[domain] = domain_counters.get(domain, 0) + 1
            else:
                cols = max(1, int(len(symbolic_instances) ** 0.5) + 1)
                row = i // cols
                col = i % cols
                x_pos = -((cols - 1) * 240) / 2 + col * 240
                y_pos = -((len(symbolic_instances) // cols) * 160) / 2 + row * 160

            display_name = inst['block_name'].replace('_', ' ').title()
            comp = HierarchicalBlock(
                block_name=display_name,
                ports=inst['ports'],
                domain=domain,
                instance_name=inst.get('instance_name', inst['block_name']),
                model_name=inst['block_name'],
            )
            comp.x = x_pos
            comp.y = y_pos

            for pin_idx, net_name in enumerate(inst.get('nets', [])):
                if pin_idx < len(comp.pins):
                    comp.pins[pin_idx].connect(net_name)
                    if net_name not in net_connections:
                        net_connections[net_name] = []
                    net_connections[net_name].append((len(created_components), pin_idx))

            item = ComponentGraphicsItem(comp)
            item.setPos(comp.x, comp.y)
            self.scene.addItem(item)
            self._components[comp.id] = comp
            self._component_items[comp.id] = item
            created_components.append(comp)

        self._render_net_wires(created_components, net_connections)
        self.zoom_fit()
        self.schematic_modified.emit()

    def _render_net_wires(self, created_components: list[Component], net_connections: dict):
        """Render orthogonal wires between components sharing the same net."""
        import uuid

        for net_name, connections in net_connections.items():
            if net_name == '0' or len(connections) < 2:
                continue

            first_elem_idx, first_pin_idx = connections[0]
            first_comp = created_components[first_elem_idx]
            if first_pin_idx >= len(first_comp.pins):
                continue

            first_pin = first_comp.pins[first_pin_idx]
            start_pos = QPointF(
                first_comp.x + first_pin.x_offset,
                first_comp.y + first_pin.y_offset,
            )

            for conn_elem_idx, conn_pin_idx in connections[1:]:
                other_comp = created_components[conn_elem_idx]
                if conn_pin_idx >= len(other_comp.pins):
                    continue

                other_pin = other_comp.pins[conn_pin_idx]
                end_pos = QPointF(
                    other_comp.x + other_pin.x_offset,
                    other_comp.y + other_pin.y_offset,
                )

                wire = Wire(id=str(uuid.uuid4())[:8])
                wire.net_name = net_name
                wire.points.append(start_pos)
                mid_point = QPointF(end_pos.x(), start_pos.y())
                if mid_point != start_pos:
                    wire.points.append(mid_point)
                wire.points.append(end_pos)

                wire_item = WireGraphicsItem(wire)
                self.scene.addItem(wire_item)
                self._wires[wire.id] = wire
                self._wire_items[wire.id] = wire_item

    @staticmethod
    def _guess_block_domain(name: str) -> str:
        """Best-effort analog/digital/mixed classification from block name."""
        upper = name.upper()
        if any(token in upper for token in ('SPI', 'REGISTER', 'CONTROLLER', 'LOGIC')):
            return 'DIGITAL'
        if any(token in upper for token in ('LDO', 'BANDGAP', 'REF')):
            return 'ANALOG'
        if 'TRANSCEIVER' in upper:
            return 'MIXED'
        return 'MIXED'
    
    @staticmethod
    def _parse_spice_value(value_str: str) -> float | None:
        """Parse a SPICE value string with engineering suffixes.
        
        Supports standard SPICE suffixes: T, G, MEG, K, M, U, N, P, F.
        
        Args:
            value_str: String like '100u', '1.5k', '10MEG', '5V'.
            
        Returns:
            Float value or None if parsing fails.
        """
        import re
        value_str = value_str.strip().upper()
        
        # Remove trailing unit letters like V, A, H, F, OHM etc.
        value_str = re.sub(r'(OHM|OHMS|VOLT|VOLTS|AMP|AMPS|HENRY|FARAD)S?$', '', value_str, flags=re.I)
        
        suffixes = {
            'T': 1e12, 'G': 1e9, 'MEG': 1e6, 'K': 1e3,
            'M': 1e-3, 'MIL': 25.4e-6, 'U': 1e-6,
            'N': 1e-9, 'P': 1e-12, 'F': 1e-15,
        }
        
        # Try matching number + suffix
        match = re.match(r'^([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)\s*(MEG|MIL|[TGKMNUPF])?(.*)$', value_str, re.I)
        if match:
            try:
                num = float(match.group(1))
                suffix = (match.group(2) or '').upper()
                multiplier = suffixes.get(suffix, 1.0)
                return num * multiplier
            except ValueError:
                return None
        return None

    def _expand_subckt_line(
        self, line: str, prefix: str, net_map: dict[str, str]
    ) -> str:
        """Expand a .SUBCKT body line with prefixed refs and remapped nets.

        Used by load_from_netlist() to inline subcircuit instances. Component
        reference designators are prefixed with the instance name, port nets
        are remapped to top-level connections, and internal nets are prefixed
        to avoid collisions.

        Args:
            line: A SPICE element line from inside a .SUBCKT body.
            prefix: Instance prefix for unique naming.
            net_map: Mapping from subcircuit port names to top-level nets.

        Returns:
            Expanded line string, or empty string if unparseable.
        """
        tokens = line.split()
        if not tokens:
            return ''

        ref = tokens[0]
        first_char = ref[0].upper()

        new_ref = f"{ref[0]}_{prefix}_{ref[1:]}" if len(ref) > 1 else f"{ref[0]}_{prefix}"

        # Determine which token positions (1-indexed) contain net names
        net_positions: set[int] = set()
        if first_char in ('R', 'C', 'L', 'D'):
            net_positions = {1, 2}
        elif first_char in ('V', 'I'):
            net_positions = {1, 2}
        elif first_char == 'M':
            net_positions = {1, 2, 3, 4}
        elif first_char == 'Q':
            net_positions = {1, 2, 3}
        elif first_char in ('E', 'G'):
            net_positions = {1, 2}
            if len(tokens) > 3 and tokens[3].upper() in ('VCVS', 'VCCS', 'POLY'):
                net_positions.update({4, 5})
            else:
                net_positions.update({3, 4})
        else:
            return line  # Unknown prefix, pass through

        result = [new_ref]
        for i in range(1, len(tokens)):
            tok = tokens[i]
            if i in net_positions:
                if tok in net_map:
                    result.append(net_map[tok])
                elif tok == '0' or tok.lower() == 'gnd':
                    result.append(tok)
                else:
                    result.append(f"{prefix}_{tok}")
            else:
                result.append(tok)

        return ' '.join(result)

    def export_image(self, filename: str):
        """Export schematic as image."""
        from PyQt6.QtGui import QImage, QPainter
        from PyQt6.QtCore import QRectF
        
        # Get bounding rect
        rect = self.scene.itemsBoundingRect()
        rect = rect.adjusted(-50, -50, 50, 50)
        
        if filename.endswith('.pdf'):
            from PyQt6.QtGui import QPdfWriter
            writer = QPdfWriter(filename)
            writer.setPageSize(writer.PageSize.A4)
            painter = QPainter(writer)
            self.scene.render(painter, QRectF(), rect)
            painter.end()
        else:
            # PNG or other image format
            image = QImage(int(rect.width()), int(rect.height()),
                          QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.white)
            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            self.scene.render(painter, QRectF(), rect)
            painter.end()
            image.save(filename)
