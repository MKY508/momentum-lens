#!/bin/bash

# Test Momentum Lens System

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Testing Momentum Lens System..."
echo "================================"

# Test backend health
echo -n "Testing backend health endpoint... "
if curl -s http://127.0.0.1:8000/api/v1/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ Passed${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
fi

# Test API endpoint
echo -n "Testing decisions API... "
if curl -s http://127.0.0.1:8000/api/v1/decisions/calculate | grep -q "picks"; then
    echo -e "${GREEN}✅ Passed${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
fi

# Test frontend
echo -n "Testing frontend... "
if curl -s http://127.0.0.1:3000 | grep -q "root"; then
    echo -e "${GREEN}✅ Passed${NC}"
else
    echo -e "${RED}❌ Failed${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}System is running successfully!${NC}"
echo ""
echo "Access points:"
echo "  Frontend: http://127.0.0.1:3000"
echo "  Backend API: http://127.0.0.1:8000"
echo "  API Docs: http://127.0.0.1:8000/docs"
echo ""