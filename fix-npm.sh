#!/bin/bash

# NPM依赖修复脚本

echo "🔧 修复NPM依赖问题..."
echo "========================"

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 清理现有的node_modules和锁文件
echo -e "${BLUE}🧹 清理旧的依赖...${NC}"
cd frontend
rm -rf node_modules package-lock.json
echo -e "${GREEN}✅ 清理完成${NC}"

# 使用legacy-peer-deps安装
echo -e "${BLUE}📦 安装依赖（使用兼容模式）...${NC}"
npm install --legacy-peer-deps

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 依赖安装成功！${NC}"
    echo ""
    echo "现在可以运行以下命令启动系统："
    echo "  ./quick-start-lite.sh"
    echo ""
else
    echo -e "${YELLOW}⚠️  安装失败，尝试强制安装...${NC}"
    npm install --force
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ 强制安装成功！${NC}"
    else
        echo -e "${RED}❌ 安装失败，请检查错误信息${NC}"
        exit 1
    fi
fi

cd ..
echo "========================"
echo -e "${GREEN}✨ 修复完成！${NC}"