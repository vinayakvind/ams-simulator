# Manual NgSpice Installation Helper
# Use this if you've already downloaded ngspice-42_64.zip

param(
    [string]$ZipPath = "$env:USERPROFILE\Downloads\ngspice-42_64.zip"
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  NgSpice Manual Installation Helper" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if ZIP exists
if (-not (Test-Path $ZipPath)) {
    Write-Host "ERROR: ZIP file not found at: $ZipPath" -ForegroundColor Red
    Write-Host "`nPlease:" -ForegroundColor Yellow
    Write-Host "1. Download from: https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/ngspice-42_64.zip/download"
    Write-Host "2. Save to: $ZipPath"
    Write-Host "3. Run this script again`n"
    
    $customPath = Read-Host "Or enter the full path to the ZIP file (or press Enter to exit)"
    if ($customPath) {
        $ZipPath = $customPath
        if (-not (Test-Path $ZipPath)) {
            Write-Host "ERROR: File not found: $ZipPath" -ForegroundColor Red
            exit 1
        }
    }
    else {
        exit 1
    }
}

Write-Host "Found ZIP file: $ZipPath" -ForegroundColor Green
Write-Host "Size: $((Get-Item $ZipPath).Length / 1MB | ForEach-Object { '{0:N2}' -f $_ }) MB`n"

$installPath = "C:\ngspice"
$tempDir = "$env:TEMP\ngspice_extract"

# Extract
Write-Host "Extracting..." -ForegroundColor Yellow
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -Path $tempDir -ItemType Directory -Force | Out-Null

try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ZipPath, $tempDir)
    
    # Find ngspice folder
    $ngspiceFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "*ngspice*" } | Select-Object -First 1
    
    if (-not $ngspiceFolder) {
        # Files might be at root
        if (Test-Path "$tempDir\bin\ngspice.exe") {
            $ngspiceFolder = Get-Item $tempDir
        }
        else {
            throw "Could not find ngspice files in archive"
        }
    }
    
    Write-Host "Found ngspice at: $($ngspiceFolder.FullName)" -ForegroundColor Green
    
    # Install
    Write-Host "`nInstalling to: $installPath" -ForegroundColor Yellow
    if (Test-Path $installPath) {
        Write-Host "Removing old installation..." -ForegroundColor Gray
        Remove-Item -Path $installPath -Recurse -Force
    }
    
    Copy-Item -Path $ngspiceFolder.FullName -Destination $installPath -Recurse -Force
    Write-Host "Installation complete!" -ForegroundColor Green
}
catch {
    Write-Host "`nERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    if (Test-Path $tempDir) {
        Remove-Item -Path $tempDir -Recurse -Force
    }
}

# Add to PATH
Write-Host "`nConfiguring PATH..." -ForegroundColor Yellow
$binPath = "$installPath\bin"

if (-not (Test-Path $binPath)) {
    Write-Host "ERROR: $binPath not found!" -ForegroundColor Red
    exit 1
}

# Try user PATH first (doesn't require admin)
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$binPath*") {
    Write-Host "Adding to user PATH..." -ForegroundColor Gray
    $newUserPath = if ($userPath) { "$userPath;$binPath" } else { $binPath }
    [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
    Write-Host "Added to user PATH" -ForegroundColor Green
}
else {
    Write-Host "Already in user PATH" -ForegroundColor Green
}

# Update current session
$env:Path = "$env:Path;$binPath"

# Verify
Write-Host "`nVerifying installation..." -ForegroundColor Yellow
$ngspiceExe = "$binPath\ngspice.exe"

if (Test-Path $ngspiceExe) {
    try {
        $version = & $ngspiceExe --version 2>&1 | Select-Object -First 1
        Write-Host "✓ ngspice.exe found and working!" -ForegroundColor Green
        Write-Host "  Version: $version" -ForegroundColor Cyan
        Write-Host "  Path: $ngspiceExe" -ForegroundColor Cyan
    }
    catch {
        Write-Host "⚠ ngspice.exe found but execution failed" -ForegroundColor Yellow
        Write-Host "  This may be normal - try running in a new terminal" -ForegroundColor Gray
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Installation Successful!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nIMPORTANT:" -ForegroundColor Yellow
Write-Host "  Please restart your terminal/IDE for PATH changes to take effect.`n"

Write-Host "To test:" -ForegroundColor White
Write-Host "  ngspice --version" -ForegroundColor Cyan
Write-Host "`nOr test with AMS Simulator:" -ForegroundColor White
Write-Host "  python simulator\engine\ngspice_backend.py`n" -ForegroundColor Cyan

Read-Host "Press Enter to exit"
