"""
Components Module for AMS Simulator.
Contains all circuit component definitions including transistors, passives,
sources, and digital gates.
"""

from simulator.components.base import Component, Pin, ComponentProperty
from simulator.components.passive import Resistor, Capacitor, Inductor
from simulator.components.transistors import NMOS, PMOS, NPN, PNP
from simulator.components.sources import (
    VoltageSource, CurrentSource, VoltageProbe, CurrentProbe,
    PulseSource, SineSource, PWLSource
)
from simulator.components.digital import (
    ANDGate, ORGate, NOTGate, NANDGate, NORGate, XORGate, XNORGate,
    DFlipFlop, SRLatch, Mux2to1
)
from simulator.components.amplifiers import OpAmp, Comparator
from simulator.components.diodes import Diode, Zener, LED
from simulator.components.analog_blocks import (
    LDORegulator, BandgapReference, CurrentMirror, OTA,
    VoltageBuffer, LevelShifter
)
from simulator.components.hierarchy import HierarchicalBlock

__all__ = [
    # Base
    "Component", "Pin", "ComponentProperty",
    # Passive
    "Resistor", "Capacitor", "Inductor",
    # Transistors
    "NMOS", "PMOS", "NPN", "PNP",
    # Sources
    "VoltageSource", "CurrentSource", "VoltageProbe", "CurrentProbe",
    "PulseSource", "SineSource", "PWLSource",
    # Digital
    "ANDGate", "ORGate", "NOTGate", "NANDGate", "NORGate", "XORGate", "XNORGate",
    "DFlipFlop", "SRLatch", "Mux2to1",
    # Amplifiers
    "OpAmp", "Comparator",
    # Diodes
    "Diode", "Zener", "LED",
    # Analog Blocks
    "LDORegulator", "BandgapReference", "CurrentMirror",
    "OTA", "VoltageBuffer", "LevelShifter",
    # Hierarchy
    "HierarchicalBlock",
]
