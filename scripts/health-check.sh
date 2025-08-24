#!/bin/bash

# Comprehensive health check script for Momentum Lens ETF trading system
# This script verifies all system components are running correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load environment variables if available
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Default values
BACKEND_URL=${BACKEND_URL:-"http://localhost:8000"}
FRONTEND_URL=${FRONTEND_URL:-"http://localhost:3000"}
DATABASE_URL=${DATABASE_URL:-"postgresql://momentum_user:momentum_password@localhost:5432/momentum_lens"}
REDIS_URL=${REDIS_URL:-"redis://localhost:6379"}

# Health check results
HEALTH_RESULTS=()
EXIT_CODE=0

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Momentum Lens Health Check${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Function to print status messages
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Function to add result
add_result() {
    local component=$1
    local status=$2
    local message=$3
    
    HEALTH_RESULTS+=("$component|$status|$message")
    
    if [ "$status" = "FAIL" ]; then
        EXIT_CODE=1
    fi
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local url=$1
    local name=$2
    local expected_status=${3:-200}
    local timeout=${4:-10}
    
    print_info "Testing $name: $url"
    
    if response=$(curl -s -w "%{http_code}" --max-time "$timeout" "$url" 2>/dev/null); then
        status_code="${response: -3}"
        body="${response%???}"
        
        if [ "$status_code" -eq "$expected_status" ]; then
            print_status "$name is responding (HTTP $status_code)"
            add_result "$name" "PASS" "HTTP $status_code"
            return 0
        else
            print_error "$name returned HTTP $status_code (expected $expected_status)"
            add_result "$name" "FAIL" "HTTP $status_code"
            return 1
        fi
    else
        print_error "$name is not responding"
        add_result "$name" "FAIL" "No response"
        return 1
    fi
}

# Function to test JSON API endpoint
test_json_api() {
    local url=$1
    local name=$2
    local expected_field=$3
    local timeout=${4:-10}
    
    print_info "Testing $name JSON API: $url"
    
    if response=$(curl -s --max-time "$timeout" -H "Content-Type: application/json" "$url" 2>/dev/null); then
        if echo "$response" | jq -e ".$expected_field" >/dev/null 2>&1; then
            print_status "$name JSON API is working"
            add_result "$name API" "PASS" "JSON response valid"
            return 0
        else
            print_error "$name JSON API response is invalid"
            add_result "$name API" "FAIL" "Invalid JSON response"
            return 1
        fi
    else
        print_error "$name JSON API is not responding"
        add_result "$name API" "FAIL" "No JSON response"
        return 1
    fi
}

# Function to test WebSocket connection
test_websocket() {
    local url=$1
    local name=$2
    local timeout=${3:-10}
    
    print_info "Testing $name WebSocket: $url"
    
    if command_exists wscat; then
        if timeout "$timeout" wscat -c "$url" -w 5 < /dev/null >/dev/null 2>&1; then
            print_status "$name WebSocket is working"
            add_result "$name WebSocket" "PASS" "Connection successful"
            return 0
        else
            print_error "$name WebSocket connection failed"
            add_result "$name WebSocket" "FAIL" "Connection failed"
            return 1
        fi
    else
        print_warning "$name WebSocket test skipped (wscat not available)"
        add_result "$name WebSocket" "SKIP" "wscat not available"
        return 0
    fi
}

# Function to test database connection
test_database() {
    print_info "Testing database connection..."
    
    if command_exists psql; then
        if echo "SELECT 1;" | psql "$DATABASE_URL" >/dev/null 2>&1; then
            print_status "Database connection is working"
            add_result "Database" "PASS" "Connection successful"
            
            # Test database schema
            if schema_count=$(echo "SELECT count(*) FROM information_schema.schemata WHERE schema_name IN ('market_data', 'trading', 'analytics');" | psql "$DATABASE_URL" -t 2>/dev/null); then
                schema_count=$(echo "$schema_count" | tr -d ' ')
                if [ "$schema_count" -eq 3 ]; then
                    print_status "Database schema is complete"
                    add_result "Database Schema" "PASS" "All schemas present"
                else
                    print_warning "Database schema incomplete ($schema_count/3 schemas)"
                    add_result "Database Schema" "WARN" "$schema_count/3 schemas"
                fi
            fi
            
            return 0
        else
            print_error "Database connection failed"
            add_result "Database" "FAIL" "Connection failed"
            return 1
        fi
    else
        print_warning "Database test skipped (psql not available)"
        add_result "Database" "SKIP" "psql not available"
        return 0
    fi
}

# Function to test Redis connection
test_redis() {
    print_info "Testing Redis connection..."
    
    if command_exists redis-cli; then
        # Extract Redis connection details from URL
        redis_host="localhost"
        redis_port="6379"
        
        if [[ "$REDIS_URL" =~ redis://([^:]*):([^@]*@)?([^:]+):([0-9]+) ]]; then
            redis_host="${BASH_REMATCH[3]}"
            redis_port="${BASH_REMATCH[4]}"
        fi
        
        if redis-cli -h "$redis_host" -p "$redis_port" ping >/dev/null 2>&1; then
            print_status "Redis connection is working"
            add_result "Redis" "PASS" "Connection successful"
            return 0
        else
            print_error "Redis connection failed"
            add_result "Redis" "FAIL" "Connection failed"
            return 1
        fi
    else
        print_warning "Redis test skipped (redis-cli not available)"
        add_result "Redis" "SKIP" "redis-cli not available"
        return 0
    fi
}

# Function to check Docker services
check_docker_services() {
    print_info "Checking Docker services..."
    
    if command_exists docker && command_exists docker-compose; then
        compose_file="$PROJECT_DIR/docker-compose.yml"
        
        if [ -f "$compose_file" ]; then
            cd "$PROJECT_DIR"
            
            # Get running containers
            running_containers=$(docker-compose ps -q 2>/dev/null | wc -l | tr -d ' ')
            
            if [ "$running_containers" -gt 0 ]; then
                print_status "$running_containers Docker containers are running"
                add_result "Docker Services" "PASS" "$running_containers containers running"
                
                # Check individual container health
                docker-compose ps --format "table {{.Name}}\t{{.State}}\t{{.Status}}" | while IFS=$'\t' read -r name state status; do
                    if [ "$name" != "Name" ]; then
                        if [[ "$state" == *"Up"* ]]; then
                            print_status "Container $name is healthy"
                        else
                            print_error "Container $name is unhealthy ($state)"
                        fi
                    fi
                done
                
                return 0
            else
                print_warning "No Docker containers are running"
                add_result "Docker Services" "WARN" "No containers running"
                return 1
            fi
        else
            print_warning "docker-compose.yml not found"
            add_result "Docker Services" "SKIP" "No compose file"
            return 0
        fi
    else
        print_info "Docker not available, checking local services..."
        add_result "Docker Services" "SKIP" "Docker not available"
        return 0
    fi
}

# Function to check system resources
check_system_resources() {
    print_info "Checking system resources..."
    
    # Check CPU usage
    if command_exists top; then
        cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        if (( $(echo "$cpu_usage > 80" | bc -l) )); then
            print_warning "High CPU usage: ${cpu_usage}%"
            add_result "CPU Usage" "WARN" "${cpu_usage}%"
        else
            print_status "CPU usage is normal: ${cpu_usage}%"
            add_result "CPU Usage" "PASS" "${cpu_usage}%"
        fi
    fi
    
    # Check memory usage
    if command_exists free; then
        memory_info=$(free | grep Mem)
        total=$(echo "$memory_info" | awk '{print $2}')
        used=$(echo "$memory_info" | awk '{print $3}')
        memory_usage=$(echo "scale=1; $used * 100 / $total" | bc -l)
        
        if (( $(echo "$memory_usage > 85" | bc -l) )); then
            print_warning "High memory usage: ${memory_usage}%"
            add_result "Memory Usage" "WARN" "${memory_usage}%"
        else
            print_status "Memory usage is normal: ${memory_usage}%"
            add_result "Memory Usage" "PASS" "${memory_usage}%"
        fi
    fi
    
    # Check disk space
    if command_exists df; then
        disk_usage=$(df "$PROJECT_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
        if [ "$disk_usage" -gt 85 ]; then
            print_warning "High disk usage: ${disk_usage}%"
            add_result "Disk Usage" "WARN" "${disk_usage}%"
        else
            print_status "Disk usage is normal: ${disk_usage}%"
            add_result "Disk Usage" "PASS" "${disk_usage}%"
        fi
    fi
}

# Function to check log files
check_logs() {
    print_info "Checking log files..."
    
    logs_dir="$PROJECT_DIR/logs"
    
    if [ -d "$logs_dir" ]; then
        log_files=$(find "$logs_dir" -name "*.log" -type f | wc -l)
        if [ "$log_files" -gt 0 ]; then
            print_status "$log_files log files found"
            add_result "Log Files" "PASS" "$log_files files"
            
            # Check for recent errors
            recent_errors=$(find "$logs_dir" -name "*.log" -type f -mtime -1 -exec grep -l -i "error\|critical\|fatal" {} \; 2>/dev/null | wc -l)
            if [ "$recent_errors" -gt 0 ]; then
                print_warning "$recent_errors log files contain recent errors"
                add_result "Log Errors" "WARN" "$recent_errors files with errors"
            else
                print_status "No recent errors in log files"
                add_result "Log Errors" "PASS" "No recent errors"
            fi
        else
            print_warning "No log files found"
            add_result "Log Files" "WARN" "No log files"
        fi
    else
        print_warning "Logs directory not found"
        add_result "Log Files" "WARN" "Logs directory missing"
    fi
}

# Main health check execution
echo "Starting comprehensive health check..."
echo ""

# Check Docker services first
check_docker_services

# Core service health checks
echo -e "\n${BLUE}Testing Core Services...${NC}"
test_http_endpoint "$BACKEND_URL" "Backend"
test_http_endpoint "$FRONTEND_URL" "Frontend"

# API specific tests
echo -e "\n${BLUE}Testing API Endpoints...${NC}"
test_json_api "$BACKEND_URL/api/v1/health" "Backend Health" "status"
test_http_endpoint "$BACKEND_URL/docs" "API Documentation"

# WebSocket tests
echo -e "\n${BLUE}Testing WebSocket Connections...${NC}"
ws_url=$(echo "$BACKEND_URL" | sed 's/http/ws/')
test_websocket "$ws_url/ws/prices" "Price Stream"
test_websocket "$ws_url/ws/signals" "Signal Stream"

# Database and cache tests
echo -e "\n${BLUE}Testing Data Services...${NC}"
test_database
test_redis

# System resource checks
echo -e "\n${BLUE}Checking System Resources...${NC}"
check_system_resources

# Log file checks
echo -e "\n${BLUE}Checking Log Files...${NC}"
check_logs

# Summary report
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  Health Check Summary${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

pass_count=0
warn_count=0
fail_count=0
skip_count=0

for result in "${HEALTH_RESULTS[@]}"; do
    IFS='|' read -r component status message <<< "$result"
    
    case "$status" in
        "PASS")
            echo -e "${GREEN}✓${NC} $component: $message"
            ((pass_count++))
            ;;
        "WARN")
            echo -e "${YELLOW}⚠${NC} $component: $message"
            ((warn_count++))
            ;;
        "FAIL")
            echo -e "${RED}✗${NC} $component: $message"
            ((fail_count++))
            ;;
        "SKIP")
            echo -e "${BLUE}○${NC} $component: $message"
            ((skip_count++))
            ;;
    esac
done

echo ""
echo -e "Results: ${GREEN}$pass_count passed${NC}, ${YELLOW}$warn_count warnings${NC}, ${RED}$fail_count failed${NC}, ${BLUE}$skip_count skipped${NC}"

# Final status
if [ $fail_count -eq 0 ] && [ $warn_count -eq 0 ]; then
    echo -e "${GREEN}✅ All health checks passed!${NC}"
    exit 0
elif [ $fail_count -eq 0 ]; then
    echo -e "${YELLOW}⚠️ Health checks passed with warnings${NC}"
    exit 0
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi