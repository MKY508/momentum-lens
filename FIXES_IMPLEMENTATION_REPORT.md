# Momentum Lens 必要修复实施报告

## 执行日期
2025-08-25

## 已完成的修复

### 1. ✅ 动量/资格判定一致性（SatelliteModuleEnhanced.tsx）

**问题**：资格总览显示红叉，但下方检查点都是绿勾
**解决方案**：实现统一判定逻辑

```typescript
// 统一判定口径
details.overallPass = 
  details.bufferPass &&           // 缓冲阈值通过
  details.minHoldingPass &&        // 最短持有期通过
  details.correlationPass &&       // 相关性 ≤ 0.8
  details.legLimitPass;            // 腿数限制通过

// 任何一项不通过，总览显示❌并标出具体未通过项
```

**实现细节**：
- ✅ 资格总览明确显示"合格"或"不合格"
- ✅ 四个检查项分别显示通过状态
- ✅ 未通过时显示具体原因警告
- ✅ 按钮根据资格状态启用/禁用

### 2. ✅ 相关性热图只展示卫星候选

**问题**：热图包含核心标的 510300
**解决方案**：过滤掉核心标的，只显示卫星池

```typescript
// 热图只展示卫星候选 Top5
const top5 = enhancedMomentumData
  .filter(etf => etf.code !== '510300')  // 排除核心标的
  .slice(0, 5);

// 添加说明文字
<Typography variant="caption">
  注：只显示卫星候选池，不包含核心标的(510300)
</Typography>
```

### 3. ✅ 动量表格新增关键列

**新增的列**：
1. **ρ(Top1)** - 与 Top1 的相关系数
2. **缓冲差** - score_new − score_hold
3. **持有剩余** - 最短持有期剩余天数

```typescript
// 为每个 ETF 计算增强数据
{
  correlationWithTop1,     // 与 Top1 的相关性
  bufferDiff,              // 缓冲差值
  minHoldingDaysRemaining, // 最短持有剩余天数
}
```

**视觉优化**：
- 相关系数 > 0.8 显示红色警告
- 缓冲差 ≥ 3% 显示绿色
- 持有剩余天数 > 0 显示橙色警告

### 4. 🚧 单位/标签清晰化（待实施）

**计划修复**：
```typescript
// 决策台 - 市场环境指标
旧：波动: 2.50 / 震荡: 45.00
新：ATR20/价: 2.5% / 带内天数: 14/30 (46.7%)

// 参数设置
旧：最大持仓天数
新：最短持有期（天）
```

### 5. 🚧 年线/CHOP 口径固化（待实施）

**计划实现**：
```typescript
// 年线状态显示
年线: ABOVE (+1.2%)  // 显示 (收盘/MA200 - 1)

// CHOP 触发条款（三选二）
震荡: ON 
✓ 带内天数 > 50%
✓ ATR20/价 < 2.5%
○ 分散度 > 阈值

// CHOP=ON 时自动锁定参数
if (isChoppy) {
  buffer = 4%;      // 锁定
  minHolding = 28;   // 锁定
  bandwidth = ±7pp;  // 锁定
  legCount = 1;      // 锁定
}
```

## 待实施的必要修复

### 6. 时间轴/时区一致性

**问题**：日志显示跨年错乱（2024/2025）
**计划**：
- 统一使用 Asia/Shanghai 时区
- 所有时间戳带 tz 信息
- 过滤器默认最近 30 个交易日

### 7. 决策-订单-日志可追溯性

**需要保存的字段**：
```typescript
interface TradeLog {
  // 新增字段
  iopv_at_order: number;
  iopv_band_low: number;
  iopv_band_high: number;
  correlation_with_top1: number;
  score_old: number;
  score_new: number;
  score_diff: number;
  buffer_threshold: number;
  min_hold_ok: boolean;
  regime_snapshot: MarketRegime;
  idempotency_key: string;
}
```

## 推荐优化（已规划）

### 8. QDII 门槛功能

```typescript
// QDII 状态区
interface QDIIStatus {
  latestPremium: number;
  allowed: boolean;
  reason: string;
}

// 判定逻辑
if (premium <= 2%) 允许买入
if (premium >= 3%) 暂停，资金转 511990
```

### 9. API 测试页增强

```typescript
// 可比结果表格
interface SourceTestResult {
  source: string;
  status: 'OK' | 'FAIL';
  latency: number;  // ms
  price: number;
  change: number;   // %
  timestamp: Date;
}

// 导出功能
exportToCSV(results);

// 7天稳定性评分
interface StabilityScore {
  successRate: number;
  avgLatency: number;
  p99Latency: number;
  drift: number;
}
```

## 实施优先级

### 🔴 立即修复（影响正确性）
1. ✅ 动量/资格判定一致性
2. ✅ 相关性热图卫星池隔离
3. ✅ 动量表新增关键列
4. ⏳ 单位标签清晰化
5. ⏳ 时区一致性
6. ⏳ 决策可追溯性

### 🟡 重要优化（提升稳定性）
7. ⏳ 年线/CHOP 口径固化
8. ⏳ QDII 门槛
9. ⏳ API 测试增强
10. ⏳ 再平衡建议

### 🟢 体验优化（锦上添花）
11. ⏳ 术语卡/帮助浮层
12. ⏳ Preset 一键切档
13. ⏳ 回测微应用
14. ⏳ 通知中心

## 验收清单

### 已完成 ✅
- [x] Satellite 资格判定统一，总览与细项一致
- [x] 相关性热图只显示卫星候选，排除 510300
- [x] 动量表包含 ρ(Top1)、缓冲差、持有剩余三列
- [x] 资格不合格时按钮禁用，显示具体原因

### 待完成 ⏳
- [ ] 决策台单位正确（ATR%、带内天数/30）
- [ ] CHOP=ON 时参数自动锁定
- [ ] 日志保存完整决策快照
- [ ] 时区统一为 CST
- [ ] QDII 溢价门槛生效
- [ ] API 测试页显示可比结果

## 技术说明

### 文件位置
- 增强版 Satellite 模块：`frontend/src/components/Satellite/SatelliteModuleEnhanced.tsx`
- 原始版本保留：`frontend/src/components/Satellite/SatelliteModule.tsx`

### 使用方式
```typescript
// 在 App.tsx 中替换导入
import SatelliteModule from './components/Satellite/SatelliteModuleEnhanced';
```

### 测试建议
1. 验证资格判定逻辑的各种组合
2. 确认相关性计算排除核心标的
3. 检查新列数据的准确性
4. 测试按钮启用/禁用逻辑

## 下一步行动

1. **立即**：将 SatelliteModuleEnhanced 集成到主应用
2. **今天**：完成单位标签和时区修复
3. **本周**：实施 CHOP 逻辑和 QDII 门槛
4. **下周**：增强 API 测试页和决策追溯

---

*实施工程师：Claude Code*
*审核建议：产品团队验收后部署*