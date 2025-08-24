#!/bin/bash

# 使用Vite创建现代化前端（避免Create-React-App的依赖问题）

echo "🚀 使用Vite创建现代化前端"
echo "==========================="

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}📦 步骤1: 备份现有前端...${NC}"
if [ -d "frontend" ]; then
    mv frontend frontend_backup_$(date +%Y%m%d_%H%M%S)
    echo -e "${GREEN}✅ 原前端已备份${NC}"
fi

echo -e "${BLUE}📦 步骤2: 创建Vite项目...${NC}"
npm create vite@latest frontend -- --template react-ts
echo -e "${GREEN}✅ Vite项目创建完成${NC}"

cd frontend

echo -e "${BLUE}📦 步骤3: 安装必要依赖...${NC}"
npm install \
  @mui/material@^5.14.0 \
  @mui/icons-material@^5.14.0 \
  @emotion/react@^11.11.0 \
  @emotion/styled@^11.11.0 \
  axios@^1.6.0 \
  react-router-dom@^6.20.0 \
  lightweight-charts@^4.1.0 \
  recharts@^2.10.0 \
  react-hot-toast@^2.4.0 \
  socket.io-client@^4.6.0 \
  date-fns@^2.30.0 \
  @tanstack/react-query@^5.12.0

echo -e "${GREEN}✅ 依赖安装完成${NC}"

echo -e "${BLUE}📦 步骤4: 配置Vite...${NC}"
cat > vite.config.ts << 'EOF'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
})
EOF
echo -e "${GREEN}✅ Vite配置完成${NC}"

echo -e "${BLUE}📦 步骤5: 创建基础App组件...${NC}"
cat > src/App.tsx << 'EOF'
import React, { useState } from 'react'
import { Toaster } from 'react-hot-toast'
import './App.css'

function App() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/decisions/calculate')
      const result = await response.json()
      setData(result)
    } catch (error) {
      console.error('Error:', error)
    }
    setLoading(false)
  }

  return (
    <div className="App">
      <header className="App-header">
        <h1>🎯 Momentum Lens</h1>
        <p>智能ETF动量交易系统</p>
      </header>
      
      <main>
        <div className="dashboard">
          <div className="card">
            <h2>决策台</h2>
            <button onClick={fetchData} disabled={loading}>
              {loading ? '计算中...' : '生成交易决策'}
            </button>
            
            {data && (
              <div className="results">
                <h3>交易建议</h3>
                <div className="picks">
                  {data.picks?.map((pick: any, index: number) => (
                    <div key={index} className="pick-card">
                      <h4>{pick.code} - {pick.name}</h4>
                      <p>Score: {pick.score?.toFixed(3)}</p>
                      <p>目标权重: {(pick.target_weight * 100).toFixed(1)}%</p>
                      <p>理由: {pick.reason}</p>
                    </div>
                  ))}
                </div>
                
                <div className="environment">
                  <h3>市场环境</h3>
                  <p>年线状态: {data.environment?.yearline ? '📈 上方' : '📉 下方'}</p>
                  <p>ATR20: {data.environment?.atr20_pct?.toFixed(2)}%</p>
                  <p>CHOP: {data.environment?.chop ? '开启' : '关闭'}</p>
                </div>
              </div>
            )}
          </div>
          
          <div className="card">
            <h2>快速链接</h2>
            <ul>
              <li><a href="http://localhost:8000/docs" target="_blank">📚 API文档</a></li>
              <li><a href="http://localhost:8000/api/v1/health" target="_blank">❤️ 健康检查</a></li>
              <li><a href="http://localhost:8000/api/v1/market/data-sources" target="_blank">📊 数据源状态</a></li>
            </ul>
          </div>
        </div>
      </main>
      
      <Toaster position="top-right" />
    </div>
  )
}

export default App
EOF
echo -e "${GREEN}✅ App组件创建完成${NC}"

echo -e "${BLUE}📦 步骤6: 创建样式文件...${NC}"
cat > src/App.css << 'EOF'
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
}

.App {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.App-header {
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.App-header h1 {
  font-size: 2.5rem;
  margin-bottom: 10px;
}

.dashboard {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 20px;
}

.card {
  background: white;
  border-radius: 10px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card h2 {
  margin-bottom: 20px;
  color: #333;
}

button {
  background: #667eea;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.3s;
}

button:hover {
  background: #5a67d8;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.results {
  margin-top: 20px;
}

.picks {
  display: grid;
  gap: 15px;
  margin-top: 10px;
}

.pick-card {
  background: #f7fafc;
  padding: 15px;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.pick-card h4 {
  color: #2d3748;
  margin-bottom: 8px;
}

.pick-card p {
  color: #4a5568;
  margin: 5px 0;
}

.environment {
  margin-top: 20px;
  padding: 15px;
  background: #edf2f7;
  border-radius: 8px;
}

.environment h3 {
  color: #2d3748;
  margin-bottom: 10px;
}

.environment p {
  color: #4a5568;
  margin: 8px 0;
}

ul {
  list-style: none;
}

ul li {
  margin: 10px 0;
}

ul li a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s;
}

ul li a:hover {
  color: #5a67d8;
}

@media (max-width: 768px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
}
EOF
echo -e "${GREEN}✅ 样式创建完成${NC}"

echo -e "${BLUE}📦 步骤7: 创建环境配置...${NC}"
cat > .env << 'EOF'
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
EOF
echo -e "${GREEN}✅ 环境配置完成${NC}"

cd ..

echo ""
echo "==========================="
echo -e "${GREEN}✨ Vite前端创建完成！${NC}"
echo ""
echo "启动方式："
echo "1. 启动后端："
echo "   cd backend && source venv/bin/activate && python main_lite.py"
echo ""
echo "2. 启动前端："
echo "   cd frontend && npm run dev"
echo ""
echo "访问地址："
echo "   前端: http://localhost:3000"
echo "   API: http://localhost:8000"
echo ""
echo "优势："
echo "   ✓ 无依赖冲突"
echo "   ✓ 启动速度快"
echo "   ✓ 热更新更流畅"
echo "   ✓ 构建体积更小"