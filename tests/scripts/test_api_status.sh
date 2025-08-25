#!/bin/bash

echo "========================================="
echo "Momentum Lens API 状态检查"
echo "========================================="
echo ""

BASE_URL="http://localhost:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试函数
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    
    response=$(curl -s -o /dev/null -w "%{http_code}" -X $method "$BASE_URL$endpoint")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✅${NC} $description: $endpoint"
    else
        echo -e "${RED}❌${NC} $description: $endpoint (HTTP $response)"
    fi
}

echo "核心API端点测试："
echo "-----------------"
test_endpoint "GET" "/api/health" "健康检查"
test_endpoint "GET" "/api/market/indicators" "市场指标"
test_endpoint "GET" "/api/decisions/current" "当前决策"
test_endpoint "GET" "/api/portfolio/holdings" "持仓信息"
test_endpoint "GET" "/api/market/momentum-rankings" "动量排名"
test_endpoint "GET" "/api/market/correlation?anchor=510300" "相关性矩阵"
test_endpoint "GET" "/api/market/hs300-chart?period=6M" "HS300图表"
test_endpoint "GET" "/api/portfolio/dca-schedule" "定投计划"
test_endpoint "GET" "/api/trading/logs" "交易日志"
test_endpoint "GET" "/api/performance/metrics" "绩效指标"
test_endpoint "GET" "/api/config/settings" "配置信息"

echo ""
echo "POST端点测试："
echo "-------------"
test_endpoint "POST" "/api/decisions/calculate" "计算决策"
test_endpoint "POST" "/api/market/test-source" "测试数据源"

echo ""
echo "CORS预检测试："
echo "-------------"
cors_response=$(curl -s -o /dev/null -w "%{http_code}" \
    -X OPTIONS "$BASE_URL/api/market/test-source" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: POST")

if [ "$cors_response" = "200" ]; then
    echo -e "${GREEN}✅${NC} CORS预检请求正常"
else
    echo -e "${RED}❌${NC} CORS预检请求失败 (HTTP $cors_response)"
fi

echo ""
echo "WebSocket兼容性："
echo "-----------------"
test_endpoint "GET" "/socket.io/" "Socket.IO回退端点"

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="