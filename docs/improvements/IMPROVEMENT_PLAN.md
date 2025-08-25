# 📋 Momentum Lens 系统改进计划

## 一、核心问题修复

### 1. ✅ 动量评分公式统一性
**现状**：已确认代码中统一使用 `Score = 0.6 × r60 + 0.4 × r120`
**位置**：`backend/core/decision_engine.py:175`
```python
# FIXED weights per requirements - NOT configurable
weight_60d = 0.6
weight_120d = 0.4
```

### 2. 🔴 CHOP震荡层判定逻辑分散（需要修复）

**问题描述**：
- CHOP判定条件在多处定义，缺乏统一管理
- "三选二"规则实现不清晰

**改进方案**：
```python
# backend/core/market_analyzer.py (新建)
class MarketAnalyzer:
    def assess_chop_status(self, 
                          hs300_data: pd.DataFrame,
                          atr_20: float,
                          price: float,
                          ma200: pd.Series) -> ChopStatus:
        """
        统一的CHOP震荡层判定逻辑
        满足3选2条件即判定为震荡状态
        """
        conditions_met = 0
        reasons = []
        
        # 条件1: 近30日在MA200±3%带内天数≥10
        band_days = self._count_days_in_band(hs300_data, ma200, 0.03, 30)
        if band_days >= 10:
            conditions_met += 1
            reasons.append(f"带内天数: {band_days}/30")
        
        # 条件2: ATR20/价格≥3.5% 且 MA200的5日斜率在±0.5%
        atr_ratio = atr_20 / price
        ma200_slope = self._calculate_ma_slope(ma200, 5)
        if atr_ratio >= 0.035 and abs(ma200_slope) <= 0.005:
            conditions_met += 1
            reasons.append(f"ATR比率: {atr_ratio:.2%}, MA斜率: {ma200_slope:.3%}")
        
        # 条件3: 双窗分散度小
        dispersion = self._calculate_dispersion(hs300_data)
        if dispersion['top1_top3'] < 0.03 and dispersion['top1_top5'] < 0.08:
            conditions_met += 1
            reasons.append(f"分散度: T1-T3={dispersion['top1_top3']:.2%}")
        
        return ChopStatus(
            is_chop=conditions_met >= 2,
            conditions_met=conditions_met,
            reasons=reasons,
            timestamp=datetime.now()
        )
```

### 3. 🔴 年线闸控制逻辑（需要增强）

**问题**：缺少"连续五日"确认逻辑

**改进方案**：
```python
# backend/core/yearline_monitor.py
class YearlineMonitor:
    def __init__(self):
        self.confirmation_days = 5
        self.above_yearline_count = 0
        self.unlock_status = False
        self.unlock_date = None
        
    def check_yearline_unlock(self, hs300_price: float, ma200: float) -> bool:
        """
        检查年线解锁条件：连续5日收盘在MA200上，且最后一日≥+1%
        """
        if hs300_price > ma200:
            self.above_yearline_count += 1
            
            # 检查连续5日条件
            if self.above_yearline_count >= self.confirmation_days:
                # 检查最后一日涨幅
                if (hs300_price - ma200) / ma200 >= 0.01:
                    self.unlock_status = True
                    self.unlock_date = datetime.now()
                    logger.info(f"年线解锁确认: 连续{self.above_yearline_count}日站上MA200")
                    return True
        else:
            # 跌破年线，重置计数
            self.above_yearline_count = 0
            
        return False
    
    def check_yearline_fallback(self, hs300_price: float, ma200: float) -> bool:
        """
        检查年线回落：解锁后3日内收盘≤-1%重新跌回MA200
        """
        if not self.unlock_status or not self.unlock_date:
            return False
            
        days_since_unlock = (datetime.now() - self.unlock_date).days
        
        if days_since_unlock <= 3:
            if (hs300_price - ma200) / ma200 <= -0.01:
                logger.warning(f"年线回落警告: 解锁后{days_since_unlock}日跌回MA200")
                self.unlock_status = False
                return True
                
        return False
```

### 4. 🔴 数据源容错机制（需要增强）

**改进方案**：
```python
# backend/core/data_fetcher_enhanced.py
class EnhancedDataFetcher:
    def __init__(self):
        self.primary_source = EastMoneyAPI()
        self.backup_sources = [
            SinaFinanceAPI(),
            YahooFinanceAPI(),
            AkShareAPI()  # 新增开源数据源
        ]
        self.cache = RedisCache()
        self.retry_config = {
            'max_retries': 3,
            'backoff_factor': 2,
            'timeout': 10
        }
        
    async def fetch_with_fallback(self, 
                                  symbol: str,
                                  data_type: str) -> pd.DataFrame:
        """
        带容错的数据获取
        """
        # 1. 尝试从缓存获取
        cached_data = await self.cache.get(f"{symbol}:{data_type}")
        if cached_data and self._is_data_fresh(cached_data):
            return cached_data
            
        # 2. 尝试主数据源
        try:
            data = await self._fetch_with_retry(
                self.primary_source, 
                symbol, 
                data_type
            )
            if self._validate_data(data):
                await self.cache.set(f"{symbol}:{data_type}", data)
                return data
        except Exception as e:
            logger.error(f"主数据源失败: {e}")
            
        # 3. 尝试备用数据源
        for backup_source in self.backup_sources:
            try:
                data = await self._fetch_with_retry(
                    backup_source,
                    symbol,
                    data_type
                )
                if self._validate_data(data):
                    logger.info(f"使用备用数据源: {backup_source.__class__.__name__}")
                    await self.cache.set(f"{symbol}:{data_type}", data)
                    return data
            except Exception as e:
                logger.warning(f"备用数据源 {backup_source.__class__.__name__} 失败: {e}")
                continue
                
        # 4. 所有源失败，返回缓存的过期数据（如果有）
        if cached_data:
            logger.warning("使用过期缓存数据")
            return cached_data
            
        raise DataFetchError(f"无法获取 {symbol} 的 {data_type} 数据")
```

## 二、功能增强

### 1. 🚀 回测系统实现

```python
# backend/backtest/backtester.py
class MomentumLensBacktester:
    """
    策略回测引擎
    """
    def __init__(self, 
                 start_date: datetime,
                 end_date: datetime,
                 initial_capital: float = 1000000):
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.decision_engine = DecisionEngine()
        self.portfolio_manager = PortfolioManager()
        self.risk_manager = RiskManager()
        
    def run_backtest(self) -> BacktestResult:
        """
        执行回测
        """
        results = []
        portfolio_value = self.initial_capital
        
        for date in pd.date_range(self.start_date, self.end_date, freq='D'):
            # 1. 获取历史数据
            market_data = self._get_historical_data(date)
            
            # 2. 生成交易信号
            signals = self.decision_engine.generate_signals(
                market_data,
                date
            )
            
            # 3. 风险检查
            approved_signals = self.risk_manager.check_signals(
                signals,
                portfolio_value
            )
            
            # 4. 执行交易
            trades = self.portfolio_manager.execute_trades(
                approved_signals,
                market_data
            )
            
            # 5. 更新组合价值
            portfolio_value = self._calculate_portfolio_value(
                date,
                market_data
            )
            
            # 6. 记录结果
            results.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'trades': trades,
                'positions': self.portfolio_manager.get_positions()
            })
            
        return self._analyze_results(results)
    
    def _analyze_results(self, results: List[Dict]) -> BacktestResult:
        """
        分析回测结果
        """
        df = pd.DataFrame(results)
        
        # 计算关键指标
        total_return = (df.iloc[-1]['portfolio_value'] - self.initial_capital) / self.initial_capital
        annual_return = (1 + total_return) ** (252 / len(df)) - 1
        sharpe_ratio = self._calculate_sharpe_ratio(df)
        max_drawdown = self._calculate_max_drawdown(df)
        win_rate = self._calculate_win_rate(df)
        
        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            trades=df['trades'].sum(),
            daily_values=df[['date', 'portfolio_value']]
        )
```

### 2. 🧪 单元测试覆盖

```python
# tests/test_decision_engine.py
import pytest
from backend.core.decision_engine import DecisionEngine

class TestDecisionEngine:
    
    @pytest.fixture
    def engine(self):
        return DecisionEngine()
    
    def test_momentum_score_calculation(self, engine):
        """测试动量评分计算"""
        # 测试正常情况
        score = engine.calculate_momentum_score(10.0, 20.0)
        assert score == pytest.approx(0.6 * 10 + 0.4 * 20, rel=1e-5)
        
        # 测试负收益
        score = engine.calculate_momentum_score(-5.0, -10.0)
        assert score == pytest.approx(0.6 * (-5) + 0.4 * (-10), rel=1e-5)
        
    def test_chop_assessment(self, engine):
        """测试CHOP震荡判断"""
        # 模拟满足2个条件的情况
        market_data = create_mock_market_data(
            band_days=11,  # 满足条件1
            atr_ratio=0.04,  # 满足条件2
            dispersion={'top1_top3': 0.05}  # 不满足条件3
        )
        
        status = engine.assess_market_regime(market_data)
        assert status.is_chop == True
        assert status.conditions_met == 2
        
    def test_yearline_unlock(self, engine):
        """测试年线解锁逻辑"""
        # 模拟连续5日站上年线
        for i in range(5):
            engine.update_market_data(
                hs300_price=3100 + i * 10,
                ma200=3000
            )
        
        assert engine.yearline_unlocked == True
        
        # 测试3日内回落
        engine.update_market_data(
            hs300_price=2970,  # 跌破1%
            ma200=3000
        )
        
        assert engine.second_leg_allowed == False
```

### 3. 📊 前端增强

```typescript
// frontend/src/components/Dashboard/MarketEnvironmentPanel.tsx
import React from 'react';
import { Box, Card, Grid, Typography, Chip } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, Tooltip } from 'recharts';

interface MarketEnvironmentPanelProps {
  hs300Data: any[];
  ma200Data: any[];
  chopStatus: ChopStatus;
  yearlineStatus: YearlineStatus;
}

export const MarketEnvironmentPanel: React.FC<MarketEnvironmentPanelProps> = ({
  hs300Data,
  ma200Data,
  chopStatus,
  yearlineStatus
}) => {
  return (
    <Card>
      <Box p={3}>
        <Typography variant="h6" gutterBottom>
          市场环境实时监控
        </Typography>
        
        <Grid container spacing={3}>
          {/* 年线状态指示器 */}
          <Grid item xs={12} md={4}>
            <Box>
              <Typography variant="subtitle2" color="textSecondary">
                年线状态
              </Typography>
              <Chip
                label={yearlineStatus.unlocked ? '已解锁' : '未解锁'}
                color={yearlineStatus.unlocked ? 'success' : 'default'}
                icon={yearlineStatus.daysAbove ? 
                  <span>{yearlineStatus.daysAbove}/5</span> : undefined
                }
              />
              {yearlineStatus.fallbackWarning && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  警告：可能回落至年线下方
                </Alert>
              )}
            </Box>
          </Grid>
          
          {/* CHOP震荡指标 */}
          <Grid item xs={12} md={4}>
            <Box>
              <Typography variant="subtitle2" color="textSecondary">
                CHOP震荡状态
              </Typography>
              <Box display="flex" gap={1} mt={1}>
                {chopStatus.conditions.map((condition, index) => (
                  <Chip
                    key={index}
                    label={condition.name}
                    size="small"
                    color={condition.met ? 'success' : 'default'}
                    variant={condition.met ? 'filled' : 'outlined'}
                  />
                ))}
              </Box>
              <Typography variant="caption" color="textSecondary" mt={1}>
                {chopStatus.conditionsMet}/3 条件满足
                {chopStatus.isChop && ' - 震荡市'}
              </Typography>
            </Box>
          </Grid>
          
          {/* HS300 vs MA200 图表 */}
          <Grid item xs={12} md={4}>
            <LineChart width={300} height={150} data={hs300Data}>
              <XAxis dataKey="date" hide />
              <YAxis hide />
              <Tooltip />
              <Line 
                type="monotone" 
                dataKey="hs300" 
                stroke="#1976d2" 
                strokeWidth={2}
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="ma200" 
                stroke="#ff9800" 
                strokeWidth={2}
                strokeDasharray="5 5"
                dot={false}
              />
            </LineChart>
          </Grid>
        </Grid>
      </Box>
    </Card>
  );
};
```

## 三、实施计划

### 第一阶段：核心逻辑修复（1周）
- [ ] 统一CHOP判定逻辑
- [ ] 实现年线解锁确认机制
- [ ] 增强数据源容错
- [ ] 添加幂等性控制

### 第二阶段：测试框架完善（1周）
- [ ] 实现单元测试（目标覆盖率>90%）
- [ ] 集成测试框架
- [ ] 性能测试基准

### 第三阶段：回测系统（2周）
- [ ] 实现回测引擎
- [ ] 历史数据准备
- [ ] 回测报告生成
- [ ] 参数优化工具

### 第四阶段：前端优化（1周）
- [ ] 市场环境实时监控面板
- [ ] 年线/CHOP状态可视化
- [ ] 交易信号详情展示
- [ ] 回测结果展示

## 四、监控指标

### 系统健康度
- 数据源可用性 > 99.5%
- API响应时间 < 100ms (P95)
- 决策计算时间 < 500ms
- WebSocket延迟 < 50ms

### 策略效果
- 年化收益率
- 最大回撤
- 夏普比率
- 胜率
- 平均持有期

### 风险控制
- 止损触发率
- 相关性违规次数
- 仓位偏差告警
- 数据异常检测

## 五、代码规范

### Python (PEP 8)
```python
# 使用 black 格式化
black backend/ --line-length 88

# 使用 ruff 检查
ruff check backend/

# 类型注解
from typing import Optional, List, Dict
def calculate_score(returns: List[float]) -> Optional[float]:
    ...
```

### TypeScript (ESLint)
```typescript
// 使用 prettier 格式化
npm run format

// 使用 ESLint 检查
npm run lint

// 严格类型
interface TradingSignal {
  code: string;
  score: number;
  timestamp: Date;
}
```

## 六、文档完善

### API文档
- 使用 FastAPI 自动生成 OpenAPI 文档
- 添加请求/响应示例
- 错误码说明

### 开发文档
- 架构设计文档
- 数据流程图
- 部署指南
- 故障排查手册

### 用户文档
- 快速开始指南
- 策略说明
- 参数配置指南
- FAQ

---

## 更新日志

- 2024-12-XX: 初始版本，识别核心问题
- 2024-12-XX: 添加详细改进方案
- 2024-12-XX: 制定实施计划

## 负责人

- 架构设计：[@architect]
- 后端开发：[@backend-dev]
- 前端开发：[@frontend-dev]
- 测试：[@qa-engineer]
- 文档：[@tech-writer]