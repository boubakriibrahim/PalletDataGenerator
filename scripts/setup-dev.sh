#!/bin/bash
# Development setup script for Unix-like systems (Linux, macOS)
# Usage: ./scripts/setup-dev.sh

set -e  # Exit on any error

echo "🚀 Setting up PalletDataGenerator development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect OS
OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
fi

echo -e "${BLUE}Detected OS: $OS${NC}"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    echo -e "${YELLOW}Please install Python 3.9 or later and try again.${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${BLUE}Python version: $PYTHON_VERSION${NC}"

# Check if conda is available (recommended for Blender integration)
if command -v conda &> /dev/null; then
    echo -e "${GREEN}Conda detected. Using conda environment.${NC}"
    CONDA_AVAILABLE=true

    # Check if blender environment exists
    if conda env list | grep -q "blender"; then
        echo -e "${YELLOW}Conda environment 'blender' already exists. Activating...${NC}"
        eval "$(conda shell.bash hook)"
        conda activate blender
    else
        echo -e "${BLUE}Creating conda environment 'blender'...${NC}"
        conda create -n blender python=3.11 -y
        eval "$(conda shell.bash hook)"
        conda activate blender
    fi
else
    echo -e "${YELLOW}Conda not detected. Using system Python with venv.${NC}"
    CONDA_AVAILABLE=false

    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi

    # Activate virtual environment
    source venv/bin/activate
fi

# Upgrade pip
echo -e "${BLUE}Upgrading pip...${NC}"
pip install --upgrade pip

# Install development requirements
echo -e "${BLUE}Installing development requirements...${NC}"
pip install -r requirements-dev.txt

# Install the package in development mode
echo -e "${BLUE}Installing package in development mode...${NC}"
pip install -e .

# Setup pre-commit hooks
echo -e "${BLUE}Setting up pre-commit hooks...${NC}"
pre-commit install

# Create shell aliases file
ALIASES_FILE="$HOME/.pallet_aliases"
echo -e "${BLUE}Creating shell aliases...${NC}"

cat > "$ALIASES_FILE" << 'EOF'
# PalletDataGenerator Development Aliases
alias pgen='palletgen'
alias pgen-info='palletgen info'
alias pgen-config='palletgen config'
alias pgen-generate='palletgen generate'
alias pgen-test='pytest tests/ -v'
alias pgen-lint='pre-commit run --all-files'
alias pgen-docs='cd docs && make html'
alias pgen-clean='find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true'

# Development helpers
alias pgen-dev-setup='pre-commit run --all-files && pytest tests/ -v'
alias pgen-build='python -m build'
alias pgen-format='black src/ tests/ && ruff check --fix src/ tests/'
EOF

# Add aliases to shell profile
SHELL_PROFILE=""
if [[ "$OS" == "macos" ]]; then
    if [[ "$SHELL" == *"zsh"* ]]; then
        SHELL_PROFILE="$HOME/.zshrc"
    else
        SHELL_PROFILE="$HOME/.bash_profile"
    fi
elif [[ "$OS" == "linux" ]]; then
    SHELL_PROFILE="$HOME/.bashrc"
fi

if [[ -n "$SHELL_PROFILE" ]]; then
    # Check if aliases are already sourced
    if ! grep -q "source.*pallet_aliases" "$SHELL_PROFILE" 2>/dev/null; then
        echo "" >> "$SHELL_PROFILE"
        echo "# PalletDataGenerator aliases" >> "$SHELL_PROFILE"
        echo "if [ -f \"$ALIASES_FILE\" ]; then" >> "$SHELL_PROFILE"
        echo "    source \"$ALIASES_FILE\"" >> "$SHELL_PROFILE"
        echo "fi" >> "$SHELL_PROFILE"
        echo -e "${GREEN}Aliases added to $SHELL_PROFILE${NC}"
    else
        echo -e "${YELLOW}Aliases already configured in $SHELL_PROFILE${NC}"
    fi
fi

# Run initial tests
echo -e "${BLUE}Running initial tests...${NC}"
if pytest tests/ -v --tb=short; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed, but setup completed.${NC}"
fi

# Final instructions
echo -e "\n${GREEN}🎉 Development environment setup complete!${NC}"
echo -e "\n${BLUE}Next steps:${NC}"
echo -e "1. Reload your shell or run: ${YELLOW}source $SHELL_PROFILE${NC}"
echo -e "2. Try the CLI: ${YELLOW}pgen info --version${NC}"
echo -e "3. Run tests: ${YELLOW}pgen-test${NC}"
echo -e "4. Check code quality: ${YELLOW}pgen-lint${NC}"
echo -e "5. Build docs: ${YELLOW}pgen-docs${NC}"

if [[ "$CONDA_AVAILABLE" == "true" ]]; then
    echo -e "\n${BLUE}Conda environment 'blender' is active.${NC}"
    echo -e "To activate it in new shells: ${YELLOW}conda activate blender${NC}"
else
    echo -e "\n${BLUE}Virtual environment created in ./venv${NC}"
    echo -e "To activate it in new shells: ${YELLOW}source venv/bin/activate${NC}"
fi

echo -e "\n${GREEN}Happy coding! 🚀${NC}"
