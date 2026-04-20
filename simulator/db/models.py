"""
Database model dataclasses for AMS Simulator.

Plain Python dataclasses that mirror database rows. Each has to_dict()
and from_row() for serialization. No ORM dependency — uses stdlib sqlite3.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Optional


def _json_loads(val: Any) -> Any:
    """Safely parse JSON, returning empty dict/list on failure."""
    if isinstance(val, (dict, list)):
        return val
    if not val:
        return {}
    try:
        return json.loads(val)
    except (json.JSONDecodeError, TypeError):
        return {}


def _json_loads_list(val: Any) -> list:
    """Safely parse JSON as a list."""
    result = _json_loads(val)
    return result if isinstance(result, list) else []


@dataclass
class Technology:
    """PDK/process technology definition."""

    id: Optional[int] = None
    name: str = ""
    node_nm: int = 180
    vdd_nominal: float = 1.8
    description: str = ""
    params: dict = field(default_factory=dict)
    lib_file_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "node_nm": self.node_nm,
            "vdd_nominal": self.vdd_nominal,
            "description": self.description,
            "params_json": json.dumps(self.params),
            "lib_file_path": self.lib_file_path,
        }

    @classmethod
    def from_row(cls, row: dict) -> Technology:
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            node_nm=row.get("node_nm", 180),
            vdd_nominal=row.get("vdd_nominal", 1.8),
            description=row.get("description", ""),
            params=_json_loads(row.get("params_json")),
            lib_file_path=row.get("lib_file_path", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass
class ProcessCorner:
    """Process corner (TT, FF, SS, SF, FS) for a technology."""

    id: Optional[int] = None
    technology_id: int = 0
    name: str = "TT"
    temperature: float = 27.0
    voltage_scale: float = 1.0
    description: str = ""
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "technology_id": self.technology_id,
            "name": self.name,
            "temperature": self.temperature,
            "voltage_scale": self.voltage_scale,
            "description": self.description,
            "params_json": json.dumps(self.params),
        }

    @classmethod
    def from_row(cls, row: dict) -> ProcessCorner:
        return cls(
            id=row.get("id"),
            technology_id=row.get("technology_id", 0),
            name=row.get("name", "TT"),
            temperature=row.get("temperature", 27.0),
            voltage_scale=row.get("voltage_scale", 1.0),
            description=row.get("description", ""),
            params=_json_loads(row.get("params_json")),
        )


@dataclass
class DeviceModel:
    """SPICE device model card."""

    id: Optional[int] = None
    technology_id: int = 0
    corner_id: Optional[int] = None
    name: str = ""
    device_type: str = "nmos"
    level: int = 1
    params: dict = field(default_factory=dict)
    spice_text: str = ""
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "technology_id": self.technology_id,
            "corner_id": self.corner_id,
            "name": self.name,
            "device_type": self.device_type,
            "level": self.level,
            "params_json": json.dumps(self.params),
            "spice_text": self.spice_text,
            "description": self.description,
        }

    @classmethod
    def from_row(cls, row: dict) -> DeviceModel:
        return cls(
            id=row.get("id"),
            technology_id=row.get("technology_id", 0),
            corner_id=row.get("corner_id"),
            name=row.get("name", ""),
            device_type=row.get("device_type", "nmos"),
            level=row.get("level", 1),
            params=_json_loads(row.get("params_json")),
            spice_text=row.get("spice_text", ""),
            description=row.get("description", ""),
        )

    def to_spice(self) -> str:
        """Generate SPICE .MODEL line from stored parameters."""
        if self.spice_text:
            return self.spice_text
        dtype = self.device_type.upper()
        # Map common types
        type_map = {
            "NMOS": "NMOS",
            "PMOS": "PMOS",
            "NPN": "NPN",
            "PNP": "PNP",
            "DIODE": "D",
            "RES": "R",
            "CAP": "C",
        }
        spice_type = type_map.get(dtype, dtype)
        params_str = " ".join(
            f"{k.upper()}={v}" for k, v in self.params.items()
        )
        return f".MODEL {self.name} {spice_type} ({params_str})"


@dataclass
class LibraryComponent:
    """Reusable subcircuit/cell in the component library."""

    id: Optional[int] = None
    name: str = ""
    category: str = "analog"
    parent_id: Optional[int] = None
    technology_id: Optional[int] = None
    pins: list = field(default_factory=list)
    params: dict = field(default_factory=dict)
    netlist: str = ""
    python_class: str = ""
    description: str = ""
    author: str = ""
    version: str = "1.0"
    tags: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "parent_id": self.parent_id,
            "technology_id": self.technology_id,
            "pins_json": json.dumps(self.pins),
            "params_json": json.dumps(self.params),
            "netlist": self.netlist,
            "python_class": self.python_class,
            "description": self.description,
            "author": self.author,
            "version": self.version,
            "tags": self.tags,
        }

    @classmethod
    def from_row(cls, row: dict) -> LibraryComponent:
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            category=row.get("category", "analog"),
            parent_id=row.get("parent_id"),
            technology_id=row.get("technology_id"),
            pins=_json_loads_list(row.get("pins_json")),
            params=_json_loads(row.get("params_json")),
            netlist=row.get("netlist", ""),
            python_class=row.get("python_class", ""),
            description=row.get("description", ""),
            author=row.get("author", ""),
            version=row.get("version", "1.0"),
            tags=row.get("tags", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass
class CircuitDesign:
    """Top-level circuit design, versioned."""

    id: Optional[int] = None
    name: str = ""
    version: int = 1
    technology_id: Optional[int] = None
    description: str = ""
    netlist: str = ""
    dsl_script: str = ""
    schematic_json: str = ""
    hierarchy: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    author: str = ""
    status: str = "draft"
    parent_version_id: Optional[int] = None
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "technology_id": self.technology_id,
            "description": self.description,
            "netlist": self.netlist,
            "dsl_script": self.dsl_script,
            "schematic_json": self.schematic_json,
            "hierarchy_json": json.dumps(self.hierarchy),
            "params_json": json.dumps(self.params),
            "author": self.author,
            "status": self.status,
            "parent_version_id": self.parent_version_id,
        }

    @classmethod
    def from_row(cls, row: dict) -> CircuitDesign:
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            version=row.get("version", 1),
            technology_id=row.get("technology_id"),
            description=row.get("description", ""),
            netlist=row.get("netlist", ""),
            dsl_script=row.get("dsl_script", ""),
            schematic_json=row.get("schematic_json", ""),
            hierarchy=_json_loads(row.get("hierarchy_json")),
            params=_json_loads(row.get("params_json")),
            author=row.get("author", ""),
            status=row.get("status", "draft"),
            parent_version_id=row.get("parent_version_id"),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass
class SimulationConfig:
    """Analysis setup for a circuit."""

    id: Optional[int] = None
    circuit_id: int = 0
    name: str = ""
    analysis_type: str = "dc"
    settings: dict = field(default_factory=dict)
    corner_id: Optional[int] = None
    temperature: float = 27.0
    stimulus: dict = field(default_factory=dict)
    measurements: list = field(default_factory=list)
    description: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "circuit_id": self.circuit_id,
            "name": self.name,
            "analysis_type": self.analysis_type,
            "settings_json": json.dumps(self.settings),
            "corner_id": self.corner_id,
            "temperature": self.temperature,
            "stimulus_json": json.dumps(self.stimulus),
            "measurements_json": json.dumps(self.measurements),
            "description": self.description,
        }

    @classmethod
    def from_row(cls, row: dict) -> SimulationConfig:
        return cls(
            id=row.get("id"),
            circuit_id=row.get("circuit_id", 0),
            name=row.get("name", ""),
            analysis_type=row.get("analysis_type", "dc"),
            settings=_json_loads(row.get("settings_json")),
            corner_id=row.get("corner_id"),
            temperature=row.get("temperature", 27.0),
            stimulus=_json_loads(row.get("stimulus_json")),
            measurements=_json_loads_list(row.get("measurements_json")),
            description=row.get("description", ""),
            created_at=row.get("created_at", ""),
        )


@dataclass
class SimulationResult:
    """Simulation run result with metadata."""

    id: Optional[int] = None
    config_id: Optional[int] = None
    circuit_id: int = 0
    corner_id: Optional[int] = None
    status: str = "pending"
    started_at: str = ""
    completed_at: str = ""
    elapsed_secs: float = 0.0
    summary: dict = field(default_factory=dict)
    measurements: dict = field(default_factory=dict)
    error_message: str = ""
    engine_version: str = ""
    host_info: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "circuit_id": self.circuit_id,
            "corner_id": self.corner_id,
            "status": self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_secs": self.elapsed_secs,
            "summary_json": json.dumps(self.summary),
            "measurements_json": json.dumps(self.measurements),
            "error_message": self.error_message,
            "engine_version": self.engine_version,
            "host_info": self.host_info,
        }

    @classmethod
    def from_row(cls, row: dict) -> SimulationResult:
        return cls(
            id=row.get("id"),
            config_id=row.get("config_id"),
            circuit_id=row.get("circuit_id", 0),
            corner_id=row.get("corner_id"),
            status=row.get("status", "pending"),
            started_at=row.get("started_at", ""),
            completed_at=row.get("completed_at", ""),
            elapsed_secs=row.get("elapsed_secs", 0.0),
            summary=_json_loads(row.get("summary_json")),
            measurements=_json_loads(row.get("measurements_json")),
            error_message=row.get("error_message", ""),
            engine_version=row.get("engine_version", ""),
            host_info=row.get("host_info", ""),
            created_at=row.get("created_at", ""),
        )


@dataclass
class StandardCell:
    """Standard cell for SoC-scale digital backbone."""

    id: Optional[int] = None
    technology_id: int = 0
    name: str = ""
    cell_type: str = ""
    drive_strength: int = 1
    pins: list = field(default_factory=list)
    timing: dict = field(default_factory=dict)
    power: dict = field(default_factory=dict)
    area: float = 0.0
    netlist: str = ""
    behavioral_model: str = ""
    liberty_data: str = ""

    def to_dict(self) -> dict:
        return {
            "technology_id": self.technology_id,
            "name": self.name,
            "cell_type": self.cell_type,
            "drive_strength": self.drive_strength,
            "pins_json": json.dumps(self.pins),
            "timing_json": json.dumps(self.timing),
            "power_json": json.dumps(self.power),
            "area": self.area,
            "netlist": self.netlist,
            "behavioral_model": self.behavioral_model,
            "liberty_data": self.liberty_data,
        }

    @classmethod
    def from_row(cls, row: dict) -> StandardCell:
        return cls(
            id=row.get("id"),
            technology_id=row.get("technology_id", 0),
            name=row.get("name", ""),
            cell_type=row.get("cell_type", ""),
            drive_strength=row.get("drive_strength", 1),
            pins=_json_loads_list(row.get("pins_json")),
            timing=_json_loads(row.get("timing_json")),
            power=_json_loads(row.get("power_json")),
            area=row.get("area", 0.0),
            netlist=row.get("netlist", ""),
            behavioral_model=row.get("behavioral_model", ""),
            liberty_data=row.get("liberty_data", ""),
        )


@dataclass
class SweepRun:
    """Parametric/corner/Monte Carlo sweep run."""

    id: Optional[int] = None
    circuit_id: int = 0
    name: str = ""
    sweep_type: str = "parametric"
    sweep_def: dict = field(default_factory=dict)
    status: str = "pending"
    total_points: int = 0
    completed_points: int = 0
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "circuit_id": self.circuit_id,
            "name": self.name,
            "sweep_type": self.sweep_type,
            "sweep_def_json": json.dumps(self.sweep_def),
            "status": self.status,
            "total_points": self.total_points,
            "completed_points": self.completed_points,
        }

    @classmethod
    def from_row(cls, row: dict) -> SweepRun:
        return cls(
            id=row.get("id"),
            circuit_id=row.get("circuit_id", 0),
            name=row.get("name", ""),
            sweep_type=row.get("sweep_type", "parametric"),
            sweep_def=_json_loads(row.get("sweep_def_json")),
            status=row.get("status", "pending"),
            total_points=row.get("total_points", 0),
            completed_points=row.get("completed_points", 0),
            created_at=row.get("created_at", ""),
            completed_at=row.get("completed_at", ""),
        )


@dataclass
class ProjectRecord:
    """Top-level design workspace/project."""

    id: Optional[int] = None
    name: str = ""
    technology_id: Optional[int] = None
    description: str = ""
    settings: dict = field(default_factory=dict)
    db_path: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "technology_id": self.technology_id,
            "description": self.description,
            "settings_json": json.dumps(self.settings),
            "db_path": self.db_path,
        }

    @classmethod
    def from_row(cls, row: dict) -> ProjectRecord:
        return cls(
            id=row.get("id"),
            name=row.get("name", ""),
            technology_id=row.get("technology_id"),
            description=row.get("description", ""),
            settings=_json_loads(row.get("settings_json")),
            db_path=row.get("db_path", ""),
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )


@dataclass
class DesignSpecRecord:
    """Formal design specification for a circuit."""

    id: Optional[int] = None
    circuit_id: int = 0
    name: str = ""
    parameter: str = ""
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    typical: Optional[float] = None
    unit: str = ""
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {
            "circuit_id": self.circuit_id,
            "name": self.name,
            "parameter": self.parameter,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "typical": self.typical,
            "unit": self.unit,
            "weight": self.weight,
        }

    @classmethod
    def from_row(cls, row: dict) -> DesignSpecRecord:
        return cls(
            id=row.get("id"),
            circuit_id=row.get("circuit_id", 0),
            name=row.get("name", ""),
            parameter=row.get("parameter", ""),
            min_val=row.get("min_val"),
            max_val=row.get("max_val"),
            typical=row.get("typical"),
            unit=row.get("unit", ""),
            weight=row.get("weight", 1.0),
        )


@dataclass
class CampaignRecord:
    """Validation campaign grouping simulation runs."""

    id: Optional[int] = None
    project_id: Optional[int] = None
    name: str = ""
    description: str = ""
    block_list: list = field(default_factory=list)
    corner_list: list = field(default_factory=list)
    temp_list: list = field(default_factory=list)
    analysis_list: list = field(default_factory=list)
    status: str = "pending"
    total_jobs: int = 0
    completed_jobs: int = 0
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "block_list_json": json.dumps(self.block_list),
            "corner_list_json": json.dumps(self.corner_list),
            "temp_list_json": json.dumps(self.temp_list),
            "analysis_list_json": json.dumps(self.analysis_list),
            "status": self.status,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
        }

    @classmethod
    def from_row(cls, row: dict) -> CampaignRecord:
        return cls(
            id=row.get("id"),
            project_id=row.get("project_id"),
            name=row.get("name", ""),
            description=row.get("description", ""),
            block_list=_json_loads_list(row.get("block_list_json")),
            corner_list=_json_loads_list(row.get("corner_list_json")),
            temp_list=_json_loads_list(row.get("temp_list_json")),
            analysis_list=_json_loads_list(row.get("analysis_list_json")),
            status=row.get("status", "pending"),
            total_jobs=row.get("total_jobs", 0),
            completed_jobs=row.get("completed_jobs", 0),
            created_at=row.get("created_at", ""),
            completed_at=row.get("completed_at", ""),
        )


@dataclass
class CampaignResultRecord:
    """Per-circuit result within a campaign for a specific corner/temp/analysis."""

    id: Optional[int] = None
    campaign_id: int = 0
    circuit_id: int = 0
    corner: str = ""
    temperature: float = 27.0
    analysis_type: str = ""
    result_id: Optional[int] = None
    specs_summary: dict = field(default_factory=dict)
    pass_fail: str = "pending"
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "circuit_id": self.circuit_id,
            "corner": self.corner,
            "temperature": self.temperature,
            "analysis_type": self.analysis_type,
            "result_id": self.result_id,
            "specs_summary_json": json.dumps(self.specs_summary),
            "pass_fail": self.pass_fail,
            "details_json": json.dumps(self.details),
        }

    @classmethod
    def from_row(cls, row: dict) -> CampaignResultRecord:
        return cls(
            id=row.get("id"),
            campaign_id=row.get("campaign_id", 0),
            circuit_id=row.get("circuit_id", 0),
            corner=row.get("corner", ""),
            temperature=row.get("temperature", 27.0),
            analysis_type=row.get("analysis_type", ""),
            result_id=row.get("result_id"),
            specs_summary=_json_loads(row.get("specs_summary_json")),
            pass_fail=row.get("pass_fail", "pending"),
            details=_json_loads(row.get("details_json")),
        )
