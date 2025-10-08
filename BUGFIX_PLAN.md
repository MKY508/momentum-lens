# 回测系统全面修复计划

## 问题诊断总结

根据用户提供的回测日志分析，发现以下关键问题：

### 1. 程序层面问题（Bug）

#### 1.1 榜首动量弱/强判定逻辑错误 ✅ 已定位
**位置**: `momentum_cli/business/reports.py:332-337`
**问题**: 
- 使用原始动量得分（0.2424）与固定阈值（0.3/0.7）比较
- 应该使用动量分位数（98.3%）或标准化后的得分
**修复方案**:
```python
# 使用动量分位数判断
momentum_percentile = top_row.get("momentum_percentile")
if momentum_percentile is not None:
    if momentum_percentile < 50:  # 低于中位数
        entries.append(("榜首动量弱", "warning"))
    elif momentum_percentile > 70:  # 高于70分位
        entries.append(("榜首动量强", "success"))
```

#### 1.2 趋势闸未实现为硬约束 ❌ 未实现
**问题**: 策略闸口只是文案提示，未影响实际持仓数和仓位
**修复方案**: 在选仓器中实现硬约束逻辑

#### 1.3 选仓器相关性过滤有缺陷 ❌ 严重
**问题**: 选出了"银行ETF(-0.4416动量) + 黄金(43.5%分位) + 港互(67.8%分位)"
**原因**: 相关性过滤只考虑去相关，不考虑动量阈值
**修复方案**: 先过滤动量分位≥60%，再在候选集中求解最小相关性

#### 1.4 观察期计数逻辑错误 ❌ 需验证
**问题**: 观察期=2/3时，低动量腿被粘住
**修复方案**: 严格实现"当期排名>K → counter++；否则counter=0"

#### 1.5 短期样本年化率夸大 ❌ 严重
**问题**: 2个月样本报"年化307.82%"
**修复方案**: 样本<180天时不显示年化和夏普

#### 1.6 组合级风控未生效 ❌ 严重
**问题**: 最大回撤-53.57%，但文档中的-15%/-20%/-30%阶梯未触发
**修复方案**: 实现组合回撤阈值的逐级降仓机制

### 2. 策略层面问题

#### 2.1 A股2021-2023横盘期动量策略天然劣势
- 高相关性风格拥挤（科技/新能源簇）
- 频繁风格反转导致"追高杀跌"

#### 2.2 仅2腿且多为同风格 → 左尾风险大
- 缺乏风格对冲（价值/红利/有色/海外）
- 需要行业簇分散

#### 2.3 缺少动量阈值过滤
- 被迫持有差腿（Top1分位<50%时仍满仓）

## 修复优先级

### P0 - 立即修复（影响结果正确性）
1. ✅ 修复选仓器相关性过滤逻辑
2. ✅ 修复短期样本年化率计算
3. ✅ 实现组合级风控硬约束
4. ✅ 修复榜首动量判定逻辑

### P1 - 高优先级（影响策略效果）
5. ✅ 实现趋势闸硬约束
6. ✅ 添加动量阈值过滤
7. ✅ 修正观察期计数逻辑

### P2 - 中优先级（改善用户体验）
8. ✅ 增强回测日志和诊断信息
9. ⏳ 添加持仓vs应选对比
10. ⏳ 添加信号时间戳和样本量

## 详细修复方案

### 修复1: 选仓器相关性过滤

**文件**: `momentum_cli/business/backtest.py`

**新增函数**:
```python
def select_assets_with_constraints(
    momentum_scores: pd.Series,
    momentum_percentiles: pd.Series,
    correlation_matrix: pd.DataFrame,
    top_n: int,
    *,
    min_percentile: float = 60.0,
    max_correlation: float = 0.85,
) -> List[str]:
    """
    在约束条件下选择资产
    
    约束:
    1. 动量分位数 >= min_percentile
    2. 两两相关性 <= max_correlation（尽力而为）
    3. 若无法满足，优先保证动量阈值，然后缩腿
    """
    # 1. 过滤动量分位数
    candidates = momentum_percentiles[momentum_percentiles >= min_percentile]
    if len(candidates) == 0:
        # 无合格候选，返回空或持现
        return []
    
    # 2. 按动量得分排序
    candidates_sorted = candidates.sort_values(ascending=False)
    
    # 3. 贪心选择：逐个添加，检查相关性
    selected = []
    for code in candidates_sorted.index:
        if len(selected) >= top_n:
            break
        
        # 检查与已选资产的相关性
        if len(selected) > 0:
            correlations = [
                correlation_matrix.loc[code, s] 
                for s in selected 
                if code in correlation_matrix.index and s in correlation_matrix.columns
            ]
            if correlations and max(correlations) > max_correlation:
                continue  # 相关性过高，跳过
        
        selected.append(code)
    
    return selected
```

### 修复2: 短期样本年化率

**文件**: `momentum_cli/business/backtest.py`

**修改位置**: `run_simple_backtest` 函数

```python
# 计算交易日数
trading_days = len(portfolio_returns)

# 只有足够长的样本才计算年化
if trading_days >= 180:
    ann_return = (1 + total_return) ** (252 / trading_days) - 1
    sharpe = (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252)
    
    print(colorize(f"年化收益: {ann_return:.2%}", ...))
    print(colorize(f"夏普比率: {sharpe:.2f}", ...))
else:
    print(colorize(f"样本期过短({trading_days}天)，不计算年化指标", "warning"))
```

### 修复3: 组合级风控

**新增类**:
```python
class PortfolioRiskManager:
    """组合风控管理器"""
    
    def __init__(self):
        self.peak_value = None
        self.drawdown_thresholds = [-0.15, -0.20, -0.30]
        self.exposure_levels = [0.40, 0.25, 0.10]  # 对应的卫星仓位
    
    def update(self, current_value: float) -> dict:
        """更新并返回风控决策"""
        if self.peak_value is None:
            self.peak_value = current_value
        else:
            self.peak_value = max(self.peak_value, current_value)
        
        drawdown = (current_value - self.peak_value) / self.peak_value
        
        # 确定当前风控等级
        risk_level = 0
        for i, threshold in enumerate(self.drawdown_thresholds):
            if drawdown <= threshold:
                risk_level = i + 1
        
        return {
            "drawdown": drawdown,
            "risk_level": risk_level,
            "max_satellite_exposure": self.exposure_levels[risk_level] if risk_level < len(self.exposure_levels) else 0.0,
            "triggered": risk_level > 0,
        }
```

### 修复4: 趋势闸硬约束

**新增函数**:
```python
def calculate_market_regime(
    market_data: pd.DataFrame,
    current_date: pd.Timestamp,
) -> dict:
    """
    计算市场状态
    
    Returns:
        {
            "above_ma200": bool,
            "atr_pct": float,
            "max_legs": int,  # 最大持仓数
            "leg_exposure": float,  # 单腿仓位
        }
    """
    if current_date not in market_data.index:
        return {"max_legs": 1, "leg_exposure": 0.15}
    
    row = market_data.loc[current_date]
    above_ma200 = bool(row.get("above_ma200", False))
    atr_pct = float(row.get("atr20_pct", 0))
    
    if above_ma200:
        if atr_pct < 4.0:
            # 强趋势市场
            return {"above_ma200": True, "atr_pct": atr_pct, "max_legs": 2, "leg_exposure": 0.20}
        else:
            # 正常市场
            return {"above_ma200": True, "atr_pct": atr_pct, "max_legs": 2, "leg_exposure": 0.18}
    else:
        # 弱势市场
        return {"above_ma200": False, "atr_pct": atr_pct, "max_legs": 1, "leg_exposure": 0.15}
```

## 测试计划

### 单元测试
1. 测试选仓器在各种边界条件下的行为
2. 测试年化率计算的样本长度判断
3. 测试组合风控的阈值触发
4. 测试趋势闸的市场状态判断

### 集成测试
1. 使用历史数据回测，验证修复后的结果
2. 对比修复前后的持仓选择
3. 验证日志输出的完整性

## 实施步骤

1. ✅ 创建修复分支
2. ⏳ 实现P0修复
3. ⏳ 运行单元测试
4. ⏳ 实现P1修复
5. ⏳ 运行集成测试
6. ⏳ 更新文档
7. ⏳ 合并到主分支

