#!/bin/bash

# Docker startup script for Momentum Lens ETF trading system
# This script handles the complete Docker-based deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="$SCRIPT_DIR/.env"

# Default environment
BUILD_ENV=${BUILD_ENV:-production}
COMPOSE_PROFILES=${COMPOSE_PROFILES:-""}

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Momentum Lens ETF Trading System - DOCKER${NC}"
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

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down Docker services..."
    docker-compose -f "$COMPOSE_FILE" down
    print_status "Docker cleanup completed"
}

# Set up signal handlers
trap cleanup EXIT INT TERM

# Parse command line arguments
COMMAND="up"
FOLLOW_LOGS="true"
REBUILD="false"
DETACHED="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            REBUILD="true"
            shift
            ;;
        --detach|-d)
            DETACHED="true"
            FOLLOW_LOGS="false"
            shift
            ;;
        --no-logs)
            FOLLOW_LOGS="false"
            shift
            ;;
        --production)
            BUILD_ENV="production"
            COMPOSE_PROFILES="production"
            shift
            ;;
        --development)
            BUILD_ENV="development"
            shift
            ;;
        down|stop|restart|logs|ps|exec)
            COMMAND="$1"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [COMMAND]"
            echo ""
            echo "Commands:"
            echo "  up         Start all services (default)"
            echo "  down       Stop all services"
            echo "  stop       Stop all services (alias for down)"
            echo "  restart    Restart all services"
            echo "  logs       Show logs"
            echo "  ps         Show running containers"
            echo ""
            echo "Options:"
            echo "  --build            Force rebuild of images"
            echo "  --detach, -d       Run in detached mode"
            echo "  --no-logs          Don't follow logs after startup"
            echo "  --production       Use production profile with SSL proxy"
            echo "  --development      Use development environment"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                           # Start in development mode"
            echo "  $0 --production --detach     # Start in production mode"
            echo "  $0 --build                   # Rebuild and start"
            echo "  $0 down                      # Stop all services"
            echo "  $0 logs                      # Show logs"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check Docker dependencies
print_status "Checking Docker dependencies..."

if ! command_exists docker; then
    print_error "Docker is not installed"
    echo "Please install Docker from https://docker.com/"
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is not installed"
    echo "Please install Docker Compose"
    exit 1
fi

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    print_error "Docker is not running"
    echo "Please start Docker"
    exit 1
fi

print_status "Docker is available and running"

# Check compose file
if [ ! -f "$COMPOSE_FILE" ]; then
    print_error "Docker compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Load and validate environment
print_status "Loading environment configuration..."

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$SCRIPT_DIR/.env.example" ]; then
        print_warning "No .env file found. Creating from template..."
        cp "$SCRIPT_DIR/.env.example" "$ENV_FILE"
        print_warning "Please edit .env file with your configuration before running again"
        exit 1
    else
        print_error "No .env file or .env.example template found"
        exit 1
    fi
fi

# Export environment variables
export BUILD_ENV
if [ -n "$COMPOSE_PROFILES" ]; then
    export COMPOSE_PROFILES
fi

print_status "Using build environment: $BUILD_ENV"
if [ -n "$COMPOSE_PROFILES" ]; then
    print_status "Using profiles: $COMPOSE_PROFILES"
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p "$SCRIPT_DIR/logs" "$SCRIPT_DIR/data" "$SCRIPT_DIR/nginx/ssl"

# Handle different commands
case $COMMAND in
    "up")
        # Build images if requested or if they don't exist
        if [ "$REBUILD" = "true" ]; then
            print_status "Building Docker images..."
            docker-compose -f "$COMPOSE_FILE" build --no-cache
        else
            print_status "Building Docker images (if needed)..."
            docker-compose -f "$COMPOSE_FILE" build
        fi

        # Start services
        print_status "Starting Docker services..."
        
        if [ "$DETACHED" = "true" ]; then
            docker-compose -f "$COMPOSE_FILE" up -d
        else
            # Start in background first to allow health checks
            docker-compose -f "$COMPOSE_FILE" up -d
            
            # Wait for services to be healthy
            print_status "Waiting for services to be healthy..."
            
            # Function to wait for container health
            wait_for_healthy() {
                local service=$1
                local max_attempts=${2:-60}
                local attempt=1
                
                print_status "Waiting for $service to be healthy..."
                
                while [ $attempt -le $max_attempts ]; do
                    local health_status=$(docker-compose -f "$COMPOSE_FILE" ps -q "$service" | xargs -I {} docker inspect --format='{{.State.Health.Status}}' {} 2>/dev/null || echo "unhealthy")
                    
                    if [ "$health_status" = "healthy" ]; then
                        print_status "$service is healthy!"
                        return 0
                    elif [ "$health_status" = "unhealthy" ]; then
                        print_warning "$service is unhealthy (attempt $attempt/$max_attempts)"
                    else
                        print_status "$service is starting... (attempt $attempt/$max_attempts)"
                    fi
                    
                    sleep 2
                    ((attempt++))
                done
                
                print_error "$service failed to become healthy within $((max_attempts * 2)) seconds"
                return 1
            }
            
            # Wait for core services
            wait_for_healthy "postgres" 30
            wait_for_healthy "redis" 15
            wait_for_healthy "backend" 30
            wait_for_healthy "frontend" 20
            
            # Show service status
            print_status "Service status:"
            docker-compose -f "$COMPOSE_FILE" ps
            
            # Get service URLs
            print_status "Getting service information..."
            
            FRONTEND_PORT=$(docker-compose -f "$COMPOSE_FILE" port frontend 80 2>/dev/null | cut -d: -f2 || echo "3000")
            BACKEND_PORT=$(docker-compose -f "$COMPOSE_FILE" port backend 8000 2>/dev/null | cut -d: -f2 || echo "8000")
            
            # Display access information
            echo ""
            echo -e "${GREEN}================================================${NC}"
            echo -e "${GREEN}  Momentum Lens is now running in Docker!${NC}"
            echo -e "${GREEN}================================================${NC}"
            echo ""
            echo -e "${BLUE}Frontend:${NC} http://localhost:$FRONTEND_PORT"
            echo -e "${BLUE}Backend API:${NC} http://localhost:$BACKEND_PORT"
            echo -e "${BLUE}API Documentation:${NC} http://localhost:$BACKEND_PORT/docs"
            echo -e "${BLUE}Health Check:${NC} http://localhost:$BACKEND_PORT/api/v1/health"
            
            if [ "$BUILD_ENV" = "production" ] && [[ "$COMPOSE_PROFILES" == *"production"* ]]; then
                NGINX_PORT=$(docker-compose -f "$COMPOSE_FILE" port nginx 80 2>/dev/null | cut -d: -f2 || echo "80")
                NGINX_HTTPS_PORT=$(docker-compose -f "$COMPOSE_FILE" port nginx 443 2>/dev/null | cut -d: -f2 || echo "443")
                echo -e "${BLUE}Production Proxy:${NC} http://localhost:$NGINX_PORT"
                echo -e "${BLUE}Production HTTPS:${NC} https://localhost:$NGINX_HTTPS_PORT"
            fi
            
            echo ""
            echo -e "${BLUE}Docker Commands:${NC}"
            echo -e "  View logs: docker-compose -f $COMPOSE_FILE logs -f"
            echo -e "  Stop: docker-compose -f $COMPOSE_FILE down"
            echo -e "  Status: docker-compose -f $COMPOSE_FILE ps"
            echo ""
            
            if [ "$FOLLOW_LOGS" = "true" ]; then
                echo -e "${YELLOW}Following logs (Ctrl+C to stop)...${NC}"
                echo ""
                docker-compose -f "$COMPOSE_FILE" logs -f
            else
                echo -e "${YELLOW}Services are running in detached mode${NC}"
                echo -e "${YELLOW}Use 'docker-compose -f $COMPOSE_FILE logs -f' to view logs${NC}"
            fi
        fi
        ;;
        
    "down"|"stop")
        print_status "Stopping Docker services..."
        docker-compose -f "$COMPOSE_FILE" down
        print_status "All services stopped"
        ;;
        
    "restart")
        print_status "Restarting Docker services..."
        docker-compose -f "$COMPOSE_FILE" restart
        print_status "All services restarted"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
        
    "logs")
        print_status "Showing Docker logs..."
        docker-compose -f "$COMPOSE_FILE" logs -f
        ;;
        
    "ps")
        print_status "Docker service status:"
        docker-compose -f "$COMPOSE_FILE" ps
        ;;
        
    *)
        print_error "Unknown command: $COMMAND"
        echo "Use --help for usage information"
        exit 1
        ;;
esac