# ETF收益率计算未考虑分红导致排名严重失真

## 问题描述

系统在计算ETF动量排名时使用单位净值(Unit NAV)计算收益率，未考虑分红除权的影响，导致高分红ETF（如银行ETF）的收益率严重失真，排名错误。

## 影响范围

- **严重程度**: 🔴 Critical
- **影响模块**: 
  - 后端: `/api/market/momentum-rankings` 接口
  - 前端: SatelliteModule 组件
  - 数据: 所有分红ETF的动量评分和排名

## 具体案例

### 案例1: 银行ETF (512800) 

**问题时间**: 2025年8月25日

**错误表现**:
- 名义60日收益率: -47.24%
- 名义120日收益率: -42.66%
- 动量评分: -45.41
- 排名: 第12名（垫底）

**实际情况**:
- 2025年7月4日分红: 0.857元/份
- 分红前价格: 1.77元
- 分红后价格: 0.89元（除权）
- 真实60日收益率: +5.80%（含分红）
- 真实120日收益率: +4.50%（含分红）
- 正确动量评分: +5.29
- 正确排名: 第11名

**影响**: 53.04%的收益率差异，完全颠倒了投资决策

### 案例2: 券商ETF (512000)

**错误表现**:
- 名义60日收益率: -35.91%
- 名义120日收益率: -39.55%
- 动量评分: -37.36
- 排名: 第11名

**实际情况**:
- 存在大额分红（推测约1.0元/份）
- 真实60日收益率: +28.09%（含分红）
- 真实120日收益率: -20.65%（含分红）
- 正确动量评分: +8.75
- 正确排名: 第10名

**影响**: 64.00%的收益率差异，从巨亏变为盈利28%

## 根本原因

1. **数据源问题**: 使用价格数据而非累计净值
   ```python
   # 错误方式
   return_rate = (current_price / past_price - 1) * 100
   
   # 正确方式
   return_rate = (current_nav / past_nav - 1) * 100  # 使用累计净值
   ```

2. **分红事件未处理**: 系统未检测和调整分红除权事件

3. **数据验证缺失**: 缺少多数据源交叉验证机制

## 解决方案

### 1. 创建ETF数据处理器 (`etf_data_handler.py`)

```python
class ETFDataHandler:
    def detect_dividend_events(self, df: pd.DataFrame, threshold: float = 0.15):
        """检测分红除权事件（单日跌幅>15%）"""
        
    def get_adjusted_prices(self, code: str, use_nav: bool = True):
        """获取复权后的价格数据，优先使用累计净值"""
        
    def calculate_returns_with_dividend(self, code: str, periods: List[int]):
        """计算考虑分红的真实收益率"""
```

### 2. 多数据源验证

```python
def verify_with_multiple_sources(self, code: str, name: str):
    """
    使用多个数据源验证ETF数据
    - 东方财富 (fund_etf_hist_em)
    - 新浪财经 (fund_etf_hist_sina)
    - 基金净值 (fund_etf_fund_info_em)
    """
```

### 3. 前端显示优化

- 添加分红标识
- 显示真实收益率vs名义收益率
- 橙色标记表示有分红影响

```typescript
interface MomentumETF {
  r60: number;           // 真实收益率
  r60_nominal?: number;  // 名义收益率
  has_dividend?: boolean;
  dividend_impact?: number;
}
```

## 测试验证

### 验证脚本
```bash
python test_dividend_adjustment.py
```

### 预期结果
```
银行ETF验证结果:
  真实60日收益: 5.80%
  名义60日收益: -47.24%
  分红影响: 53.04%
  动量评分: 5.29
```

## 修复后的API响应

```json
{
  "code": "512800",
  "name": "银行ETF",
  "score": 5.29,
  "r60": 5.8,
  "r120": 4.5,
  "r60_nominal": -47.24,
  "r120_nominal": -42.66,
  "has_dividend": true,
  "dividend_impact": 53.04
}
```

## 预防措施

1. **使用累计净值而非单位净值**
2. **实施分红事件自动检测**
3. **多数据源交叉验证**
4. **添加数据质量监控告警**
5. **定期验证高分红ETF数据**

## 相关文件

- `backend/etf_data_handler.py` - 分红调整处理器
- `backend/main_lite.py` - API端点更新
- `frontend/src/types/index.ts` - 类型定义更新
- `frontend/src/components/Satellite/SatelliteModule.tsx` - UI显示更新

## 参考资料

- [ETF分红除权规则](https://www.sse.com.cn/etf)
- [累计净值vs单位净值](https://fund.eastmoney.com)
- AKShare文档: `fund_etf_fund_info_em` 接口

## 标签

`bug` `critical` `data-accuracy` `dividend-adjustment` `etf`