# 🚀 NgSpice Installation - Quick Guide

## Option 1: Manual Installation (Recommended - 5 minutes)

### Step 1: Download
1. Open this link in your browser: https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/ngspice-42_64.zip/download
2. Wait for the download to start (SourceForge will redirect)
3. Save the file (approximately 15-20 MB)

### Step 2: Extract
1. Once downloaded, right-click `ngspice-42_64.zip`
2. Select "Extract All..."
3. Extract to: `C:\ngspice`
   - The final structure should be: `C:\ngspice\bin\ngspice.exe`

### Step 3: Add to PATH
**Method A - GUI (Easy)**:
1. Press `Windows + R`, type `sysdm.cpl`, press Enter
2. Go to "Advanced" tab → Click "Environment Variables"
3. Under "System variables", find and select "Path"
4. Click "Edit" → "New"
5. Add: `C:\ngspice\bin`
6. Click OK on all dialogs

**Method B - PowerShell (Quick)**:
```powershell
# Run this in PowerShell (as Administrator):
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
$path += ";C:\ngspice\bin"
[Environment]::SetEnvironmentVariable("Path", $path, "Machine")
```

### Step 4: Verify
Open a **new** terminal and run:
```powershell
ngspice --version
```

Should show: `ngspice-42` (or similar)

## Option 2: Using the Installation Script

If you have the ZIP file already downloaded:

1. Save `ngspice-42_64.zip` to `C:\Users\vinay\Downloads\`
2. Run this PowerShell command:

```powershell
cd "C:\Users\vinay\My Simulator"
& ".\manual_install_ngspice.ps1"
```

## Option 3: Test Without Installation

The AMS Simulator works fine without ngspice for simple circuits. You can:
- Use the built-in Python engine for R-L-C circuits
- Install ngspice later when needed for complex circuits

## Troubleshooting

### "ngspice not recognized"
- Make sure you've extracted to `C:\ngspice\bin\ngspice.exe`
- Restart your terminal/PowerShell after adding to PATH
- Run: `$env:Path -split ';'` to check if `C:\ngspice\bin` is listed

### Download Issues
- SourceForge sometimes blocks automated downloads
- Use your web browser to download manually
- Alternative: Try older version (41 or 40) from the same page

### Permission Errors
- Extract to your user folder: `C:\Users\vinay\ngspice`
- Use User PATH instead of System PATH
- Run PowerShell as Administrator for system-wide installation

## Quick Test in AMS Simulator

After installation, test with:

```powershell
cd "C:\Users\vinay\My Simulator"
& ".venv\Scripts\python.exe" -c "from simulator.engine.ngspice_backend import NgSpiceBackend; b=NgSpiceBackend(); print(f'NgSpice Available: {b.is_available()}'); print(f'Version: {b.get_version()}')"
```

## What You Get with NgSpice

✅ All 7 standard circuits will work  
✅ Better convergence for complex circuits  
✅ Professional-grade accuracy  
✅ BSIM3/4 MOSFET models  
✅ Industry-standard simulation  

## Without NgSpice

✅ Linear circuits work perfectly (RC filters, etc.)  
⚠️ DC-DC converters need enhancement  
⚠️ Op-amp circuits may not converge  

**Recommendation**: Install ngspice for best results, but not mandatory for learning/simple circuits.

---

**Need Help?**
- Full guide: See `NGSPICE_SETUP_GUIDE.md`
- Run installation script: `.\install_ngspice.ps1`
- Manual download: https://sourceforge.net/projects/ngspice/files/
