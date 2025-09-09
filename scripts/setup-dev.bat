@echo off
REM Development setup script for Windows
REM Usage: scripts\setup-dev.bat

setlocal enabledelayedexpansion

echo 🚀 Setting up PalletDataGenerator development environment...

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python 3 is required but not installed.
    echo Please install Python 3.9 or later from https://python.org and try again.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Check if conda is available
conda --version >nul 2>&1
if %errorlevel% equ 0 (
    echo Conda detected. Using conda environment.
    set CONDA_AVAILABLE=1

    REM Check if blender environment exists
    conda env list | findstr "blender" >nul
    if %errorlevel% equ 0 (
        echo Conda environment 'blender' already exists. Activating...
        call conda activate blender
    ) else (
        echo Creating conda environment 'blender'...
        call conda create -n blender python=3.11 -y
        call conda activate blender
    )
) else (
    echo Conda not detected. Using system Python with venv.
    set CONDA_AVAILABLE=0

    REM Create virtual environment
    if not exist "venv" (
        echo Creating virtual environment...
        python -m venv venv
    )

    REM Activate virtual environment
    call venv\Scripts\activate.bat
)

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip

REM Install development requirements
echo Installing development requirements...
pip install -r requirements-dev.txt

REM Install the package in development mode
echo Installing package in development mode...
pip install -e .

REM Setup pre-commit hooks
echo Setting up pre-commit hooks...
pre-commit install

REM Create batch file with aliases
echo Creating aliases batch file...
set ALIASES_FILE=%USERPROFILE%\pallet_aliases.bat

(
echo @echo off
echo REM PalletDataGenerator Development Aliases
echo doskey pgen=palletgen $*
echo doskey pgen-info=palletgen info $*
echo doskey pgen-config=palletgen config $*
echo doskey pgen-generate=palletgen generate $*
echo doskey pgen-test=pytest tests/ -v $*
echo doskey pgen-lint=pre-commit run --all-files $*
echo doskey pgen-docs=cd docs ^&^& make html $*
echo doskey pgen-clean=for /d /r . %%%%d in ^(__pycache__^) do @if exist "%%%%d" rd /s /q "%%%%d" $*
echo.
echo REM Development helpers
echo doskey pgen-dev-setup=pre-commit run --all-files ^&^& pytest tests/ -v $*
echo doskey pgen-build=python -m build $*
echo doskey pgen-format=black src/ tests/ ^&^& ruff check --fix src/ tests/ $*
) > "%ALIASES_FILE%"

REM Add to Windows startup (optional)
echo.
echo Aliases created in %ALIASES_FILE%
echo To use aliases in new command prompts, run: %ALIASES_FILE%
echo.
echo You can add this to your Windows startup by creating a shortcut in:
echo %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup

REM Run initial tests
echo Running initial tests...
pytest tests/ -v --tb=short
if %errorlevel% equ 0 (
    echo ✅ All tests passed!
) else (
    echo ⚠️  Some tests failed, but setup completed.
)

REM Final instructions
echo.
echo 🎉 Development environment setup complete!
echo.
echo Next steps:
echo 1. Run aliases: %ALIASES_FILE%
echo 2. Try the CLI: pgen info --version
echo 3. Run tests: pgen-test
echo 4. Check code quality: pgen-lint
echo 5. Build docs: pgen-docs

if %CONDA_AVAILABLE% equ 1 (
    echo.
    echo Conda environment 'blender' is active.
    echo To activate it in new shells: conda activate blender
) else (
    echo.
    echo Virtual environment created in .\venv
    echo To activate it in new shells: venv\Scripts\activate.bat
)

echo.
echo Happy coding! 🚀
pause
