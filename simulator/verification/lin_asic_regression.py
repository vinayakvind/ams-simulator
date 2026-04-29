"""LIN ASIC regression runner and test-case catalog."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any, Callable, Optional

from simulator.api.server import (
    _ASIC_BLOCK_TESTS,
    _check_block_pass,
    _evaluate_block,
    _get_asic_block_catalog,
    _read_asic_design_file,
    _run_asic_mixed_signal_flow,
    _run_lin_controller_rtl_test,
    _run_spi_controller_rtl_test,
)
from simulator.engine.analog_engine import AnalogEngine, TransientAnalysis
from simulator.engine.rtl_engine import RTLSimulator


ROOT = Path(__file__).resolve().parents[2]
ASIC_ROOT = ROOT / "designs" / "lin_asic"


def _console_safe(text: str) -> str:
    """Return text that can be printed on the current console encoding."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def get_default_report_paths() -> dict[str, Path]:
    """Return default JSON and Markdown output locations for ASIC regressions."""
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return {
        "json": reports_dir / "lin_asic_regression_latest.json",
        "markdown": reports_dir / "lin_asic_regression_latest.md",
        "log": reports_dir / "lin_asic_regression_latest.log",
    }


def build_lin_asic_test_catalog() -> list[dict[str, Any]]:
    """Return the GUI/API-visible LIN ASIC test catalog."""
    return [
        {
            "case_id": "ANA-BGR-STARTUP",
            "block": "Bandgap Reference",
            "category": "Analog",
            "standard": "Internal analog spec",
            "description": "VREF startup from power-on; 1.14V to 1.26V steady-state target.",
        },
        {
            "case_id": "ANA-LDO-3V3",
            "block": "LDO Analog Supply",
            "category": "Analog",
            "standard": "Internal power-tree spec",
            "description": "12V to 3.3V regulation during startup and steady-state.",
        },
        {
            "case_id": "ANA-LDO-1V8",
            "block": "LDO Digital Supply",
            "category": "Analog",
            "standard": "Internal power-tree spec",
            "description": "3.3V to 1.8V regulation for digital core domain.",
        },
        {
            "case_id": "ANA-LDO-5V0",
            "block": "LDO LIN Supply",
            "category": "Analog",
            "standard": "LIN PHY supply requirement",
            "description": "12V to 5V LIN supply startup and steady-state regulation.",
        },
        {
            "case_id": "ANA-LIN-BUS-SWING",
            "block": "LIN Transceiver",
            "category": "Mixed",
            "standard": "ISO 17987 / LIN 2.2A",
            "description": "Dominant and recessive bus voltage swing on the single-wire LIN bus.",
        },
        {
            "case_id": "DIG-SPI-DECODE",
            "block": "SPI Controller",
            "category": "Digital",
            "standard": "SPI slave protocol",
            "description": "Command framing and register address/data decode from the SPI slave RTL.",
        },
        {
            "case_id": "DIG-REGFILE-CONTROL",
            "block": "Register File",
            "category": "Digital",
            "standard": "LIN ASIC register map",
            "description": "Reset defaults, write/read decode, and control-output fanout from the register bank.",
        },
        {
            "case_id": "DIG-LIN-CTRL",
            "block": "LIN Controller",
            "category": "Digital",
            "standard": "ISO 17987 / LIN 2.2A",
            "description": "Reset path, master/slave readiness, and break/sync state-machine reachability.",
        },
        {
            "case_id": "DIG-CTRL-SEQUENCE",
            "block": "Control Logic",
            "category": "Digital",
            "standard": "Internal startup-sequencing spec",
            "description": "POR release and staged enable sequencing for BGR/LDO/LIN blocks.",
        },
        {
            "case_id": "TOP-MS-BRIDGE",
            "block": "LIN Mixed-Signal Interface",
            "category": "Top",
            "standard": "ISO 17987 / LIN 2.2A",
            "description": "Digital TXD drives analog LIN bus and analog LIN bus reconstructs RXD logic.",
        },
    ]


def _run_analog_case(case_id: str, block_name: str, spec: dict) -> dict[str, Any]:
    t_start = datetime.now()
    engine = AnalogEngine()
    engine.load_netlist(spec["netlist"])
    sim_results = TransientAnalysis(engine).run(spec["settings"])
    meas = _evaluate_block(block_name, spec, sim_results)
    passed = _check_block_pass(block_name, spec, meas)
    elapsed_ms = round((datetime.now() - t_start).total_seconds() * 1000, 1)
    detail = spec["what_is_tested"]
    if block_name == "lin_transceiver":
        detail += f" High={meas.get('output_peak', 0):.3f}V Low={meas.get('output_valley', 0):.3f}V."
    else:
        detail += f" Mean={meas.get('output_steady_mean', 0):.3f}V."
    return {
        "case_id": case_id,
        "block": block_name,
        "status": "PASS" if passed else "FAIL",
        "details": detail,
        "measurements": meas,
        "elapsed_ms": elapsed_ms,
    }


def _run_register_file_rtl_test() -> dict[str, Any]:
    catalog = _get_asic_block_catalog()["register_file"]
    code = _read_asic_design_file(catalog.get("rtl_file"))
    if not code:
        raise RuntimeError("register_file RTL source is missing")

    sim = RTLSimulator()
    sim._clk_sig = "clk"
    sim._rst_sig = "rst_n"
    sim.load_verilog(code)
    sim.set_input("reg_addr", 0)
    sim.set_input("reg_wdata", 0)
    sim.set_input("reg_wr", 0)
    sim.set_input("reg_rd", 0)
    sim.set_input("lin_rx_data", 0)
    sim.set_input("irq_flag", 0)
    sim.reset(cycles=2)
    sim.tick(1)

    default_mask = (
        (sim.get_output("bgr_en") << 3) |
        (sim.get_output("ldo_lin_en") << 2) |
        (sim.get_output("ldo_dig_en") << 1) |
        sim.get_output("ldo_ana_en")
    )

    sim.set_input("reg_addr", 0x02)
    sim.set_input("reg_wdata", 0x12)
    sim.set_input("reg_wr", 1)
    sim.tick(1)
    sim.set_input("reg_wr", 0)
    sim.tick(1)

    sim.set_input("reg_addr", 0x11)
    sim.set_input("reg_wdata", 0x02)
    sim.set_input("reg_wr", 1)
    sim.tick(1)
    sim.set_input("reg_addr", 0x12)
    sim.set_input("reg_wdata", 0x34)
    sim.tick(1)
    sim.set_input("reg_wr", 0)
    sim.tick(1)

    measurements = {
        "default_power_mask": default_mask,
        "lin_en_after_reset": sim.get_output("lin_en"),
        "sleep_mode_after_write": sim.get_output("sleep_mode"),
        "baud_div_after_write": sim.get_output("baud_div"),
    }
    passed = (
        measurements["default_power_mask"] == 0x0F and
        measurements["lin_en_after_reset"] == 1 and
        measurements["sleep_mode_after_write"] == 1 and
        measurements["baud_div_after_write"] == 0x0234
    )
    return {
        "case_id": "DIG-REGFILE-CONTROL",
        "block": "register_file",
        "status": "PASS" if passed else "FAIL",
        "details": (
            "Reset defaults, CTRL register write, and baud-divisor fanout were exercised "
            f"(mask=0x{default_mask:02X}, baud_div=0x{measurements['baud_div_after_write']:04X})."
        ),
        "measurements": measurements,
    }


def _run_control_logic_rtl_test() -> dict[str, Any]:
    catalog = _get_asic_block_catalog()["control_logic"]
    code = _read_asic_design_file(catalog.get("rtl_file"))
    if not code:
        raise RuntimeError("control_logic RTL source is missing")

    sim = RTLSimulator()
    sim._clk_sig = "clk_in"
    sim._rst_sig = "rst_n"
    sim.load_verilog(code)
    sim.set_input("sleep_mode", 0)
    sim.set_input("bgr_req", 1)
    sim.set_input("ldo_ana_req", 1)
    sim.set_input("ldo_dig_req", 1)
    sim.set_input("ldo_lin_req", 1)
    sim.set_input("lin_req", 1)
    sim.reset(cycles=2)
    sim.tick(10)

    measurements = {
        "bgr_en": sim.get_output("bgr_en"),
        "ldo_ana_en": sim.get_output("ldo_ana_en"),
        "ldo_dig_en": sim.get_output("ldo_dig_en"),
        "ldo_lin_en": sim.get_output("ldo_lin_en"),
        "lin_en": sim.get_output("lin_en"),
        "por_n": sim.get_output("por_n"),
        "clk_out": sim.get_output("clk_out"),
    }

    sim.set_input("sleep_mode", 1)
    sim.tick(1)
    measurements["lin_en_in_sleep"] = sim.get_output("lin_en")

    passed = (
        measurements["bgr_en"] == 1 and
        measurements["ldo_ana_en"] == 1 and
        measurements["ldo_dig_en"] == 1 and
        measurements["ldo_lin_en"] == 1 and
        measurements["lin_en"] == 1 and
        measurements["por_n"] == 1 and
        measurements["lin_en_in_sleep"] == 0
    )
    return {
        "case_id": "DIG-CTRL-SEQUENCE",
        "block": "control_logic",
        "status": "PASS" if passed else "FAIL",
        "details": "Power sequence advanced through BGR, analog LDO, digital LDO, LIN enable, then de-asserted LIN in sleep mode.",
        "measurements": measurements,
    }


def _build_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("status") == "PASS")
    failed = sum(1 for result in results if result.get("status") != "PASS")
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "overall": "PASS" if failed == 0 else "FAIL",
    }


def _build_coverage(summary: dict[str, Any], catalog: list[dict[str, Any]]) -> dict[str, Any]:
    functional_percent = 100.0 * summary["passed"] / max(1, summary["total"])
    standards_cases = sum(1 for entry in catalog if "ISO 17987" in entry.get("standard", "") or "LIN" in entry.get("standard", ""))
    standards_percent = 100.0 * standards_cases / max(1, len(catalog))
    return {
        "functional_percent": functional_percent,
        "standards_percent": standards_percent,
    }


def _write_markdown_report(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# LIN ASIC Regression Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Standard Target: {report['standard']}",
        f"- Overall: {report['summary']['overall']}",
        "",
        "## Summary",
        "",
        f"- Total tests: {report['summary']['total']}",
        f"- Passed: {report['summary']['passed']}",
        f"- Failed: {report['summary']['failed']}",
        f"- Functional coverage: {report['coverage']['functional_percent']:.1f}%",
        f"- Standards-linked coverage: {report['coverage']['standards_percent']:.1f}%",
        "",
        "## Test Results",
        "",
        "| Case ID | Block | Status | Details |",
        "|---------|-------|--------|---------|",
    ]
    for test in report["tests"]:
        lines.append(
            f"| {test['case_id']} | {test['block']} | {test['status']} | {test['details']} |"
        )
    if report.get("log_path"):
        lines.append("")
        lines.append(f"Regression log: {report['log_path']}")
    lines.append("")
    lines.append(f"## Test Plan\n\nSee {report['test_plan_path']} for the detailed ASIC test plan.")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_lin_asic_regression(
    json_path: Optional[Path] = None,
    markdown_path: Optional[Path] = None,
    log_path: Optional[Path] = None,
    verbose: bool = True,
    emit: Optional[Callable[[str], None]] = None,
) -> dict[str, Any]:
    """Run the LIN ASIC regression suite and optionally write reports to disk."""
    default_paths = get_default_report_paths()
    json_path = Path(json_path or default_paths["json"])
    markdown_path = Path(markdown_path or default_paths["markdown"])
    log_path = Path(log_path or default_paths["log"])

    catalog = build_lin_asic_test_catalog()
    results: list[dict[str, Any]] = []

    analog_case_ids = {
        "bandgap": "ANA-BGR-STARTUP",
        "ldo_analog": "ANA-LDO-3V3",
        "ldo_digital": "ANA-LDO-1V8",
        "ldo_lin": "ANA-LDO-5V0",
        "lin_transceiver": "ANA-LIN-BUS-SWING",
    }

    def _emit_result(result: dict[str, Any]) -> None:
        if not verbose:
            return
        message = f"[{result['status']}] {result['case_id']} - {result['details']}"
        if emit is not None:
            emit(message)
        else:
            print(_console_safe(message))

    for block_name, spec in _ASIC_BLOCK_TESTS.items():
        result = _run_analog_case(analog_case_ids[block_name], block_name, spec)
        results.append(result)
        _emit_result(result)

    spi_result = _run_spi_controller_rtl_test()
    results.append({
        "case_id": "DIG-SPI-DECODE",
        "block": "spi_controller",
        "status": spi_result["status"],
        "details": spi_result["what_is_tested"],
        "measurements": spi_result.get("measurements", {}),
    })
    _emit_result(results[-1])

    reg_result = _run_register_file_rtl_test()
    results.append(reg_result)
    _emit_result(reg_result)

    lin_result = _run_lin_controller_rtl_test()
    results.append({
        "case_id": "DIG-LIN-CTRL",
        "block": "lin_controller",
        "status": lin_result["status"],
        "details": lin_result["what_is_tested"],
        "measurements": lin_result.get("measurements", {}),
    })
    _emit_result(results[-1])

    ctrl_result = _run_control_logic_rtl_test()
    results.append(ctrl_result)
    _emit_result(ctrl_result)

    mixed_report = _run_asic_mixed_signal_flow()
    results.append({
        "case_id": "TOP-MS-BRIDGE",
        "block": "lin_mixed_signal_interface",
        "status": mixed_report["mixed_signal"]["status"],
        "details": mixed_report["mixed_signal"]["what_is_tested"],
        "measurements": mixed_report["mixed_signal"].get("measurements", {}),
    })
    _emit_result(results[-1])

    summary = _build_summary(results)
    coverage = _build_coverage(summary, catalog)
    report = {
        "chip": "LIN_ASIC",
        "generated_at": datetime.now().isoformat(),
        "standard": "ISO 17987 / LIN 2.2A",
        "summary": summary,
        "coverage": coverage,
        "tests": results,
        "test_cases": catalog,
        "report_path": str(json_path),
        "markdown_report_path": str(markdown_path),
        "log_path": str(log_path),
        "test_plan_path": str(ASIC_ROOT / "LIN_ASIC_TESTPLAN.md"),
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    _write_markdown_report(report, markdown_path)
    return report