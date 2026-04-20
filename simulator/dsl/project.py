"""
Project - Top-level workspace for the DSL.

The single entry point for users. Creates/opens a DB-backed workspace,
manages technologies, blocks, chips, and simulation campaigns.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from simulator.db.connection import SimDB
from simulator.db.models import (
    Technology,
    ProcessCorner,
    DeviceModel,
    ProjectRecord,
)
from simulator.db import queries
from simulator.dsl.block import Block


# ── Default technology setup ────────────────────────────────

_GENERIC180_MODELS = [
    DeviceModel(
        name="NMOS", device_type="nmos", level=1,
        params={"VTO": 0.4, "KP": 120e-6, "LAMBDA": 0.01},
        spice_text=".MODEL NMOS NMOS (VTO=0.4 KP=120u LAMBDA=0.01)",
    ),
    DeviceModel(
        name="PMOS", device_type="pmos", level=1,
        params={"VTO": -0.4, "KP": 40e-6, "LAMBDA": 0.01},
        spice_text=".MODEL PMOS PMOS (VTO=-0.4 KP=40u LAMBDA=0.01)",
    ),
    DeviceModel(
        name="NPN", device_type="npn", level=1,
        params={"BF": 100, "IS": 1e-14, "VAF": 100},
        spice_text=".MODEL NPN NPN (BF=100 IS=1e-14 VAF=100)",
    ),
    DeviceModel(
        name="PNP", device_type="pnp", level=1,
        params={"BF": 100, "IS": 1e-14, "VAF": 100},
        spice_text=".MODEL PNP PNP (BF=100 IS=1e-14 VAF=100)",
    ),
    DeviceModel(
        name="D1N4148", device_type="diode", level=1,
        params={"IS": 2.52e-9, "N": 1.752, "BV": 100, "RS": 0.568},
        spice_text=".MODEL D1N4148 D (IS=2.52e-9 N=1.752 BV=100 RS=0.568)",
    ),
]

_DEFAULT_CORNERS = ["TT", "FF", "SS", "SF", "FS"]


class Project:
    """Top-level workspace mapping to a SQLite database and technology.

    Usage:
        proj = Project("my_chip", technology="generic180")
        with proj.block("ldo") as ldo:
            ...
        results = proj.run(blocks=["ldo"], analyses=["dc"], corners=["TT"])
    """

    def __init__(
        self,
        name: str,
        technology: str = "generic180",
        db_path: Optional[str] = None,
    ):
        self._name = name
        self._technology_name = technology

        # Database path defaults to <name>.ams.db in current directory
        if db_path is None:
            db_path = f"{name}.ams.db"
        self._db_path = str(Path(db_path).resolve())

        # Initialize database
        self._db = SimDB(self._db_path)
        self._db.initialize()

        # Ensure technology exists
        self._technology_id = self._ensure_technology(technology)

        # Ensure project record exists
        self._project_id = self._ensure_project()

    # ── Technology setup ──

    def _ensure_technology(self, tech_name: str) -> int:
        """Look up or create the technology. Returns technology ID."""
        tech = queries.get_technology(self._db, tech_name)
        if tech is not None:
            return tech.id

        # Create default technology
        if tech_name == "generic180":
            tech = Technology(
                name="generic180",
                node_nm=180,
                vdd_nominal=1.8,
                description="Generic 180nm process for simulation",
            )
        else:
            tech = Technology(
                name=tech_name,
                node_nm=0,
                vdd_nominal=1.8,
                description=f"Technology: {tech_name}",
            )

        tech_id = queries.save_technology(self._db, tech)

        # Create default process corners
        for corner_name in _DEFAULT_CORNERS:
            corner = ProcessCorner(
                technology_id=tech_id,
                name=corner_name,
                temperature=27.0,
                description=f"{corner_name} corner",
            )
            queries.save_process_corner(self._db, corner)

        # Create default device models (cornerless = apply to all corners)
        if tech_name == "generic180":
            for model in _GENERIC180_MODELS:
                model.technology_id = tech_id
                model.corner_id = None  # applies to all corners
                queries.save_device_model(self._db, model)

        self._db.commit()
        return tech_id

    def _ensure_project(self) -> int:
        """Look up or create the project record. Returns project ID."""
        proj = queries.get_project(self._db, self._name)
        if proj is not None:
            self._project_record = proj
            return proj.id

        rec = ProjectRecord(
            name=self._name,
            technology_id=self._technology_id,
            description="",
            db_path=self._db_path,
        )
        proj_id = queries.save_project(self._db, rec)
        self._db.commit()
        rec.id = proj_id
        self._project_record = rec
        return proj_id

    # ── Public properties ──

    @property
    def name(self) -> str:
        return self._name

    @property
    def db(self) -> SimDB:
        return self._db

    @property
    def technology_id(self) -> int:
        return self._technology_id

    @property
    def technology_name(self) -> str:
        return self._technology_name

    @property
    def project_id(self) -> int:
        return self._project_id

    # ── Block factory ──

    def block(self, name: str, **params: Any) -> Block:
        """Create a new Block context manager for circuit definition.

        Usage:
            with proj.block("ldo") as ldo:
                ldo.port("vin", "input")
                r1 = ldo.add("R", value="10k")
        """
        return Block(self, name, **params)

    def get_block(self, name: str) -> Block:
        """Load an existing block from the database by name."""
        return Block.load(self, name)

    def list_blocks(self) -> list[str]:
        """List all circuit/block names in the database."""
        rows = self._db.fetchall(
            "SELECT DISTINCT name FROM circuits ORDER BY name"
        )
        return [r["name"] for r in rows]

    # ── Chip factory ──

    def chip(self, name: str) -> Any:
        """Create a Chip context manager for SoC composition.

        Usage:
            with proj.chip("top") as top:
                bgr = top.use("bandgap_ref")
                ldo = top.use("ldo_regulator")
                top.wire(bgr.vout, ldo.vref)
        """
        from simulator.dsl.chip import Chip
        return Chip(self, name)

    # ── SPICE import ──

    def import_spice(
        self, spice_path: str, block_name: Optional[str] = None
    ) -> Block:
        """Import a .spice netlist file as a Block stored in the DB.

        Args:
            spice_path: Path to the .spice file
            block_name: Name for the block (default: filename stem)

        Returns:
            The imported Block.
        """
        from simulator.dsl.importer import SpiceImporter
        importer = SpiceImporter(self)
        return importer.import_file(spice_path, block_name)

    # ── Simulation pipeline ──

    def run(
        self,
        blocks: list[str],
        analyses: list[str],
        corners: list[str] = None,
        temps: list[float] = None,
        specs: Optional[dict[str, dict]] = None,
        auto_design: bool = False,
        max_workers: Optional[int] = None,
    ) -> Any:
        """Execute a full simulation campaign.

        Args:
            blocks: List of block names to simulate
            analyses: Analysis types ("dc", "ac", "transient")
            corners: Process corners (default: ["TT"])
            temps: Temperatures in Celsius (default: [27.0])
            specs: Per-block specs dict {block: {signal: (min, max, unit)}}
            auto_design: Run AutoDesigner before simulation
            max_workers: Parallel workers (default: CPU count)

        Returns:
            CampaignResult with summary, report, and comparison methods.
        """
        from simulator.dsl.pipeline import Pipeline

        if corners is None:
            corners = ["TT"]
        if temps is None:
            temps = [27.0]

        pipeline = Pipeline(self)
        return pipeline.execute(
            blocks=blocks,
            analyses=analyses,
            corners=corners,
            temps=temps,
            specs=specs,
            auto_design=auto_design,
            max_workers=max_workers,
        )

    # ── Campaign queries ──

    def list_campaigns(self) -> list[dict]:
        """List all campaigns for this project."""
        campaigns = queries.get_campaigns(self._db, self._project_id)
        return [
            {
                "id": c.id,
                "name": c.name,
                "status": c.status,
                "blocks": c.block_list,
                "corners": c.corner_list,
                "temps": c.temp_list,
                "total_jobs": c.total_jobs,
                "completed_jobs": c.completed_jobs,
                "created_at": c.created_at,
            }
            for c in campaigns
        ]

    def compare(self, campaign_id_a: int, campaign_id_b: int) -> dict:
        """Compare two campaigns side by side."""
        summary_a = queries.get_campaign_summary(self._db, campaign_id_a)
        summary_b = queries.get_campaign_summary(self._db, campaign_id_b)
        results_a = queries.get_campaign_results(self._db, campaign_id_a)
        results_b = queries.get_campaign_results(self._db, campaign_id_b)

        return {
            "campaign_a": summary_a,
            "campaign_b": summary_b,
            "results_a": len(results_a),
            "results_b": len(results_b),
            "a_passed": summary_a.get("all_passed", False),
            "b_passed": summary_b.get("all_passed", False),
        }

    # ── Cleanup ──

    def close(self) -> None:
        """Close the database connection."""
        self._db.close()

    def __enter__(self) -> Project:
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"Project('{self._name}', technology='{self._technology_name}', "
            f"db='{self._db_path}')"
        )
