# Momentum Lens Deployment Guide

This guide provides comprehensive instructions for deploying the Momentum Lens ETF trading system in development, staging, and production environments.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+) or macOS
- **Docker**: Version 20.10+ with Docker Compose v2
- **Python**: Version 3.11+
- **Node.js**: Version 18+
- **PostgreSQL**: Version 14+ (with TimescaleDB extension)
- **Redis**: Version 6+

### Hardware Requirements

**Development:**
- 4GB RAM minimum, 8GB recommended
- 20GB free disk space
- 2 CPU cores

**Production:**
- 16GB RAM minimum, 32GB recommended
- 100GB free disk space (SSD preferred)
- 4+ CPU cores
- Load balancer (for high availability)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/momentum-lens.git
cd momentum-lens

# Copy environment template
cp .env.example .env

# Edit environment variables
nano .env
```

### 2. Development Deployment

```bash
# Start all services locally
./start.sh

# Or use Docker for consistent environment
./start-docker.sh
```

### 3. Production Deployment

```bash
# Build and start with production configuration
./start-docker.sh --production --detach
```

## Deployment Methods

## Method 1: Local Development

### Prerequisites Check

```bash
# Check system dependencies
./scripts/health-check.sh

# Verify database connection
python scripts/migrate.py check
```

### Start Services

```bash
# Development mode with hot reload
./start.sh

# Available at:
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Stop Services

```bash
# Graceful shutdown
./stop.sh

# Force stop if needed
./stop.sh --force
```

## Method 2: Docker Development

### Build and Start

```bash
# Build and start all services
./start-docker.sh

# With rebuild
./start-docker.sh --build

# Development mode with hot reload
./start-docker.sh --development
```

### Managing Services

```bash
# View logs
docker-compose logs -f

# Restart specific service
docker-compose restart backend

# Execute command in container
docker-compose exec backend bash
```

## Method 3: Production Docker

### Environment Setup

```bash
# Production environment variables
cp .env.example .env.production

# Configure production settings
sed -i 's/DEBUG=true/DEBUG=false/g' .env.production
sed -i 's/ENVIRONMENT=development/ENVIRONMENT=production/g' .env.production

# Set strong passwords and keys
sed -i 's/momentum_password_change_this/$(openssl rand -base64 32)/g' .env.production
sed -i 's/your_super_secret_key_change_this/$(openssl rand -base64 64)/g' .env.production
```

### Deploy Production

```bash
# Start with production profile
COMPOSE_PROFILES=production ./start-docker.sh --production --detach

# With SSL/HTTPS support
./start-docker.sh --production --detach

# Check deployment
./scripts/health-check.sh
```

## Environment Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@host:5432/momentum_lens
REDIS_URL=redis://:password@host:6379/0

# Security
SECRET_KEY=your_secret_key_minimum_32_characters
JWT_SECRET_KEY=jwt_secret_key

# APIs
MARKET_DATA_API_KEY=your_api_key
TUSHARE_TOKEN=your_tushare_token

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### Optional Configuration

```bash
# Monitoring
ENABLE_MONITORING=true
GRAFANA_PASSWORD=secure_password

# Notifications
SMTP_HOST=smtp.gmail.com
SMTP_USER=your_email@gmail.com
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Trading
DEFAULT_PRESET=balanced
EXECUTION_WINDOWS=10:30,14:00
TIMEZONE=Asia/Shanghai
```

## Database Setup

### Initialize Database

```bash
# Create database and run migrations
python scripts/migrate.py init

# Or using Docker
docker-compose exec backend python scripts/migrate.py init
```

### Migration Management

```bash
# Check current status
python scripts/migrate.py status

# Run pending migrations
python scripts/migrate.py migrate

# Rollback if needed
python scripts/migrate.py rollback
```

### Backup and Restore

```bash
# Create backup
pg_dump $DATABASE_URL > backup-$(date +%Y%m%d).sql

# Restore backup
psql $DATABASE_URL < backup-20241215.sql
```

## Monitoring and Logging

### Start Monitoring Stack

```bash
# Start monitoring services
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3001 (admin/admin123)
# Prometheus: http://localhost:9090
# AlertManager: http://localhost:9093
```

### Log Management

```bash
# View application logs
tail -f logs/backend.log
tail -f logs/frontend.log

# Docker container logs
docker-compose logs -f backend
docker-compose logs -f frontend

# System logs with journalctl
sudo journalctl -u momentum-lens -f
```

## SSL/HTTPS Configuration

### Self-signed Certificates (Development)

```bash
# Generate self-signed certificate
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

### Let's Encrypt (Production)

```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## Performance Optimization

### Database Tuning

```sql
-- PostgreSQL configuration
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### Application Tuning

```bash
# Increase worker processes
export WORKERS=4

# Optimize Redis
redis-cli CONFIG SET maxmemory 512mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

### Container Resource Limits

```yaml
# docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1.0'
        reservations:
          memory: 512M
          cpus: '0.5'
```

## Security Hardening

### System Security

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Disable root login
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/g' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Application Security

```bash
# Set secure file permissions
chmod 600 .env*
chmod 700 scripts/
chmod 755 *.sh

# Use strong passwords
export SECRET_KEY=$(openssl rand -base64 64)
export DB_PASSWORD=$(openssl rand -base64 32)
```

### Network Security

```bash
# Configure nginx security headers
# See nginx/nginx-proxy.conf for security headers

# Use HTTPS only in production
export FORCE_HTTPS=true
```

## Troubleshooting

### Common Issues

**1. Database Connection Failed**
```bash
# Check database status
pg_isready -h localhost -p 5432

# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check firewall
sudo ufw status
```

**2. Redis Connection Failed**
```bash
# Check Redis status
redis-cli ping

# Check Redis configuration
redis-cli CONFIG GET maxmemory
```

**3. High Memory Usage**
```bash
# Check memory usage
free -h
docker stats

# Optimize containers
docker system prune -f
```

**4. SSL Certificate Issues**
```bash
# Check certificate validity
openssl x509 -in nginx/ssl/cert.pem -text -noout

# Renew Let's Encrypt certificate
sudo certbot renew
```

### Health Check and Diagnostics

```bash
# Run comprehensive health check
./scripts/health-check.sh

# Check service status
docker-compose ps

# View recent logs
docker-compose logs --tail=100

# Test API endpoints
curl -f http://localhost:8000/api/v1/health
curl -f http://localhost:3000/health
```

### Log Analysis

```bash
# Find errors in logs
grep -i error logs/*.log

# Monitor real-time logs
tail -f logs/*.log | grep -i error

# Check application metrics
curl http://localhost:9090/api/v1/query?query=up
```

## Maintenance

### Regular Tasks

**Daily:**
- Monitor system health
- Check log files for errors
- Verify backup completion

**Weekly:**
- Update system packages
- Clean old log files
- Review performance metrics

**Monthly:**
- Update application dependencies
- Review security configurations
- Test backup restoration

### Maintenance Scripts

```bash
# Daily maintenance
./scripts/daily-maintenance.sh

# Clean old logs
find logs/ -name "*.log" -mtime +7 -delete

# Update system packages
sudo apt update && sudo apt upgrade -y
```

## Scaling and High Availability

### Horizontal Scaling

```bash
# Scale backend services
docker-compose up -d --scale backend=3

# Use load balancer
# Configure nginx upstream servers
```

### Database Scaling

```bash
# Configure read replicas
# Set up connection pooling
# Implement caching strategies
```

### Monitoring Scaling

```bash
# Set up alerting
# Monitor key metrics
# Implement auto-scaling
```

## CI/CD Pipeline

### GitHub Actions

The repository includes comprehensive CI/CD workflows:

- **CI Pipeline** (`.github/workflows/ci.yml`)
  - Automated testing
  - Security scanning
  - Docker image building
  - Integration tests

- **Deployment Pipeline** (`.github/workflows/deploy.yml`)
  - Staging deployment
  - Production deployment with approval
  - Rollback capability

### Setting Up CI/CD

```bash
# Configure GitHub secrets
CONTAINER_REGISTRY
REGISTRY_USERNAME
REGISTRY_PASSWORD
STAGING_HOST
STAGING_SSH_KEY
PRODUCTION_HOST
PRODUCTION_SSH_KEY
SLACK_WEBHOOK
```

## Support and Documentation

- **API Documentation**: http://localhost:8000/docs
- **Monitoring Dashboards**: http://localhost:3001
- **Health Check Endpoint**: http://localhost:8000/api/v1/health
- **System Status**: `./scripts/health-check.sh`

For additional support, check the logs and use the health check script to diagnose issues.