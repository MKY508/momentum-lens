# Momentum Lens 修复需求文档

## 文档信息
- **创建日期**: 2025-08-25
- **版本**: 1.0
- **状态**: 待实施
- **优先级**: P0-必须修 > P1-推荐修 > P2-锦上添花

---

## 一、必须修复的问题（P0 - 影响正确性/一致性）

### 1.1 动量/资格判定一致性 ✅ 已完成
**状态**: ✅ 已在 `SatelliteModuleEnhanced.tsx` 中实现

**问题描述**:
- Satellite 右侧"前 5 名 ETF 资格合格"显示红叉
- 但下方四个检查点都显示绿勾
- 逻辑不一致，用户困惑

**解决方案**:
```typescript
// 统一判定口径
overallPass = bufferPass ∧ minHoldingPass ∧ correlationPass ∧ legLimitPass

// 实现细节
interface QualificationDetail {
  bufferPass: boolean;        // 缓冲阈值 ≥ 3%
  minHoldingPass: boolean;     // 最短持有期满足
  correlationPass: boolean;    // ρ ≤ 0.8
  legLimitPass: boolean;       // 腿数 ≤ 2
  overallPass: boolean;        // 全部通过才为 true
}
```

**验收标准**:
- [x] 资格总览与细项判定完全一致
- [x] 任何一项不通过，总览显示❌
- [x] 明确标出具体未通过项

---

### 1.2 相关性热图范围 ✅ 已完成
**状态**: ✅ 已在 `SatelliteModuleEnhanced.tsx` 中实现

**问题描述**:
- 热图包含 510300（Core 标的）
- 第二腿候选应只在卫星池中比较

**解决方案**:
```typescript
// 热图只展示卫星候选
const satelliteCandidates = data.filter(etf => etf.code !== '510300');

// 动量表增加 ρ(Top1) 列
correlationWithTop1 = getCorrelation(etf, top1);
```

---

### 1.3 单位/标签不清晰 ⏳ 待实施

**问题描述**:
- 决策台显示"波动: 2.50 / 震荡: 45.00"看不出单位
- 参数页"最大持仓天数"实际是最短持有期

**修复方案**:

#### 决策台市场环境
```typescript
// 旧显示
波动: 2.50 / 震荡: 45.00

// 新显示
ATR20/价: 2.5%
带内天数: 14/30 (46.7%)
```

#### 参数设置页
```typescript
// 旧标签
最大持仓天数: 28 天

// 新标签
最短持有期（天）: 28

// CHOP=ON 时自动锁定
if (regime === 'CHOPPY') {
  minHolding = 28;  // 锁定，灰掉滑杆
}
```

**实现位置**:
- `frontend/src/components/Dashboard/DecisionDashboard.tsx`
- `frontend/src/components/Settings/ParameterSettings.tsx`

---

### 1.4 时间轴/时区一致性 ⏳ 待实施

**问题描述**:
- 日志筛选 2025/07/26–2025/08/25
- 但显示 2024-08-... 记录
- 时区混乱

**修复方案**:
```typescript
// 统一时区处理
import { zonedTimeToUtc, utcToZonedTime } from 'date-fns-tz';

const CST_TIMEZONE = 'Asia/Shanghai';

// 所有时间戳转换
const cstTime = utcToZonedTime(date, CST_TIMEZONE);

// 日志记录带时区
interface TradeLog {
  timestamp: Date;
  timezone: 'Asia/Shanghai';
  tradingDate: string; // YYYY-MM-DD in CST
}

// 过滤器默认
defaultDateRange = getLast30TradingDays(CST_TIMEZONE);
```

**实现位置**:
- `frontend/src/components/Logs/LogsKPI.tsx`
- `backend/routers/trading.py`

---

### 1.5 年线/CHOP 口径固化 ⏳ 待实施

**问题描述**:
- 年线状态缺少具体数值
- CHOP 触发条件不明确
- 参数联动逻辑不清晰

**修复方案**:

#### 年线显示增强
```typescript
// 决策台 - 市场环境
interface YearlineStatus {
  position: 'ABOVE' | 'BELOW';
  deviation: number; // (Close/MA200 - 1)
}

// 显示示例
年线: ABOVE (+1.2%)  // 收盘价高于年线 1.2%
```

#### CHOP 触发条款（三选二）
```typescript
interface ChopConditions {
  inBandDays: boolean;      // 带内天数 > 50%
  lowVolatility: boolean;   // ATR20/价 < 2.5%
  highDispersion: boolean;  // 分散度 > 阈值
}

// 显示触发的条件
震荡: ON
✓ 带内天数 18/30 (60%)
✓ ATR/价 2.1% < 2.5%
○ 分散度未触发
```

#### 参数自动锁定
```typescript
// CHOP=ON 时强制设置
if (marketRegime === 'CHOPPY') {
  lockedParams = {
    buffer: 4,         // 4% 缓冲
    minHolding: 28,    // 4 周最短
    bandwidth: 7,      // ±7pp
    legCount: 1        // 单腿
  };
  // UI 显示锁定图标，滑杆禁用
}
```

**实现位置**:
- `frontend/src/components/Dashboard/DecisionDashboard.tsx`
- `frontend/src/components/Settings/ParameterSettings.tsx`

---

### 1.6 决策-订单-日志可追溯性 ⏳ 待实施

**问题描述**:
- 无法回放交易决策理由
- 缺少关键快照数据

**修复方案**:
```typescript
// 扩展日志数据结构
interface EnhancedTradeLog {
  // 原有字段
  ...existingFields,
  
  // 新增追溯字段
  iopvAtOrder: number;
  iopvBandLow: number;
  iopvBandHigh: number;
  correlationWithTop1: number;
  scoreOld: number;
  scoreNew: number;
  scoreDiff: number;
  bufferThreshold: number;
  minHoldOk: boolean;
  regimeSnapshot: {
    yearline: 'ABOVE' | 'BELOW';
    choppy: boolean;
    atr: number;
    inBandDays: number;
  };
  idempotencyKey: string; // 防重复下单
}

// 保存时机
onOrderPlaced = (order) => {
  saveDecisionSnapshot(order);
};
```

**实现位置**:
- `backend/models/trade_log.py`
- `backend/core/order_manager.py`
- `frontend/src/types/index.ts`

---

## 二、推荐优化（P1 - 稳定性/易用性）

### 2.1 API 测试页增强 ⏳ 待实施

**需求描述**:
提供可比较的数据源测试结果

**实现方案**:
```typescript
// 测试结果数据结构
interface DataSourceTest {
  source: string;           // 'EastMoney' | 'AkShare' | 'Sina'
  status: 'OK' | 'FAIL';
  latency: number;          // ms
  price: number;
  change: number;           // %
  timestamp: Date;
}

// 稳定性评分（7天滚动）
interface StabilityMetrics {
  successRate: number;      // 成功率
  avgLatency: number;       // 平均延迟
  p99Latency: number;       // 99分位延迟
  driftScore: number;       // 数据漂移度
}

// UI 组件
<DataGrid
  columns={[
    { field: 'source', headerName: '数据源' },
    { field: 'status', headerName: '状态' },
    { field: 'latency', headerName: '延迟(ms)' },
    { field: 'price', headerName: '价格' },
    { field: 'change', headerName: '涨跌幅' },
  ]}
  exportable={true}
/>
```

**实现位置**:
- `frontend/src/pages/APITest.tsx`

---

### 2.2 QDII 门槛功能 ⏳ 待实施

**需求描述**:
QDII 溢价控制

**实现方案**:
```typescript
// QDII 状态组件
interface QDIIStatus {
  latestPremium: number;
  threshold: {
    buy: 2,      // ≤2% 可买
    pause: 3     // ≥3% 暂停
  };
  allowed: boolean;
  action: 'BUY' | 'PAUSE' | 'REDIRECT_511990';
  reason: string;
}

// 决策卡右侧显示
<Card>
  <CardContent>
    <Typography>QDII 状态</Typography>
    <Chip 
      label={`溢价 ${premium}%`}
      color={premium <= 2 ? 'success' : 'error'}
    />
    {premium >= 3 && (
      <Alert severity="warning">
        溢价过高，资金转向 511990
      </Alert>
    )}
  </CardContent>
</Card>
```

**实现位置**:
- `frontend/src/components/Dashboard/DecisionDashboard.tsx`
- `frontend/src/components/Core/CoreModule.tsx`

---

### 2.3 Satellite 动量表补充列 ✅ 已完成

**状态**: ✅ 已在 `SatelliteModuleEnhanced.tsx` 中实现

已添加：
- ρ(Top1) - 与 Top1 的相关系数
- 缓冲差值 - score_new − score_hold
- 最短持有剩余天数

---

### 2.4 再平衡建议 ⏳ 待实施

**需求描述**:
Core 页提供一键调仓建议

**实现方案**:
```typescript
// 再平衡计算
interface RebalanceSuggestion {
  etf: string;
  currentWeight: number;
  targetWeight: number;
  deviation: number;
  action: 'BUY' | 'SELL' | 'HOLD';
  shares: number;
}

// 生成建议
const generateRebalance = () => {
  const suggestions = portfolio.map(holding => {
    const deviation = holding.weight - holding.target;
    if (Math.abs(deviation) > 2) {  // ±2pp 容差
      return {
        etf: holding.code,
        action: deviation > 0 ? 'SELL' : 'BUY',
        shares: calculateShares(deviation)
      };
    }
    return null;
  }).filter(Boolean);
  
  return suggestions;
};

// UI 按钮
<Button onClick={generateRebalance}>
  回到目标 ±2pp
</Button>
```

**实现位置**:
- `frontend/src/components/Core/CoreModule.tsx`

---

### 2.5 日志/KPI 关键指标 ⏳ 待实施

**需求描述**:
- IS（实施偏差）公式明确
- 单位换手收益计算

**实现方案**:
```typescript
// IS 计算
const IS = (executionPrice / iopvAtOrder - 1) * 100; // %

// 单位换手收益
const unitTurnoverReturn = monthlyReturn / monthlyTurnover;

// 自动提示
if (unitTurnoverReturn < 0) {
  showAlert('建议下月卫星配比降低 10pp');
}

// KPI 卡片
<MetricCard
  title="IS 实施偏差"
  value={`${IS.toFixed(2)}%`}
  formula="(成交价/下单IOPV - 1)"
  threshold={0.5}
/>
```

**实现位置**:
- `frontend/src/components/Logs/LogsKPI.tsx`

---

### 2.6 异常与停牌兜底 ⏳ 待实施

**需求描述**:
处理标的异常状态

**实现方案**:
```typescript
// ETF 状态枚举
enum ETFStatus {
  NORMAL = 'NORMAL',
  SUSPENDED = 'SUSPENDED',    // 停牌
  MERGED = 'MERGED',          // 合并
  DELISTED = 'DELISTED',      // 退市
  NO_DATA = 'NO_DATA'         // 无数据
}

// 异常处理
if (etf.status !== 'NORMAL') {
  return (
    <Alert severity="error">
      {etf.name} {getStatusMessage(etf.status)}
      <Button disabled>不可下单</Button>
    </Alert>
  );
}
```

**实现位置**:
- `frontend/src/components/Dashboard/DecisionDashboard.tsx`
- `backend/core/data_fetcher.py`

---

## 三、锦上添花（P2 - 体验/效率）

### 3.1 术语卡/帮助浮层

**实现方案**:
```typescript
// 术语定义
const TERMS = {
  MA200: {
    name: '200日均线',
    formula: 'SUM(Close, 200) / 200',
    description: '长期趋势指标'
  },
  ATR20: {
    name: '20日真实波幅',
    formula: 'SMA(TR, 20)',
    description: '波动率指标'
  },
  CHOP: {
    name: '震荡市',
    description: '横盘震荡状态'
  }
};

// 帮助组件
<IconButton onClick={() => setHelpOpen(true)}>
  <HelpIcon />
</IconButton>
```

### 3.2 Preset 一键切档

**实现方案**:
```typescript
// 预设配置
const PRESETS = {
  aggressive: { buffer: 2, minHold: 14 },
  balanced: { buffer: 3, minHold: 28 },
  conservative: { buffer: 4, minHold: 28 }
};

// 自动切换逻辑
if (marketRegime === 'CHOPPY') {
  autoSwitchTo('conservative');
  showReason('震荡市自动切换为保守模式');
}
```

### 3.3 回测微应用

**实现方案**:
```typescript
// 轻量回测
const backtest = async (startDate, endDate) => {
  const results = await api.backtest({
    strategy: 'momentum',
    params: currentParams,
    period: { start: startDate, end: endDate }
  });
  
  return {
    monthlyTurnover: results.turnover,
    winRate: results.winRate,
    maxDrawdown: results.drawdown,
    unitReturn: results.return / results.turnover
  };
};
```

### 3.4 通知中心

**实现方案**:
```typescript
// 事件枚举
enum TradingEvent {
  YEARLINE_CROSS = 'YEARLINE_CROSS',
  CHOP_CHANGE = 'CHOP_CHANGE',
  STOP_HIT = 'STOP_HIT',
  QDII_STATUS = 'QDII_STATUS'
}

// 通知配置
interface NotificationConfig {
  local: boolean;
  feishu?: string;    // webhook
  telegram?: string;  // bot token
}
```

---

## 四、小规范调整

### 4.1 术语统一
- "滑点成本" → "IS 实施偏差"
- "资格状态" → 固定四条：缓冲/最短持有/相关性/腿数限制

### 4.2 格式规范
- 百分比保留 1 位小数：2.5%
- 金额使用千分位：¥4,750
- 时间统一 CST 时区

### 4.3 颜色语义
- 🟢 绿色 = 通过/正常
- 🟠 橙色 = 注意/临界
- 🔴 红色 = 不通过/错误

---

## 五、实施计划

### 第一阶段（立即）
1. ✅ 动量/资格判定一致性
2. ✅ 相关性热图优化
3. ✅ 动量表新增列
4. ⏳ 单位标签清晰化
5. ⏳ 时区一致性

### 第二阶段（本周）
6. ⏳ 年线/CHOP 逻辑
7. ⏳ 决策追溯性
8. ⏳ QDII 门槛
9. ⏳ API 测试增强

### 第三阶段（下周）
10. ⏳ 再平衡建议
11. ⏳ 日志 KPI 指标
12. ⏳ 异常处理

### 第四阶段（可选）
13. ⏳ 术语帮助
14. ⏳ Preset 切换
15. ⏳ 回测功能
16. ⏳ 通知中心

---

## 六、验收标准

### 必须通过
- [ ] 决策台：单位正确，触发条款显示
- [ ] Satellite：资格判定一致，新列数据准确
- [ ] Core：目标偏差显示，DCA 计划清晰
- [ ] 日志：保存完整快照，时区正确
- [ ] API 测试：显示对比结果，可导出

### 建议通过
- [ ] QDII 溢价控制生效
- [ ] 再平衡建议可用
- [ ] IS 指标计算正确
- [ ] 异常状态处理完善

---

## 七、技术资源

### 已完成文件
- `frontend/src/components/Satellite/SatelliteModuleEnhanced.tsx`

### 相关文档
- `FIXES_IMPLEMENTATION_REPORT.md` - 实施报告
- `ENHANCEMENT_REPORT.md` - 增强报告
- `SMART_CLEANUP_PLAN.md` - 清理计划

### 依赖库
- date-fns-tz - 时区处理
- @mui/material - UI 组件
- recharts - 图表
- axios - API 调用

---

*文档维护：请在实施每项修复后更新状态*
*最后更新：2025-08-25*