"""
CRUD query helpers for AMS Simulator database.

All functions take a SimDB instance and model dataclasses,
returning IDs for inserts or model instances for queries.
"""

from __future__ import annotations

import json
from typing import Optional

from simulator.db.connection import SimDB
from simulator.db.models import (
    Technology,
    ProcessCorner,
    DeviceModel,
    LibraryComponent,
    CircuitDesign,
    SimulationConfig,
    SimulationResult,
    StandardCell,
    SweepRun,
    ProjectRecord,
    DesignSpecRecord,
    CampaignRecord,
    CampaignResultRecord,
)


# ── Technology operations ────────────────────────────────────


def save_technology(db: SimDB, tech: Technology) -> int:
    """Insert or update a technology. Returns the technology ID."""
    data = tech.to_dict()
    with db.transaction() as conn:
        if tech.id is not None:
            conn.execute(
                """UPDATE technologies SET name=?, node_nm=?, vdd_nominal=?,
                   description=?, params_json=?, lib_file_path=?,
                   updated_at=datetime('now')
                   WHERE id=?""",
                (
                    data["name"],
                    data["node_nm"],
                    data["vdd_nominal"],
                    data["description"],
                    data["params_json"],
                    data["lib_file_path"],
                    tech.id,
                ),
            )
            return tech.id
        cursor = conn.execute(
            """INSERT INTO technologies (name, node_nm, vdd_nominal, description,
               params_json, lib_file_path)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data["node_nm"],
                data["vdd_nominal"],
                data["description"],
                data["params_json"],
                data["lib_file_path"],
            ),
        )
        return cursor.lastrowid


def get_technology(db: SimDB, name: str) -> Optional[Technology]:
    """Look up a technology by name."""
    row = db.fetchone("SELECT * FROM technologies WHERE name=?", (name,))
    return Technology.from_row(dict(row)) if row else None


def list_technologies(db: SimDB) -> list[Technology]:
    """List all technologies."""
    rows = db.fetchall("SELECT * FROM technologies ORDER BY name")
    return [Technology.from_row(dict(r)) for r in rows]


# ── Process corner operations ────────────────────────────────


def save_process_corner(db: SimDB, corner: ProcessCorner) -> int:
    """Insert a process corner. Returns the corner ID."""
    data = corner.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO process_corners
               (technology_id, name, temperature, voltage_scale, description, params_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                data["technology_id"],
                data["name"],
                data["temperature"],
                data["voltage_scale"],
                data["description"],
                data["params_json"],
            ),
        )
        return cursor.lastrowid


def get_process_corners(db: SimDB, technology_id: int) -> list[ProcessCorner]:
    """Get all corners for a technology."""
    rows = db.fetchall(
        "SELECT * FROM process_corners WHERE technology_id=? ORDER BY name",
        (technology_id,),
    )
    return [ProcessCorner.from_row(dict(r)) for r in rows]


# ── Device model operations ──────────────────────────────────


def save_device_model(db: SimDB, model: DeviceModel) -> int:
    """Insert or update a device model. Returns the model ID."""
    data = model.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO device_models
               (technology_id, corner_id, name, device_type, level,
                params_json, spice_text, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["technology_id"],
                data["corner_id"],
                data["name"],
                data["device_type"],
                data["level"],
                data["params_json"],
                data["spice_text"],
                data["description"],
            ),
        )
        return cursor.lastrowid


def get_device_models(
    db: SimDB,
    technology_id: int,
    corner_id: Optional[int] = None,
    device_type: Optional[str] = None,
) -> list[DeviceModel]:
    """Query device models with optional filters."""
    sql = "SELECT * FROM device_models WHERE technology_id=?"
    params: list = [technology_id]
    if corner_id is not None:
        sql += " AND corner_id=?"
        params.append(corner_id)
    if device_type is not None:
        sql += " AND device_type=?"
        params.append(device_type)
    sql += " ORDER BY name"
    rows = db.fetchall(sql, tuple(params))
    return [DeviceModel.from_row(dict(r)) for r in rows]


def get_model_spice_text(
    db: SimDB, model_name: str, tech_name: str, corner: str = "TT"
) -> str:
    """Get the SPICE text for a specific model, technology, and corner.

    Falls back to cornerless model if corner-specific not found.
    """
    row = db.fetchone(
        """SELECT dm.* FROM device_models dm
           JOIN technologies t ON dm.technology_id = t.id
           LEFT JOIN process_corners pc ON dm.corner_id = pc.id
           WHERE dm.name=? AND t.name=?
           AND (pc.name=? OR dm.corner_id IS NULL)
           ORDER BY dm.corner_id DESC LIMIT 1""",
        (model_name, tech_name, corner),
    )
    if row:
        model = DeviceModel.from_row(dict(row))
        return model.to_spice()
    return ""


def get_all_models_spice(
    db: SimDB, tech_name: str, corner: str = "TT"
) -> str:
    """Get all SPICE .MODEL lines for a technology and corner."""
    rows = db.fetchall(
        """SELECT dm.* FROM device_models dm
           JOIN technologies t ON dm.technology_id = t.id
           LEFT JOIN process_corners pc ON dm.corner_id = pc.id
           WHERE t.name=?
           AND (pc.name=? OR dm.corner_id IS NULL)
           ORDER BY dm.name""",
        (tech_name, corner),
    )
    lines = []
    for r in rows:
        model = DeviceModel.from_row(dict(r))
        lines.append(model.to_spice())
    return "\n".join(lines)


# ── Component library operations ─────────────────────────────


def save_library_component(db: SimDB, comp: LibraryComponent) -> int:
    """Insert or update a library component. Returns the component ID."""
    data = comp.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO component_library
               (name, category, parent_id, technology_id, pins_json, params_json,
                netlist, python_class, description, author, version, tags)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data["category"],
                data["parent_id"],
                data["technology_id"],
                data["pins_json"],
                data["params_json"],
                data["netlist"],
                data["python_class"],
                data["description"],
                data["author"],
                data["version"],
                data["tags"],
            ),
        )
        return cursor.lastrowid


def get_library_component(
    db: SimDB, name: str, version: str = "1.0"
) -> Optional[LibraryComponent]:
    """Look up a library component by name and version."""
    row = db.fetchone(
        "SELECT * FROM component_library WHERE name=? AND version=?",
        (name, version),
    )
    return LibraryComponent.from_row(dict(row)) if row else None


def list_library_components(
    db: SimDB, category: Optional[str] = None, technology_id: Optional[int] = None
) -> list[LibraryComponent]:
    """List library components with optional filters."""
    sql = "SELECT * FROM component_library WHERE 1=1"
    params: list = []
    if category:
        sql += " AND category=?"
        params.append(category)
    if technology_id is not None:
        sql += " AND technology_id=?"
        params.append(technology_id)
    sql += " ORDER BY category, name"
    rows = db.fetchall(sql, tuple(params))
    return [LibraryComponent.from_row(dict(r)) for r in rows]


# ── Circuit operations (versioned) ───────────────────────────


def save_circuit(db: SimDB, circuit: CircuitDesign) -> int:
    """Save a circuit design. Auto-increments version if name exists."""
    data = circuit.to_dict()
    with db.transaction() as conn:
        if circuit.id is not None:
            conn.execute(
                """UPDATE circuits SET name=?, version=?, technology_id=?,
                   description=?, netlist=?, dsl_script=?, schematic_json=?,
                   hierarchy_json=?, params_json=?, author=?, status=?,
                   parent_version_id=?, updated_at=datetime('now')
                   WHERE id=?""",
                (
                    data["name"],
                    data["version"],
                    data["technology_id"],
                    data["description"],
                    data["netlist"],
                    data["dsl_script"],
                    data["schematic_json"],
                    data["hierarchy_json"],
                    data["params_json"],
                    data["author"],
                    data["status"],
                    data["parent_version_id"],
                    circuit.id,
                ),
            )
            return circuit.id

        # Auto-version: find max version for this name
        row = conn.execute(
            "SELECT MAX(version) as max_v FROM circuits WHERE name=?",
            (data["name"],),
        ).fetchone()
        next_version = (row["max_v"] or 0) + 1 if row and row["max_v"] else 1
        data["version"] = next_version

        # Link to previous version
        if next_version > 1:
            prev = conn.execute(
                "SELECT id FROM circuits WHERE name=? AND version=?",
                (data["name"], next_version - 1),
            ).fetchone()
            if prev:
                data["parent_version_id"] = prev["id"]

        cursor = conn.execute(
            """INSERT INTO circuits
               (name, version, technology_id, description, netlist, dsl_script,
                schematic_json, hierarchy_json, params_json, author, status,
                parent_version_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["name"],
                data["version"],
                data["technology_id"],
                data["description"],
                data["netlist"],
                data["dsl_script"],
                data["schematic_json"],
                data["hierarchy_json"],
                data["params_json"],
                data["author"],
                data["status"],
                data.get("parent_version_id"),
            ),
        )
        return cursor.lastrowid


def get_circuit(
    db: SimDB, name: str, version: Optional[int] = None
) -> Optional[CircuitDesign]:
    """Get a circuit by name and optional version. Latest version if not specified."""
    if version is not None:
        row = db.fetchone(
            "SELECT * FROM circuits WHERE name=? AND version=?",
            (name, version),
        )
    else:
        row = db.fetchone(
            "SELECT * FROM circuits WHERE name=? ORDER BY version DESC LIMIT 1",
            (name,),
        )
    return CircuitDesign.from_row(dict(row)) if row else None


def get_circuit_by_id(db: SimDB, circuit_id: int) -> Optional[CircuitDesign]:
    """Get a circuit by its database ID."""
    row = db.fetchone("SELECT * FROM circuits WHERE id=?", (circuit_id,))
    return CircuitDesign.from_row(dict(row)) if row else None


def get_circuit_history(db: SimDB, name: str) -> list[CircuitDesign]:
    """Get all versions of a circuit, ordered by version."""
    rows = db.fetchall(
        "SELECT * FROM circuits WHERE name=? ORDER BY version", (name,)
    )
    return [CircuitDesign.from_row(dict(r)) for r in rows]


# ── Simulation config operations ─────────────────────────────


def save_simulation_config(db: SimDB, config: SimulationConfig) -> int:
    """Save a simulation config. Returns the config ID."""
    data = config.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO simulation_configs
               (circuit_id, name, analysis_type, settings_json, corner_id,
                temperature, stimulus_json, measurements_json, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["circuit_id"],
                data["name"],
                data["analysis_type"],
                data["settings_json"],
                data["corner_id"],
                data["temperature"],
                data["stimulus_json"],
                data["measurements_json"],
                data["description"],
            ),
        )
        return cursor.lastrowid


# ── Simulation result operations ─────────────────────────────


def save_result(db: SimDB, result: SimulationResult) -> int:
    """Save a simulation result. Returns the result ID."""
    data = result.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO simulation_results
               (config_id, circuit_id, corner_id, status, started_at, completed_at,
                elapsed_secs, summary_json, measurements_json, error_message,
                engine_version, host_info)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["config_id"],
                data["circuit_id"],
                data["corner_id"],
                data["status"],
                data["started_at"],
                data["completed_at"],
                data["elapsed_secs"],
                data["summary_json"],
                data["measurements_json"],
                data["error_message"],
                data["engine_version"],
                data["host_info"],
            ),
        )
        return cursor.lastrowid


def update_result_status(
    db: SimDB, result_id: int, status: str, error_message: str = ""
) -> None:
    """Update the status of a simulation result."""
    with db.transaction() as conn:
        conn.execute(
            "UPDATE simulation_results SET status=?, error_message=? WHERE id=?",
            (status, error_message, result_id),
        )


def get_results_for_circuit(db: SimDB, circuit_id: int) -> list[SimulationResult]:
    """Get all results for a circuit."""
    rows = db.fetchall(
        "SELECT * FROM simulation_results WHERE circuit_id=? ORDER BY created_at DESC",
        (circuit_id,),
    )
    return [SimulationResult.from_row(dict(r)) for r in rows]


def get_latest_result(db: SimDB, config_id: int) -> Optional[SimulationResult]:
    """Get the most recent result for a simulation config."""
    row = db.fetchone(
        """SELECT * FROM simulation_results
           WHERE config_id=? ORDER BY created_at DESC LIMIT 1""",
        (config_id,),
    )
    return SimulationResult.from_row(dict(row)) if row else None


# ── Standard cell operations ─────────────────────────────────


def save_standard_cell(db: SimDB, cell: StandardCell) -> int:
    """Save a standard cell. Returns the cell ID."""
    data = cell.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO standard_cells
               (technology_id, name, cell_type, drive_strength, pins_json,
                timing_json, power_json, area, netlist, behavioral_model, liberty_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["technology_id"],
                data["name"],
                data["cell_type"],
                data["drive_strength"],
                data["pins_json"],
                data["timing_json"],
                data["power_json"],
                data["area"],
                data["netlist"],
                data["behavioral_model"],
                data["liberty_data"],
            ),
        )
        return cursor.lastrowid


def get_standard_cells(
    db: SimDB, technology_id: int, cell_type: Optional[str] = None
) -> list[StandardCell]:
    """Get standard cells for a technology."""
    sql = "SELECT * FROM standard_cells WHERE technology_id=?"
    params: list = [technology_id]
    if cell_type:
        sql += " AND cell_type=?"
        params.append(cell_type)
    sql += " ORDER BY name"
    rows = db.fetchall(sql, tuple(params))
    return [StandardCell.from_row(dict(r)) for r in rows]


# ── Sweep operations ─────────────────────────────────────────


def save_sweep_run(db: SimDB, sweep: SweepRun) -> int:
    """Save a sweep run. Returns the sweep ID."""
    data = sweep.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO sweep_runs
               (circuit_id, name, sweep_type, sweep_def_json, status,
                total_points, completed_points)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                data["circuit_id"],
                data["name"],
                data["sweep_type"],
                data["sweep_def_json"],
                data["status"],
                data["total_points"],
                data["completed_points"],
            ),
        )
        return cursor.lastrowid


def save_sweep_point(
    db: SimDB, sweep_run_id: int, result_id: int, point_index: int, params: dict
) -> int:
    """Save a single sweep point."""
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO sweep_points
               (sweep_run_id, result_id, point_index, params_json)
               VALUES (?, ?, ?, ?)""",
            (sweep_run_id, result_id, point_index, json.dumps(params)),
        )
        return cursor.lastrowid


def update_sweep_progress(
    db: SimDB, sweep_id: int, completed_points: int, status: str = "running"
) -> None:
    """Update sweep run progress."""
    with db.transaction() as conn:
        conn.execute(
            "UPDATE sweep_runs SET completed_points=?, status=? WHERE id=?",
            (completed_points, status, sweep_id),
        )


# ── Project operations ──────────────────────────────────────


def save_project(db: SimDB, project: ProjectRecord) -> int:
    """Insert or update a project. Returns the project ID."""
    data = project.to_dict()
    with db.transaction() as conn:
        if project.id is not None:
            conn.execute(
                """UPDATE projects SET name=?, technology_id=?, description=?,
                   settings_json=?, db_path=?, updated_at=datetime('now')
                   WHERE id=?""",
                (
                    data["name"],
                    data["technology_id"],
                    data["description"],
                    data["settings_json"],
                    data["db_path"],
                    project.id,
                ),
            )
            return project.id
        cursor = conn.execute(
            """INSERT OR REPLACE INTO projects
               (name, technology_id, description, settings_json, db_path)
               VALUES (?, ?, ?, ?, ?)""",
            (
                data["name"],
                data["technology_id"],
                data["description"],
                data["settings_json"],
                data["db_path"],
            ),
        )
        return cursor.lastrowid


def get_project(db: SimDB, name: str) -> Optional[ProjectRecord]:
    """Look up a project by name."""
    row = db.fetchone("SELECT * FROM projects WHERE name=?", (name,))
    return ProjectRecord.from_row(dict(row)) if row else None


def list_projects(db: SimDB) -> list[ProjectRecord]:
    """List all projects."""
    rows = db.fetchall("SELECT * FROM projects ORDER BY name")
    return [ProjectRecord.from_row(dict(r)) for r in rows]


# ── Design spec operations ──────────────────────────────────


def save_design_spec(db: SimDB, spec: DesignSpecRecord) -> int:
    """Insert or replace a design spec. Returns the spec ID."""
    data = spec.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO design_specs
               (circuit_id, name, parameter, min_val, max_val, typical, unit, weight)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["circuit_id"],
                data["name"],
                data["parameter"],
                data["min_val"],
                data["max_val"],
                data["typical"],
                data["unit"],
                data["weight"],
            ),
        )
        return cursor.lastrowid


def get_design_specs(db: SimDB, circuit_id: int) -> list[DesignSpecRecord]:
    """Get all design specs for a circuit."""
    rows = db.fetchall(
        "SELECT * FROM design_specs WHERE circuit_id=? ORDER BY name",
        (circuit_id,),
    )
    return [DesignSpecRecord.from_row(dict(r)) for r in rows]


# ── Campaign operations ─────────────────────────────────────


def save_campaign(db: SimDB, campaign: CampaignRecord) -> int:
    """Insert a campaign. Returns the campaign ID."""
    data = campaign.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT INTO campaigns
               (project_id, name, description, block_list_json,
                corner_list_json, temp_list_json, analysis_list_json,
                status, total_jobs, completed_jobs)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["project_id"],
                data["name"],
                data["description"],
                data["block_list_json"],
                data["corner_list_json"],
                data["temp_list_json"],
                data["analysis_list_json"],
                data["status"],
                data["total_jobs"],
                data["completed_jobs"],
            ),
        )
        return cursor.lastrowid


def update_campaign_status(
    db: SimDB, campaign_id: int, status: str, completed_jobs: int = 0
) -> None:
    """Update campaign status and progress."""
    with db.transaction() as conn:
        if status in ("completed", "failed"):
            conn.execute(
                """UPDATE campaigns SET status=?, completed_jobs=?,
                   completed_at=datetime('now') WHERE id=?""",
                (status, completed_jobs, campaign_id),
            )
        else:
            conn.execute(
                "UPDATE campaigns SET status=?, completed_jobs=? WHERE id=?",
                (status, completed_jobs, campaign_id),
            )


def get_campaign_by_id(db: SimDB, campaign_id: int) -> Optional[CampaignRecord]:
    """Get a campaign by its ID."""
    row = db.fetchone("SELECT * FROM campaigns WHERE id=?", (campaign_id,))
    return CampaignRecord.from_row(dict(row)) if row else None


def get_campaigns(db: SimDB, project_id: int) -> list[CampaignRecord]:
    """Get all campaigns for a project."""
    rows = db.fetchall(
        "SELECT * FROM campaigns WHERE project_id=? ORDER BY created_at DESC",
        (project_id,),
    )
    return [CampaignRecord.from_row(dict(r)) for r in rows]


# ── Campaign result operations ──────────────────────────────


def save_campaign_result(db: SimDB, result: CampaignResultRecord) -> int:
    """Insert or replace a campaign result. Returns the result ID."""
    data = result.to_dict()
    with db.transaction() as conn:
        cursor = conn.execute(
            """INSERT OR REPLACE INTO campaign_results
               (campaign_id, circuit_id, corner, temperature, analysis_type,
                result_id, specs_summary_json, pass_fail, details_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                data["campaign_id"],
                data["circuit_id"],
                data["corner"],
                data["temperature"],
                data["analysis_type"],
                data["result_id"],
                data["specs_summary_json"],
                data["pass_fail"],
                data["details_json"],
            ),
        )
        return cursor.lastrowid


def get_campaign_results(
    db: SimDB, campaign_id: int, circuit_id: Optional[int] = None
) -> list[CampaignResultRecord]:
    """Get campaign results, optionally filtered by circuit."""
    sql = "SELECT * FROM campaign_results WHERE campaign_id=?"
    params: list = [campaign_id]
    if circuit_id is not None:
        sql += " AND circuit_id=?"
        params.append(circuit_id)
    sql += " ORDER BY corner, temperature, analysis_type"
    rows = db.fetchall(sql, tuple(params))
    return [CampaignResultRecord.from_row(dict(r)) for r in rows]


def get_campaign_summary(db: SimDB, campaign_id: int) -> dict:
    """Get an aggregated summary of a campaign's pass/fail status."""
    results = get_campaign_results(db, campaign_id)
    total = len(results)
    passed = sum(1 for r in results if r.pass_fail == "pass")
    failed = sum(1 for r in results if r.pass_fail == "fail")
    pending = sum(1 for r in results if r.pass_fail == "pending")
    return {
        "campaign_id": campaign_id,
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "all_passed": failed == 0 and pending == 0 and total > 0,
    }
