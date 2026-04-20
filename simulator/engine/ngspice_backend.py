"""
NgSpice Backend Integration for AMS Simulator

Provides an interface to use ngspice for more accurate and robust circuit simulation.
"""

import os
import subprocess
import tempfile
import re
import numpy as np
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class NgSpiceBackend:
    """Interface to ngspice circuit simulator."""
    
    def __init__(self, ngspice_path: Optional[str] = None):
        """Initialize ngspice backend.
        
        Args:
            ngspice_path: Path to ngspice executable. If None, searches PATH.
        """
        self.ngspice_path = ngspice_path or self._find_ngspice()
        self._temp_dir = None
    
    def _find_ngspice(self) -> Optional[str]:
        """Try to find ngspice executable in PATH or common locations."""
        # On Windows, prefer ngspice_con.exe (console version) for batch mode
        if os.name == 'nt':
            # Check common Windows installation paths - prefer console version
            common_paths = [
                r'C:\ngspice\bin\ngspice_con.exe',  # Console version first
                r'C:\ngspice\bin\ngspice.exe',
                r'C:\Program Files\ngspice\bin\ngspice_con.exe',
                r'C:\Program Files\ngspice\bin\ngspice.exe',
                r'C:\Program Files (x86)\ngspice\bin\ngspice_con.exe',
                r'C:\Program Files (x86)\ngspice\bin\ngspice.exe',
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        # Check if ngspice is in PATH
        try:
            result = subprocess.run(['ngspice_con' if os.name == 'nt' else 'ngspice', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ngspice_con' if os.name == 'nt' else 'ngspice'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Try regular ngspice in PATH
        try:
            result = subprocess.run(['ngspice', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return 'ngspice'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        return None
    
    def is_available(self) -> bool:
        """Check if ngspice is available."""
        if self.ngspice_path is None:
            return False
        
        # First check if the file exists
        if os.path.exists(self.ngspice_path):
            return True
        
        # Try running a simple command
        try:
            result = subprocess.run([self.ngspice_path, '-v'],
                                  capture_output=True, text=True, timeout=5)
            # ngspice may return non-zero for version, but if it runs, it's available
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            return False
    
    def simulate(self, netlist_content: str) -> Dict[str, any]:
        """Run simulation using ngspice.
        
        Args:
            netlist_content: SPICE netlist content
            
        Returns:
            Dictionary with simulation results
        """
        if not self.is_available():
            raise RuntimeError("ngspice is not available. Please install ngspice.")
        
        # Create temporary directory for simulation files
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write netlist to file
            netlist_path = os.path.join(temp_dir, 'circuit.cir')
            raw_file = os.path.join(temp_dir, 'circuit.raw')
            
            # Add control commands for ASCII raw file output
            full_netlist = netlist_content.strip()
            
            # Check if netlist already has .control section
            if '.control' not in full_netlist.lower():
                # Remove .end if present and add control section
                if full_netlist.lower().endswith('.end'):
                    full_netlist = full_netlist[:-4].strip()
                
                # Use relative path for raw file (works better with ngspice on Windows)
                full_netlist += '''

.control
set filetype=ascii
run
write circuit.raw all
print all
quit
.endc
.end
'''
            
            with open(netlist_path, 'w') as f:
                f.write(full_netlist)
            
            # Run ngspice
            try:
                result = subprocess.run(
                    [self.ngspice_path, '-b', netlist_path],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=temp_dir
                )
                
                # Check for simulation errors (but don't fail on warnings)
                if result.returncode != 0 and 'error' in result.stderr.lower():
                    raise RuntimeError(f"ngspice simulation failed:\n{result.stderr}")
                
                # Try multiple parsing methods
                results = {}
                
                # Method 1: Parse raw file if it exists
                if os.path.exists(raw_file):
                    results = self._parse_raw_file(raw_file)
                
                # Method 2: Parse stdout for print output
                if not results and result.stdout:
                    results = self._parse_stdout(result.stdout)
                
                # Method 3: Look for other output files
                if not results:
                    for f in os.listdir(temp_dir):
                        if f.endswith('.raw') or f.endswith('.txt'):
                            try:
                                results = self._parse_raw_file(os.path.join(temp_dir, f))
                                if results:
                                    break
                            except:
                                pass
                
                return results
                    
            except subprocess.TimeoutExpired:
                raise RuntimeError("ngspice simulation timed out")
    
    def _parse_raw_file(self, raw_file: str) -> Dict[str, any]:
        """Parse ngspice binary raw file.
        
        Args:
            raw_file: Path to .raw file
            
        Returns:
            Dictionary with simulation results
        """
        results = {}
        
        try:
            with open(raw_file, 'rb') as f:
                content = f.read()
            
            # Try to parse as ASCII first (some versions output ASCII)
            try:
                text = content.decode('utf-8', errors='ignore')
                if 'Variables:' in text and 'Values:' in text:
                    return self._parse_ascii_raw(text)
            except:
                pass
            
            # Try binary parsing
            try:
                return self._parse_binary_raw(content)
            except:
                pass
                
        except Exception as e:
            print(f"Warning: Failed to parse raw file: {e}")
        
        return results
    
    def _parse_binary_raw(self, content: bytes) -> Dict[str, any]:
        """Parse binary format raw file."""
        import struct
        
        results = {}
        
        # Find header end (look for 'Binary:' or 'Values:')
        try:
            text_part = content.decode('utf-8', errors='ignore')
        except:
            return results
        
        # Extract variable names from header
        variables = []
        lines = text_part.split('\n')
        in_vars = False
        num_points = 0
        
        for line in lines:
            line_stripped = line.strip()
            if 'No. Points:' in line:
                try:
                    num_points = int(line.split(':')[1].strip())
                except:
                    pass
            elif line_stripped == 'Variables:':
                in_vars = True
            elif line_stripped in ('Binary:', 'Values:'):
                in_vars = False
                break
            elif in_vars and line_stripped:
                parts = line_stripped.split()
                if len(parts) >= 2:
                    var_name = parts[1]
                    variables.append(var_name)
        
        # For binary data, we'd need to find the binary section and parse it
        # This is complex - for now, try ASCII parsing
        if 'Values:' in text_part:
            return self._parse_ascii_raw(text_part)
        
        return results
    
    def _parse_ascii_raw(self, text: str) -> Dict[str, any]:
        """Parse ASCII format raw file.
        
        Format:
        Variables:
            0   time    time
            1   v(in)   voltage
            2   v(out)  voltage
        Values:
         0      0.000000e+00
                0.000000e+00
                0.000000e+00
         1      1.000000e-11
                5.000000e-02
                ...
        
        For AC analysis (complex):
         0      1.000000e+00,0.000000e+00
                1.000000e+00,0.000000e+00
                9.999605e-01,-6.282937e-03
        """
        results = {}
        lines = text.split('\n')
        
        # Check if this is complex data (AC analysis)
        is_complex = False
        for line in lines:
            if 'Flags:' in line and 'complex' in line.lower():
                is_complex = True
                break
        
        # Find variables section
        var_section = False
        variables = []
        num_vars = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped == 'Variables:':
                var_section = True
                continue
            elif stripped == 'Values:':
                var_section = False
                break
            elif var_section and stripped:
                # Parse variable line: "0  time  time" or "1  v(in)  voltage"
                parts = stripped.split()
                if len(parts) >= 2:
                    variables.append(parts[1])
        
        if not variables:
            return results
        
        num_vars = len(variables)
        
        # Initialize result arrays
        for var in variables:
            results[var] = []
        
        def parse_value(s: str):
            """Parse a value that might be complex (real,imag format)."""
            s = s.strip()
            if ',' in s:
                # Complex number
                parts = s.split(',')
                if len(parts) == 2:
                    try:
                        return complex(float(parts[0]), float(parts[1]))
                    except ValueError:
                        return None
            else:
                # Real number
                try:
                    return float(s)
                except ValueError:
                    return None
        
        # Parse values section
        in_values = False
        current_values = []
        
        for line in lines:
            stripped = line.strip()
            
            if stripped == 'Values:':
                in_values = True
                continue
            elif not in_values:
                continue
            
            if not stripped:
                # Empty line might indicate end of a data point
                continue
            
            # Try to parse the line - handle complex numbers
            parts = stripped.split()
            
            if len(parts) == 2 and not ',' in stripped:
                # Format: "index    value" - start of new data point (real)
                try:
                    idx = int(parts[0])
                    val = parse_value(parts[1])
                    if val is not None:
                        # If we have a complete previous point, save it
                        if len(current_values) == num_vars:
                            for i, var in enumerate(variables):
                                results[var].append(current_values[i])
                        
                        # Start new point
                        current_values = [val]
                except ValueError:
                    continue
            elif len(parts) == 1 or ',' in stripped:
                # Single value or complex value - continuation or start
                # Check if it starts with an index
                if '\t' in line or '  ' in line:
                    # Might have index at start
                    line_parts = line.split()
                    if line_parts:
                        try:
                            # Check if first part is an index
                            idx = int(line_parts[0].rstrip(','))
                            # Rest is the value
                            val_str = line_parts[1] if len(line_parts) > 1 else ''
                            val = parse_value(val_str)
                            if val is not None:
                                if len(current_values) == num_vars:
                                    for i, var in enumerate(variables):
                                        results[var].append(current_values[i])
                                current_values = [val]
                                continue
                        except ValueError:
                            pass
                
                # Regular continuation value
                val = parse_value(stripped)
                if val is not None:
                    current_values.append(val)
        
        # Don't forget the last point
        if len(current_values) == num_vars:
            for i, var in enumerate(variables):
                results[var].append(current_values[i])
        
        # Convert lists to numpy arrays and format keys
        formatted_results = {}
        for key, value in results.items():
            if value:
                arr = np.array(value)
                # Format key properly
                key_lower = key.lower()
                if key_lower.startswith('v(') or key_lower.startswith('i('):
                    formatted_results[key] = arr
                elif key_lower == 'time':
                    formatted_results['time'] = arr
                elif key_lower == 'frequency':
                    formatted_results['frequency'] = arr
                else:
                    formatted_results[f'V({key})'] = arr
        
        return formatted_results
    
    def _parse_stdout(self, stdout: str) -> Dict[str, any]:
        """Parse simulation results from stdout.
        
        This is a fallback when raw file parsing fails.
        """
        results = {}
        lines = stdout.split('\n')
        
        # First try to parse tabular format (from transient/ac analysis)
        tabular_results = self._parse_tabular_stdout(lines)
        if tabular_results:
            return tabular_results
        
        # Look for node voltages in output
        voltage_pattern = re.compile(r'v\(([^)]+)\)\s*=\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', re.IGNORECASE)
        current_pattern = re.compile(r'i\(([^)]+)\)\s*=\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', re.IGNORECASE)
        
        # Also look for print output format: "node = value"
        print_pattern = re.compile(r'^\s*(\w+)\s*=\s*([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)', re.MULTILINE)
        
        for line in lines:
            # Check for v(node) = value format
            match = voltage_pattern.search(line)
            if match:
                node = match.group(1)
                value = float(match.group(2))
                results[f'V({node})'] = value
                continue
            
            # Check for i(source) = value format
            match = current_pattern.search(line)
            if match:
                source = match.group(1)
                value = float(match.group(2))
                results[f'I({source})'] = value
                continue
            
            # Check for simple print format
            match = print_pattern.search(line)
            if match:
                name = match.group(1)
                value = float(match.group(2))
                if name.lower() not in ['index', 'time', 'frequency']:
                    results[f'V({name})'] = value
        
        return results
    
    def _parse_tabular_stdout(self, lines: List[str]) -> Dict[str, any]:
        """Parse tabular format from stdout (transient/AC analysis).
        
        Looks for format like:
        Index   time            in              out
        --------------------------------------------------------------------------------
        0       0.000000e+00    0.000000e+00    0.000000e+00
        1       1.000000e-11    5.000000e-02    5.000000e-10
        """
        results = {}
        headers = []
        data_started = False
        header_line_idx = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Look for header line starting with "Index"
            if stripped.lower().startswith('index') and 'time' in stripped.lower():
                # Parse headers
                headers = stripped.split()
                header_line_idx = i
                continue
            
            # Skip separator line (dashes)
            if headers and i == header_line_idx + 1 and stripped.startswith('-'):
                data_started = True
                # Initialize data arrays
                for h in headers:
                    results[h] = []
                continue
            
            # Parse data rows
            if data_started and stripped:
                parts = stripped.split()
                if len(parts) >= len(headers):
                    try:
                        # Check if first column is an index number
                        int(parts[0])
                        for j, h in enumerate(headers):
                            try:
                                results[h].append(float(parts[j]))
                            except (ValueError, IndexError):
                                pass
                    except ValueError:
                        # Not a data row, might be end of data
                        if stripped.startswith('-') or not stripped[0].isdigit():
                            data_started = False
                            break
        
        # Convert to numpy arrays and format keys
        if results:
            formatted = {}
            for key, values in results.items():
                if values:
                    arr = np.array(values)
                    # Format keys properly
                    key_lower = key.lower()
                    if key_lower == 'index':
                        continue  # Skip index column
                    elif key_lower == 'time':
                        formatted['time'] = arr
                    elif key_lower.startswith('v(') or key_lower.startswith('i('):
                        formatted[key] = arr
                    else:
                        # Assume it's a node voltage
                        formatted[f'V({key})'] = arr
            return formatted
        
        return {}
    
    def simulate_netlist_file(self, netlist_file: str) -> Dict[str, any]:
        """Run simulation from a netlist file.
        
        Args:
            netlist_file: Path to SPICE netlist file
            
        Returns:
            Dictionary with simulation results
        """
        with open(netlist_file, 'r') as f:
            netlist_content = f.read()
        
        return self.simulate(netlist_content)
    
    def get_version(self) -> str:
        """Get ngspice version string."""
        if not self.is_available():
            return "Not available"
        
        try:
            result = subprocess.run([self.ngspice_path, '--version'],
                                  capture_output=True, text=True, timeout=5)
            # Extract version from output
            for line in result.stdout.split('\n'):
                if 'ngspice' in line.lower():
                    return line.strip()
            return "Unknown version"
        except Exception:
            return "Unknown"


def test_ngspice_backend():
    """Test function to verify ngspice backend functionality."""
    backend = NgSpiceBackend()
    
    print("Testing NgSpice Backend")
    print("=" * 60)
    print(f"NgSpice available: {backend.is_available()}")
    
    if backend.is_available():
        print(f"NgSpice version: {backend.get_version()}")
        print(f"NgSpice path: {backend.ngspice_path}")
        
        # Test simple voltage divider
        netlist = """
Voltage Divider Test
V1 input 0 DC 10
R1 input output 1k
R2 output 0 1k
.dc V1 10 10 1
.end
"""
        
        print("\nTesting simple voltage divider simulation...")
        try:
            results = backend.simulate(netlist)
            print(f"Results: {results}")
            if 'V(output)' in results or 'output' in results:
                print("✓ Basic simulation working!")
            else:
                print("⚠ Simulation ran but no voltage results found")
        except Exception as e:
            print(f"✗ Simulation failed: {e}")
    else:
        print("\n⚠ NgSpice not found. Install from: http://ngspice.sourceforge.net/")
        print("  Or the built-in Python engine will be used instead.")
    
    print("=" * 60)


if __name__ == '__main__':
    test_ngspice_backend()
