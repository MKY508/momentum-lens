# Codex 实施指南 - ETF 动量策略系统

## 🎯 项目目标
构建一个生产级的 ETF 动量策略量化交易系统，包含完整的回测、实盘、监控和报告功能。

## 📋 优先级任务清单

### Priority 1: 立即实施 (本周完成)

#### Task 1.1: 完善配置系统
```python
# 需要创建的文件：config_manager.py
class ConfigManager:
    """
    配置管理器，支持：
    - YAML 配置加载和验证
    - 参数热更新
    - 环境变量覆盖
    - 配置版本管理
    """
    def load_config(self, config_path: str) -> Dict
    def validate_config(self, config: Dict) -> bool
    def hot_reload(self) -> None
    def get_etf_pool(self) -> List[ETFInfo]
```

#### Task 1.2: ETF 数据获取优化
```python
# 需要优化的文件：data_adapter.py
class EnhancedDataAdapter:
    """
    增强数据适配器，新增：
    - 50+ ETF 候选池管理
    - 批量数据获取
    - 智能缓存机制
    - 失败重试策略
    """
    def batch_fetch_etf_data(self, etf_codes: List[str]) -> pd.DataFrame
    def get_realtime_quotes(self, etf_codes: List[str]) -> Dict
    def cache_historical_data(self, etf_code: str, days: int) -> None
```

#### Task 1.3: 动量计算引擎
```python
# 需要创建的文件：momentum_engine.py
class MomentumEngine:
    """
    多周期动量计算引擎：
    - 20/60/120/240 日动量
    - 加权评分系统
    - 自适应参数
    """
    def calculate_momentum(self, price_data: pd.DataFrame, periods: List[int]) -> pd.DataFrame
    def weighted_momentum_score(self, momentums: Dict, weights: Dict) -> float
    def rank_by_momentum(self, etf_pool: List[str]) -> pd.DataFrame
```

### Priority 2: 核心功能 (第2周)

#### Task 2.1: 风险控制模块
```python
# 需要创建的文件：risk_manager.py
class RiskManager:
    """
    风险管理系统：
    - 止损机制（-8%硬止损）
    - 相关性矩阵计算
    - 最大回撤控制
    - 仓位动态调整
    """
    def check_stop_loss(self, positions: Dict) -> List[Alert]
    def calculate_correlation_matrix(self, returns: pd.DataFrame) -> pd.DataFrame
    def adjust_position_by_risk(self, target_positions: Dict) -> Dict
```

#### Task 2.2: 核心卫星配置器
```python
# 需要创建的文件：portfolio_allocator.py
class CoreSatelliteAllocator:
    """
    核心卫星配置：
    - 核心仓位 40-60%
    - 卫星仓位 40-60%
    - 动态再平衡
    """
    def allocate_core_positions(self, capital: float, etfs: List) -> Dict
    def allocate_satellite_positions(self, capital: float, etfs: List) -> Dict
    def rebalance_portfolio(self, current: Dict, target: Dict) -> List[Order]
```

#### Task 2.3: 六周建仓执行器
```python
# 需要创建的文件：position_builder.py
class PositionBuilder:
    """
    渐进建仓系统：
    - 6周建仓计划
    - 每周执行跟踪
    - 市场时机判断
    """
    def generate_weekly_plan(self, total_capital: float) -> Dict
    def execute_weekly_build(self, week_num: int, plan: Dict) -> List[Order]
    def track_build_progress(self) -> pd.DataFrame
```

### Priority 3: 回测系统 (第3-4周)

#### Task 3.1: Backtrader 策略封装
```python
# 需要创建的文件：backtest_strategy.py
import backtrader as bt

class ETFMomentumStrategy(bt.Strategy):
    """
    Backtrader 策略类：
    - 动量信号生成
    - 核心卫星执行
    - 风控规则应用
    """
    params = dict(
        momentum_periods=[20, 60, 120, 240],
        rebalance_freq='weekly',
        stop_loss=-0.08,
        core_ratio=0.5
    )
    
    def __init__(self):
        # 初始化指标
        pass
    
    def next(self):
        # 策略主逻辑
        pass
```

#### Task 3.2: 回测分析报告
```python
# 需要创建的文件：backtest_analyzer.py
class BacktestAnalyzer:
    """
    回测分析系统：
    - 收益率分析
    - 风险指标计算
    - HTML/PDF 报告生成
    """
    def analyze_returns(self, results) -> Dict
    def calculate_metrics(self, results) -> pd.DataFrame
    def generate_report(self, results, format='html') -> str
```

### Priority 4: 实盘交易 (第5-6周)

#### Task 4.1: EasyTrader 集成
```python
# 需要创建的文件：live_trader.py
class LiveTrader:
    """
    实盘交易执行：
    - 同花顺接口对接
    - 订单管理
    - 成交确认
    """
    def connect_broker(self, config: Dict) -> bool
    def place_order(self, order: Order) -> str
    def get_positions(self) -> Dict
    def sync_with_strategy(self) -> None
```

#### Task 4.2: 实盘监控系统
```python
# 需要创建的文件：monitor.py
class TradingMonitor:
    """
    实时监控：
    - 持仓跟踪
    - 盈亏计算
    - 异常告警
    """
    def monitor_positions(self) -> None
    def calculate_pnl(self) -> Dict
    def send_alert(self, alert: Alert) -> None
```

### Priority 5: 前端界面 (第7-8周)

#### Task 5.1: Streamlit 多页面应用
```python
# 需要优化的文件：app.py
import streamlit as st

# 页面结构
pages = {
    "仪表板": dashboard_page,
    "策略配置": strategy_config_page,
    "回测分析": backtest_page,
    "实盘监控": live_trading_page,
    "历史记录": history_page,
    "风险管理": risk_management_page
}

def main():
    st.set_page_config(page_title="ETF动量策略系统", layout="wide")
    page = st.sidebar.selectbox("选择页面", list(pages.keys()))
    pages[page]()
```

#### Task 5.2: 实时数据展示
```python
# 需要创建的文件：ui_components.py
class UIComponents:
    """
    UI 组件库：
    - K线图
    - 收益曲线
    - 持仓饼图
    - 相关性热力图
    """
    @staticmethod
    def plot_candlestick(data: pd.DataFrame) -> None
    @staticmethod
    def plot_returns_curve(returns: pd.Series) -> None
    @staticmethod
    def plot_positions_pie(positions: Dict) -> None
```

## 🏗️ 项目结构建议

```
momentum-lens/
├── config/
│   ├── config_complete.yaml      # 完整配置文件
│   ├── config_manager.py         # 配置管理器
│   └── validator.py              # 配置验证器
├── core/
│   ├── momentum_engine.py        # 动量计算引擎
│   ├── portfolio_allocator.py    # 组合配置器
│   ├── risk_manager.py          # 风险管理器
│   └── position_builder.py      # 建仓执行器
├── data/
│   ├── data_adapter.py          # 数据适配器
│   ├── cache_manager.py         # 缓存管理
│   └── database.py              # 数据库接口
├── backtest/
│   ├── backtest_strategy.py     # 回测策略
│   ├── backtest_engine.py       # 回测引擎
│   └── backtest_analyzer.py     # 回测分析
├── trading/
│   ├── live_trader.py           # 实盘交易
│   ├── order_manager.py         # 订单管理
│   └── monitor.py               # 实盘监控
├── ui/
│   ├── app.py                   # Streamlit 主应用
│   ├── pages/                   # 页面模块
│   └── components/              # UI组件
├── utils/
│   ├── logger.py                # 日志工具
│   ├── notifications.py         # 通知系统
│   └── helpers.py               # 辅助函数
├── tests/
│   ├── test_momentum.py         # 动量测试
│   ├── test_risk.py            # 风控测试
│   └── test_backtest.py        # 回测测试
├── reports/                     # 报告输出
├── logs/                        # 日志文件
└── exports/                     # 数据导出
```

## 📝 代码规范要求

### 1. 代码风格
- 使用 Black 格式化，行长度 88
- 遵循 PEP 8 规范
- 所有函数必须有 docstring
- 使用 Type Hints

### 2. 测试要求
- 单元测试覆盖率 > 80%
- 每个核心功能必须有测试
- 使用 pytest 框架
- Mock 外部依赖

### 3. 文档要求
- README.md 保持更新
- API 文档使用 Sphinx
- 每个模块有独立文档
- 包含使用示例

## 🚀 快速开始步骤

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置文件
cp config_complete.yaml config.yaml
# 编辑 config.yaml，填入实际参数

# 3. 初始化数据库
python scripts/init_db.py

# 4. 运行回测
python backtest/run_backtest.py --config config.yaml

# 5. 启动系统
streamlit run ui/app.py
```

## ⚡ 性能优化建议

1. **数据层优化**
   - 使用连接池管理数据库连接
   - Redis 缓存热点数据
   - 批量操作减少 I/O

2. **计算优化**
   - NumPy 向量化运算
   - 多进程并行计算
   - Numba JIT 加速

3. **内存优化**
   - 使用生成器处理大数据
   - 及时释放无用对象
   - 数据类型优化

## 🔧 调试技巧

1. **日志级别**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **性能分析**
   ```python
   import cProfile
   cProfile.run('main()')
   ```

3. **内存分析**
   ```python
   from memory_profiler import profile
   @profile
   def my_function():
       pass
   ```

## 📊 关键指标监控

- **策略指标**: 年化收益率、夏普比率、最大回撤
- **执行指标**: 滑点、成交率、延迟
- **系统指标**: CPU、内存、网络延迟
- **风险指标**: VaR、止损触发次数、相关性

## 🎯 里程碑检查点

- [ ] Week 1: 配置系统完成，50+ ETF 数据获取正常
- [ ] Week 2: 动量计算准确，风控机制完善
- [ ] Week 4: 5年回测完成，年化收益 >15%
- [ ] Week 6: 模拟盘稳定运行
- [ ] Week 8: UI 界面完成，响应时间 <1s
- [ ] Week 10: 导出功能完善，报告自动生成

## 💡 最佳实践

1. **版本控制**: 每个功能一个分支，完成后合并
2. **代码审查**: 重要功能需要 code review
3. **持续集成**: 使用 GitHub Actions 自动测试
4. **监控告警**: 生产环境必须有监控
5. **灾备方案**: 数据定期备份，异常恢复机制

---

*本指南将根据项目进展持续更新，请定期查看最新版本。*