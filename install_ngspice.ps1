# NgSpice Installation Script for Windows
# This script downloads and installs ngspice to C:\ngspice

$ErrorActionPreference = "Stop"

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   NgSpice Installation Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$installPath = "C:\ngspice"
$tempDir = "$env:TEMP\ngspice_install"

# Create temp directory
if (Test-Path $tempDir) {
    Remove-Item -Path $tempDir -Recurse -Force
}
New-Item -Path $tempDir -ItemType Directory -Force | Out-Null

Write-Host "Step 1: Downloading ngspice binaries..." -ForegroundColor Yellow

# Try multiple mirrors
$mirrors = @(
    "https://downloads.sourceforge.net/project/ngspice/ng-spice-rework/42/ngspice-42_64.zip",
    "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/ngspice-42_64.zip/download"
)

$downloaded = $false
foreach ($url in $mirrors) {
    try {
        Write-Host "  Trying: $url" -ForegroundColor Gray
        $zipFile = "$tempDir\ngspice.zip"
        
        # Use System.Net.WebClient for better reliability
        $webClient = New-Object System.Net.WebClient
        $webClient.Headers.Add("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        $webClient.DownloadFile($url, $zipFile)
        
        if ((Test-Path $zipFile) -and ((Get-Item $zipFile).Length -gt 1MB)) {
            Write-Host "  Download successful! ($('{0:N2}' -f ((Get-Item $zipFile).Length / 1MB)) MB)" -ForegroundColor Green
            $downloaded = $true
            break
        }
    }
    catch {
        Write-Host "  Failed: $($_.Exception.Message)" -ForegroundColor Red
    }
}

if (-not $downloaded) {
    Write-Host ""
    Write-Host "ERROR: Could not download ngspice automatically." -ForegroundColor Red
    Write-Host ""
    Write-Host "Please download manually:" -ForegroundColor Yellow
    Write-Host "1. Visit: https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/" -ForegroundColor White
    Write-Host "2. Download: ngspice-42_64.zip" -ForegroundColor White
    Write-Host "3. Extract to: C:\ngspice" -ForegroundColor White
    Write-Host "4. Add to PATH: C:\ngspice\bin" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to open download page in browser"
    Start-Process "https://sourceforge.net/projects/ngspice/files/ng-spice-rework/42/ngspice-42_64.zip/download"
    exit 1
}

Write-Host ""
Write-Host "Step 2: Extracting files..." -ForegroundColor Yellow

try {
    # Extract using .NET
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zipFile, $tempDir)
    
    # Find the ngspice folder (it might be nested)
    $ngspiceFolder = Get-ChildItem -Path $tempDir -Directory | Where-Object { $_.Name -like "ngspice*" } | Select-Object -First 1
    
    if ($ngspiceFolder) {
        # Copy to final destination
        if (Test-Path $installPath) {
            Write-Host "  Removing old installation..." -ForegroundColor Gray
            Remove-Item -Path $installPath -Recurse -Force
        }
        
        Write-Host "  Installing to $installPath..." -ForegroundColor Gray
        Copy-Item -Path $ngspiceFolder.FullName -Destination $installPath -Recurse -Force
        Write-Host "  Installation complete!" -ForegroundColor Green
    }
    else {
        throw "Could not find ngspice folder in archive"
    }
}
catch {
    Write-Host "  ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Step 3: Configuring PATH..." -ForegroundColor Yellow

$binPath = "$installPath\bin"

if (Test-Path $binPath) {
    # Get current PATH
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    
    if ($currentPath -notlike "*$binPath*") {
        try {
            # Add to system PATH (requires admin)
            $newPath = "$currentPath;$binPath"
            [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
            Write-Host "  Added to system PATH" -ForegroundColor Green
        }
        catch {
            Write-Host "  Could not add to system PATH (need admin rights)" -ForegroundColor Yellow
            Write-Host "  Adding to user PATH instead..." -ForegroundColor Yellow
            
            $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
            if ($userPath -notlike "*$binPath*") {
                $newUserPath = "$userPath;$binPath"
                [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
                Write-Host "  Added to user PATH" -ForegroundColor Green
            }
        }
        
        # Update current session PATH
        $env:Path = "$env:Path;$binPath"
    }
    else {
        Write-Host "  Already in PATH" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Step 4: Verifying installation..." -ForegroundColor Yellow

$ngspiceExe = "$binPath\ngspice.exe"
if (Test-Path $ngspiceExe) {
    try {
        $version = & $ngspiceExe --version 2>&1 | Select-Object -First 1
        Write-Host "  ngspice installed successfully!" -ForegroundColor Green
        Write-Host "  Version: $version" -ForegroundColor Green
        Write-Host "  Location: $ngspiceExe" -ForegroundColor Green
    }
    catch {
        Write-Host "  WARNING: ngspice.exe found but could not run" -ForegroundColor Yellow
    }
}
else {
    Write-Host "  ERROR: ngspice.exe not found!" -ForegroundColor Red
    exit 1
}

# Cleanup
Write-Host ""
Write-Host "Step 5: Cleaning up..." -ForegroundColor Yellow
Remove-Item -Path $tempDir -Recurse -Force
Write-Host "  Temporary files removed" -ForegroundColor Green

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "NgSpice has been installed to: $installPath" -ForegroundColor White
Write-Host "Binary location: $binPath\ngspice.exe" -ForegroundColor White
Write-Host ""
Write-Host "IMPORTANT: Please restart your terminal or IDE for PATH changes to take effect." -ForegroundColor Yellow
Write-Host ""
Write-Host "To test the installation, run:" -ForegroundColor White
Write-Host "  ngspice --version" -ForegroundColor Cyan
Write-Host ""
Write-Host "To test with AMS Simulator, run:" -ForegroundColor White
Write-Host "  python -c ""from simulator.engine.ngspice_backend import NgSpiceBackend; b=NgSpiceBackend(); print(f'Available: {b.is_available()}, Version: {b.get_version()}')""" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
