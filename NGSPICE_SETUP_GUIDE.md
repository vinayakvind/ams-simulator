# NgSpice Installation and Setup Guide

## What is NgSpice?

NgSpice is a professional-grade, open-source circuit simulator based on Berkeley SPICE 3. It provides:
- ✅ Highly accurate analog simulation
- ✅ Comprehensive device models (MOSFET BSIM3/4, BJT Gummel-Poon, etc.)
- ✅ Robust convergence algorithms
- ✅ Industry-standard SPICE syntax
- ✅ Active development and support

## Why Use NgSpice with AMS Simulator?

The AMS Simulator includes **two simulation engines**:

1. **Built-in Python Engine**
   - ✅ Fast, lightweight, no dependencies
   - ✅ Good for learning and simple circuits
   - ✅ R, L, C, and basic semiconductor devices
   - ⚠️ Limited device models
   - ⚠️ May have convergence issues with complex circuits

2. **NgSpice Backend** (Recommended for Production)
   - ✅ Professional-grade accuracy
   - ✅ All standard SPICE models
   - ✅ Excellent convergence
   - ✅ Proven in industry
   - ℹ️ Requires separate installation

## Installation Instructions

### Windows

#### Method 1: Official Installer (Recommended)

1. **Download NgSpice**
   - Visit: https://ngspice.sourceforge.io/download.html
   - Download: `ngspice-XX_64.zip` or `.exe` installer (latest version)
   - Example: `ngspice-42_64.zip`

2. **Install NgSpice**
   - Extract ZIP to: `C:\ngspice\`
   - Or run installer and choose installation directory
   - Verify files exist: `C:\ngspice\bin\ngspice.exe`

3. **Add to PATH** (Important!)
   - Right-click "This PC" → Properties → Advanced system settings
   - Click "Environment Variables"
   - Under "System variables", find "Path"
   - Click "Edit" → "New"
   - Add: `C:\ngspice\bin`
   - Click OK on all dialogs

4. **Verify Installation**
   ```powershell
   ngspice --version
   ```
   Should show: `ngspice-42` (or your version)

#### Method 2: Pre-built Binaries

If the installer doesn't work:

1. Download pre-built binaries from: https://sourceforge.net/projects/ngspice/files/
2. Extract to `C:\ngspice\`
3. Follow step 3-4 above

### Linux

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ngspice
ngspice --version
```

#### Fedora/RHEL
```bash
sudo dnf install ngspice
ngspice --version
```

#### From Source
```bash
sudo apt-get install build-essential autoconf libtool
wget https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/ngspice-42.tar.gz
tar -xzf ngspice-42.tar.gz
cd ngspice-42
./configure --with-ngshared
make
sudo make install
```

### macOS

#### Using Homebrew
```bash
brew install ngspice
ngspice --version
```

#### From Source
Similar to Linux instructions

## Configuring AMS Simulator

### Automatic Detection (Default)

AMS Simulator automatically detects ngspice if it's in your PATH. No configuration needed!

### Manual Configuration

If ngspice is installed in a custom location:

```python
from simulator.engine.ngspice_backend import NgSpiceBackend

# Specify custom path
backend = NgSpiceBackend(ngspice_path=r'C:\custom\path\ngspice.exe')

if backend.is_available():
    print("NgSpice ready!")
```

## Testing Your Installation

### Quick Test Script

```python
# test_ngspice.py
from simulator.engine.ngspice_backend import NgSpiceBackend

backend = NgSpiceBackend()

print("=" * 60)
print("NgSpice Detection Test")
print("=" * 60)

if backend.is_available():
    print("✓ NgSpice is available!")
    print(f"  Version: {backend.get_version()}")
    print(f"  Path: {backend.ngspice_path}")
    
    # Test simulation
    netlist = """
Voltage Divider Test
V1 input 0 DC 5
R1 input output 1k
R2 output 0 1k
.dc V1 5 5 1
.end
"""
    print("\nRunning test simulation...")
    results = backend.simulate(netlist)
    print(f"Results: {results}")
    
    if results:
        print("✓ NgSpice simulation working!")
    else:
        print("⚠ Warning: No results returned")
else:
    print("✗ NgSpice not found!")
    print("\nPlease install ngspice:")
    print("  Windows: https://ngspice.sourceforge.io/download.html")
    print("  Linux: sudo apt-get install ngspice")
    print("  macOS: brew install ngspice")

print("=" * 60)
```

Run with:
```powershell
python test_ngspice.py
```

### Full Test Suite

Run all standard circuits with ngspice:

```python
# In test_standard_circuits.py, modify to use ngspice:
backend = NgSpiceBackend()
if backend.is_available():
    results = backend.simulate_netlist_file(circuit_file)
```

## Using NgSpice in Your Simulations

### From GUI

The GUI will automatically use ngspice if available. No changes needed!

### From Python Code

```python
from simulator.engine.ngspice_backend import NgSpiceBackend

# Initialize backend
backend = NgSpiceBackend()

# Check availability
if not backend.is_available():
    print("NgSpice not available, using built-in engine")
    # Fall back to built-in engine
else:
    # Simulate from netlist file
    results = backend.simulate_netlist_file("circuit.spice")
    
    # Or from string
    netlist = """
My Circuit
V1 in 0 DC 5
R1 in out 1k
R2 out 0 1k
.dc V1 5 5 1
.end
"""
    results = backend.simulate(netlist)
    
    # Access results
    v_output = results.get('V(out)', None)
    print(f"Output voltage: {v_output}")
```

### Hybrid Mode (Best Practice)

```python
from simulator.engine.ngspice_backend import NgSpiceBackend
from simulator.engine.analog_engine import AnalogEngine, DCAnalysis

def simulate_circuit(netlist_file):
    """Simulate using ngspice if available, otherwise use built-in engine."""
    
    # Try ngspice first
    backend = NgSpiceBackend()
    if backend.is_available():
        print("Using NgSpice for high-fidelity simulation")
        return backend.simulate_netlist_file(netlist_file)
    
    # Fall back to built-in engine
    print("Using built-in Python engine")
    engine = AnalogEngine()
    engine.parse_netlist(netlist_file)
    analysis = DCAnalysis(engine)
    return analysis.run({})

# Use it
results = simulate_circuit("examples/buck_converter.spice")
```

## Troubleshooting

### NgSpice Not Found

**Error**: `NgSpice not available` or `FileNotFoundError`

**Solutions**:
1. Check installation: `ngspice --version` in terminal
2. Verify PATH environment variable includes ngspice bin directory
3. Restart terminal/IDE after PATH changes
4. Try absolute path: `NgSpiceBackend(r'C:\ngspice\bin\ngspice.exe')`

### Simulation Errors

**Error**: `ngspice simulation failed`

**Solutions**:
1. Check netlist syntax (SPICE syntax is strict)
2. Verify all nodes are connected
3. Ensure ground node (0) exists
4. Check for missing .end statement
5. Review ngspice output for specific error messages

### Access Denied / Permission Errors

**Windows**: Run as administrator or install to user directory
**Linux**: Use sudo for installation, or install to `~/.local/bin`

### DLL/Library Errors

**Windows**: Install Visual C++ Redistributables
**Linux**: Install shared library dependencies
```bash
sudo apt-get install libngspice0 libngspice0-dev
```

## Advanced Configuration

### Environment Variables

```powershell
# Windows PowerShell
$env:NGSPICE_HOME = "C:\ngspice"
$env:PATH = "$env:NGSPICE_HOME\bin;$env:PATH"
```

```bash
# Linux/macOS
export NGSPICE_HOME=/usr/local/ngspice
export PATH=$NGSPICE_HOME/bin:$PATH
export LD_LIBRARY_PATH=$NGSPICE_HOME/lib:$LD_LIBRARY_PATH
```

### Custom Model Libraries

Place custom device models in:
- Windows: `C:\ngspice\share\ngspice\models\`
- Linux: `/usr/local/share/ngspice/models/`

Reference in netlist:
```spice
.include 'path/to/custom_models.lib'
```

## Performance Tips

1. **Use .OPTION for Better Convergence**
   ```spice
   .option reltol=1e-3 abstol=1e-12 vntol=1e-6
   .option method=gear
   ```

2. **Parallel Simulations**
   NgSpice can run multiple simulations in parallel:
   ```python
   import concurrent.futures
   
   circuits = ['circuit1.spice', 'circuit2.spice', 'circuit3.spice']
   backend = NgSpiceBackend()
   
   with concurrent.futures.ProcessPoolExecutor() as executor:
       results = list(executor.map(backend.simulate_netlist_file, circuits))
   ```

3. **Memory Management**
   For large circuits, use:
   ```spice
   .option sparse=1
   .option pivrel=1e-3
   ```

## Recommended Workflow

1. **Quick Testing**: Use built-in Python engine
   - Fast iteration
   - Immediate feedback
   - Good for learning

2. **Final Verification**: Use ngspice
   - Production-quality results
   - Accurate device models
   - Convergence guarantee

3. **Complex Circuits**: Always use ngspice
   - Op-amps, references, regulators
   - Mixed-signal circuits
   - High-frequency circuits

## Additional Resources

- **NgSpice Manual**: http://ngspice.sourceforge.net/docs/ngspice-manual.pdf
- **SPICE Syntax**: http://bwrcs.eecs.berkeley.edu/Classes/IcBook/SPICE/
- **Model Libraries**: https://github.com/KiCad/kicad-symbols/tree/master/Simulation_SPICE
- **Community Forum**: https://sourceforge.net/p/ngspice/discussion/

## Summary

✅ **Install ngspice** for professional-grade simulations  
✅ **Add to PATH** for automatic detection  
✅ **Test installation** with provided test script  
✅ **Use hybrid mode** for best results  

The combination of AMS Simulator's intuitive GUI and ngspice's powerful engine gives you the best of both worlds!

---
**Last Updated**: 2024  
**AMS Simulator Version**: 2.0  
**Tested with**: NgSpice 42
