#!/bin/bash

echo "====================================="
echo "Momentum Lens 全模块测试"
echo "====================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASE_URL="http://localhost:8000"
FAILED=0

# 测试函数
test_module() {
    local module=$1
    local endpoint=$2
    local check_field=$3
    
    echo -e "${YELLOW}测试 $module...${NC}"
    
    response=$(curl -s "$BASE_URL$endpoint")
    
    if [ -z "$response" ]; then
        echo -e "${RED}❌ $module: 无响应${NC}"
        FAILED=$((FAILED + 1))
        return
    fi
    
    # 检查特定字段是否存在
    if [ ! -z "$check_field" ]; then
        if echo "$response" | grep -q "\"$check_field\""; then
            echo -e "${GREEN}✅ $module: 正常 (包含字段 $check_field)${NC}"
        else
            echo -e "${RED}❌ $module: 缺少字段 $check_field${NC}"
            echo "  响应: $(echo $response | head -c 100)..."
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "${GREEN}✅ $module: 正常${NC}"
    fi
}

echo "1. 决策台模块测试"
echo "-----------------"
test_module "市场指标" "/api/market/indicators" "yearline"
test_module "当前决策" "/api/decisions/current" "firstLeg"

echo ""
echo "2. Core模块测试"
echo "---------------"
test_module "持仓信息" "/api/portfolio/holdings" "targetWeight"
test_module "定投计划" "/api/portfolio/dca-schedule" "nextDate"
test_module "HS300图表" "/api/market/hs300-chart?period=6M" "prices"

echo ""
echo "3. Satellite模块测试"
echo "-------------------"
test_module "动量排名" "/api/market/momentum-rankings" "volume"
test_module "相关性矩阵" "/api/market/correlation?anchor=510300" "values"

echo ""
echo "4. 日志/KPI模块测试"
echo "------------------"
test_module "交易日志" "/api/trading/logs" "timestamp"
test_module "绩效指标" "/api/performance/metrics" "totalReturn"
test_module "收益数据" "/api/performance/returns?period=6M" "data"
test_module "回撤数据" "/api/performance/drawdown" "current"
test_module "预警信息" "/api/alerts" "timestamp"

echo ""
echo "5. 配置模块测试"
echo "---------------"
test_module "系统配置" "/api/config/settings" "presets"

echo ""
echo "====================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}所有模块测试通过！${NC}"
else
    echo -e "${RED}有 $FAILED 个测试失败${NC}"
    echo ""
    echo "修复建议："
    echo "1. 运行 ./fix_all.sh 重启服务"
    echo "2. 检查 backend.log 查看错误"
    echo "3. 参考 TROUBLESHOOTING.md 排查问题"
fi
echo "====================================="