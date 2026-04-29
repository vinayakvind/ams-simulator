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

from .design_reference import (
    find_design_block,
    load_design_reference,
    query_design_reference,
    render_design_reference_html,
    summarize_design_reference,
)

from .portfolio import (
    build_portfolio_payload,
    generate_portfolio_artifacts,
    load_portfolio_entries,
    write_portfolio_markdown,
)

from .chip_catalog import (
    build_chip_catalog_payload,
    generate_chip_catalog_report,
    write_chip_catalog_markdown,
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

    # Design reference
    'find_design_block',
    'load_design_reference',
    'query_design_reference',
    'render_design_reference_html',
    'summarize_design_reference',

    # Portfolio
    'build_portfolio_payload',
    'generate_portfolio_artifacts',
    'load_portfolio_entries',
    'write_portfolio_markdown',

    # Chip catalog
    'build_chip_catalog_payload',
    'generate_chip_catalog_report',
    'write_chip_catalog_markdown',
]
