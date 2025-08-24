# Momentum Lens - 智能ETF动量交易系统

## 项目简介

Momentum Lens 是一个专为中国市场设计的智能化ETF动量交易系统。通过综合动量评分、相关性分析和多层风险管理，为投资者提供系统化的交易决策支持。

### 核心特性

- 🎯 **双腿策略**: Core-Satellite结构，核心稳健+卫星进攻
- 📊 **动量评分**: 基于60/120日涨幅的智能评分系统
- 🔒 **风险控制**: 止损、缓冲区、最短持有期多重保护
- ⚡ **一键决策**: 简化操作，每周二定期执行
- 📈 **实时监控**: WebSocket推送，实时数据更新

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/momentum-lens.git
cd momentum-lens
```

2. **后端设置**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **前端设置**
```bash
cd frontend
npm install
```

4. **数据库初始化**
```bash
# 创建数据库
createdb momentum_lens

# 运行迁移
python backend/manage.py migrate
```

5. **启动服务**
```bash
# 启动后端
cd backend
uvicorn main:app --reload

# 启动前端（新终端）
cd frontend
npm start
```

访问 http://localhost:3000 即可使用系统。

## 项目结构

```
momentum-lens/
├── backend/              # 后端服务
│   ├── api/             # API端点
│   ├── core/            # 核心业务逻辑
│   │   ├── decision_engine.py    # 决策引擎
│   │   ├── portfolio_manager.py  # 组合管理
│   │   ├── risk_manager.py       # 风险管理
│   │   └── data_fetcher.py       # 数据获取
│   ├── models/          # 数据模型
│   ├── utils/           # 工具函数
│   └── tests/           # 测试代码
├── frontend/            # 前端应用
│   ├── src/
│   │   ├── components/  # React组件
│   │   ├── services/    # API服务
│   │   └── styles/      # 样式文件
│   └── public/          # 静态资源
├── data/                # 数据文件
├── docs/                # 文档
├── scripts/             # 脚本工具
└── tests/               # 集成测试
```

## 核心功能

### 1. 决策台
- 市场环境评估（年线、ATR、CHOP）
- 参数预设（进攻/均衡/保守）
- 一键生成交易建议
- 资格检查和限价计算

### 2. Core模块（核心持仓）
- 目标配置：60%稳健资产
- 包含：沪深300、红利、货币、黄金、标普500
- 自动再平衡提醒

### 3. Satellite模块（卫星持仓）
- 目标配置：40%动量资产
- 动态选择高动量ETF
- 月度轮动检查
- 相关性控制（ρ≤0.8）

### 4. 风险管理
- 多级止损（-10%到-15%）
- 缓冲区控制（2%-4%）
- 最短持有期（2-4周）
- 实时预警推送

## 使用指南

### 每周操作流程

1. **周日晚上**: 打开系统，查看下周交易计划
2. **周二上午10:30**: 执行第一批交易指令
3. **周二下午14:00**: 执行第二批交易指令
4. **日常**: 关注系统预警，无需频繁操作
5. **月末**: 检查是否需要调整卫星持仓

### 参数设置

| 模式 | 止损 | 缓冲 | 最短持有 | 适合人群 |
|-----|------|------|---------|---------|
| 进攻 | -10% | 2% | 2周 | 风险偏好高 |
| 均衡 | -12% | 3% | 2周 | 一般投资者 |
| 保守 | -15% | 4% | 4周 | 风险厌恶型 |

## ETF池

### Core池（核心）
- 510300/159919: 沪深300
- 510880: 上证红利
- 511990: 华宝添益（货币）
- 518880: 华安黄金
- 513500: 标普500（QDII）

### Satellite池（卫星）
- 588000: 科创50
- 512760: 半导体
- 512720: 计算机
- 516010: 游戏动漫
- 516160: 新能源
- 512400: 有色金属
- 512800: 银行
- 512000: 券商
- 512170: 医疗

## API文档

详细API文档请访问：http://localhost:8000/docs

主要端点：
- `GET /api/market/overview` - 市场概览
- `POST /api/decisions/calculate` - 计算交易决策
- `GET /api/portfolio/holdings` - 获取当前持仓
- `POST /api/orders/create` - 创建交易订单

## 配置说明

创建 `.env` 文件并配置以下参数：

```env
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost/momentum_lens
REDIS_URL=redis://localhost:6379

# API密钥
MARKET_DATA_API_KEY=your_api_key

# 交易配置
DEFAULT_PRESET=balanced
EXECUTION_WINDOWS=10:30,14:00
MAX_LEGS=2

# 风险参数
DEFAULT_STOP_LOSS=0.12
DEFAULT_BUFFER=0.03
MIN_HOLDING_DAYS=14
```

## 开发指南

### 运行测试
```bash
# 后端测试
cd backend
pytest

# 前端测试
cd frontend
npm test
```

### 代码规范
```bash
# Python代码格式化
black backend/
flake8 backend/

# JavaScript代码格式化
npm run lint
npm run format
```

## 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 联系方式

- 项目主页: [https://github.com/yourusername/momentum-lens](https://github.com/yourusername/momentum-lens)
- Issue反馈: [https://github.com/yourusername/momentum-lens/issues](https://github.com/yourusername/momentum-lens/issues)

## 免责声明

本系统仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。

---

**Momentum Lens** - 让投资决策更智能、更系统、更简单。