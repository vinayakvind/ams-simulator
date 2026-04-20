"""
Specs Monitoring - Specification checking and violation detection.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import json


class ComparisonOperator(Enum):
    """Comparison operators for specifications."""
    EQUAL = 'eq'
    NOT_EQUAL = 'neq'
    LESS_THAN = 'lt'
    LESS_EQUAL = 'le'
    GREATER_THAN = 'gt'
    GREATER_EQUAL = 'ge'
    IN_RANGE = 'range'
    NOT_IN_RANGE = 'not_range'


class SpecStatus(Enum):
    """Specification check status."""
    PASS = 'pass'
    FAIL = 'fail'
    WARN = 'warn'
    SKIP = 'skip'


@dataclass
class Specification:
    """A single specification to check."""
    name: str
    signal: str
    operator: ComparisonOperator
    value: Union[float, List[float]]  # Single value or [min, max] for range
    tolerance: float = 0.0  # Percentage tolerance
    units: str = ''
    description: str = ''
    severity: str = 'error'  # error, warning
    
    def check(self, measured_value: float) -> tuple[SpecStatus, str]:
        """
        Check if measured value meets specification.
        
        Returns:
            Tuple of (status, message)
        """
        # Apply tolerance
        tol = abs(self.value) * self.tolerance / 100 if isinstance(self.value, (int, float)) else 0
        
        if self.operator == ComparisonOperator.EQUAL:
            target = self.value
            passed = abs(measured_value - target) <= tol if tol > 0 else measured_value == target
            msg = f"{measured_value:.6g} {'==' if passed else '!='} {target:.6g}"
        
        elif self.operator == ComparisonOperator.NOT_EQUAL:
            target = self.value
            passed = measured_value != target
            msg = f"{measured_value:.6g} {'!=' if passed else '=='} {target:.6g}"
        
        elif self.operator == ComparisonOperator.LESS_THAN:
            limit = self.value
            passed = measured_value < limit + tol
            msg = f"{measured_value:.6g} {'<' if passed else '>='} {limit:.6g}"
        
        elif self.operator == ComparisonOperator.LESS_EQUAL:
            limit = self.value
            passed = measured_value <= limit + tol
            msg = f"{measured_value:.6g} {'<=' if passed else '>'} {limit:.6g}"
        
        elif self.operator == ComparisonOperator.GREATER_THAN:
            limit = self.value
            passed = measured_value > limit - tol
            msg = f"{measured_value:.6g} {'>' if passed else '<='} {limit:.6g}"
        
        elif self.operator == ComparisonOperator.GREATER_EQUAL:
            limit = self.value
            passed = measured_value >= limit - tol
            msg = f"{measured_value:.6g} {'>=' if passed else '<'} {limit:.6g}"
        
        elif self.operator == ComparisonOperator.IN_RANGE:
            min_val, max_val = self.value
            passed = min_val - tol <= measured_value <= max_val + tol
            msg = f"{min_val:.6g} <= {measured_value:.6g} <= {max_val:.6g}"
        
        elif self.operator == ComparisonOperator.NOT_IN_RANGE:
            min_val, max_val = self.value
            passed = measured_value < min_val - tol or measured_value > max_val + tol
            msg = f"{measured_value:.6g} outside [{min_val:.6g}, {max_val:.6g}]"
        
        else:
            return SpecStatus.SKIP, "Unknown operator"
        
        if passed:
            return SpecStatus.PASS, msg
        elif self.severity == 'warning':
            return SpecStatus.WARN, msg
        else:
            return SpecStatus.FAIL, msg


@dataclass
class SpecResult:
    """Result of a specification check."""
    spec: Specification
    status: SpecStatus
    measured_value: float
    message: str
    timestamp: Optional[float] = None  # For transient specs


@dataclass
class SpecsReport:
    """Report of specification checks."""
    results: List[SpecResult] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        return len(self.results)
    
    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == SpecStatus.PASS)
    
    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == SpecStatus.FAIL)
    
    @property
    def warnings(self) -> int:
        return sum(1 for r in self.results if r.status == SpecStatus.WARN)
    
    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 100.0
        return self.passed / self.total * 100
    
    @property
    def is_passing(self) -> bool:
        return self.failed == 0


class SpecsMonitor:
    """
    Monitors simulation results against specifications.
    """
    
    def __init__(self):
        self._specs: List[Specification] = []
    
    def add_spec(self, name: str, signal: str, operator: str, value: Union[float, List[float]],
                 tolerance: float = 0.0, units: str = '', description: str = '',
                 severity: str = 'error') -> Specification:
        """Add a specification to monitor."""
        # Parse operator
        op_map = {
            '==': ComparisonOperator.EQUAL,
            '=': ComparisonOperator.EQUAL,
            'eq': ComparisonOperator.EQUAL,
            '!=': ComparisonOperator.NOT_EQUAL,
            'neq': ComparisonOperator.NOT_EQUAL,
            '<': ComparisonOperator.LESS_THAN,
            'lt': ComparisonOperator.LESS_THAN,
            '<=': ComparisonOperator.LESS_EQUAL,
            'le': ComparisonOperator.LESS_EQUAL,
            '>': ComparisonOperator.GREATER_THAN,
            'gt': ComparisonOperator.GREATER_THAN,
            '>=': ComparisonOperator.GREATER_EQUAL,
            'ge': ComparisonOperator.GREATER_EQUAL,
            'range': ComparisonOperator.IN_RANGE,
            'in_range': ComparisonOperator.IN_RANGE,
            'not_range': ComparisonOperator.NOT_IN_RANGE,
        }
        
        op = op_map.get(operator.lower(), ComparisonOperator.EQUAL)
        
        spec = Specification(
            name=name,
            signal=signal,
            operator=op,
            value=value,
            tolerance=tolerance,
            units=units,
            description=description,
            severity=severity
        )
        self._specs.append(spec)
        return spec
    
    def load_specs(self, specs_file: str):
        """Load specifications from a JSON or YAML file."""
        from pathlib import Path
        
        path = Path(specs_file)
        suffix = path.suffix.lower()
        
        if suffix == '.json':
            with open(path) as f:
                data = json.load(f)
        elif suffix in ['.yaml', '.yml']:
            try:
                import yaml
                with open(path) as f:
                    data = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML required for YAML specs files")
        else:
            raise ValueError(f"Unsupported specs file format: {suffix}")
        
        for spec_data in data.get('specs', []):
            self.add_spec(**spec_data)
    
    def check_dc(self, results: Dict[str, float]) -> SpecsReport:
        """Check DC analysis results against specs."""
        report = SpecsReport()
        
        for spec in self._specs:
            # Find matching signal
            signal_key = spec.signal
            if signal_key not in results:
                # Try with V() wrapper
                signal_key = f'V({spec.signal})'
            
            if signal_key not in results:
                report.results.append(SpecResult(
                    spec=spec,
                    status=SpecStatus.SKIP,
                    measured_value=0,
                    message=f"Signal {spec.signal} not found in results"
                ))
                continue
            
            measured = results[signal_key]
            status, message = spec.check(measured)
            
            report.results.append(SpecResult(
                spec=spec,
                status=status,
                measured_value=measured,
                message=message
            ))
        
        return report
    
    def check_transient(self, results: Dict[str, List[float]], time: List[float]) -> SpecsReport:
        """Check transient analysis results against specs."""
        report = SpecsReport()
        
        for spec in self._specs:
            # Find matching signal
            signal_key = spec.signal
            if signal_key not in results:
                signal_key = f'V({spec.signal})'
            
            if signal_key not in results:
                report.results.append(SpecResult(
                    spec=spec,
                    status=SpecStatus.SKIP,
                    measured_value=0,
                    message=f"Signal {spec.signal} not found in results"
                ))
                continue
            
            signal_data = results[signal_key]
            
            # Check at final time by default
            measured = signal_data[-1] if signal_data else 0
            status, message = spec.check(measured)
            
            report.results.append(SpecResult(
                spec=spec,
                status=status,
                measured_value=measured,
                message=message,
                timestamp=time[-1] if time else None
            ))
        
        return report
    
    def check_ac(self, results: Dict[str, List[float]], frequency: List[float]) -> SpecsReport:
        """Check AC analysis results against specs."""
        import numpy as np
        
        report = SpecsReport()
        
        for spec in self._specs:
            signal_key = spec.signal
            
            # Handle magnitude and phase
            if 'mag' in signal_key.lower():
                pass
            elif 'phase' in signal_key.lower():
                pass
            else:
                signal_key = f'mag({spec.signal})'
            
            if signal_key not in results:
                report.results.append(SpecResult(
                    spec=spec,
                    status=SpecStatus.SKIP,
                    measured_value=0,
                    message=f"Signal {spec.signal} not found in results"
                ))
                continue
            
            signal_data = results[signal_key]
            
            # Use max magnitude by default
            measured = max(signal_data) if signal_data else 0
            status, message = spec.check(measured)
            
            report.results.append(SpecResult(
                spec=spec,
                status=status,
                measured_value=measured,
                message=message
            ))
        
        return report


class MeasurementExtractor:
    """Extract common measurements from simulation results."""
    
    @staticmethod
    def dc_gain(output: List[float], input_sweep: List[float]) -> float:
        """Calculate DC gain from sweep results."""
        if len(output) < 2 or len(input_sweep) < 2:
            return 0
        
        delta_out = output[-1] - output[0]
        delta_in = input_sweep[-1] - input_sweep[0]
        
        return delta_out / delta_in if delta_in != 0 else 0
    
    @staticmethod
    def max_value(signal: List[float]) -> float:
        """Get maximum value of signal."""
        return max(signal) if signal else 0
    
    @staticmethod
    def min_value(signal: List[float]) -> float:
        """Get minimum value of signal."""
        return min(signal) if signal else 0
    
    @staticmethod
    def peak_to_peak(signal: List[float]) -> float:
        """Get peak-to-peak amplitude."""
        if not signal:
            return 0
        return max(signal) - min(signal)
    
    @staticmethod
    def average(signal: List[float]) -> float:
        """Get average value."""
        if not signal:
            return 0
        return sum(signal) / len(signal)
    
    @staticmethod
    def rms(signal: List[float]) -> float:
        """Get RMS value."""
        import numpy as np
        if not signal:
            return 0
        return np.sqrt(np.mean(np.array(signal) ** 2))
    
    @staticmethod
    def rise_time(signal: List[float], time: List[float], 
                  low_pct: float = 0.1, high_pct: float = 0.9) -> float:
        """Calculate rise time (10% to 90% by default)."""
        if len(signal) < 2:
            return 0
        
        min_val = min(signal)
        max_val = max(signal)
        amplitude = max_val - min_val
        
        low_threshold = min_val + amplitude * low_pct
        high_threshold = min_val + amplitude * high_pct
        
        t_low = None
        t_high = None
        
        for i, (s, t) in enumerate(zip(signal, time)):
            if t_low is None and s >= low_threshold:
                t_low = t
            if t_high is None and s >= high_threshold:
                t_high = t
                break
        
        if t_low is not None and t_high is not None:
            return t_high - t_low
        return 0
    
    @staticmethod
    def fall_time(signal: List[float], time: List[float],
                  high_pct: float = 0.9, low_pct: float = 0.1) -> float:
        """Calculate fall time (90% to 10% by default)."""
        if len(signal) < 2:
            return 0
        
        min_val = min(signal)
        max_val = max(signal)
        amplitude = max_val - min_val
        
        high_threshold = min_val + amplitude * high_pct
        low_threshold = min_val + amplitude * low_pct
        
        # Find falling edge
        t_high = None
        t_low = None
        found_peak = False
        
        for i, (s, t) in enumerate(zip(signal, time)):
            if s >= max_val * 0.99:
                found_peak = True
            if found_peak:
                if t_high is None and s <= high_threshold:
                    t_high = t
                if t_high is not None and s <= low_threshold:
                    t_low = t
                    break
        
        if t_high is not None and t_low is not None:
            return t_low - t_high
        return 0
    
    @staticmethod
    def delay(signal1: List[float], signal2: List[float], time: List[float],
              threshold_pct: float = 0.5) -> float:
        """Calculate delay between two signals at 50% threshold."""
        if len(signal1) < 2 or len(signal2) < 2:
            return 0
        
        # Find crossing times
        def find_crossing(signal: List[float]) -> Optional[float]:
            min_val = min(signal)
            max_val = max(signal)
            threshold = min_val + (max_val - min_val) * threshold_pct
            
            for i in range(len(signal) - 1):
                if signal[i] < threshold <= signal[i + 1]:
                    # Linear interpolation
                    ratio = (threshold - signal[i]) / (signal[i + 1] - signal[i])
                    return time[i] + ratio * (time[i + 1] - time[i])
            return None
        
        t1 = find_crossing(signal1)
        t2 = find_crossing(signal2)
        
        if t1 is not None and t2 is not None:
            return t2 - t1
        return 0
    
    @staticmethod
    def bandwidth_3db(magnitude: List[float], frequency: List[float]) -> float:
        """Calculate -3dB bandwidth from AC analysis."""
        import numpy as np
        
        if not magnitude or not frequency:
            return 0
        
        mag_db = 20 * np.log10(np.array(magnitude) + 1e-15)
        max_db = max(mag_db)
        threshold = max_db - 3
        
        for i, (m, f) in enumerate(zip(mag_db, frequency)):
            if m <= threshold:
                if i > 0:
                    # Linear interpolation
                    ratio = (threshold - mag_db[i-1]) / (m - mag_db[i-1])
                    return frequency[i-1] + ratio * (f - frequency[i-1])
                return f
        
        return frequency[-1] if frequency else 0
    
    @staticmethod
    def phase_margin(magnitude: List[float], phase: List[float], 
                     frequency: List[float]) -> float:
        """Calculate phase margin at unity gain."""
        import numpy as np
        
        if not magnitude or not phase:
            return 0
        
        # Find unity gain frequency (0dB)
        mag_db = 20 * np.log10(np.array(magnitude) + 1e-15)
        
        ugf_idx = None
        for i in range(len(mag_db) - 1):
            if mag_db[i] >= 0 and mag_db[i + 1] < 0:
                ugf_idx = i
                break
        
        if ugf_idx is None:
            return 180  # No unity gain crossing
        
        # Get phase at unity gain frequency
        phase_at_ugf = phase[ugf_idx]
        
        return 180 + phase_at_ugf
    
    @staticmethod
    def gain_margin(magnitude: List[float], phase: List[float],
                    frequency: List[float]) -> float:
        """Calculate gain margin at -180° phase."""
        import numpy as np
        
        if not magnitude or not phase:
            return float('inf')
        
        # Find frequency where phase = -180°
        phase_margin_idx = None
        for i in range(len(phase) - 1):
            if phase[i] >= -180 and phase[i + 1] < -180:
                phase_margin_idx = i
                break
        
        if phase_margin_idx is None:
            return float('inf')  # Never reaches -180°
        
        # Get magnitude at that frequency
        mag_db = 20 * np.log10(magnitude[phase_margin_idx] + 1e-15)
        
        return -mag_db
