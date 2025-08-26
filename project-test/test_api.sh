#!/bin/bash

# API测试脚本

echo "========================================="
echo "   ETF动量决策系统 - API测试"
echo "========================================="
echo ""

API_URL="http://127.0.0.1:8000"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 测试函数
test_api() {
    local endpoint=$1
    local name=$2
    
    echo -n "测试 $name ... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL$endpoint")
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✅ 成功${NC}"
        # 显示部分数据
        curl -s "$API_URL$endpoint" | head -c 200
        echo ""
    else
        echo -e "${RED}❌ 失败 (HTTP $response)${NC}"
    fi
    echo ""
}

# 测试各个端点
echo "📊 测试API端点："
echo ""

test_api "/" "根路径"
test_api "/api/health" "健康检查"
test_api "/api/market/realtime" "实时市场数据"
test_api "/api/index/hs300" "沪深300指数"
test_api "/api/momentum/ranking" "动量排名"
test_api "/api/portfolio/suggestions" "组合建议"

echo ""
echo "========================================="
echo "测试完成！"
echo ""
echo "📊 前端界面: http://127.0.0.1:3000"
echo "📝 API文档: http://127.0.0.1:8000/docs"
echo "========================================="