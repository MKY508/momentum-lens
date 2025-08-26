# ETF动量核心卫星策略系统 V2

## 🎯 系统概述

基于Streamlit + Backtrader + AkShare的轻量级ETF动量策略系统，实现核心卫星配置、动量选股、可转债网格和半自动下单。

### 核心特性
- ✅ **极简架构**: 仅5个核心文件，代码量减少60%
- ✅ **实时数据**: AkShare获取A股ETF/可转债实时数据
- ✅ **智能决策**: 双窗动量打分 + 相关性筛除 + 资格检查
- ✅ **半自动交易**: 生成条件单脚本，支持easytrader批量下单
- ✅ **一键部署**: 单命令启动，无需复杂配置

## 📦 快速开始

### 1. 安装启动
```bash
# 克隆项目
cd projecttest2

# 一键启动
chmod +x start.sh
./start.sh

# 或手动启动
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

### 2. 访问系统
打开浏览器访问: http://127.0.0.1:8501

## 🏗️ 系统架构

```
projecttest2/
├── app.py              # Streamlit UI主界面
├── data_adapter.py     # 数据适配层(AkShare)
├── indicators.py       # 技术指标计算
├── decision_engine.py  # 决策引擎
├── trading_helper.py   # 半自动交易助手
├── config.yaml        # 策略配置
└── requirements.txt   # 依赖包
```

## 📊 策略逻辑

### 1. 资产配置
- **Core (40%)**: 沪深300、上证50、红利ETF、黄金ETF
- **Satellite (30%)**: 动量Top2 ETF（相关性<0.8）
- **可转债 (10%)**: 规模>3亿、溢价<30%、评级AA-以上
- **现金 (20%)**: 华宝添益或场内货基

### 2. 动量计算
```python
动量得分 = r60 * 0.6 + r120 * 0.4
其中：
- r60: 3个月收益率
- r120: 6个月收益率
```

### 3. 资格检查
- 成交额 > 5000万
- MA200状态: 非跌破
- 相关系数 < 0.8
- 最短持有 14天
- 缓冲区 3%

### 4. 风控规则
- 默认止损: -12%
- 震荡市止损: -15%
- 趋势市止损: -10%

## 💡 使用指南

### 决策面板
1. 系统自动判断市场状态（牛/熊/震荡）
2. 根据市场状态调整Core配置
3. 选择动量最强的2只ETF作为卫星
4. 筛选评分最高的3只可转债

### 订单生成
1. 设置总资金
2. 选择交易时间（周二10:30/14:00）
3. 生成CSV订单文件
4. 导出easytrader脚本

### 半自动交易
```python
# 生成的脚本示例
import easytrader
user = easytrader.use('ht')  # 华泰
user.prepare('config.json')

for order in orders:
    user.buy(order['代码'], amount=order['金额'])
```

## 🔧 配置说明

编辑 `config.yaml` 调整策略参数：

```yaml
strategy:
  core_ratio: 0.4        # Core比例
  satellite_ratio: 0.3   # 卫星比例
  momentum:
    r60_weight: 0.6      # 3月动量权重
    r120_weight: 0.4     # 6月动量权重
```

## 📈 回测功能（开发中）

- Backtrader集成
- 历史回测分析
- 收益曲线展示
- 风险指标计算

## ⚠️ 风险提示

1. 本系统仅供研究学习，不构成投资建议
2. 实盘交易前请充分测试
3. 注意数据延迟（免费接口约15分钟）
4. 定期检查策略有效性

## 🛠️ 技术栈

- **前端**: Streamlit 1.29
- **数据**: AkShare 1.11
- **回测**: Backtrader 1.9
- **交易**: easytrader 1.12
- **可视化**: Plotly 5.18

## 📝 更新日志

### V2.0 (2024-08)
- 重构为Streamlit单页应用
- 简化为5个核心文件
- 集成半自动交易功能
- 优化动量计算逻辑

## 🤝 贡献

欢迎提交Issue和PR！

## 📄 License

MIT License