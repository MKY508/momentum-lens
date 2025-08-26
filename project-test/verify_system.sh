#!/bin/bash

echo "=" * 50
echo "🔍 ETF动量决策系统 - 运行状态检查"
echo "=" * 50
echo ""

# 检查前端
echo "1. 前端服务 (React):"
if curl -s http://127.0.0.1:3000 > /dev/null; then
    echo "   ✅ 前端运行正常"
    echo "   📊 访问地址: http://127.0.0.1:3000"
else
    echo "   ❌ 前端服务未运行"
fi

echo ""
echo "2. 后端API (FastAPI):"
if curl -s http://127.0.0.1:8000/docs > /dev/null; then
    echo "   ✅ API运行正常"
    echo "   📚 API文档: http://127.0.0.1:8000/docs"
    
    # 尝试调用API
    echo ""
    echo "   测试API端点:"
    
    # 市场环境
    MARKET=$(curl -s http://127.0.0.1:8000/api/market/environment 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "   ✅ /api/market/environment - 可访问"
    else
        echo "   ⚠️  /api/market/environment - 不可访问"
    fi
    
else
    echo "   ❌ API服务未运行"
fi

echo ""
echo "3. 系统摘要:"
echo "   前端地址: http://127.0.0.1:3000"
echo "   API文档: http://127.0.0.1:8000/docs"
echo "   配置文件: config/config.yaml"
echo ""
echo "💡 提示:"
echo "   - 访问前端界面查看决策控制台"
echo "   - 访问API文档了解所有接口"
echo "   - 运行 python test_system.py 进行功能测试"
echo ""