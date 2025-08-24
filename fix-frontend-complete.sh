#!/bin/bash

# 完整的前端依赖修复脚本
# 解决所有已知的兼容性问题

echo "🔧 完整前端依赖修复"
echo "===================="

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📦 步骤1: 彻底清理...${NC}"
cd frontend
rm -rf node_modules package-lock.json
echo -e "${GREEN}✅ 清理完成${NC}"

echo -e "${BLUE}📦 步骤2: 创建兼容的package.json...${NC}"
cat > package.json << 'EOF'
{
  "name": "momentum-lens-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "@mui/material": "^5.14.0",
    "@mui/icons-material": "^5.14.0",
    "@emotion/react": "^11.11.0",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.0",
    "react-router-dom": "^6.20.0",
    "lightweight-charts": "^4.1.0",
    "recharts": "^2.10.0",
    "react-hot-toast": "^2.4.0",
    "socket.io-client": "^4.6.0",
    "date-fns": "^2.30.0",
    "@tanstack/react-query": "^5.12.0",
    "ajv": "^8.12.0",
    "ajv-keywords": "^5.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/node": "^20.10.0",
    "typescript": "^4.9.5"
  },
  "eslintConfig": {
    "extends": [
      "react-app"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}
EOF
echo -e "${GREEN}✅ package.json更新完成${NC}"

echo -e "${BLUE}📦 步骤3: 安装依赖...${NC}"
npm install --legacy-peer-deps

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  标准安装失败，尝试强制安装...${NC}"
    npm install --force
fi

echo -e "${GREEN}✅ 依赖安装完成${NC}"

echo -e "${BLUE}🔍 步骤4: 验证关键模块...${NC}"
MISSING_MODULES=0

# 检查关键模块
if [ ! -d "node_modules/react" ]; then
    echo -e "${RED}❌ React未安装${NC}"
    MISSING_MODULES=1
fi

if [ ! -d "node_modules/react-scripts" ]; then
    echo -e "${RED}❌ react-scripts未安装${NC}"
    MISSING_MODULES=1
fi

if [ ! -d "node_modules/ajv" ]; then
    echo -e "${RED}❌ ajv未安装${NC}"
    MISSING_MODULES=1
fi

if [ $MISSING_MODULES -eq 0 ]; then
    echo -e "${GREEN}✅ 所有关键模块已安装${NC}"
else
    echo -e "${RED}❌ 有关键模块缺失${NC}"
fi

cd ..

echo ""
echo "===================="
echo -e "${GREEN}✨ 修复完成！${NC}"
echo ""
echo "如果仍有问题，可以尝试："
echo "1. 使用Vite替代create-react-app："
echo "   ./use-vite.sh"
echo ""
echo "2. 或者直接运行后端API："
echo "   cd backend && source venv/bin/activate && python main_lite.py"