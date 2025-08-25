#!/bin/bash

echo "================================"
echo "Momentum Lens 万能修复脚本"
echo "================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}[1/4] 停止当前后端服务...${NC}"
ps aux | grep -E 'python.*main_lite' | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null
sleep 1
echo -e "${GREEN}✅ 服务已停止${NC}"

echo -e "${YELLOW}[2/4] 启动后端服务...${NC}"
cd backend
./venv/bin/python main_lite.py > ../backend.log 2>&1 &
cd ..
sleep 3
echo -e "${GREEN}✅ 后端服务已启动${NC}"

echo -e "${YELLOW}[3/4] 验证API端点...${NC}"
# 测试关键端点
health_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
if [ "$health_status" = "200" ]; then
    echo -e "${GREEN}✅ API健康检查正常${NC}"
else
    echo -e "${RED}❌ API健康检查失败${NC}"
    exit 1
fi

echo -e "${YELLOW}[4/4] 测试所有模块...${NC}"

# 测试决策台
decision_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/decisions/current)
if [ "$decision_status" = "200" ]; then
    echo -e "${GREEN}✅ 决策台API正常${NC}"
else
    echo -e "${RED}❌ 决策台API失败${NC}"
fi

# 测试Core模块
holdings_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/portfolio/holdings)
dca_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/portfolio/dca-schedule)
if [ "$holdings_status" = "200" ] && [ "$dca_status" = "200" ]; then
    echo -e "${GREEN}✅ Core模块API正常${NC}"
else
    echo -e "${RED}❌ Core模块API失败${NC}"
fi

# 测试Satellite模块
momentum_status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/market/momentum-rankings)
correlation_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/market/correlation?anchor=510300")
if [ "$momentum_status" = "200" ] && [ "$correlation_status" = "200" ]; then
    echo -e "${GREEN}✅ Satellite模块API正常${NC}"
else
    echo -e "${RED}❌ Satellite模块API失败${NC}"
fi

echo ""
echo "================================"
echo -e "${GREEN}修复完成！${NC}"
echo "================================"
echo ""
echo "请访问以下地址："
echo "• 前端应用: http://localhost:3000"
echo "• API文档: http://localhost:8000/docs"
echo ""
echo "如果仍有问题，请运行："
echo "• ./test_api_status.sh  # 详细API测试"
echo "• tail -f backend.log   # 查看后端日志"