# 动量透镜 - A股ETF核心卫星策略系统

一个基于动量策略的A股ETF半自动化投资决策系统，采用核心-卫星配置模式，结合可转债网格交易。

## 系统架构

- **前端**: React 18 + TypeScript + Vite
- **后端**: Python 3.11 + FastAPI
- **数据库**: PostgreSQL + TimescaleDB
- **缓存**: Redis
- **数据源**: AKShare (可扩展)

## 核心功能

### 1. 核心卫星策略
- **Core资产** (40%): 宽基、红利、债券、黄金、海外资产
- **卫星资产** (30%): 动量选股的行业/主题ETF
- **可转债** (10%): 网格交易策略
- **现金储备** (20%): 灵活调配

### 2. 动量评分系统
- 双窗口动量计算 (3月60% + 6月40%)
- MA200年线状态判断
- ATR20波动率监控
- CHOP震荡指数分析

### 3. 风险控制
- 单一标的上限15%
- 相关性控制 (<0.8)
- 止损线 (-12%)
- IOPV溢价率控制

### 4. 自动化功能
- 市场环境分析
- 卫星ETF选择
- 再平衡建议
- 6周定投计划
- 订单导出

## 快速开始

### 环境要求
- Docker & Docker Compose
- Node.js 18+
- Python 3.11+

### 安装步骤

1. **克隆项目**
```bash
git clone <repository>
cd project-test
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库密码等
```

3. **使用Docker Compose启动**
```bash
docker-compose up -d
```

4. **访问系统**
- 前端界面: http://localhost:3000
- API文档: http://localhost:8000/docs

### 本地开发

**后端开发**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

**前端开发**
```bash
cd frontend
npm install
npm run dev
```

## 配置说明

### 主配置文件 (config/config.yaml)
```yaml
capital: 200000           # 总资金
dca_weeks: 6             # 定投周数
execution_day: "Tue"     # 执行日
execution_windows:       # 执行时间窗口
  - "10:30"
  - "14:00"

core_target:             # Core资产目标配置
  broad: 0.20           # 宽基
  dividend: 0.10        # 红利
  bond_cash: 0.15       # 债券货币
  gold: 0.10           # 黄金
  sp500: 0.05          # 标普500

satellite_target: 0.30   # 卫星资产目标
convertible_target: 0.10 # 可转债目标
```

### 持仓配置 (config/positions.yaml)
记录当前持仓状态，包括：
- Core持仓明细
- 卫星持仓明细
- 可转债持仓
- 定投进度

## API接口

### 市场分析
- `GET /api/market/environment` - 获取市场环境
- `GET /api/momentum/ranking` - 动量排名

### 决策生成
- `POST /api/decisions/generate` - 生成投资决策
- `GET /api/decisions/satellite` - 卫星ETF选择

### 组合管理
- `GET /api/portfolio/summary` - 组合汇总
- `GET /api/portfolio/positions` - 当前持仓
- `POST /api/portfolio/rebalance` - 再平衡建议
- `POST /api/portfolio/dca` - 执行定投

### 数据接口
- `GET /api/data/etfs` - ETF列表
- `GET /api/data/etf/{code}/price` - ETF价格
- `GET /api/data/convertibles` - 可转债列表

## 核心算法

### 动量计算
```python
momentum_score = r3m * 0.6 + r6m * 0.4
```

### 市场状态判断
- MA200比率 > 1.05: 强势站上年线
- MA200比率 0.95-1.05: 震荡区间
- MA200比率 < 0.95: 弱势跌破年线

### 换腿条件
1. 持有时间 >= 2周
2. 触发止损 (-12%)
3. 动量衰减超过缓冲区 (3%)

## 监控指标

### KPI指标
- 总收益率
- 夏普比率
- 最大回撤
- 胜率
- 平均持有期

### 风险指标
- 单一持仓集中度
- 模块权重偏离
- 止损触发
- 溢价率异常

## 部署说明

### 生产环境部署
1. 修改docker-compose.yml中的环境变量
2. 配置SSL证书 (nginx/ssl/)
3. 设置数据备份策略
4. 配置监控告警

### 性能优化
- PostgreSQL使用TimescaleDB优化时序数据
- Redis缓存热点数据
- 前端资源CDN加速
- API响应压缩

## 开发指南

### 添加新的数据源
1. 实现DataSourceInterface接口
2. 在DataSourceFactory注册
3. 更新配置文件

### 添加新的指标
1. 在indicators模块添加计算逻辑
2. 更新MomentumCalculator
3. 添加相应的API接口

## 注意事项

1. **数据源限制**: AKShare有请求频率限制，建议使用缓存
2. **交易时间**: 系统设计为盘后决策，盘中执行
3. **回测功能**: 当前版本不包含回测，需要另行开发
4. **实盘对接**: 需要对接券商API实现自动下单

## License

MIT License

## 联系方式

如有问题或建议，请提交Issue或Pull Request。