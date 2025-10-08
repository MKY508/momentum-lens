# Momentum Lens 系统性问题修复清单

## 🚨 紧急问题（P0 - 立即修复）

### 1. 导入错误修复
- [x] **问题**: `unified_strategy_menu.py` 导入 `colorize` 失败
- [x] **原因**: `colorize` 在 `utils.colors` 而非 `ui` 模块
- [x] **修复**: 已修改导入路径
- [ ] **验证**: 测试CLI启动是否正常

### 2. 回测结果不一致问题
- [ ] **问题**: 简易回测结果与推荐配置结果差异巨大
  - 推荐配置: 年化11.22%, 夏普0.69, 回撤-24.34%
  - 简易回测: 年化2.79%, 夏普0.23, 回撤-46.53%
- [ ] **可能原因**:
  - 数据源不同（ETF池不同）
  - 回测逻辑不同（观察期实现有bug）
  - 时间区间不同
  - 参数传递错误
- [ ] **需要调查**:
  - 对比 `batch_backtest.py` 和 `business/backtest.py` 的逻辑差异
  - 检查观察期实现是否正确
  - 验证ETF池是否一致
  - 检查时间区间是否对齐

### 3. 观察期逻辑验证
- [ ] **问题**: 观察期=1 vs 观察期=2 的实现是否正确
- [ ] **需要验证**:
  - `batch_backtest.py` 中的观察期逻辑
  - `business/backtest.py` 中的观察期逻辑
  - `unified_strategy_menu.py` 中的观察期逻辑
  - 三者是否一致
- [ ] **测试用例**: 手动构造简单数据验证观察期行为

---

## 🔴 高优先级问题（P1 - 本周修复）

### 4. ETF池配置统一
- [ ] **问题**: 不同模块使用不同的ETF池
- [ ] **需要统一**:
  - `batch_backtest.py` 的 ALL_CODES
  - `unified_strategy_menu.py` 的 ALL_CODES
  - 券池预设中的ETF列表
  - 确保所有回测使用相同的ETF池
- [ ] **建议**: 创建统一的ETF池配置文件

### 5. 回测逻辑统一
- [ ] **问题**: 多个回测实现，逻辑可能不一致
- [ ] **需要统一**:
  - `batch_backtest.py` 的 `run_single_backtest()`
  - `business/backtest.py` 的 `run_simple_backtest()`
  - `unified_strategy_menu.py` 的 `_execute_backtest()`
- [ ] **建议**: 提取公共回测逻辑到 `business/backtest_core.py`

### 6. 参数传递验证
- [ ] **问题**: 参数在不同层级传递时可能丢失或转换错误
- [ ] **需要检查**:
  - 观察期参数传递链路
  - 相关性阈值参数传递链路
  - Top_N参数传递链路
  - 调仓频率参数传递链路
- [ ] **建议**: 使用dataclass统一参数传递

### 7. 数据对齐问题
- [ ] **问题**: 价格数据、动量数据、调仓日期可能不对齐
- [ ] **需要检查**:
  - `close_df` 和 `momentum_df` 的索引对齐
  - 调仓日期生成逻辑（月末 vs 周五）
  - 数据缺失处理逻辑
- [ ] **建议**: 添加数据对齐验证函数

### 8. 性能指标计算验证
- [ ] **问题**: 夏普比率、最大回撤计算可能有误
- [ ] **需要验证**:
  - 年化收益计算公式
  - 夏普比率计算公式（无风险利率假设）
  - 最大回撤计算逻辑
  - 换手率计算逻辑
- [ ] **建议**: 与标准库（如empyrical）对比验证

---

## 🟡 中优先级问题（P2 - 本月修复）

### 9. 核心-卫星回测实现
- [ ] **问题**: 核心-卫星回测框架已建立但未实现
- [ ] **需要实现**:
  - 核心仓（60%）+ 卫星仓（40%）配置
  - 再平衡逻辑（偏离>5%时触发）
  - 止损逻辑（单只ETF回撤>15%）
  - 防御逻辑（大盘MA200以下降低卫星仓）
- [ ] **参考**: `business/backtest.py` 中的 `core_satellite_portfolio_returns()`

### 10. 宏观长波策略对齐
- [ ] **问题**: 简单分析中的"宏观长波"策略参数未对齐到twelve-minus-one
- [ ] **需要检查**:
  - 当前"宏观长波"策略的参数
  - 是否与twelve-minus-one一致
  - 如果不一致，是否需要统一
- [ ] **建议**: 在分析预设中明确标注推荐配置

### 11. 实验性策略集成测试
- [ ] **问题**: 8个实验性预设未经过完整测试
- [ ] **需要测试**:
  - 每个预设是否能正常运行
  - 参数是否合理
  - 结果是否符合预期
- [ ] **建议**: 创建自动化测试脚本

### 12. 基准指数数据可用性
- [ ] **问题**: 基准指数ETF可能缺失数据
- [ ] **需要检查**:
  - 510300.XSHG (沪深300) 数据完整性
  - 510500.XSHG (中证500) 数据完整性
  - 512260.XSHG (中证1000) 数据完整性
  - 159949.XSHE (创业板50) 数据完整性
- [ ] **建议**: 添加数据缺失时的降级处理

### 13. 调仓记录持久化
- [ ] **问题**: 调仓记录未持久化到 `trade_log.csv`
- [ ] **需要实现**:
  - 每次调仓自动记录到CSV
  - 记录格式：日期、操作、代码、权重
  - 支持查看历史记录
- [ ] **参考**: 现有的 `trade_log.csv` 格式

---

## 🟢 低优先级问题（P3 - 未来优化）

### 14. 用户体验优化
- [ ] **进度条**: 长时间回测时显示进度
- [ ] **结果缓存**: 避免重复计算
- [ ] **快捷键**: 支持键盘快捷操作
- [ ] **颜色主题**: 支持自定义配色

### 15. 错误处理增强
- [ ] **数据缺失**: 友好的错误提示
- [ ] **参数验证**: 输入参数合法性检查
- [ ] **异常恢复**: 回测失败时的降级处理
- [ ] **日志记录**: 详细的调试日志

### 16. 文档完善
- [ ] **API文档**: 核心函数的docstring
- [ ] **示例代码**: 常见使用场景的示例
- [ ] **FAQ**: 常见问题解答
- [ ] **视频教程**: 录制操作演示视频

### 17. 测试覆盖
- [ ] **单元测试**: 核心函数的单元测试
- [ ] **集成测试**: 端到端的集成测试
- [ ] **回归测试**: 防止已修复问题再次出现
- [ ] **性能测试**: 回测速度优化

### 18. 高级功能
- [ ] **参数优化**: 自动寻找最优参数组合
- [ ] **蒙特卡洛模拟**: 评估策略稳健性
- [ ] **情景分析**: 不同市场环境下的表现
- [ ] **归因分析**: 收益来源分解

---

## 📋 问题诊断流程

### 回测结果不一致的诊断步骤

#### Step 1: 数据源对比
```python
# 检查ETF池
print("batch_backtest.py ETF池:", ALL_CODES)
print("unified_strategy_menu.py ETF池:", ALL_CODES)
print("券池预设ETF池:", core_codes + satellite_codes)

# 检查时间区间
print("batch_backtest.py 时间区间:", TRAIN_PERIOD, TEST_PERIOD)
print("简易回测时间区间:", start_date, end_date)
```

#### Step 2: 参数对比
```python
# 检查关键参数
print("策略:", strategy_key)
print("调仓频率:", frequency)
print("持仓数量:", top_n)
print("观察期:", observation_period)
print("相关性阈值:", correlation_threshold)
```

#### Step 3: 逻辑对比
```python
# 对比观察期实现
# batch_backtest.py 的实现
for code in current_set:
    if code in top_set:
        observation_counter[code] = 0
        next_hold.append(code)
    else:
        observation_counter[code] = observation_counter.get(code, 0) + 1
        if observation_period <= 0 or observation_counter[code] >= observation_period:
            pass  # 卖出
        else:
            next_hold.append(code)  # 继续持有

# business/backtest.py 的实现
# 需要检查是否一致
```

#### Step 4: 结果对比
```python
# 运行相同参数的回测
result1 = batch_backtest.run_single_backtest(...)
result2 = business.backtest.run_simple_backtest(...)
result3 = unified_strategy_menu._execute_backtest(...)

# 对比关键指标
print("年化收益:", result1['annualized_return'], result2['annualized_return'], result3['annualized_return'])
print("夏普比率:", result1['sharpe_ratio'], result2['sharpe_ratio'], result3['sharpe_ratio'])
print("最大回撤:", result1['max_drawdown'], result2['max_drawdown'], result3['max_drawdown'])
```

---

## 🔧 修复优先级排序

### 本次对话必须完成（P0）
1. ✅ 导入错误修复
2. ⏳ 回测结果不一致问题诊断
3. ⏳ 观察期逻辑验证
4. ⏳ ETF池配置统一

### 本周完成（P1）
5. 回测逻辑统一
6. 参数传递验证
7. 数据对齐问题
8. 性能指标计算验证

### 本月完成（P2）
9. 核心-卫星回测实现
10. 宏观长波策略对齐
11. 实验性策略集成测试
12. 基准指数数据可用性
13. 调仓记录持久化

### 未来优化（P3）
14-18. 用户体验、错误处理、文档、测试、高级功能

---

## 📊 当前状态总结

### 已完成 ✅
- 统一策略菜单框架
- 8个实验性预设
- 完整文档体系
- 导入错误修复

### 进行中 ⏳
- 回测结果不一致问题诊断
- 观察期逻辑验证

### 待开始 ⏸️
- ETF池配置统一
- 回测逻辑统一
- 核心-卫星回测实现

---

**下一步行动**: 立即开始诊断回测结果不一致问题，找出根本原因并修复。

