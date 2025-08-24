#!/bin/bash

# Graceful shutdown script for Momentum Lens ETF trading system
# This script stops all services and performs cleanup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$SCRIPT_DIR/logs"
DATA_DIR="$SCRIPT_DIR/data"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"

# Default ports
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Momentum Lens ETF Trading System - SHUTDOWN${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to gracefully stop process
stop_process() {
    local pid_file=$1
    local process_name=$2
    local timeout=${3:-10}
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            print_status "Stopping $process_name (PID: $pid)..."
            
            # Try graceful shutdown first
            kill -TERM "$pid"
            
            # Wait for process to exit
            local count=0
            while kill -0 "$pid" 2>/dev/null && [ $count -lt $timeout ]; do
                sleep 1
                ((count++))
            done
            
            # Force kill if still running
            if kill -0 "$pid" 2>/dev/null; then
                print_warning "$process_name didn't stop gracefully, force killing..."
                kill -KILL "$pid" 2>/dev/null || true
            fi
            
            print_status "$process_name stopped"
        else
            print_warning "$process_name (PID: $pid) was already stopped"
        fi
        
        rm -f "$pid_file"
    else
        print_status "No PID file found for $process_name"
    fi
}

# Function to stop processes by port
stop_by_port() {
    local port=$1
    local service_name=$2
    
    local pids=$(lsof -ti :"$port" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        print_status "Stopping $service_name processes on port $port..."
        echo "$pids" | xargs -r kill -TERM
        sleep 2
        
        # Force kill if still running
        local remaining_pids=$(lsof -ti :"$port" 2>/dev/null || true)
        if [ -n "$remaining_pids" ]; then
            print_warning "Force killing remaining $service_name processes..."
            echo "$remaining_pids" | xargs -r kill -KILL
        fi
        
        print_status "$service_name processes stopped"
    fi
}

# Parse command line arguments
FORCE="false"
CLEAN_DATA="false"
CLEAN_LOGS="false"
STOP_DOCKER="auto"

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE="true"
            shift
            ;;
        --clean-data)
            CLEAN_DATA="true"
            shift
            ;;
        --clean-logs)
            CLEAN_LOGS="true"
            shift
            ;;
        --docker-only)
            STOP_DOCKER="only"
            shift
            ;;
        --no-docker)
            STOP_DOCKER="no"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force, -f       Force kill processes immediately"
            echo "  --clean-data      Remove data directory after stopping"
            echo "  --clean-logs      Remove log files after stopping"
            echo "  --docker-only     Only stop Docker services"
            echo "  --no-docker       Don't stop Docker services"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Graceful shutdown"
            echo "  $0 --force            # Force shutdown"
            echo "  $0 --clean-logs       # Stop and clean logs"
            echo "  $0 --docker-only      # Only stop Docker"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if Docker services are running
DOCKER_RUNNING="false"
if command_exists docker && command_exists docker-compose; then
    if docker info >/dev/null 2>&1 && [ -f "$COMPOSE_FILE" ]; then
        if docker-compose -f "$COMPOSE_FILE" ps -q | grep -q .; then
            DOCKER_RUNNING="true"
        fi
    fi
fi

# Stop Docker services if requested and running
if [ "$STOP_DOCKER" = "only" ] || ([ "$STOP_DOCKER" = "auto" ] && [ "$DOCKER_RUNNING" = "true" ]); then
    print_status "Stopping Docker services..."
    
    if [ "$FORCE" = "true" ]; then
        docker-compose -f "$COMPOSE_FILE" kill
        docker-compose -f "$COMPOSE_FILE" down --remove-orphans
    else
        docker-compose -f "$COMPOSE_FILE" down --timeout 30
    fi
    
    print_status "Docker services stopped"
    
    if [ "$STOP_DOCKER" = "only" ]; then
        echo -e "${GREEN}Docker shutdown completed${NC}"
        exit 0
    fi
fi

# Skip local process stopping if only Docker was requested
if [ "$STOP_DOCKER" = "only" ]; then
    exit 0
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Stop development services
print_status "Stopping local development services..."

# Stop backend service
if [ "$FORCE" = "true" ]; then
    stop_by_port "$BACKEND_PORT" "Backend"
else
    stop_process "$LOGS_DIR/backend.pid" "Backend" 15
fi

# Stop frontend service
if [ "$FORCE" = "true" ]; then
    stop_by_port "$FRONTEND_PORT" "Frontend"
else
    stop_process "$LOGS_DIR/frontend.pid" "Frontend" 10
fi

# Stop any remaining Node.js processes related to the project
if [ "$FORCE" = "true" ]; then
    print_status "Stopping remaining Node.js processes..."
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "npm start" 2>/dev/null || true
fi

# Stop any remaining Python processes related to the project
if [ "$FORCE" = "true" ]; then
    print_status "Stopping remaining Python processes..."
    pkill -f "uvicorn.*main:app" 2>/dev/null || true
    pkill -f "python.*main.py" 2>/dev/null || true
fi

# Stop local Redis if started by the system
if command_exists redis-cli; then
    print_status "Checking for local Redis..."
    if redis-cli ping >/dev/null 2>&1; then
        print_status "Local Redis is running, leaving it as is..."
    fi
fi

# Clean up temporary files
print_status "Cleaning up temporary files..."

# Remove PID files
rm -f "$LOGS_DIR"/*.pid

# Remove temporary cache files
rm -rf "$DATA_DIR"/cache/*.tmp 2>/dev/null || true

# Clean logs if requested
if [ "$CLEAN_LOGS" = "true" ]; then
    print_status "Cleaning log files..."
    rm -rf "$LOGS_DIR"/*.log
    rm -rf "$LOGS_DIR"/nginx
    print_status "Log files cleaned"
fi

# Clean data if requested
if [ "$CLEAN_DATA" = "true" ]; then
    print_warning "Cleaning data directory..."
    read -p "Are you sure you want to delete all data? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$DATA_DIR"
        mkdir -p "$DATA_DIR"
        print_status "Data directory cleaned"
    else
        print_status "Data cleaning cancelled"
    fi
fi

# Final verification
print_status "Verifying shutdown..."

# Check if any processes are still running on our ports
BACKEND_PROCESSES=$(lsof -ti :"$BACKEND_PORT" 2>/dev/null || true)
FRONTEND_PROCESSES=$(lsof -ti :"$FRONTEND_PORT" 2>/dev/null || true)

if [ -n "$BACKEND_PROCESSES" ]; then
    print_warning "Backend processes still running on port $BACKEND_PORT:"
    lsof -i :"$BACKEND_PORT"
fi

if [ -n "$FRONTEND_PROCESSES" ]; then
    print_warning "Frontend processes still running on port $FRONTEND_PORT:"
    lsof -i :"$FRONTEND_PORT"
fi

# Save system state if needed
if [ -d "$DATA_DIR" ]; then
    print_status "Saving system state..."
    echo "$(date): System stopped" >> "$DATA_DIR/shutdown.log"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Momentum Lens shutdown completed${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if [ -n "$BACKEND_PROCESSES" ] || [ -n "$FRONTEND_PROCESSES" ]; then
    echo -e "${YELLOW}Warning: Some processes may still be running${NC}"
    echo -e "${YELLOW}Use --force option for immediate termination${NC}"
    exit 1
else
    echo -e "${GREEN}All services stopped successfully${NC}"
fi