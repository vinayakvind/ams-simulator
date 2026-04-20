"""
AMS Simulator Agent System - Intelligent design automation agents.

Provides autonomous agents for chip design, block building, technology
mapping, and design flow orchestration. Agents can be invoked via CLI
or programmatically to create complete IC designs.

Available Agents:
    ChipDesigner    - Top-level chip design orchestrator
    BlockBuilder    - Individual analog/digital block builder
    TechMapper      - Technology-specific parameter mapping
    DesignIndex     - Indexed design step registry for reproducibility

Usage:
    from simulator.agents import ChipDesigner

    designer = ChipDesigner(technology="generic180")
    designer.create_chip("lin_asic", spec={...})
"""

from simulator.agents.chip_designer import ChipDesigner
from simulator.agents.block_builder import BlockBuilder
from simulator.agents.tech_mapper import TechMapper
from simulator.agents.design_index import DesignIndex

__all__ = [
    "ChipDesigner",
    "BlockBuilder",
    "TechMapper",
    "DesignIndex",
]
