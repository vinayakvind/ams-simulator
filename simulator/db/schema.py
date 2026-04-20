"""
Database schema definitions for AMS Simulator.

Defines 15 SQLite tables covering technologies, device models, circuit designs,
simulation configs, results, waveform storage, standard cells, sweep tracking,
projects, design specs, and campaign management.
"""

SCHEMA_VERSION = 2

TABLES_SQL = """
-- technologies: PDK/process definitions
CREATE TABLE IF NOT EXISTS technologies (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    node_nm       INTEGER,
    vdd_nominal   REAL,
    description   TEXT DEFAULT '',
    params_json   TEXT DEFAULT '{}',
    lib_file_path TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- process_corners: TT, FF, SS, SF, FS per technology
CREATE TABLE IF NOT EXISTS process_corners (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    temperature   REAL DEFAULT 27.0,
    voltage_scale REAL DEFAULT 1.0,
    description   TEXT DEFAULT '',
    params_json   TEXT DEFAULT '{}',
    UNIQUE(technology_id, name, temperature)
);

-- device_models: SPICE model cards
CREATE TABLE IF NOT EXISTS device_models (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    corner_id     INTEGER REFERENCES process_corners(id) ON DELETE SET NULL,
    name          TEXT NOT NULL,
    device_type   TEXT NOT NULL,
    level         INTEGER DEFAULT 1,
    params_json   TEXT NOT NULL DEFAULT '{}',
    spice_text    TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    UNIQUE(technology_id, corner_id, name)
);
CREATE INDEX IF NOT EXISTS idx_device_models_tech ON device_models(technology_id);
CREATE INDEX IF NOT EXISTS idx_device_models_type ON device_models(device_type);

-- component_library: reusable subcircuits/cells
CREATE TABLE IF NOT EXISTS component_library (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    category      TEXT DEFAULT 'analog',
    parent_id     INTEGER REFERENCES component_library(id) ON DELETE SET NULL,
    technology_id INTEGER REFERENCES technologies(id),
    pins_json     TEXT NOT NULL DEFAULT '[]',
    params_json   TEXT DEFAULT '{}',
    netlist       TEXT DEFAULT '',
    python_class  TEXT DEFAULT '',
    description   TEXT DEFAULT '',
    author        TEXT DEFAULT '',
    version       TEXT DEFAULT '1.0',
    tags          TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(name, version)
);
CREATE INDEX IF NOT EXISTS idx_component_lib_cat ON component_library(category);
CREATE INDEX IF NOT EXISTS idx_component_lib_parent ON component_library(parent_id);

-- circuits: top-level circuit designs, versioned
CREATE TABLE IF NOT EXISTS circuits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    version       INTEGER NOT NULL DEFAULT 1,
    technology_id INTEGER REFERENCES technologies(id),
    description   TEXT DEFAULT '',
    netlist       TEXT DEFAULT '',
    dsl_script    TEXT DEFAULT '',
    schematic_json TEXT DEFAULT '',
    hierarchy_json TEXT DEFAULT '{}',
    params_json   TEXT DEFAULT '{}',
    author        TEXT DEFAULT '',
    status        TEXT DEFAULT 'draft',
    parent_version_id INTEGER REFERENCES circuits(id) ON DELETE SET NULL,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(name, version)
);
CREATE INDEX IF NOT EXISTS idx_circuits_name ON circuits(name);

-- simulation_configs: analysis setups
CREATE TABLE IF NOT EXISTS simulation_configs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_id    INTEGER NOT NULL REFERENCES circuits(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    analysis_type TEXT NOT NULL,
    settings_json TEXT NOT NULL DEFAULT '{}',
    corner_id     INTEGER REFERENCES process_corners(id),
    temperature   REAL DEFAULT 27.0,
    stimulus_json TEXT DEFAULT '{}',
    measurements_json TEXT DEFAULT '[]',
    description   TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sim_configs_circuit ON simulation_configs(circuit_id);

-- simulation_results: result history with metadata
CREATE TABLE IF NOT EXISTS simulation_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id     INTEGER REFERENCES simulation_configs(id) ON DELETE CASCADE,
    circuit_id    INTEGER NOT NULL REFERENCES circuits(id) ON DELETE CASCADE,
    corner_id     INTEGER REFERENCES process_corners(id),
    status        TEXT NOT NULL DEFAULT 'pending',
    started_at    TEXT,
    completed_at  TEXT,
    elapsed_secs  REAL DEFAULT 0,
    summary_json  TEXT DEFAULT '{}',
    measurements_json TEXT DEFAULT '{}',
    error_message TEXT DEFAULT '',
    engine_version TEXT DEFAULT '',
    host_info     TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sim_results_config ON simulation_results(config_id);
CREATE INDEX IF NOT EXISTS idx_sim_results_circuit ON simulation_results(circuit_id);

-- waveform_data: efficient storage for time-series data
CREATE TABLE IF NOT EXISTS waveform_data (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id     INTEGER NOT NULL REFERENCES simulation_results(id) ON DELETE CASCADE,
    signal_name   TEXT NOT NULL,
    signal_type   TEXT DEFAULT 'voltage',
    num_points    INTEGER NOT NULL,
    min_value     REAL,
    max_value     REAL,
    mean_value    REAL,
    storage_type  TEXT DEFAULT 'blob',
    data_blob     BLOB,
    file_path     TEXT DEFAULT '',
    dtype         TEXT DEFAULT 'float64',
    UNIQUE(result_id, signal_name)
);
CREATE INDEX IF NOT EXISTS idx_waveform_result ON waveform_data(result_id);

-- standard_cells: for SoC-scale digital backbone
CREATE TABLE IF NOT EXISTS standard_cells (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    technology_id INTEGER NOT NULL REFERENCES technologies(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    cell_type     TEXT NOT NULL,
    drive_strength INTEGER DEFAULT 1,
    pins_json     TEXT NOT NULL DEFAULT '[]',
    timing_json   TEXT DEFAULT '{}',
    power_json    TEXT DEFAULT '{}',
    area          REAL DEFAULT 0,
    netlist       TEXT DEFAULT '',
    behavioral_model TEXT DEFAULT '',
    liberty_data  TEXT DEFAULT '',
    UNIQUE(technology_id, name)
);
CREATE INDEX IF NOT EXISTS idx_stdcells_tech ON standard_cells(technology_id);

-- sweep_runs: parameter/corner/Monte Carlo sweep runs
CREATE TABLE IF NOT EXISTS sweep_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_id    INTEGER NOT NULL REFERENCES circuits(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    sweep_type    TEXT NOT NULL,
    sweep_def_json TEXT NOT NULL DEFAULT '{}',
    status        TEXT DEFAULT 'pending',
    total_points  INTEGER DEFAULT 0,
    completed_points INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now')),
    completed_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_sweep_runs_circuit ON sweep_runs(circuit_id);

-- sweep_points: individual points in a sweep
CREATE TABLE IF NOT EXISTS sweep_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sweep_run_id  INTEGER NOT NULL REFERENCES sweep_runs(id) ON DELETE CASCADE,
    result_id     INTEGER NOT NULL REFERENCES simulation_results(id) ON DELETE CASCADE,
    point_index   INTEGER NOT NULL,
    params_json   TEXT NOT NULL DEFAULT '{}',
    UNIQUE(sweep_run_id, point_index)
);

-- projects: top-level design workspaces
CREATE TABLE IF NOT EXISTS projects (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    technology_id INTEGER REFERENCES technologies(id),
    description   TEXT DEFAULT '',
    settings_json TEXT DEFAULT '{}',
    db_path       TEXT DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);

-- design_specs: formal specification records per circuit
CREATE TABLE IF NOT EXISTS design_specs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    circuit_id    INTEGER NOT NULL REFERENCES circuits(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    parameter     TEXT NOT NULL,
    min_val       REAL,
    max_val       REAL,
    typical       REAL,
    unit          TEXT DEFAULT '',
    weight        REAL DEFAULT 1.0,
    UNIQUE(circuit_id, name)
);
CREATE INDEX IF NOT EXISTS idx_design_specs_circuit ON design_specs(circuit_id);

-- campaigns: validation campaign grouping
CREATE TABLE IF NOT EXISTS campaigns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    description      TEXT DEFAULT '',
    block_list_json  TEXT DEFAULT '[]',
    corner_list_json TEXT DEFAULT '[]',
    temp_list_json   TEXT DEFAULT '[]',
    analysis_list_json TEXT DEFAULT '[]',
    status           TEXT DEFAULT 'pending',
    total_jobs       INTEGER DEFAULT 0,
    completed_jobs   INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT (datetime('now')),
    completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_campaigns_project ON campaigns(project_id);

-- campaign_results: per-circuit aggregated results within a campaign
CREATE TABLE IF NOT EXISTS campaign_results (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id       INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    circuit_id        INTEGER NOT NULL REFERENCES circuits(id) ON DELETE CASCADE,
    corner            TEXT DEFAULT '',
    temperature       REAL DEFAULT 27.0,
    analysis_type     TEXT DEFAULT '',
    result_id         INTEGER REFERENCES simulation_results(id) ON DELETE SET NULL,
    specs_summary_json TEXT DEFAULT '{}',
    pass_fail         TEXT DEFAULT 'pending',
    details_json      TEXT DEFAULT '{}',
    UNIQUE(campaign_id, circuit_id, corner, temperature, analysis_type)
);
CREATE INDEX IF NOT EXISTS idx_campaign_results_campaign ON campaign_results(campaign_id);

-- schema metadata
CREATE TABLE IF NOT EXISTS _schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_schema_sql() -> str:
    """Return the full schema SQL for table creation."""
    return TABLES_SQL
