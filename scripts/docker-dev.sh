#!/bin/bash
# Docker development helper script
# Usage: ./scripts/docker-dev.sh [command]

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🐳 PalletDataGenerator Docker Development Helper${NC}"

function show_help() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  dev         Start development container"
    echo "  blender     Start Blender development container"
    echo "  prod        Start production container"
    echo "  test        Run tests in container"
    echo "  docs        Build and serve documentation"
    echo "  build       Build all Docker images"
    echo "  clean       Clean up containers and images"
    echo "  shell       Open shell in development container"
    echo "  logs        Show container logs"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev                 # Start development environment"
    echo "  $0 shell               # Open bash shell in dev container"
    echo "  $0 test                # Run all tests"
    echo "  $0 docs                # Build and serve docs on port 8080"
}

function build_images() {
    echo -e "${BLUE}Building Docker images...${NC}"
    docker-compose build
    echo -e "${GREEN}✅ Images built successfully${NC}"
}

function start_dev() {
    echo -e "${BLUE}Starting development container...${NC}"
    docker-compose up -d pallet-dev
    echo -e "${GREEN}✅ Development container started${NC}"
    echo -e "${YELLOW}Use '$0 shell' to open a shell${NC}"
}

function start_blender() {
    echo -e "${BLUE}Starting Blender development container...${NC}"
    # Check if X11 forwarding is available on macOS/Linux
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "${YELLOW}For GUI apps on macOS, install XQuartz and run: xhost +localhost${NC}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xhost +local:docker 2>/dev/null || echo -e "${YELLOW}Note: X11 forwarding may not work without 'xhost +local:docker'${NC}"
    fi

    docker-compose up -d pallet-blender
    echo -e "${GREEN}✅ Blender development container started${NC}"
    echo -e "${YELLOW}Use '$0 shell pallet-blender' to open a shell${NC}"
}

function start_prod() {
    echo -e "${BLUE}Starting production container...${NC}"
    docker-compose up pallet-prod
}

function run_tests() {
    echo -e "${BLUE}Running tests in container...${NC}"
    docker-compose run --rm pallet-test
}

function build_docs() {
    echo -e "${BLUE}Building and serving documentation...${NC}"
    docker-compose up pallet-docs
}

function open_shell() {
    local container=${1:-pallet-dev}
    echo -e "${BLUE}Opening shell in $container...${NC}"

    # Check if container is running
    if ! docker-compose ps | grep -q "$container.*Up"; then
        echo -e "${YELLOW}Container not running, starting it first...${NC}"
        docker-compose up -d $container
        sleep 2
    fi

    docker-compose exec $container bash
}

function show_logs() {
    local container=${1:-pallet-dev}
    echo -e "${BLUE}Showing logs for $container...${NC}"
    docker-compose logs -f $container
}

function clean_up() {
    echo -e "${BLUE}Cleaning up containers and images...${NC}"
    docker-compose down -v
    docker-compose down --rmi all --remove-orphans
    docker system prune -f
    echo -e "${GREEN}✅ Cleanup completed${NC}"
}

# Main command handling
case "${1:-help}" in
    "dev")
        start_dev
        ;;
    "blender")
        start_blender
        ;;
    "prod")
        start_prod
        ;;
    "test")
        run_tests
        ;;
    "docs")
        build_docs
        ;;
    "build")
        build_images
        ;;
    "shell")
        open_shell $2
        ;;
    "logs")
        show_logs $2
        ;;
    "clean")
        clean_up
        ;;
    "help"|*)
        show_help
        ;;
esac
