"""
CLI Runner - Command-line interface for running simulations.
"""

import argparse
import sys
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any

from simulator.engine.analog_engine import AnalogEngine, DCAnalysis, ACAnalysis, TransientAnalysis
from simulator.engine.digital_engine import DigitalEngine
from simulator.engine.mixed_signal_engine import MixedSignalEngine
from simulator.engine.ngspice_backend import NgSpiceBackend


class SimulationRunner:
    """Command-line simulation runner."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._analog_engine = AnalogEngine()
        self._digital_engine = DigitalEngine()
        self._mixed_engine = MixedSignalEngine()
        self._ngspice_backend: Optional[NgSpiceBackend] = None
    
    def log(self, message: str):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            print(f"[INFO] {message}")

    def _get_ngspice_backend(self) -> NgSpiceBackend:
        """Lazily create the ngspice backend when a transient fallback needs it."""
        if self._ngspice_backend is None:
            self._ngspice_backend = NgSpiceBackend()
        return self._ngspice_backend

    def _netlist_uses_unsupported_behavioral_sources(self, netlist: str) -> bool:
        """Detect transient netlists that require ngspice for TABLE/POLY E sources."""
        for raw_line in netlist.splitlines():
            stripped = raw_line.strip()
            if not stripped or stripped.startswith('*') or stripped.startswith('.'):
                continue
            if stripped[0].upper() != 'E':
                continue
            upper_line = stripped.upper()
            if 'TABLE' in upper_line or 'POLY' in upper_line:
                return True
        return False

    def _should_use_ngspice(self, netlist: str, analysis_type: str) -> bool:
        """Use ngspice only when the built-in transient solver cannot represent the netlist."""
        return analysis_type == 'transient' and self._netlist_uses_unsupported_behavioral_sources(netlist)

    def _prepare_ngspice_netlist(self, netlist: str, analysis_type: str, kwargs: dict) -> str:
        """Inject the requested analysis command into a netlist for ngspice batch mode."""
        filtered_lines: list[str] = []
        for line in netlist.strip().splitlines():
            stripped = line.strip()
            lower_line = stripped.lower()
            if any(lower_line.startswith(cmd) for cmd in ('.dc', '.ac', '.tran', '.op', '.end', '.control', '.endc')):
                continue
            filtered_lines.append(line)

        if analysis_type == 'transient':
            tstop = kwargs.get('tstop', 1e-6)
            tstep = kwargs.get('tstep', 1e-9)
            tstart = kwargs.get('tstart', 0)
            directive = f".tran {tstep} {tstop} {tstart}"
            if kwargs.get('uic', False):
                directive += ' uic'
            filtered_lines.append(directive)
        else:
            raise ValueError(f"ngspice fallback is not supported for analysis type: {analysis_type}")

        filtered_lines.append('.end')
        return '\n'.join(filtered_lines)

    def _normalize_signal_name(self, key: str) -> str:
        """Keep node naming stable across Python and ngspice backends."""
        if len(key) > 1 and key[1] == '(' and key[0].lower() in {'v', 'i'}:
            return key[0].upper() + key[1:]
        return key

    def _normalize_value(self, value: Any) -> Any:
        """Convert backend-specific numeric containers into JSON-friendly Python values."""
        if hasattr(value, 'tolist'):
            value = value.tolist()
        if isinstance(value, tuple):
            value = list(value)
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if hasattr(value, 'item'):
            try:
                return value.item()
            except Exception:
                return str(value)
        return value

    def _normalize_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize simulation results so higher-level tooling can treat both backends identically."""
        normalized: Dict[str, Any] = {}
        for key, value in results.items():
            normalized[self._normalize_signal_name(key)] = self._normalize_value(value)
        return normalized

    def _run_analysis(self, netlist: str, analysis_type: str, kwargs: dict) -> Dict[str, Any]:
        """Dispatch to the built-in simulation engine for the requested analysis."""
        if analysis_type == 'dc':
            return self._run_dc_analysis(netlist, kwargs)
        if analysis_type == 'ac':
            return self._run_ac_analysis(netlist, kwargs)
        if analysis_type == 'transient':
            return self._run_transient_analysis(netlist, kwargs)
        if analysis_type == 'digital':
            return self._run_digital_analysis(netlist, kwargs)
        if analysis_type == 'mixed':
            return self._run_mixed_analysis(netlist, kwargs)
        raise ValueError(f"Unknown analysis type: {analysis_type}")

    def _run_ngspice_transient_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run transient analysis through ngspice for unsupported behavioral SPICE constructs."""
        backend = self._get_ngspice_backend()
        prepared_netlist = self._prepare_ngspice_netlist(netlist, 'transient', kwargs)
        return self._normalize_results(backend.simulate(prepared_netlist))
    
    def run_netlist(self, netlist_path: str, analysis_type: str = 'dc',
                    output_file: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Run simulation from a netlist file.
        
        Args:
            netlist_path: Path to the netlist file
            analysis_type: Type of analysis ('dc', 'ac', 'transient', 'digital', 'mixed')
            output_file: Optional output file path for results
            **kwargs: Analysis-specific parameters
        
        Returns:
            Dictionary containing simulation results
        """
        netlist_path = Path(netlist_path)
        
        if not netlist_path.exists():
            raise FileNotFoundError(f"Netlist file not found: {netlist_path}")
        
        self.log(f"Loading netlist: {netlist_path}")
        netlist = netlist_path.read_text()
        
        # Determine analysis type from file extension if not specified
        suffix = netlist_path.suffix.lower()
        if suffix == '.v':
            analysis_type = 'digital'
        elif suffix == '.vams':
            analysis_type = 'mixed'
        
        self.log(f"Running {analysis_type} analysis...")
        start_time = time.time()
        backend_name = 'python'

        if self._should_use_ngspice(netlist, analysis_type):
            backend = self._get_ngspice_backend()
            if backend.is_available():
                self.log(f"Using ngspice fallback: {backend.ngspice_path}")
                try:
                    results = self._run_ngspice_transient_analysis(netlist, kwargs)
                    if results:
                        backend_name = 'ngspice'
                    else:
                        self.log("ngspice returned no parsed results; falling back to Python engine")
                        results = self._run_analysis(netlist, analysis_type, kwargs)
                except Exception as exc:
                    self.log(f"ngspice fallback failed ({exc}); falling back to Python engine")
                    results = self._run_analysis(netlist, analysis_type, kwargs)
            else:
                self.log("ngspice is unavailable; using Python engine for unsupported behavioral sources")
                results = self._run_analysis(netlist, analysis_type, kwargs)
        else:
            results = self._run_analysis(netlist, analysis_type, kwargs)

        results = self._normalize_results(results)
        
        elapsed = time.time() - start_time
        self.log(f"Simulation completed in {elapsed:.3f} seconds")
        
        # Add metadata
        results['metadata'] = {
            'netlist_file': str(netlist_path),
            'analysis_type': analysis_type,
            'elapsed_time': elapsed,
            'backend': backend_name,
        }
        
        # Save results if output file specified
        if output_file:
            self._save_results(results, output_file)
            self.log(f"Results saved to: {output_file}")
        
        return results
    
    def _run_dc_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run DC analysis."""
        self._analog_engine.load_netlist(netlist)
        
        analysis = DCAnalysis(self._analog_engine)
        
        settings = {}
        if 'source' in kwargs:
            settings['source'] = kwargs['source']
            settings['start'] = kwargs.get('start', 0)
            settings['stop'] = kwargs.get('stop', 5)
            settings['step'] = kwargs.get('step', 0.1)
        
        return analysis.run(settings)
    
    def _run_ac_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run AC analysis."""
        self._analog_engine.load_netlist(netlist)
        
        analysis = ACAnalysis(self._analog_engine)
        
        settings = {
            'variation': kwargs.get('variation', 'decade'),
            'points': kwargs.get('points', 10),
            'fstart': kwargs.get('fstart', 1),
            'fstop': kwargs.get('fstop', 1e6),
        }
        
        return analysis.run(settings)
    
    def _run_transient_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run transient analysis."""
        self._analog_engine.load_netlist(netlist)
        
        analysis = TransientAnalysis(self._analog_engine)
        
        settings = {
            'tstop': kwargs.get('tstop', 1e-6),
            'tstep': kwargs.get('tstep', 1e-9),
            'tstart': kwargs.get('tstart', 0),
            'uic': kwargs.get('uic', False),
        }
        
        def progress_callback(progress: float):
            if self.verbose:
                print(f"\rProgress: {progress*100:.1f}%", end='', flush=True)
        
        results = analysis.run(settings, progress_callback if self.verbose else None)
        
        if self.verbose:
            print()  # New line after progress
        
        return results
    
    def _run_digital_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run digital simulation."""
        self._digital_engine = DigitalEngine()  # Fresh engine
        self._digital_engine.load_verilog(netlist)
        
        max_time = kwargs.get('max_time', 1000)
        
        def progress_callback(progress: float):
            if self.verbose:
                print(f"\rProgress: {progress*100:.1f}%", end='', flush=True)
        
        results = self._digital_engine.run(max_time, progress_callback if self.verbose else None)
        
        if self.verbose:
            print()
        
        return results
    
    def _run_mixed_analysis(self, netlist: str, kwargs: dict) -> Dict[str, Any]:
        """Run mixed-signal simulation."""
        self._mixed_engine = MixedSignalEngine()  # Fresh engine
        self._mixed_engine.load_netlist(netlist)
        
        settings = {
            'tstop': kwargs.get('tstop', 1e-6),
            'tstep': kwargs.get('tstep', 1e-9),
        }
        
        def progress_callback(progress: float):
            if self.verbose:
                print(f"\rProgress: {progress*100:.1f}%", end='', flush=True)
        
        results = self._mixed_engine.run(settings, progress_callback if self.verbose else None)
        
        if self.verbose:
            print()
        
        return results
    
    def _save_results(self, results: Dict[str, Any], output_file: str):
        """Save results to file."""
        output_path = Path(output_file)
        suffix = output_path.suffix.lower()
        
        if suffix == '.json':
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
        elif suffix == '.csv':
            self._save_csv(results, output_path)
        else:
            # Default to JSON
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
    
    def _save_csv(self, results: Dict[str, Any], output_path: Path):
        """Save results to CSV format."""
        # Find time/sweep column
        time_col = None
        for key in ['time', 'frequency', 'sweep']:
            if key in results:
                time_col = key
                break
        
        if not time_col:
            # DC operating point - different format
            with open(output_path, 'w') as f:
                f.write("variable,value\n")
                for key, value in results.items():
                    if key not in ['type', 'metadata']:
                        f.write(f"{key},{value}\n")
            return
        
        # Time-based results
        time_values = results[time_col]
        
        # Get all signal columns
        signals = []
        for key in results.keys():
            if key not in [time_col, 'type', 'metadata']:
                if isinstance(results[key], list):
                    signals.append(key)
        
        with open(output_path, 'w') as f:
            # Header
            f.write(f"{time_col}," + ",".join(signals) + "\n")
            
            # Data rows
            for i, t in enumerate(time_values):
                row = [str(t)]
                for sig in signals:
                    val = results[sig][i] if i < len(results[sig]) else ''
                    row.append(str(val))
                f.write(",".join(row) + "\n")


def main():
    """Main entry point for CLI runner."""
    parser = argparse.ArgumentParser(
        description='AMS Simulator - Circuit Simulation CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -n circuit.spice -a dc
  %(prog)s -n circuit.spice -a transient --tstop 1e-6 --tstep 1e-9
  %(prog)s -n circuit.spice -a ac --fstart 1 --fstop 1e9
  %(prog)s -n circuit.v -a digital --max-time 1000
  %(prog)s -n circuit.vams -a mixed --tstop 1e-6
        """
    )
    
    parser.add_argument(
        '-n', '--netlist',
        required=True,
        help='Path to netlist file (.spice, .v, .vams)'
    )
    
    parser.add_argument(
        '-a', '--analysis',
        choices=['dc', 'ac', 'transient', 'digital', 'mixed'],
        default='dc',
        help='Type of analysis to run (default: dc)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output file for results (.json or .csv)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    # DC sweep parameters
    parser.add_argument(
        '--source',
        help='Source name for DC sweep'
    )
    parser.add_argument(
        '--start',
        type=float,
        default=0,
        help='DC sweep start value'
    )
    parser.add_argument(
        '--stop',
        type=float,
        default=5,
        help='DC sweep stop value'
    )
    parser.add_argument(
        '--step',
        type=float,
        default=0.1,
        help='DC sweep step value'
    )
    
    # AC parameters
    parser.add_argument(
        '--variation',
        choices=['decade', 'linear', 'octave'],
        default='decade',
        help='AC frequency variation type'
    )
    parser.add_argument(
        '--points',
        type=int,
        default=10,
        help='Points per decade/octave for AC analysis'
    )
    parser.add_argument(
        '--fstart',
        type=float,
        default=1,
        help='AC start frequency (Hz)'
    )
    parser.add_argument(
        '--fstop',
        type=float,
        default=1e6,
        help='AC stop frequency (Hz)'
    )
    
    # Transient parameters
    parser.add_argument(
        '--tstop',
        type=float,
        default=1e-6,
        help='Transient stop time (s)'
    )
    parser.add_argument(
        '--tstep',
        type=float,
        default=1e-9,
        help='Transient time step (s)'
    )
    parser.add_argument(
        '--uic',
        action='store_true',
        help='Use initial conditions'
    )
    
    # Digital parameters
    parser.add_argument(
        '--max-time',
        type=int,
        default=1000,
        help='Maximum simulation time for digital analysis'
    )
    
    args = parser.parse_args()
    
    runner = SimulationRunner(verbose=args.verbose)
    
    try:
        results = runner.run_netlist(
            netlist_path=args.netlist,
            analysis_type=args.analysis,
            output_file=args.output,
            # DC parameters
            source=args.source,
            start=args.start,
            stop=args.stop,
            step=args.step,
            # AC parameters
            variation=args.variation,
            points=args.points,
            fstart=args.fstart,
            fstop=args.fstop,
            # Transient parameters
            tstop=args.tstop,
            tstep=args.tstep,
            uic=args.uic,
            # Digital parameters
            max_time=args.max_time,
        )
        
        # Print summary
        print("\n=== Simulation Results ===")
        
        if 'type' in results:
            print(f"Analysis Type: {results['type']}")
        
        if 'metadata' in results:
            meta = results['metadata']
            print(f"Elapsed Time: {meta.get('elapsed_time', 0):.3f}s")
        
        # Print node voltages for DC OP
        if results.get('type') == 'dc_op':
            print("\nNode Voltages:")
            for key, value in results.items():
                if key.startswith('V('):
                    print(f"  {key} = {value:.6g} V")
        
        # Print signal names for other analyses
        elif 'time' in results or 'frequency' in results:
            print(f"\nSignals: {len([k for k in results.keys() if k not in ['type', 'metadata', 'time', 'frequency', 'sweep']])}")
            if 'time' in results:
                print(f"Time Points: {len(results['time'])}")
            if 'frequency' in results:
                print(f"Frequency Points: {len(results['frequency'])}")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Simulation error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
