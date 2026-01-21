#!/bin/bash

# Script to automate Oracle Database 19c setup on ARM MacOS (M1, M2, M3)
# Based on: https://www.simonpcouch.com/blog/2024-03-14-oracle/

set -e  # Exit on error
set +x  # Enable debug mode

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ORACLE_VERSION="19.3.0"
ORACLE_ZIP_NAME="LINUX.ARM64_1919000_db_home.zip"
DOCKER_IMAGE_NAME="oracle/database:19.3.0-ee"
DOCKERFILE_DIR="docker-images/OracleDatabase/SingleInstance/dockerfiles/19.3.0"

# Function to print error and exit
error_exit() {
    echo -e "${RED}ERROR: $1${NC}" >&2
    exit 1
}

# Function to print warning
warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

# Function to print success
success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Determine Docker Compose Command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    DOCKER_COMPOSE_CMD="docker compose"
fi

# Detect project directory and change context if needed
PROJECT_DIR="containerise-oracle-db"
if [ -d "$PROJECT_DIR" ] && [ ! -f "docker-compose.yml" ]; then
    echo "Detected project folder '$PROJECT_DIR'. Changing directory..."
    cd "$PROJECT_DIR"
fi

# Check for .env or databases.conf
if [ ! -f ".env" ] && [ -f "databases.conf" ]; then
    echo "Renaming databases.conf to .env..."
    mv databases.conf .env
fi

do_setup() {
    local ARG=$1
    
    echo -e "${GREEN}Oracle Database 19c on ARM MacOS Setup Script${NC}"
    echo "=============================================="
    echo ""

    # Check if running on macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        error_exit "This script is designed for macOS only."
    fi

    # Check if running on ARM architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "arm64" ]]; then
        error_exit "This script requires an ARM-based Mac (M1, M2, M3). Detected architecture: $ARCH"
    fi

    success "Running on ARM-based macOS"

    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed. Please install Docker Desktop for Mac."
    fi

    if ! docker info &> /dev/null; then
        error_exit "Docker is not running. Please start Docker Desktop."
    fi

    success "Docker is installed and running"

    # Argument handling for cleaning images
    if [[ "$ARG" == "--clean" ]]; then
        echo ""
        warning "Clean flag detected. Removing existing image and containers..."
        
        # Stop running containers if they exist
        if [ -f "docker-compose.yml" ]; then
            $DOCKER_COMPOSE_CMD down || true
        fi
        
        # Remove image if it exists
        if docker image inspect $DOCKER_IMAGE_NAME >/dev/null 2>&1; then
            docker rmi -f $DOCKER_IMAGE_NAME || warning "Failed to remove image $DOCKER_IMAGE_NAME"
            success "Removed image: $DOCKER_IMAGE_NAME"
        else
            echo "Image $DOCKER_IMAGE_NAME not found, skipping removal."
        fi
        echo ""
    fi

    # Check if git is installed
    if ! command -v git &> /dev/null; then
        error_exit "Git is not installed. Please install Git."
    fi

    # Clone oracle/docker-images repository if it doesn't exist
    if [ ! -d "docker-images" ]; then
        echo ""
        echo "Cloning oracle/docker-images repository..."
        git clone https://github.com/oracle/docker-images.git || error_exit "Failed to clone repository"
        success "Repository cloned successfully"
    else
        success "Repository already exists"
    fi

    # Navigate to the dockerfiles directory (just to check files, we will cd later)
    if [ ! -d "$DOCKERFILE_DIR" ]; then
        error_exit "Directory $DOCKERFILE_DIR not found in cloned repository"
    fi

    # Check if Oracle Database zip file exists
    echo ""
    echo "Checking for Oracle Database installation file..."
    if [ ! -f "$ORACLE_ZIP_NAME" ] && [ ! -f "$DOCKERFILE_DIR/$ORACLE_ZIP_NAME" ]; then
        warning "Oracle Database installation file not found!"
        echo ""
        echo "Please download Oracle Database 19c (19.19) for LINUX ARM (aarch64) from:"
        echo "https://www.oracle.com/database/technologies/oracle19c-linux-arm64-downloads.html"
        echo ""
        echo "The file should be named: $ORACLE_ZIP_NAME"
        echo "Place it in the current directory or in: $DOCKERFILE_DIR"
        echo ""
        read -p "Press Enter once you've downloaded and placed the file, or Ctrl+C to exit..."
        
        # Check again
        if [ ! -f "$ORACLE_ZIP_NAME" ] && [ ! -f "$DOCKERFILE_DIR/$ORACLE_ZIP_NAME" ]; then
            error_exit "Oracle Database installation file still not found!"
        fi
    fi

    # Copy the zip file to the correct location if it's in current directory
    if [ -f "$ORACLE_ZIP_NAME" ] && [ ! -f "$DOCKERFILE_DIR/$ORACLE_ZIP_NAME" ]; then
        echo "Copying $ORACLE_ZIP_NAME to $DOCKERFILE_DIR..."
        cp "$ORACLE_ZIP_NAME" "$DOCKERFILE_DIR/" || error_exit "Failed to copy installation file"
        success "Installation file copied"
    else
        success "Installation file found in correct location"
    fi

    # Build the Docker image
    echo ""

    # Check if image already exists
    if docker image inspect $DOCKER_IMAGE_NAME >/dev/null 2>&1; then
        success "Docker image $DOCKER_IMAGE_NAME already exists. Skipping build."
        echo "To force rebuild, run: ./setup-oracle-database.sh --clean"
    else
        echo "Building Docker image (this may take 10-15 minutes)..."
        # We need to change directory to build
        cd docker-images/OracleDatabase/SingleInstance/dockerfiles/

        # Patch checkSpace.sh to lower space requirement
        CHECK_SPACE_FILE="19.3.0/checkSpace.sh"
        if [ -f "$CHECK_SPACE_FILE" ]; then
            echo "Patching $CHECK_SPACE_FILE to reduce space requirement..."
            # Reduce to 12GB
            perl -pi -e 's/REQUIRED_SPACE_GB=18/REQUIRED_SPACE_GB=12/g' "$CHECK_SPACE_FILE"
            success "Space check patched (18GB -> 12GB)"
        fi

        ./buildContainerImage.sh -v $ORACLE_VERSION -e || error_exit "Failed to build Docker image"

        success "Docker image built successfully: $DOCKER_IMAGE_NAME"
        
        # Go back to the root directory
        cd ../../../../
    fi

    # Run the Docker containers using Docker Compose
    echo ""
    echo "Starting Oracle Database containers using Docker Compose..."

    if [ -f "docker-compose.yml" ] && [ -f ".env" ]; then
        success "Configuration files found."
        
        # We force recreate the monitoring service to ensure it picks up new .env values
        $DOCKER_COMPOSE_CMD up -d --build monitoring
        $DOCKER_COMPOSE_CMD up -d || error_exit "Failed to start containers with docker-compose"
    else
        error_exit "docker-compose.yml or .env missing in the root directory!"
    fi

    success "Containers started successfully"

    echo ""
    echo "=============================================="
    echo -e "${GREEN}Setup Complete!${NC}"
    echo "=============================================="
    echo ""
    echo "The databases are now initializing. This may take a few minutes."
    echo ""
    echo "To check the logs:"
    echo "  $DOCKER_COMPOSE_CMD logs -f"
    echo ""
    echo "To stop the containers:"
    echo "  $DOCKER_COMPOSE_CMD stop"
    echo ""
    echo "Configuration is in .env"
    echo ""
    echo -e "📊 Monitoring Dashboard: ${GREEN}http://localhost:8501${NC}"
    echo ""
    warning "Note: ODBC connections are not supported on macOS aarch64 at this time."
    echo ""
}

# --- Main Script Logic ---

# Debug
echo "DEBUG: Argument received: '$1'"
case "$1" in
    start)
        echo "Starting containers..."
        # Use 'start' instead of 'up -d' to avoid recreation/conflict issues on existing containers
        $DOCKER_COMPOSE_CMD start || echo "Some containers might not exist. Run '$0 setup' if you need to create them."
        success "Containers started."
        echo -e "📊 Monitoring Dashboard: ${GREEN}http://localhost:8501${NC}"
        ;;
    stop)
        echo "Stopping containers..."
        $DOCKER_COMPOSE_CMD stop
        success "Containers stopped."
        ;;
    restart)
        echo "Restarting containers..."
        $DOCKER_COMPOSE_CMD restart
        success "Containers restarted."
        echo -e "📊 Monitoring Dashboard: ${GREEN}http://localhost:8501${NC}"
        ;;
    down)
        echo "Removing containers..."
        $DOCKER_COMPOSE_CMD down
        success "Containers removed."
        ;;
    status)
        $DOCKER_COMPOSE_CMD ps
        ;;
    logs)
        $DOCKER_COMPOSE_CMD logs -f
        ;;
    setup|install)
        # Explicit setup command
        do_setup "$2"
        ;;
    clean|--clean)
        # Clean is also an explicit setup command
        do_setup "--clean"
        ;;
    *)
        echo -e "${GREEN}Oracle Database Manager (Wrapper Script)${NC}"
        echo "Usage: $0 {start|stop|restart|down|status|logs|setup|clean}"
        echo ""
        echo "Commands:"
        echo "  setup   : Build image and create containers (run first)"
        echo "  start   : Start existing containers"
        echo "  stop    : Stop running containers"
        echo "  restart : Restart containers"
        echo "  status  : Show container status"
        echo "  logs    : Follow container logs"
        echo "  down    : Remove containers"
        echo "  clean   : Remove images and containers (reset)"
        echo ""
        echo "Note: To rebuild cleanly, run: $0 setup --clean"
        exit 1
        ;;
esac
