#!/bin/bash

# Development startup script for Momentum Lens ETF trading system
# This script handles the complete development environment setup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
LOGS_DIR="$SCRIPT_DIR/logs"
DATA_DIR="$SCRIPT_DIR/data"

# Default ports
BACKEND_PORT=${BACKEND_PORT:-8000}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
DB_PORT=${DB_PORT:-5432}
REDIS_PORT=${REDIS_PORT:-6379}

# Python version requirement
REQUIRED_PYTHON="3.11"

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Momentum Lens ETF Trading System - DEV START${NC}"
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

# Function to check if port is available
port_available() {
    ! lsof -i :"$1" >/dev/null 2>&1
}

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local max_attempts=${4:-30}
    local attempt=1

    print_status "Waiting for $service_name to be ready..."
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$host" "$port" 2>/dev/null; then
            print_status "$service_name is ready!"
            return 0
        fi
        
        echo -n "."
        sleep 1
        ((attempt++))
    done
    
    print_error "$service_name failed to start within $max_attempts seconds"
    return 1
}

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down services..."
    
    # Kill background processes
    if [ -f "$LOGS_DIR/backend.pid" ]; then
        kill "$(cat "$LOGS_DIR/backend.pid")" 2>/dev/null || true
        rm -f "$LOGS_DIR/backend.pid"
    fi
    
    if [ -f "$LOGS_DIR/frontend.pid" ]; then
        kill "$(cat "$LOGS_DIR/frontend.pid")" 2>/dev/null || true
        rm -f "$LOGS_DIR/frontend.pid"
    fi
    
    print_status "Cleanup completed"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Check system dependencies
print_status "Checking system dependencies..."

# Check Python version
if command_exists python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if [[ $(echo "$PYTHON_VERSION >= $REQUIRED_PYTHON" | bc -l) -eq 1 ]]; then
        print_status "Python $PYTHON_VERSION found"
        PYTHON_CMD="python3"
    else
        print_error "Python $REQUIRED_PYTHON or higher required, found $PYTHON_VERSION"
        exit 1
    fi
else
    print_error "Python 3 is not installed"
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node -v | cut -d'v' -f2)
    print_status "Node.js $NODE_VERSION found"
else
    print_error "Node.js is not installed"
    echo "Please install Node.js 18+ from https://nodejs.org/"
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm -v)
    print_status "npm $NPM_VERSION found"
else
    print_error "npm is not installed"
    exit 1
fi

# Check PostgreSQL
if command_exists psql; then
    PSQL_VERSION=$(psql --version | head -n1 | awk '{print $3}')
    print_status "PostgreSQL $PSQL_VERSION found"
else
    print_warning "PostgreSQL client not found. Database operations may not work."
fi

# Check Redis
if command_exists redis-cli; then
    print_status "Redis client found"
else
    print_warning "Redis client not found. Cache operations may not work."
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p "$LOGS_DIR" "$DATA_DIR" "$DATA_DIR/cache"

# Check port availability
print_status "Checking port availability..."

if ! port_available $BACKEND_PORT; then
    print_error "Backend port $BACKEND_PORT is already in use"
    lsof -i :"$BACKEND_PORT"
    exit 1
fi

if ! port_available $FRONTEND_PORT; then
    print_error "Frontend port $FRONTEND_PORT is already in use"
    lsof -i :"$FRONTEND_PORT"
    exit 1
fi

print_status "Ports are available"

# Set up Python virtual environment
print_status "Setting up Python virtual environment..."

cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    print_error "requirements.txt not found in backend directory"
    exit 1
fi

# Install TA-Lib if not already installed
print_status "Checking TA-Lib installation..."
if ! python -c "import talib" 2>/dev/null; then
    print_warning "TA-Lib not found. Please install it manually:"
    echo "  - macOS: brew install ta-lib"
    echo "  - Ubuntu: sudo apt-get install libta-dev"
    echo "  - Then: pip install TA-Lib"
fi

# Set up Node.js dependencies
print_status "Setting up Node.js dependencies..."

cd "$FRONTEND_DIR"

# Install Node dependencies
if [ -f "package.json" ]; then
    print_status "Installing Node.js dependencies..."
    npm install
else
    print_error "package.json not found in frontend directory"
    exit 1
fi

# Load environment variables
print_status "Loading environment variables..."

if [ -f "$SCRIPT_DIR/.env" ]; then
    print_status "Loading .env file..."
    set -a
    source "$SCRIPT_DIR/.env"
    set +a
else
    print_warning ".env file not found. Creating from template..."
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
        print_warning "Please edit .env file with your configuration"
    else
        print_error "No .env.example template found"
    fi
fi

# Check database connection
print_status "Checking database connection..."

if [ -n "$DATABASE_URL" ]; then
    cd "$SCRIPT_DIR"
    if $PYTHON_CMD scripts/migrate.py check; then
        print_status "Database connection successful"
    else
        print_warning "Database connection failed. Services will start but may not work properly."
    fi
else
    print_warning "DATABASE_URL not set. Database operations will not work."
fi

# Check Redis connection
print_status "Checking Redis connection..."

if [ -n "$REDIS_URL" ] && command_exists redis-cli; then
    # Extract host and port from Redis URL
    REDIS_HOST=$(echo "$REDIS_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    REDIS_PORT_EXTRACTED=$(echo "$REDIS_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    if [ -z "$REDIS_HOST" ]; then
        REDIS_HOST="localhost"
    fi
    if [ -z "$REDIS_PORT_EXTRACTED" ]; then
        REDIS_PORT_EXTRACTED="6379"
    fi
    
    if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT_EXTRACTED" ping >/dev/null 2>&1; then
        print_status "Redis connection successful"
    else
        print_warning "Redis connection failed. Starting local Redis if available..."
        if command_exists redis-server; then
            redis-server --daemonize yes --port "$REDIS_PORT_EXTRACTED"
            sleep 2
        fi
    fi
else
    print_warning "REDIS_URL not set or Redis CLI not available."
fi

# Run database migrations
print_status "Running database migrations..."
cd "$SCRIPT_DIR"
if [ -n "$DATABASE_URL" ]; then
    $PYTHON_CMD scripts/migrate.py migrate || print_warning "Migration failed or no migrations needed"
fi

# Start backend service
print_status "Starting backend service..."

cd "$BACKEND_DIR"

# Set environment variables for backend
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

# Start backend in background
nohup $PYTHON_CMD -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --reload \
    --log-level info \
    > "$LOGS_DIR/backend.log" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$LOGS_DIR/backend.pid"

print_status "Backend started with PID $BACKEND_PID"

# Wait for backend to be ready
wait_for_service "localhost" "$BACKEND_PORT" "Backend API"

# Start frontend service
print_status "Starting frontend service..."

cd "$FRONTEND_DIR"

# Set environment variables for frontend
export REACT_APP_API_URL="http://localhost:$BACKEND_PORT"
export REACT_APP_WS_URL="ws://localhost:$BACKEND_PORT"
export PORT="$FRONTEND_PORT"

# Start frontend in background
nohup npm start > "$LOGS_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LOGS_DIR/frontend.pid"

print_status "Frontend started with PID $FRONTEND_PID"

# Wait for frontend to be ready
wait_for_service "localhost" "$FRONTEND_PORT" "Frontend"

# Display access information
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Momentum Lens is now running!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${BLUE}Frontend:${NC} http://localhost:$FRONTEND_PORT"
echo -e "${BLUE}Backend API:${NC} http://localhost:$BACKEND_PORT"
echo -e "${BLUE}API Documentation:${NC} http://localhost:$BACKEND_PORT/docs"
echo -e "${BLUE}Backend Health:${NC} http://localhost:$BACKEND_PORT/api/v1/health"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend: $LOGS_DIR/backend.log"
echo -e "  Frontend: $LOGS_DIR/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"

# Follow logs
print_status "Following application logs (Ctrl+C to stop)..."
tail -f "$LOGS_DIR/backend.log" "$LOGS_DIR/frontend.log"