"""
Batch Simulation Runner - Parallel execution of multiple simulations.
"""

import argparse
import sys
import json
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing

from simulator.cli.runner import SimulationRunner


@dataclass
class BatchJob:
    """A single batch simulation job."""
    id: str
    netlist_path: str
    analysis_type: str
    output_file: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = 'pending'  # pending, running, completed, failed
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0


class BatchRunner:
    """
    Batch simulation runner with parallel execution support.
    """
    
    def __init__(self, max_workers: Optional[int] = None, verbose: bool = False):
        """
        Initialize batch runner.
        
        Args:
            max_workers: Maximum number of parallel workers (default: CPU count)
            verbose: Enable verbose output
        """
        self.max_workers = max_workers or multiprocessing.cpu_count()
        self.verbose = verbose
        self._jobs: List[BatchJob] = []
    
    def log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[BATCH] {message}")
    
    def add_job(self, netlist_path: str, analysis_type: str = 'dc',
                output_file: Optional[str] = None, **kwargs) -> BatchJob:
        """Add a simulation job to the batch."""
        job_id = f"job_{len(self._jobs) + 1}"
        job = BatchJob(
            id=job_id,
            netlist_path=netlist_path,
            analysis_type=analysis_type,
            output_file=output_file,
            parameters=kwargs
        )
        self._jobs.append(job)
        return job
    
    def add_jobs_from_directory(self, directory: str, analysis_type: str = 'dc',
                                pattern: str = '*.spice', output_dir: Optional[str] = None,
                                **kwargs) -> List[BatchJob]:
        """Add all matching netlist files from a directory."""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        jobs = []
        for netlist_path in dir_path.glob(pattern):
            output_file = None
            if output_dir:
                output_path = Path(output_dir)
                output_path.mkdir(parents=True, exist_ok=True)
                output_file = str(output_path / f"{netlist_path.stem}_results.json")
            
            job = self.add_job(
                netlist_path=str(netlist_path),
                analysis_type=analysis_type,
                output_file=output_file,
                **kwargs
            )
            jobs.append(job)
        
        return jobs
    
    def add_jobs_from_config(self, config_file: str) -> List[BatchJob]:
        """Load jobs from a JSON or YAML configuration file."""
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        suffix = config_path.suffix.lower()
        
        if suffix == '.json':
            with open(config_path) as f:
                config = json.load(f)
        elif suffix in ['.yaml', '.yml']:
            try:
                import yaml
                with open(config_path) as f:
                    config = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML required for YAML config files")
        else:
            raise ValueError(f"Unsupported config format: {suffix}")
        
        jobs = []
        for job_config in config.get('jobs', []):
            job = self.add_job(
                netlist_path=job_config['netlist'],
                analysis_type=job_config.get('analysis', 'dc'),
                output_file=job_config.get('output'),
                **job_config.get('parameters', {})
            )
            jobs.append(job)
        
        return jobs
    
    def run_sequential(self) -> List[BatchJob]:
        """Run all jobs sequentially."""
        self.log(f"Running {len(self._jobs)} jobs sequentially")
        
        for job in self._jobs:
            self._run_single_job(job)
        
        return self._jobs
    
    def run_parallel(self) -> List[BatchJob]:
        """Run all jobs in parallel using thread pool."""
        self.log(f"Running {len(self._jobs)} jobs with {self.max_workers} workers")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._run_single_job, job): job
                for job in self._jobs
            }
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                job = futures[future]
                self.log(f"Completed {completed}/{len(self._jobs)}: {job.id} - {job.status}")
        
        return self._jobs
    
    def _run_single_job(self, job: BatchJob) -> BatchJob:
        """Run a single simulation job."""
        job.status = 'running'
        start_time = time.time()
        
        try:
            runner = SimulationRunner(verbose=False)
            result = runner.run_netlist(
                netlist_path=job.netlist_path,
                analysis_type=job.analysis_type,
                output_file=job.output_file,
                **job.parameters
            )
            
            job.result = result
            job.status = 'completed'
            
        except Exception as e:
            job.error = str(e)
            job.status = 'failed'
        
        job.elapsed_time = time.time() - start_time
        return job
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of batch results."""
        total = len(self._jobs)
        completed = sum(1 for j in self._jobs if j.status == 'completed')
        failed = sum(1 for j in self._jobs if j.status == 'failed')
        pending = sum(1 for j in self._jobs if j.status == 'pending')
        
        total_time = sum(j.elapsed_time for j in self._jobs)
        
        return {
            'total_jobs': total,
            'completed': completed,
            'failed': failed,
            'pending': pending,
            'total_time': total_time,
            'success_rate': completed / total * 100 if total > 0 else 0,
        }
    
    def generate_report(self, output_file: str, format: str = 'json'):
        """Generate a report of all batch results."""
        report = {
            'summary': self.get_summary(),
            'jobs': []
        }
        
        for job in self._jobs:
            job_info = {
                'id': job.id,
                'netlist': job.netlist_path,
                'analysis_type': job.analysis_type,
                'status': job.status,
                'elapsed_time': job.elapsed_time,
            }
            
            if job.error:
                job_info['error'] = job.error
            
            if job.output_file:
                job_info['output_file'] = job.output_file
            
            report['jobs'].append(job_info)
        
        output_path = Path(output_file)
        
        if format == 'json':
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        elif format == 'html':
            self._generate_html_report(report, output_path)
        elif format == 'csv':
            self._generate_csv_report(report, output_path)
    
    def _generate_html_report(self, report: dict, output_path: Path):
        """Generate HTML report."""
        summary = report['summary']
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>AMS Simulator - Batch Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .summary-item {{ display: inline-block; margin-right: 30px; }}
        .summary-value {{ font-size: 24px; font-weight: bold; color: #2196F3; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
        th {{ background: #2196F3; color: white; }}
        tr:nth-child(even) {{ background: #f9f9f9; }}
        .status-completed {{ color: green; font-weight: bold; }}
        .status-failed {{ color: red; font-weight: bold; }}
        .status-pending {{ color: orange; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>AMS Simulator - Batch Simulation Report</h1>
    
    <div class="summary">
        <div class="summary-item">
            <div>Total Jobs</div>
            <div class="summary-value">{summary['total_jobs']}</div>
        </div>
        <div class="summary-item">
            <div>Completed</div>
            <div class="summary-value" style="color: green;">{summary['completed']}</div>
        </div>
        <div class="summary-item">
            <div>Failed</div>
            <div class="summary-value" style="color: red;">{summary['failed']}</div>
        </div>
        <div class="summary-item">
            <div>Success Rate</div>
            <div class="summary-value">{summary['success_rate']:.1f}%</div>
        </div>
        <div class="summary-item">
            <div>Total Time</div>
            <div class="summary-value">{summary['total_time']:.2f}s</div>
        </div>
    </div>
    
    <h2>Job Details</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Netlist</th>
            <th>Analysis</th>
            <th>Status</th>
            <th>Time (s)</th>
            <th>Error</th>
        </tr>
"""
        
        for job in report['jobs']:
            status_class = f"status-{job['status']}"
            error = job.get('error', '-')
            
            html += f"""        <tr>
            <td>{job['id']}</td>
            <td>{job['netlist']}</td>
            <td>{job['analysis_type']}</td>
            <td class="{status_class}">{job['status'].upper()}</td>
            <td>{job['elapsed_time']:.3f}</td>
            <td>{error}</td>
        </tr>
"""
        
        html += """    </table>
</body>
</html>
"""
        
        with open(output_path, 'w') as f:
            f.write(html)
    
    def _generate_csv_report(self, report: dict, output_path: Path):
        """Generate CSV report."""
        with open(output_path, 'w') as f:
            f.write("id,netlist,analysis_type,status,elapsed_time,error\n")
            
            for job in report['jobs']:
                error = job.get('error', '').replace(',', ';')
                f.write(f"{job['id']},{job['netlist']},{job['analysis_type']},"
                       f"{job['status']},{job['elapsed_time']:.3f},\"{error}\"\n")


def main():
    """Main entry point for batch runner."""
    parser = argparse.ArgumentParser(
        description='AMS Simulator - Batch Simulation Runner',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dir ./netlists --analysis dc
  %(prog)s --dir ./netlists --analysis transient --tstop 1e-6 --output-dir ./results
  %(prog)s --config batch_config.json
  %(prog)s --dir ./netlists --pattern "*.spice" --workers 4 --report report.html
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--dir', '-d',
        help='Directory containing netlist files'
    )
    input_group.add_argument(
        '--config', '-c',
        help='Configuration file (JSON or YAML) with job definitions'
    )
    input_group.add_argument(
        '--netlists', '-n',
        nargs='+',
        help='List of netlist files to process'
    )
    
    # Processing options
    parser.add_argument(
        '--pattern', '-p',
        default='*.spice',
        help='File pattern for directory search (default: *.spice)'
    )
    
    parser.add_argument(
        '--analysis', '-a',
        choices=['dc', 'ac', 'transient', 'digital', 'mixed'],
        default='dc',
        help='Type of analysis to run (default: dc)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        help='Directory for output files'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help='Number of parallel workers (default: CPU count)'
    )
    
    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Run jobs sequentially instead of parallel'
    )
    
    parser.add_argument(
        '--report', '-r',
        help='Output file for batch report (.json, .html, or .csv)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Analysis parameters
    parser.add_argument('--tstop', type=float, default=1e-6, help='Transient stop time')
    parser.add_argument('--tstep', type=float, default=1e-9, help='Transient time step')
    parser.add_argument('--fstart', type=float, default=1, help='AC start frequency')
    parser.add_argument('--fstop', type=float, default=1e6, help='AC stop frequency')
    parser.add_argument('--points', type=int, default=10, help='Points per decade')
    parser.add_argument('--max-time', type=int, default=1000, help='Digital max time')
    
    args = parser.parse_args()
    
    runner = BatchRunner(max_workers=args.workers, verbose=args.verbose)
    
    try:
        # Build parameter dict
        params = {
            'tstop': args.tstop,
            'tstep': args.tstep,
            'fstart': args.fstart,
            'fstop': args.fstop,
            'points': args.points,
            'max_time': args.max_time,
        }
        
        # Add jobs
        if args.dir:
            jobs = runner.add_jobs_from_directory(
                directory=args.dir,
                analysis_type=args.analysis,
                pattern=args.pattern,
                output_dir=args.output_dir,
                **params
            )
        elif args.config:
            jobs = runner.add_jobs_from_config(args.config)
        elif args.netlists:
            for netlist in args.netlists:
                output_file = None
                if args.output_dir:
                    output_path = Path(args.output_dir)
                    output_path.mkdir(parents=True, exist_ok=True)
                    output_file = str(output_path / f"{Path(netlist).stem}_results.json")
                
                runner.add_job(
                    netlist_path=netlist,
                    analysis_type=args.analysis,
                    output_file=output_file,
                    **params
                )
        
        print(f"Starting batch simulation with {len(runner._jobs)} jobs...")
        print()
        
        # Run jobs
        start_time = time.time()
        
        if args.sequential:
            runner.run_sequential()
        else:
            runner.run_parallel()
        
        total_time = time.time() - start_time
        
        # Print summary
        summary = runner.get_summary()
        
        print("\n=== Batch Simulation Summary ===")
        print(f"Total Jobs:    {summary['total_jobs']}")
        print(f"Completed:     {summary['completed']}")
        print(f"Failed:        {summary['failed']}")
        print(f"Success Rate:  {summary['success_rate']:.1f}%")
        print(f"Total Time:    {total_time:.2f}s")
        
        # Generate report if requested
        if args.report:
            report_path = Path(args.report)
            report_format = report_path.suffix.lower()[1:]  # Remove leading dot
            if report_format not in ['json', 'html', 'csv']:
                report_format = 'json'
            
            runner.generate_report(args.report, format=report_format)
            print(f"\nReport saved to: {args.report}")
        
        # Print failures
        failures = [j for j in runner._jobs if j.status == 'failed']
        if failures:
            print("\n=== Failed Jobs ===")
            for job in failures:
                print(f"  {job.id}: {job.netlist_path}")
                print(f"    Error: {job.error}")
        
        return 0 if summary['failed'] == 0 else 1
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
