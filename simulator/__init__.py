"""
AMS Simulator - Analog Mixed Signal Simulator
A comprehensive circuit simulation tool with GUI editor, analog/digital simulation,
and Verilog-AMS support.
"""

__version__ = "1.0.0"
__author__ = "AMS Simulator Team"

# Import main components for convenience
from simulator.engine import (
    AnalogEngine,
    DigitalEngine,
    MixedSignalEngine,
    DCAnalysis,
    ACAnalysis,
    TransientAnalysis,
)

from simulator.reporting import (
    SpecsMonitor,
    ReportGenerator,
    MeasurementExtractor,
)

__all__ = [
    'AnalogEngine',
    'DigitalEngine',
    'MixedSignalEngine',
    'DCAnalysis',
    'ACAnalysis',
    'TransientAnalysis',
    'SpecsMonitor',
    'ReportGenerator',
    'MeasurementExtractor',
]
