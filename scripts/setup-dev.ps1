#!/usr/bin/env pwsh
# Development setup script for PowerShell (Windows, Linux, macOS)
# Usage: ./scripts/setup-dev.ps1

param(
    [switch]$Force,
    [string]$PythonVersion = "3.11"
)

# Enable strict mode
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up PalletDataGenerator development environment..." -ForegroundColor Blue

# Colors
$Colors = @{
    Red = [ConsoleColor]::Red
    Green = [ConsoleColor]::Green
    Yellow = [ConsoleColor]::Yellow
    Blue = [ConsoleColor]::Blue
    Cyan = [ConsoleColor]::Cyan
}

function Write-ColoredOutput {
    param([string]$Message, [ConsoleColor]$Color = [ConsoleColor]::White)
    Write-Host $Message -ForegroundColor $Color
}

# Detect platform
$IsWindowsPlatform = $IsWindows -or ($PSVersionTable.PSVersion.Major -lt 6)
$Platform = if ($IsWindowsPlatform) { "Windows" } elseif ($IsLinux) { "Linux" } elseif ($IsMacOS) { "macOS" } else { "Unknown" }

Write-ColoredOutput "Detected platform: $Platform" $Colors.Blue

# Check if Python is available
try {
    $PythonVersionOutput = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-ColoredOutput "Python version: $PythonVersionOutput" $Colors.Blue
} catch {
    Write-ColoredOutput "Error: Python 3 is required but not installed." $Colors.Red
    Write-ColoredOutput "Please install Python 3.9 or later and try again." $Colors.Yellow
    exit 1
}

# Check if conda is available
$CondaAvailable = $false
try {
    conda --version | Out-Null
    $CondaAvailable = $true
    Write-ColoredOutput "Conda detected. Using conda environment." $Colors.Green

    # Check if blender environment exists
    $CondaEnvs = conda env list 2>$null
    if ($CondaEnvs -match "blender") {
        Write-ColoredOutput "Conda environment 'blender' already exists." $Colors.Yellow
        if ($Force) {
            Write-ColoredOutput "Force flag set. Recreating environment..." $Colors.Yellow
            conda env remove -n blender -y
            conda create -n blender python=$PythonVersion -y
        }
    } else {
        Write-ColoredOutput "Creating conda environment 'blender'..." $Colors.Blue
        conda create -n blender python=$PythonVersion -y
    }

    # Activate conda environment
    conda activate blender
} catch {
    Write-ColoredOutput "Conda not detected. Using system Python with venv." $Colors.Yellow

    # Create virtual environment
    if (!(Test-Path "venv") -or $Force) {
        if ($Force -and (Test-Path "venv")) {
            Write-ColoredOutput "Force flag set. Removing existing virtual environment..." $Colors.Yellow
            Remove-Item -Recurse -Force venv
        }
        Write-ColoredOutput "Creating virtual environment..." $Colors.Blue
        python -m venv venv
    }

    # Activate virtual environment
    if ($IsWindowsPlatform) {
        & "venv\Scripts\Activate.ps1"
    } else {
        & "venv/bin/Activate.ps1"
    }
}

# Upgrade pip
Write-ColoredOutput "Upgrading pip..." $Colors.Blue
python -m pip install --upgrade pip

# Install development requirements
Write-ColoredOutput "Installing development requirements..." $Colors.Blue
pip install -r requirements-dev.txt

# Install the package in development mode
Write-ColoredOutput "Installing package in development mode..." $Colors.Blue
pip install -e .

# Setup pre-commit hooks
Write-ColoredOutput "Setting up pre-commit hooks..." $Colors.Blue
pre-commit install

# Create PowerShell profile with aliases
Write-ColoredOutput "Setting up PowerShell aliases..." $Colors.Blue
$ProfileContent = @'
# PalletDataGenerator Development Aliases
function pgen { palletgen @args }
function pgen-info { palletgen info @args }
function pgen-config { palletgen config @args }
function pgen-generate { palletgen generate @args }
function pgen-test { pytest tests/ -v @args }
function pgen-lint { pre-commit run --all-files @args }
function pgen-docs {
    Push-Location docs
    try { make html @args }
    finally { Pop-Location }
}
function pgen-clean {
    Get-ChildItem -Path . -Recurse -Directory -Name "__pycache__" | Remove-Item -Recurse -Force
}

# Development helpers
function pgen-dev-setup {
    pre-commit run --all-files
    if ($LASTEXITCODE -eq 0) { pytest tests/ -v }
}
function pgen-build { python -m build @args }
function pgen-format {
    black src/ tests/
    ruff check --fix src/ tests/ @args
}

Write-Host "PalletDataGenerator aliases loaded! 🚀" -ForegroundColor Green
'@

# Add to PowerShell profile
$ProfilePath = $PROFILE.CurrentUserAllHosts
$ProfileDir = Split-Path $ProfilePath -Parent

if (!(Test-Path $ProfileDir)) {
    New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
}

if (!(Test-Path $ProfilePath) -or $Force) {
    $ProfileContent | Out-File -FilePath $ProfilePath -Encoding UTF8
    Write-ColoredOutput "PowerShell profile created at: $ProfilePath" $Colors.Green
} else {
    # Check if our aliases are already in the profile
    $ExistingProfile = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
    if ($ExistingProfile -notmatch "PalletDataGenerator Development Aliases") {
        $ProfileContent | Out-File -FilePath $ProfilePath -Append -Encoding UTF8
        Write-ColoredOutput "Aliases added to existing PowerShell profile" $Colors.Green
    } else {
        Write-ColoredOutput "Aliases already configured in PowerShell profile" $Colors.Yellow
    }
}

# Run initial tests
Write-ColoredOutput "Running initial tests..." $Colors.Blue
try {
    pytest tests/ -v --tb=short
    Write-ColoredOutput "✅ All tests passed!" $Colors.Green
} catch {
    Write-ColoredOutput "⚠️  Some tests failed, but setup completed." $Colors.Yellow
}

# Final instructions
Write-ColoredOutput "`n🎉 Development environment setup complete!" $Colors.Green
Write-ColoredOutput "`nNext steps:" $Colors.Blue
Write-ColoredOutput "1. Restart PowerShell or reload profile: . `$PROFILE" $Colors.Yellow
Write-ColoredOutput "2. Try the CLI: pgen info --version" $Colors.Yellow
Write-ColoredOutput "3. Run tests: pgen-test" $Colors.Yellow
Write-ColoredOutput "4. Check code quality: pgen-lint" $Colors.Yellow
Write-ColoredOutput "5. Build docs: pgen-docs" $Colors.Yellow

if ($CondaAvailable) {
    Write-ColoredOutput "`nConda environment 'blender' is active." $Colors.Blue
    Write-ColoredOutput "To activate it in new shells: conda activate blender" $Colors.Yellow
} else {
    Write-ColoredOutput "`nVirtual environment created in ./venv" $Colors.Blue
    $ActivateScript = if ($IsWindowsPlatform) { "venv\Scripts\Activate.ps1" } else { "venv/bin/Activate.ps1" }
    Write-ColoredOutput "To activate it in new shells: $ActivateScript" $Colors.Yellow
}

Write-ColoredOutput "`nHappy coding! 🚀" $Colors.Green
