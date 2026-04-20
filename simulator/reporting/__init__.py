"""
Reporting Package for AMS Simulator.
Contains test reporting, specs monitoring, and pass/fail analysis.
"""

from .specs_monitor import (
    Specification,
    SpecResult,
    SpecsReport,
    SpecsMonitor,
    SpecStatus,
    ComparisonOperator,
    MeasurementExtractor,
)

from .report_generator import (
    ReportGenerator,
    TestReportGenerator,
    ReportSection,
)

__all__ = [
    # Specs
    'Specification',
    'SpecResult',
    'SpecsReport',
    'SpecsMonitor',
    'SpecStatus',
    'ComparisonOperator',
    'MeasurementExtractor',
    
    # Reports
    'ReportGenerator',
    'TestReportGenerator',
    'ReportSection',
]
