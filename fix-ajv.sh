#!/bin/bash

# 修复AJV模块冲突问题

echo "🔧 修复AJV模块冲突..."
echo "========================"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd frontend

echo -e "${BLUE}📦 安装兼容的AJV版本...${NC}"

# 安装兼容的ajv版本
npm install ajv@^8.0.0 --save --legacy-peer-deps

# 修复ajv-keywords
npm install ajv-keywords@^5.0.0 --save --legacy-peer-deps

# 清理缓存
echo -e "${BLUE}🧹 清理npm缓存...${NC}"
npm cache clean --force

echo -e "${GREEN}✅ AJV修复完成${NC}"

cd ..

echo ""
echo "========================"
echo -e "${GREEN}✨ 修复完成！现在尝试重新启动...${NC}"
echo ""

# 重新启动
./quick-start-lite.sh