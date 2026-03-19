<div align="center">

# 📊 Momentum Lens

### ETF 动量分析与量化回测系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![RQAlpha](https://img.shields.io/badge/RQAlpha-Supported-orange.svg)](https://github.com/ricequant/rqalpha)

**基于 RQAlpha 的专业级 ETF 动量分析工具** | 交互式图表 | 智能预警 | 回测验证

[快速开始](#-快速开始) · [核心功能](#-核心功能) · [文档](#-文档) · [问题反馈](https://github.com/MKY508/momentum-lens/issues)

</div>

---

## 🎯 核心特性

### ⚡ 一键回测所有策略对比（最推荐）

**同时运行 8 个实验性策略并生成对比表格**：

| 策略名称 | 特点 | 风格 |
|---------|------|------|
| 科学动量v1 | 经典动量策略 | 均衡 |
| 稳健动量 | 低波动率优先 | 保守 |
| 激进动量 | 纯收益率择强 | 激进 |
| 短波敏感 | 快速响应市场 | 灵活 |
| 趋势确认 | 斜率主导 | 趋势 |
| 多腿分散 | Top3 等权 | 分散 |
| 风险平价 | 逆波动率配权 | 风控 |
| 低换手 | 阻尼切换 | 低频 |

**每个策略都包含**：
- ✅ 止损机制：单只ETF从最高点回撤>15%时自动止损
- ✅ 再平衡：每月检查，偏离>5%时自动调仓
- ✅ 防御机制：大盘MA200以下时降低风险暴露

**自动输出**：累计收益、年化收益、夏普比率、最大回撤、波动率对比表

### 🎯 核心-卫星增强回测（推荐）

完整的投资组合管理系统：
- **核心仓**：60% 等权持有核心资产（沪深300/红利/短融/黄金/标普500）
- **卫星仓**：40% 动量 Top2（行业/主题 ETF）
- **风险管理**：止损 + 再平衡 + 防御机制三重保护
- **多时间段**：10年/5年/2年/1年/6个月/3个月回测

### 🔍 最优策略分析（twelve-minus-one）

- 10年历史回测（2015-2024）
- 与4大指数对比（沪深300/中证500/中证1000/创业板50）
- 完整风险指标（夏普/最大回撤/换手率）
- 当前持仓建议

### 📈 动量分析核心功能

- **智能预警**：追踪前6名ETF周度排名，连续3周下滑≥2位触发预警
- **相关性分析**：自动识别ρ≥0.85的高相关组合
- **交互式图表**：Plotly图表支持点击显示/隐藏，多维度筛选
- **模板管理**：保存/加载自定义分析配置
- **多主题支持**：极光/余烬/常青等终端配色

---

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone https://github.com/MKY508/momentum-lens.git
cd momentum-lens

# 创建虚拟环境并安装依赖
./scripts/setup.sh
source .venv/bin/activate

# 安装 CLI 到 PATH（可选）
./scripts/link_cli.sh
```

### 使用

```bash
# 方式1: 直接运行
./momentum_lens.sh

# 方式2: 如果已安装到 PATH
momentum-lens

# 一键回测所有策略
./momentum_lens.sh analyze
# 选择 "3. 回测与动量工具"
# 选择 "11. ⚡ 一键回测所有策略对比"

# 更新数据包
./momentum_lens.sh update-bundle
```

---

## 📊 核心功能

### 1. 动量分析
- **快速分析**：一键分析核心+卫星券池
- **自定义参数**：券池/窗口/权重/导出设置
- **动量预警**：周度排名监测与预警
- **相关性告警**：高相关组合识别

### 2. 回测工具
- **简易回测**：快速验证策略表现
- **多区间回测**：10年/5年/2年等多时间段
- **一键对比**：8个策略同时回测并对比
- **策略导出**：生成可执行的策略代码

### 3. 交互式图表
- Plotly 动态图表（动量得分/排名）
- 图例点击显示/隐藏
- 分组快捷按钮（全部/前6/核心/卫星）
- 自适应布局

### 4. 模板管理
- 保存自定义配置
- 快速加载预设
- 参数模板化

---

## 🏆 推荐配置

### twelve-minus-one 策略

```
策略:         twelve-minus-one (12-1月动量)
调仓频率:     monthly (月度)
持仓数量:     2
观察期:       2个月
相关性阈值:   0.70

测试期表现（2023-2024）:
年化收益:     11.22%
夏普比率:     0.69
最大回撤:     -24.34%
年化换手率:   0.10
```

**说明**：
- ✅ 训练期（2015-2022）年化收益 18.38%，夏普 0.91
- ✅ 测试期（2023-2024）年化收益 11.22%，夏普 0.69
- ⚠️ 关注测试期表现：11.22% 是"样本外"结果，更有参考价值
- ⚠️ 做好风险管理：极端事件时回撤可能超过 -40%

---

## 📚 文档

### 核心文档
- [**快速参考卡片**](QUICK_REFERENCE.md) - 功能速查表 ⭐
- [**快速开始指南**](QUICK_START.md) - 5分钟上手
- [**最终总结**](FINAL_SUMMARY.md) - 核心问题与解决方案

### 详细文档
- [**核心-卫星增强回测**](docs/CORE_SATELLITE_ENHANCED.md) - 止损/再平衡/防御机制详解 ⭐
- [**回测问题诊断**](docs/BACKTEST_ISSUES_AND_FIXES.md) - 问题分析与修复
- [**最优策略指南**](docs/BEST_STRATEGY_GUIDE.md) - twelve-minus-one 完整使用指南
- [**系统重构总结**](docs/SYSTEM_REFACTOR_SUMMARY.md) - 技术细节

---

## 🛠️ 技术栈

- **数据源**：RQAlpha 离线数据包（沪深A股/ETF/指数日线数据）
- **分析框架**：Pandas + NumPy
- **可视化**：Plotly（交互式图表）
- **终端UI**：Rich（美化终端输出）
- **回测引擎**：RQAlpha

---

## ⚠️ 重要提示

1. **样本外验证**：关注2023-2024测试期表现（11.22%年化），更有参考价值
2. **风险管理**：极端事件回撤可能超-40%，建议保留20-30%现金
3. **定期验证**：每季度检查策略表现，连续6个月夏普<0时暂停
4. **分散投资**：动量40-50%，核心底座30-40%，现金/债券20-30%
5. **免责声明**：本工具仅供研究学习，不构成投资建议

---

## 📂 项目结构

```
momentum-lens/
├── momentum_lens.sh           # CLI 入口脚本
├── momentum_cli/              # 核心 Python 包
│   ├── business/              # 业务逻辑（分析/回测）
│   ├── commands/              # 命令处理
│   ├── config/                # 配置管理
│   ├── ui/                    # 终端界面
│   └── utils/                 # 工具函数
├── scripts/
│   ├── setup.sh               # 环境安装脚本
│   └── link_cli.sh            # CLI 安装脚本
├── docs/                      # 详细文档
├── requirements.txt           # Python 依赖
└── README.md                  # 本文件
```

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🔗 相关链接

- [RQAlpha 官方文档](https://github.com/ricequant/rqalpha)
- [Plotly 文档](https://plotly.com/python/)
- [项目主页](https://github.com/MKY508/momentum-lens)

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star！**

Made with ❤️ by [MKY508](https://github.com/MKY508)

</div>
