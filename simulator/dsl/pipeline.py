"""
Pipeline - Simulation campaign orchestrator.

Generates the simulation matrix (blocks x analyses x corners x temps),
runs jobs in parallel, stores results in DB, checks specs, and returns
a CampaignResult with summary/report/comparison capabilities.
"""

from __future__ import annotations

import json
import time
import platform
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from simulator.dsl.project import Project

from simulator.db.connection import SimDB
from simulator.db.models import (
    CampaignRecord,
    CampaignResultRecord,
    SimulationConfig,
    SimulationResult,
)
from simulator.db import queries
from simulator.dsl.block import Block, SpecDef
from simulator.engine.analog_engine import (
    AnalogEngine,
    DCAnalysis,
    ACAnalysis,
    TransientAnalysis,
)


# ── Data classes for jobs ───────────────────────────────────


@dataclass
class SimJob:
    """A single simulation task in the matrix."""
    block_name: str
    analysis_type: str
    corner: str
    temperature: float
    netlist: str
    circuit_id: int = 0
    config_id: Optional[int] = None


@dataclass
class SimJobResult:
    """Result of a single simulation job."""
    job: SimJob
    status: str = "pending"  # completed, failed, error
    results: dict = field(default_factory=dict)
    elapsed_secs: float = 0.0
    error_message: str = ""
    result_id: Optional[int] = None


# ── Pipeline ────────────────────────────────────────────────


class Pipeline:
    """Orchestrates a multi-block, multi-corner, multi-temp simulation campaign."""

    def __init__(self, project: Project):
        self._project = project
        self._db = project.db

    def execute(
        self,
        blocks: list[str],
        analyses: list[str],
        corners: list[str],
        temps: list[float],
        specs: Optional[dict[str, dict]] = None,
        auto_design: bool = False,
        max_workers: Optional[int] = None,
    ) -> CampaignResult:
        """Execute a full simulation campaign.

        Steps:
            1. Create campaign record in DB
            2. Load blocks, build simulation matrix
            3. Run all jobs in parallel
            4. Store results in DB
            5. Check specs
            6. Return CampaignResult
        """
        if specs is None:
            specs = {}

        # 1. Create campaign record
        total_jobs = len(blocks) * len(analyses) * len(corners) * len(temps)
        campaign_name = (
            f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        campaign = CampaignRecord(
            project_id=self._project.project_id,
            name=campaign_name,
            block_list=blocks,
            corner_list=corners,
            temp_list=temps,
            analysis_list=analyses,
            status="running",
            total_jobs=total_jobs,
        )
        campaign_id = queries.save_campaign(self._db, campaign)
        self._db.commit()

        print(f"Campaign: {campaign_name}")
        print(f"  Blocks: {blocks}")
        print(f"  Analyses: {analyses}")
        print(f"  Corners: {corners}")
        print(f"  Temps: {temps}")
        print(f"  Total jobs: {total_jobs}")
        print()

        # 2. Build job matrix
        loaded_blocks: dict[str, Block] = {}
        jobs: list[SimJob] = []

        for block_name in blocks:
            block = Block.load(self._project, block_name)
            loaded_blocks[block_name] = block

            for corner in corners:
                for temp in temps:
                    netlist = block.to_netlist(corner=corner, temp=temp)
                    for analysis in analyses:
                        job = SimJob(
                            block_name=block_name,
                            analysis_type=analysis,
                            corner=corner,
                            temperature=temp,
                            netlist=netlist,
                            circuit_id=block.circuit_id or 0,
                        )
                        jobs.append(job)

        # 3. Run all jobs
        print(f"Running {len(jobs)} simulations...")
        start_time = time.time()

        workers = max_workers or min(4, len(jobs))
        job_results: list[SimJobResult] = []

        if workers <= 1 or len(jobs) <= 1:
            # Sequential execution
            for i, job in enumerate(jobs):
                result = self._run_single_sim(job)
                job_results.append(result)
                status_char = "+" if result.status == "completed" else "x"
                print(
                    f"  [{status_char}] {job.block_name} / {job.analysis_type} / "
                    f"{job.corner} / {job.temperature}C  ({result.elapsed_secs:.2f}s)"
                )
        else:
            # Parallel execution
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(self._run_single_sim, job): job
                    for job in jobs
                }
                for future in as_completed(futures):
                    result = future.result()
                    job_results.append(result)
                    status_char = "+" if result.status == "completed" else "x"
                    print(
                        f"  [{status_char}] {result.job.block_name} / "
                        f"{result.job.analysis_type} / {result.job.corner} / "
                        f"{result.job.temperature}C  ({result.elapsed_secs:.2f}s)"
                    )

        total_elapsed = time.time() - start_time
        completed_count = sum(1 for r in job_results if r.status == "completed")
        print(f"\nCompleted: {completed_count}/{len(jobs)} in {total_elapsed:.2f}s")

        # 4. Store results in DB
        for jr in job_results:
            self._store_result(jr, campaign_id)

        # 5. Check specs and store campaign results
        block_reports: dict[str, list[dict]] = {}
        for block_name in blocks:
            block = loaded_blocks[block_name]
            block_jobs = [r for r in job_results if r.job.block_name == block_name]
            block_specs = specs.get(block_name, {})

            report = self._check_specs(
                block_name, block, block_jobs, block_specs, campaign_id
            )
            block_reports[block_name] = report

        # 6. Update campaign status
        queries.update_campaign_status(
            self._db, campaign_id, "completed", completed_count
        )
        self._db.commit()

        return CampaignResult(
            campaign_id=campaign_id,
            db=self._db,
            block_reports=block_reports,
            job_results=job_results,
            elapsed_secs=total_elapsed,
        )

    def _run_single_sim(self, job: SimJob) -> SimJobResult:
        """Run one simulation job. Thread-safe (creates its own engine)."""
        start = time.time()
        try:
            engine = AnalogEngine()
            engine.load_netlist(job.netlist)

            if job.analysis_type == "dc":
                analysis = DCAnalysis(engine)
                results = analysis.run({})
            elif job.analysis_type == "ac":
                analysis = ACAnalysis(engine)
                results = analysis.run({
                    "variation": "decade",
                    "points": 10,
                    "fstart": 1,
                    "fstop": 1e6,
                })
            elif job.analysis_type == "transient":
                analysis = TransientAnalysis(engine)
                results = analysis.run({
                    "tstop": 1e-3,
                    "tstep": 1e-6,
                    "tstart": 0,
                })
            else:
                return SimJobResult(
                    job=job,
                    status="failed",
                    error_message=f"Unknown analysis type: {job.analysis_type}",
                    elapsed_secs=time.time() - start,
                )

            return SimJobResult(
                job=job,
                status="completed",
                results=results or {},
                elapsed_secs=time.time() - start,
            )

        except Exception as e:
            return SimJobResult(
                job=job,
                status="failed",
                error_message=str(e),
                elapsed_secs=time.time() - start,
            )

    def _store_result(self, jr: SimJobResult, campaign_id: int) -> None:
        """Store a job result in the DB."""
        # Save simulation config
        config = SimulationConfig(
            circuit_id=jr.job.circuit_id,
            name=f"{jr.job.block_name}_{jr.job.analysis_type}_{jr.job.corner}_{jr.job.temperature}",
            analysis_type=jr.job.analysis_type,
            temperature=jr.job.temperature,
            settings={"corner": jr.job.corner},
        )
        config_id = queries.save_simulation_config(self._db, config)

        # Serialize results for storage (convert numpy arrays to lists)
        summary = {}
        measurements = {}
        if jr.results:
            for key, val in jr.results.items():
                try:
                    if hasattr(val, 'tolist'):
                        # numpy array
                        arr = val.tolist()
                        if isinstance(arr, list) and len(arr) > 0:
                            measurements[key] = {
                                "min": float(min(arr)) if arr else 0,
                                "max": float(max(arr)) if arr else 0,
                                "last": float(arr[-1]) if arr else 0,
                            }
                    elif isinstance(val, (int, float)):
                        summary[key] = float(val)
                    elif isinstance(val, dict):
                        summary[key] = val
                except (TypeError, ValueError):
                    pass

        # Save result
        result = SimulationResult(
            config_id=config_id,
            circuit_id=jr.job.circuit_id,
            status=jr.status,
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            elapsed_secs=jr.elapsed_secs,
            summary=summary,
            measurements=measurements,
            error_message=jr.error_message,
            engine_version="ams-dsl-2.0",
            host_info=platform.node(),
        )
        result_id = queries.save_result(self._db, result)
        jr.result_id = result_id
        self._db.commit()

    def _check_specs(
        self,
        block_name: str,
        block: Block,
        job_results: list[SimJobResult],
        user_specs: dict,
        campaign_id: int,
    ) -> list[dict]:
        """Check simulation results against specs. Returns per-job spec reports."""
        reports = []

        # Merge block-defined specs with user-provided specs
        all_specs: dict[str, tuple] = {}
        for s in block.specs:
            all_specs[s.parameter] = (s.min_val, s.max_val, s.unit)
        for signal, spec_tuple in user_specs.items():
            if isinstance(spec_tuple, (list, tuple)) and len(spec_tuple) >= 2:
                min_v = spec_tuple[0]
                max_v = spec_tuple[1]
                unit = spec_tuple[2] if len(spec_tuple) > 2 else ""
                all_specs[signal] = (min_v, max_v, unit)

        for jr in job_results:
            spec_results: dict[str, dict] = {}
            overall_pass = True

            if jr.status != "completed":
                overall_pass = False
                spec_results["_simulation"] = {
                    "status": "fail",
                    "message": jr.error_message or "Simulation failed",
                }
            else:
                for signal, (min_v, max_v, unit) in all_specs.items():
                    measured = self._extract_measurement(jr.results, signal)
                    if measured is None:
                        spec_results[signal] = {
                            "status": "skip",
                            "message": f"Signal '{signal}' not found in results",
                        }
                        continue

                    passed = True
                    if min_v is not None and measured < min_v:
                        passed = False
                    if max_v is not None and measured > max_v:
                        passed = False

                    spec_results[signal] = {
                        "status": "pass" if passed else "fail",
                        "measured": measured,
                        "min": min_v,
                        "max": max_v,
                        "unit": unit,
                    }
                    if not passed:
                        overall_pass = False

            pass_fail = "pass" if overall_pass else "fail"

            # Store campaign result
            cr = CampaignResultRecord(
                campaign_id=campaign_id,
                circuit_id=jr.job.circuit_id,
                corner=jr.job.corner,
                temperature=jr.job.temperature,
                analysis_type=jr.job.analysis_type,
                result_id=jr.result_id,
                specs_summary=spec_results,
                pass_fail=pass_fail,
                details={"elapsed": jr.elapsed_secs},
            )
            queries.save_campaign_result(self._db, cr)

            reports.append({
                "block": block_name,
                "corner": jr.job.corner,
                "temp": jr.job.temperature,
                "analysis": jr.job.analysis_type,
                "pass_fail": pass_fail,
                "specs": spec_results,
                "elapsed": jr.elapsed_secs,
            })

        self._db.commit()
        return reports

    def _extract_measurement(self, results: dict, signal: str) -> Optional[float]:
        """Extract a scalar measurement from simulation results.

        Handles patterns like V(vout), I(rload), just 'vout', etc.
        """
        if not results:
            return None

        # Direct key match
        if signal in results:
            val = results[signal]
            if hasattr(val, '__len__') and len(val) > 0:
                return float(val[-1])  # Last value for transient
            if isinstance(val, (int, float)):
                return float(val)

        # Try V(node) pattern -> look for 'node' key in node_voltages
        import re
        m = re.match(r'V\((\w+)\)', signal, re.IGNORECASE)
        if m:
            node = m.group(1)
            # Check node_voltages dict
            nv = results.get("node_voltages", {})
            if node in nv:
                val = nv[node]
                if hasattr(val, '__len__') and len(val) > 0:
                    return float(val[-1])
                return float(val)
            # Check top-level
            if node in results:
                val = results[node]
                if hasattr(val, '__len__') and len(val) > 0:
                    return float(val[-1])
                return float(val)

        return None


# ── CampaignResult ──────────────────────────────────────────


class CampaignResult:
    """User-facing result object from a simulation campaign."""

    def __init__(
        self,
        campaign_id: int,
        db: SimDB,
        block_reports: dict[str, list[dict]],
        job_results: list[SimJobResult],
        elapsed_secs: float = 0.0,
    ):
        self._campaign_id = campaign_id
        self._db = db
        self._block_reports = block_reports
        self._job_results = job_results
        self._elapsed = elapsed_secs

    @property
    def campaign_id(self) -> int:
        return self._campaign_id

    @property
    def passed(self) -> bool:
        """True if all blocks passed all specs across all corners/temps."""
        for reports in self._block_reports.values():
            for r in reports:
                if r["pass_fail"] != "pass":
                    return False
        return True

    @property
    def total_jobs(self) -> int:
        return len(self._job_results)

    @property
    def completed_jobs(self) -> int:
        return sum(1 for r in self._job_results if r.status == "completed")

    @property
    def failed_jobs(self) -> int:
        return sum(1 for r in self._job_results if r.status == "failed")

    def summary(self) -> None:
        """Print a formatted summary table to stdout."""
        print("=" * 72)
        print(f"CAMPAIGN SUMMARY (ID: {self._campaign_id})")
        print(f"Total time: {self._elapsed:.2f}s")
        print(f"Jobs: {self.completed_jobs}/{self.total_jobs} completed, "
              f"{self.failed_jobs} failed")
        print("=" * 72)

        for block_name, reports in self._block_reports.items():
            block_pass = all(r["pass_fail"] == "pass" for r in reports)
            status = "PASS" if block_pass else "FAIL"
            print(f"\n  Block: {block_name}  [{status}]")
            print(f"  {'Corner':<8} {'Temp':>6} {'Analysis':<12} {'Status':<8} {'Time':>8}")
            print(f"  {'-'*8} {'-'*6} {'-'*12} {'-'*8} {'-'*8}")

            for r in reports:
                pf = r["pass_fail"].upper()
                print(
                    f"  {r['corner']:<8} {r['temp']:>5.0f}C {r['analysis']:<12} "
                    f"{pf:<8} {r['elapsed']:>7.2f}s"
                )

                # Show spec details for failures
                if pf == "FAIL":
                    for signal, detail in r.get("specs", {}).items():
                        if isinstance(detail, dict) and detail.get("status") == "fail":
                            measured = detail.get("measured", "N/A")
                            min_v = detail.get("min", "")
                            max_v = detail.get("max", "")
                            if isinstance(measured, float):
                                print(
                                    f"           -> {signal}: {measured:.4g} "
                                    f"(range: {min_v} to {max_v})"
                                )

        overall = "PASS" if self.passed else "FAIL"
        print(f"\n{'='*72}")
        print(f"Overall: {overall}")
        print(f"{'='*72}")

    def report(self, filename: str) -> None:
        """Generate an HTML or Markdown report file."""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "md"
        content = self._generate_report_content(ext)

        from pathlib import Path
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"Report saved: {path.resolve()}")

    def _generate_report_content(self, fmt: str) -> str:
        """Generate report content in HTML or Markdown."""
        if fmt == "html":
            return self._generate_html_report()
        return self._generate_md_report()

    def _generate_md_report(self) -> str:
        """Generate Markdown report."""
        lines = [
            f"# Campaign Report (ID: {self._campaign_id})",
            "",
            f"- **Total time**: {self._elapsed:.2f}s",
            f"- **Jobs**: {self.completed_jobs}/{self.total_jobs} completed",
            f"- **Overall**: {'PASS' if self.passed else 'FAIL'}",
            "",
        ]

        for block_name, reports in self._block_reports.items():
            block_pass = all(r["pass_fail"] == "pass" for r in reports)
            lines.append(f"## Block: {block_name} [{'PASS' if block_pass else 'FAIL'}]")
            lines.append("")
            lines.append("| Corner | Temp | Analysis | Status | Time |")
            lines.append("|--------|------|----------|--------|------|")

            for r in reports:
                pf = r["pass_fail"].upper()
                lines.append(
                    f"| {r['corner']} | {r['temp']:.0f}C | "
                    f"{r['analysis']} | {pf} | {r['elapsed']:.2f}s |"
                )

            lines.append("")

            # Spec details
            for r in reports:
                for signal, detail in r.get("specs", {}).items():
                    if isinstance(detail, dict) and detail.get("status") == "fail":
                        measured = detail.get("measured", "N/A")
                        min_v = detail.get("min", "")
                        max_v = detail.get("max", "")
                        lines.append(
                            f"- **FAIL** {r['corner']}/{r['temp']}C: "
                            f"{signal} = {measured} (expected {min_v} to {max_v})"
                        )
            lines.append("")

        return "\n".join(lines)

    def _generate_html_report(self) -> str:
        """Generate HTML report."""
        overall = "PASS" if self.passed else "FAIL"
        color = "#28a745" if self.passed else "#dc3545"

        rows_html = ""
        for block_name, reports in self._block_reports.items():
            for r in reports:
                pf = r["pass_fail"].upper()
                row_color = "#d4edda" if pf == "PASS" else "#f8d7da"
                rows_html += f"""
                <tr style="background:{row_color}">
                    <td>{block_name}</td>
                    <td>{r['corner']}</td>
                    <td>{r['temp']:.0f}C</td>
                    <td>{r['analysis']}</td>
                    <td><strong>{pf}</strong></td>
                    <td>{r['elapsed']:.2f}s</td>
                </tr>"""

        return f"""<!DOCTYPE html>
<html><head>
<title>Campaign Report #{self._campaign_id}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 2em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #dee2e6; padding: 8px 12px; text-align: left; }}
th {{ background: #343a40; color: white; }}
.status {{ font-size: 1.5em; font-weight: bold; color: {color}; }}
</style>
</head><body>
<h1>Campaign Report</h1>
<p>Campaign ID: {self._campaign_id}</p>
<p>Total time: {self._elapsed:.2f}s | Jobs: {self.completed_jobs}/{self.total_jobs}</p>
<p class="status">Overall: {overall}</p>
<table>
<tr><th>Block</th><th>Corner</th><th>Temp</th><th>Analysis</th><th>Status</th><th>Time</th></tr>
{rows_html}
</table>
</body></html>"""

    def get_block_report(self, block_name: str) -> list[dict]:
        """Get detailed spec report for a specific block."""
        return self._block_reports.get(block_name, [])

    def get_worst_case(self, block_name: str) -> Optional[dict]:
        """Identify the worst corner/temp combination for a block."""
        reports = self._block_reports.get(block_name, [])
        failures = [r for r in reports if r["pass_fail"] == "fail"]
        if failures:
            return failures[0]
        return None

    def compare_with(self, other_campaign_id: int) -> dict:
        """Compare this campaign against another."""
        this_summary = queries.get_campaign_summary(self._db, self._campaign_id)
        other_summary = queries.get_campaign_summary(self._db, other_campaign_id)
        return {
            "current": this_summary,
            "other": other_summary,
            "current_passed": this_summary.get("all_passed", False),
            "other_passed": other_summary.get("all_passed", False),
        }

    def __repr__(self) -> str:
        return (
            f"CampaignResult(id={self._campaign_id}, "
            f"passed={self.passed}, "
            f"jobs={self.completed_jobs}/{self.total_jobs})"
        )
