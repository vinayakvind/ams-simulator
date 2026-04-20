"""
AMS Simulator DSL - Python scripting interface for circuit design.

Provides a database-backed, script-oriented API for defining circuits,
composing SoC-level chips, running simulation campaigns across corners
and temperatures, and generating validation reports.

Usage:
    from simulator.dsl import Project

    proj = Project("my_chip", technology="generic180")
    proj.import_spice("examples/standard_circuits/ldo_regulator.spice", "ldo")
    results = proj.run(
        blocks=["ldo"],
        analyses=["dc", "transient"],
        corners=["TT", "FF", "SS"],
        temps=[-40, 27, 125],
    )
    results.summary()
    results.report("validation.html")
"""

from simulator.dsl.project import Project
from simulator.dsl.block import Block
from simulator.dsl.chip import Chip
from simulator.dsl.pipeline import Pipeline, CampaignResult
from simulator.dsl.importer import SpiceImporter

__all__ = [
    "Project",
    "Block",
    "Chip",
    "Pipeline",
    "CampaignResult",
    "SpiceImporter",
]
