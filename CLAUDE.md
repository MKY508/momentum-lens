# CLAUDE.md - Momentum Lens 架构文档

## 项目概述

Momentum Lens 是一个智能化的ETF动量交易系统，专注于中国市场的量化投资策略。系统通过动量评分、相关性分析和风险管理，实现半自动化的投资决策支持。

### 核心理念
- **双腿策略**：Core-Satellite结构，核心持仓60%，卫星动量40%
- **动量驱动**：基于60/120日涨幅的动量评分系统
- **风险控制**：多层风险管理，包括止损、缓冲区、最短持有期
- **一键决策**：简化操作流程，周二定期执行

### 目标用户
- 量化投资爱好者
- 追求系统化交易的个人投资者
- 需要决策辅助的ETF投资者

## 系统架构设计

### 技术栈选择

```
前端层：React 18 + TypeScript + TradingView Charts
后端层：Python 3.11 + FastAPI + WebSocket
数据层：PostgreSQL + TimescaleDB + Redis
基础设施：Docker + Nginx + GitHub Actions
```

### 架构图

```
┌─────────────────────────────────────────┐
│          React Dashboard                │
│   (决策台/Core/Satellite/日志/参数)      │
└────────────────┬────────────────────────┘
                 │ REST API + WebSocket
┌────────────────▼────────────────────────┐
│           FastAPI Backend               │
│  ┌──────────┬──────────┬─────────────┐ │
│  │决策引擎   │组合管理   │风险管理      │ │
│  └──────────┴──────────┴─────────────┘ │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│     PostgreSQL + Redis + Market API     │
└─────────────────────────────────────────┘
```

## 核心模块设计

### 1. 数据采集模块 (DataFetcher)

**职责**：获取市场数据和计算技术指标

```python
class DataFetcher:
    - fetch_hs300_data()      # 获取沪深300数据
    - fetch_etf_prices()       # 获取ETF价格
    - calculate_ma200()        # 计算200日均线
    - calculate_atr()          # 计算ATR(20)
    - get_iopv_premium()       # 获取IOPV溢价
```

**数据源**：
- 主数据源：东方财富/新浪财经API
- 备用数据源：雅虎财经
- 实时数据：WebSocket推送

### 2. 决策引擎 (DecisionEngine)

**职责**：生成交易信号和建议

```python
class DecisionEngine:
    - assess_market_regime()   # 判断市场环境
    - calculate_momentum_score() # 计算动量分数
    - check_correlation()      # 检查相关性(ρ≤0.8)
    - generate_signals()       # 生成交易信号
    - check_qualifications()  # 检查资格条件
```

**核心算法**：
- 动量评分：Score = 0.6 × r60 + 0.4 × r120 （r60为60日涨幅，r120为120日涨幅）
- CHOP判断：3选2条件（30日带内天数≥10、ATR20/价≥3.5%、分散度小）
- 相关性矩阵：90日对数收益率相关系数（ρ≤0.8为合格）

### 3. 组合管理模块 (PortfolioManager)

**职责**：管理持仓和再平衡

```python
class PortfolioManager:
    - track_positions()        # 跟踪持仓
    - calculate_weights()      # 计算权重
    - rebalance_core()        # Core再平衡
    - rotate_satellite()      # Satellite轮动
    - generate_orders()       # 生成订单
```

**核心持仓 (60%目标)**：
- 510300/159919: 沪深300 (20%)
- 510880: 上证红利 (15%)
- 511990: 货币ETF (10%)
- 518880: 黄金ETF (10%)
- 513500: 标普500 (5%, 溢价≤2%)

**卫星持仓 (40%目标)**：
- 动态选择2只ETF
- 每只5-10%权重
- 月度轮动检查

### 4. 风险管理模块 (RiskManager)

**职责**：监控和管理风险

```python
class RiskManager:
    - check_stop_loss()       # 止损检查(-10%~-15%)
    - check_min_holding()     # 最短持有期(2-4周)
    - check_buffer_zone()     # 缓冲区检查(2-4%)
    - monitor_drawdown()      # 回撤监控
    - generate_alerts()       # 生成预警
```

### 5. 订单管理模块 (OrderManager)

**职责**：生成和管理交易订单

```python
class OrderManager:
    - create_limit_order()    # 创建限价单
    - calculate_iopv_band()   # 计算IOPV区间
    - schedule_execution()    # 安排执行时间
    - track_execution()       # 跟踪执行状态
```

## 数据模型

### ETF信息表 (etf_info)
```sql
CREATE TABLE etf_info (
    code VARCHAR(6) PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(20),  -- Core/Satellite
    style VARCHAR(20),     -- 成长/价值/周期/防御
    tracking_index VARCHAR(50),
    aum DECIMAL(20,2),
    expense_ratio DECIMAL(5,4)
);
```

### 价格历史表 (price_history)
```sql
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    code VARCHAR(6),
    date DATE,
    open DECIMAL(10,4),
    high DECIMAL(10,4),
    low DECIMAL(10,4),
    close DECIMAL(10,4),
    volume BIGINT,
    iopv DECIMAL(10,4),
    premium_discount DECIMAL(5,4),
    INDEX idx_code_date (code, date)
);
```

### 持仓表 (holdings)
```sql
CREATE TABLE holdings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    code VARCHAR(6),
    entry_price DECIMAL(10,4),
    entry_date DATE,
    shares INTEGER,
    current_weight DECIMAL(5,4),
    target_weight DECIMAL(5,4),
    stop_loss_price DECIMAL(10,4)
);
```

### 交易记录表 (transactions)
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    code VARCHAR(6),
    action VARCHAR(10),  -- BUY/SELL
    price DECIMAL(10,4),
    shares INTEGER,
    amount DECIMAL(20,2),
    fee DECIMAL(10,2),
    executed_at TIMESTAMP,
    order_type VARCHAR(20),  -- LIMIT/MARKET
    execution_window VARCHAR(10)  -- 10:30/14:00
);
```

## API设计

### RESTful端点

#### 市场数据
```
GET /api/market/overview         # 市场概览
GET /api/market/etf/{code}      # ETF详情
GET /api/market/indicators      # 技术指标
```

#### 决策相关
```
POST /api/decisions/calculate   # 计算决策
GET /api/decisions/current      # 当前建议
GET /api/decisions/history      # 历史决策
```

#### 组合管理
```
GET /api/portfolio/holdings     # 当前持仓
POST /api/portfolio/update      # 更新持仓
GET /api/portfolio/performance  # 绩效分析
```

#### 订单管理
```
POST /api/orders/create         # 创建订单
GET /api/orders/pending         # 待执行订单
POST /api/orders/execute        # 执行订单
```

### WebSocket通道

```
/ws/prices          # 实时价格推送
/ws/portfolio       # 组合变动推送
/ws/alerts          # 预警信息推送
```

## 前端组件设计

### A. 决策台 (DecisionDashboard)

```jsx
<DecisionDashboard>
  <EnvironmentBar>        // 市场环境指标
    <YearlineChip />      // 年线状态
    <ATRChip />           // 波动率
    <CHOPChip />          // 震荡指标
  </EnvironmentBar>
  
  <ParameterBar>          // 参数选择
    <PresetSelector />    // 进攻/均衡/固定
    <CustomParams />      // 自定义参数
  </ParameterBar>
  
  <DecisionCard>          // 决策卡片
    <LegRecommendation /> // 推荐标的
    <PriceBand />         // 限价区间
    <QualificationLights /> // 资格灯
    <ActionButtons />     // 执行按钮
  </DecisionCard>
</DecisionDashboard>
```

### B. Core模块 (CoreModule)

```jsx
<CoreModule>
  <HoldingsTable />       // 持仓表格
  <HS300Chart />          // 沪深300图表
  <RebalancingMeter />    // 再平衡仪表
  <DCAScheduler />        // 定投计划
</CoreModule>
```

### C. Satellite模块 (SatelliteModule)

```jsx
<SatelliteModule>
  <MomentumRankings />    // 动量排行
  <CorrelationHeatmap />  // 相关性热图
  <QualificationStatus /> // 资格状态
  <RotationControls />    // 轮动控制
</SatelliteModule>
```

### D. 日志/KPI模块 (LogsModule)

```jsx
<LogsModule>
  <TradeLog />            // 交易日志
  <PerformanceMetrics />  // 绩效指标
  <RiskMetrics />         // 风险指标
  <SystemAlerts />        // 系统预警
</LogsModule>
```

## 实施计划

### 第一阶段：基础设施 (第1-2周)

**目标**：搭建开发环境和基础架构

任务清单：
- [ ] 初始化项目结构
- [ ] 配置数据库 (PostgreSQL + Redis)
- [ ] 搭建FastAPI后端框架
- [ ] 实现基础数据获取接口
- [ ] 配置Docker环境

### 第二阶段：核心引擎 (第3-4周)

**目标**：实现决策和计算引擎

任务清单：
- [ ] 实现动量评分算法
- [ ] 实现相关性计算
- [ ] 实现市场环境判断
- [ ] 实现资格检查逻辑
- [ ] 集成技术指标计算

### 第三阶段：前端开发 (第5-6周)

**目标**：构建用户界面

任务清单：
- [ ] 搭建React项目框架
- [ ] 实现决策台组件
- [ ] 实现Core/Satellite模块
- [ ] 集成图表库
- [ ] 实现实时数据更新

### 第四阶段：集成优化 (第7-8周)

**目标**：系统集成和优化

任务清单：
- [ ] 前后端集成测试
- [ ] 性能优化
- [ ] 部署配置
- [ ] 用户测试
- [ ] 文档完善

## 关键决策和权衡

### 技术选型理由

1. **FastAPI vs Django**
   - 选择FastAPI：原生异步支持，更适合实时数据处理
   - WebSocket支持更好
   - 性能更优，响应时间<100ms

2. **React vs Vue**
   - 选择React：金融组件生态更丰富
   - TypeScript支持更成熟
   - TradingView集成更容易

3. **PostgreSQL + TimescaleDB**
   - 时序数据优化
   - 支持复杂查询
   - 成熟稳定

4. **Redis缓存**
   - 亚毫秒级响应
   - 支持发布订阅
   - 减少数据库压力

### 设计原则

1. **模块化设计**
   - 高内聚低耦合
   - 独立部署能力
   - 清晰的接口定义

2. **容错性**
   - 优雅降级
   - 断路器模式
   - 重试机制

3. **可观测性**
   - 结构化日志
   - 指标监控
   - 分布式追踪

## 测试策略

### 单元测试
- 覆盖率目标: >90%
- 重点: 计算逻辑、决策算法

### 集成测试
- API端点测试
- 数据流测试
- WebSocket连接测试

### 端到端测试
- 用户工作流测试
- 关键路径测试
- 异常场景测试

### 性能测试
- 响应时间: <100ms
- 并发用户: 100+
- 数据处理: 1000+ ETF

## 部署和运维

### 容器化
```dockerfile
# 后端Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

### 环境配置
```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
  
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
  
  postgres:
    image: timescale/timescaledb:latest-pg15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
```

### 监控告警
- Prometheus + Grafana 监控
- ELK Stack 日志分析
- Sentry 错误追踪

## 安全考虑

1. **API安全**
   - JWT认证
   - Rate Limiting
   - CORS配置

2. **数据安全**
   - 敏感数据加密
   - SQL注入防护
   - XSS防护

3. **交易安全**
   - 订单确认机制
   - 限价保护
   - 异常检测

## 维护和扩展

### 版本管理
- 语义化版本 (SemVer)
- Git Flow工作流
- 自动化发布

### 扩展计划
- 支持更多ETF品种
- 加入期权策略
- 多账户管理
- 回测系统

## 附录

### ETF代码清单

#### Core池 (60%)
- 510300/159919: 沪深300
- 510880: 上证红利
- 511990: 华宝添益
- 518880: 华安黄金
- 513500: 标普500

#### Satellite池 (40%)
**成长线（每期只选1支）**：
- 588000: 科创50
- 512760: 半导体
- 512720: 计算机
- 516010/159869: 游戏动漫（二选一）

**电新链（三选一）**：
- 516160: 新能源
- 515790: 光伏
- 515030: 新能源车

**其他行业**：
- 512400: 有色金属
- 512800: 银行
- 512000: 券商
- 512170: 医疗

### 预警阈值（固化配置）

#### 市场环境判断
1. **年线解锁**：HS300连续5日收盘在MA200上，且最后一日≥+1%
2. **年线回落**：补完第二腿后3日内，收盘≤-1%重新跌回MA200
3. **震荡层(CHOP)开启**（满足3选2）：
   - a) 近30日在MA200±3%带内天数≥10
   - b) ATR20/价≥3.5%且MA200的5日斜率在±0.5%
   - c) 双窗分散度小：Top1-Top3<3%且Top1-Top5<8%

#### 交易限制
- **QDII(513500)**：溢价≤2%才买，≥3%暂停
- **止损档位**：
  - 默认：-12%
  - 强趋势：-10%
  - 震荡：-15%
  - 破200日线：减半持仓

### 默认参数设置（均衡档位）

| 参数 | 进攻模式 | 均衡模式（默认） | 保守模式 |
|------|---------|-----------------|---------|
| 止损 | -10% | -12% | -15% |
| 缓冲 | 2% | 3% | 4% |
| 最短持有 | 2周 | 2周 | 4周 |
| 带宽 | ±7pp | ±5pp | ±3pp |
| 腿数上限 | 2 | 2 | 1 |

### 执行节奏

- **周日晚**: 生成下周交易计划（自检清单）
- **周二 10:30**: 第一腿执行（Score Top1，5%，限价IOPV×[0.999,1.001]）
- **周二 14:00**: 第二腿执行（ρ≤0.8的候选，5%，同样限价带）
- **下周同窗口**: 复核满足则各从5%→10%
- **月末**: 检查轮动条件
- **日常**: 监控预警信号

### 调整触发条件

只有出现以下信号才调整参数或动作：

1. **进入CHOP** → 缓冲4%、最短4周、止损-15%、腿数1
2. **解锁后3日内年线回落** → 第二腿清零，回到1条腿
3. **单腿跌破自身200日线** → 该腿减半（继续观察）
4. **月末单位换手收益<0** → 次月卫星降10pp（如40%→30%）
5. **两腿相关性ρ>0.8** → 第二腿换成风格更"远"的候选
6. **513500溢价≥3%** → 暂停；≤2%才恢复

### 自检清单（周日执行）

- [ ] HS300：收盘vs MA200（在上/在下）、ATR20/价、30日带内天数
- [ ] Sat候选：60/120日涨幅与Score=0.6×r60+0.4×r120排名
- [ ] 若允许两腿：Top2相对Top1的ρ≤0.8
- [ ] 本周参数：缓冲3%、最短持有2周、带宽±5pp
- [ ] Core DCA：按6周计划买入1/6，513500溢价阈值已设

---

*本文档将随项目进展持续更新*
*最后更新: 2024-08-24*