# Quick Reference - Standard Circuits & Fixes

## ✅ What Was Fixed

1. **Terminal Widget Command Execution** - PowerShell parsing error fixed
2. **Standard Circuits Integration** - All 11 circuits verified and working
3. **Circuit Library Documentation** - Complete guide generated

---

## 📚 Available Standard Circuits (11 Total)

### Power Supplies
- **Buck Converter** (12V→5V) - `buck_converter.spice`
- **Boost Converter** (5V→12V) - `boost_converter.spice`  
- **Buck-Boost** (12V→-12V) - `buck_boost_converter.spice`
- **Flyback** (48V→12V isolated) - `flyback_converter.spice`
- **LDO Regulator** (5V→3.3V) - `ldo_regulator.spice`

### Analog
- **Bandgap Reference** (1.25V) - `bandgap_reference.spice`
- **Differential Amplifier** (40dB gain) - `differential_amplifier.spice`
- **RC High-Pass Filter** (1kHz) - `rc_highpass.spice`

### Data Converters
- **SAR ADC** (8-bit) - `sar_adc.spice`
- **Sigma-Delta ADC** - `sigma_delta_adc.spice`
- **R-2R DAC** (8-bit) - `r2r_dac.spice`

---

## 🚀 How to Use

### In GUI
```
File → Open Standard Circuit → Select any circuit → Load → Simulate
```

### In Terminal Widget (inside GUI)
```
$ ams-sim --netlist buck_converter.spice --analysis transient
```

### Via Command Line
```bash
python -m simulator.cli.runner --netlist examples/standard_circuits/buck_converter.spice
```

---

## 📊 Test Status
```
ALL 11 CIRCUITS: ✅ VERIFIED & WORKING
- Simulation: ✅ All pass
- GUI Integration: ✅ Working
- CLI Tools: ✅ Fixed and working
- Batch Processing: ✅ Functional
```

---

## 📄 Documentation Files
- `STANDARD_CIRCUITS_GUIDE.md` - Complete circuit catalog
- `STANDARD_CIRCUITS_VERIFICATION.md` - Detailed verification report  
- `test_standard_circuits_detailed.py` - Verification script

---

## ✨ Examples

**Simulate buck converter:**
```bash
$ ams-sim --netlist buck_converter.spice --analysis transient --tstop 100e-6
```

**Batch simulate all:**
```bash
python -m simulator.cli.batch --dir examples/standard_circuits
```

**Get help:**
```bash
$ python -m simulator.cli.runner --help
```

---

**Status:** Everything is working! The simulator and all standard circuits are ready to use.
