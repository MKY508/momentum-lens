#!/bin/bash

# 修复ajv和相关依赖的兼容性问题

echo "🔧 修复AJV依赖兼容性问题..."
echo "============================="

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📦 步骤1: 清理现有依赖...${NC}"
cd frontend
rm -rf node_modules package-lock.json
echo -e "${GREEN}✅ 清理完成${NC}"

echo -e "${BLUE}📦 步骤2: 安装兼容的ajv版本...${NC}"
# 首先安装特定版本的ajv和ajv-keywords以解决兼容性问题
npm install ajv@^8.12.0 ajv-keywords@^5.1.0 --save --legacy-peer-deps
echo -e "${GREEN}✅ AJV核心包安装完成${NC}"

echo -e "${BLUE}📦 步骤3: 安装所有依赖...${NC}"
npm install --legacy-peer-deps
echo -e "${GREEN}✅ 依赖安装完成${NC}"

echo -e "${BLUE}🔨 步骤4: 修复潜在的版本冲突...${NC}"
# 强制解决任何剩余的版本冲突
npm dedupe --legacy-peer-deps
echo -e "${GREEN}✅ 依赖树优化完成${NC}"

# 验证安装
echo -e "${BLUE}🔍 步骤5: 验证安装...${NC}"
if [ -d "node_modules/ajv/dist/compile/codegen" ]; then
    echo -e "${GREEN}✅ AJV模块路径存在${NC}"
else
    echo -e "${YELLOW}⚠️  AJV模块路径不存在，尝试重新安装...${NC}"
    npm install ajv@latest ajv-keywords@latest --save --force
fi

cd ..

echo ""
echo "============================="
echo -e "${GREEN}✨ 修复完成！${NC}"
echo ""
echo "现在可以运行："
echo "  ./quick-start-lite.sh"
echo ""
echo "如果仍有问题，请运行："
echo "  ./fix-frontend-complete.sh"