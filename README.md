# Momentum Lens v2.2 - 核心-卫星增强回测系统

## 🚀 快速开始

```bash
# 启动系统
./momentum_lens.sh analyze

# 选择 "3. 回测与动量工具"
# 选择 "10. 🔬 核心-卫星增强回测（含止损/再平衡/防御）"
```

## 📊 核心功能

### 1. 核心-卫星增强回测（推荐）✨

**完整的投资组合管理系统**：
- ✅ **止损机制**：单只ETF从最高点回撤>15%时自动止损
- ✅ **再平衡机制**：每月检查，偏离>5%时自动再平衡
- ✅ **防御机制**：大盘MA200以下时，降低卫星仓至20%
- ✅ **多区间回测**：10年/5年/2年/1年/6个月/3个月

**策略逻辑**：
- 核心仓：60%等权持有核心券池（沪深300/红利/短融/黄金/标普500）
- 卫星仓：40%择优持有动量Top2（行业/主题ETF）
- 止损：控制单只ETF最大损失
- 再平衡：保持核心-卫星比例，自动"高抛低吸"
- 防御：熊市时降低风险暴露

### 2. 最优策略分析（twelve-minus-one）

**完整的策略验证系统**：
- 10年历史回测（2015-2024）
- 与基准指数对比（沪深300/中证500/中证1000/创业板50）
- 风险指标分析（夏普/最大回撤/换手率）
- 当前持仓建议
- 策略有效性验证

### 3. 实验性策略（8个预设）

**多种策略风格可选**：
1. 科学动量v1（经典）
2. 稳健动量（低波优先）
3. 激进动量（纯择强）
4. 短波敏感（快速响应）
5. 趋势确认（斜率主导）
6. 多腿分散（Top3等权）
7. 风险平价（逆波动配权）
8. 低换手（阻尼切换）

## 🏆 推荐配置

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

## 📚 文档

### 核心文档
- [快速参考卡片](QUICK_REFERENCE.md) - 功能速查表 ⭐
- [快速开始指南](QUICK_START.md) - 5分钟上手
- [最终总结](FINAL_SUMMARY.md) - 核心问题与解决方案

### 详细文档
- [核心-卫星增强回测](docs/CORE_SATELLITE_ENHANCED.md) - 止损/再平衡/防御机制详解 ⭐
- [回测问题诊断](docs/BACKTEST_ISSUES_AND_FIXES.md) - 问题分析与修复
- [最优策略指南](docs/BEST_STRATEGY_GUIDE.md) - twelve-minus-one完整使用指南
- [系统重构总结](docs/SYSTEM_REFACTOR_SUMMARY.md) - 技术细节

## ⚠️ 重要提示

1. **关注测试期表现**：2023-2024的11.22%年化收益是"样本外"结果，更有参考价值
2. **做好风险管理**：极端事件时回撤可能超过-40%，建议保留20-30%现金
3. **定期验证**：每季度检查策略表现，连续6个月夏普<0时暂停策略
4. **分散投资**：动量策略40-50%，核心底座30-40%，现金/债券20-30%

---


# momentum-lens

组合核心/卫星 ETF 的动量分析工具，基于本地 RQAlpha 数据包运行，提供交互式图表、预警提示以及模板化配置，适合量化交易与定期资产复盘。

## 功能亮点

- **一键快速分析**：默认聚合“核心 + 卫星”券池，自动使用最新本地 RQAlpha bundle。
- **自定义参数**：交互式引导选择券池、动量窗口、权重、导出设置等，支持模板保存与加载。
- **动量预警系统**：追踪前 6 名 ETF 的周度排名，一旦连续 3 周以上下滑且累计下滑 ≥ 2 位即输出预警。
- **相关性告警**：券池较大时自动筛出相关系数 ρ ≥ 0.85 的高相关组合，避免冗长矩阵。
- **交互式图表**：Plotly 图表支持分组按钮与“点击单个图例隐藏/显示”，并可自定义主题、线宽。
- **主题化终端界面**：提供极光/余烬/常青等配色，设置后全局统一并落盘。
- **环境清理与依赖安装工具**：内置数据包更新、Plotly 安装、结果清理等辅助脚本。

## 项目初始化

```bash
# 克隆或复制项目后，初始化 Git 仓库（如尚未初始化）
cd /path/to/momentum-lens
git init

# 建议将默认分支改为 main
git branch -m main
```

### Python 环境

```bash
# 创建并安装依赖
./scripts/setup.sh

# 激活
source .venv/bin/activate
```

`requirements.txt` 已列出运行所需的核心依赖（numpy、pandas、plotly、h5py、rqalpha 等）。

### CLI 安装到 PATH

```bash
./scripts/link_cli.sh
# 确保 ~/.local/bin 已加入 PATH
```

脚本会把 `momentum_lens.sh` 链接为 `~/.local/bin/momentum-lens`，之后可直接使用 `momentum-lens` 命令。

## 快速开始

```bash
# 快速分析（核心 + 卫星）
momentum-lens

# 自定义分析
momentum-lens analyze --preset core --start 2024-01-01 --end 2024-12-31 --no-plot

# 更新 RQAlpha 数据包
momentum-lens update-bundle
```

进入交互式菜单后，依次可访问：

1. 快速分析（核心+卫星）
2. 自定义运行动量分析
3. 回测与动量工具（简易回测、多区间回测、动量回溯、策略导出）
4. 模板管理（列出、运行、保存、删除）
5. 报告回顾（查看最近生成的分析文本）
6. 更新数据（rqalpha bundle）
7. 设置与工具：
   - 券池预设管理（新增、编辑、恢复默认）
   - 分析预设管理
   - 模板设置
   - 终端主题与色彩
   - 图表样式配置
   - Plotly 及其他依赖安装
   - 数据包更新
   - 清理生成文件
8. 关于 Momentum Lens（版本信息、项目主页）

## 预警说明

- **动量排名连续走弱**：默认监测最新排名前 6 的 ETF，若最近 3 个自然周（按周收盘）排名持续走弱，且累计下滑 ≥ 2 位则触发预警。
- **高相关性告警**：当券池规模超过 15 只 ETF 时，不再完整展示矩阵，而是列出 ρ ≥ 0.85 的高相关组合，帮助控制仓位集中度。

预警内容会出现在：
- 终端文本报告（“预警提示 / Alerts”区块）
- Markdown 输出（对应章节）
- JSON 输出的 `alerts` 字段，可供自动化流程消费。

## Plotly 图表

生成的 Plotly 文件位于 `results/` 目录：
- `momentum_scores_interactive.html`
- `momentum_ranks_interactive.html`

图表特点：
- 图例支持点击单个 ETF 显示/隐藏。
- 默认聚焦前 6 名，提供“全部/前6/仅核心/仅卫星/仅其他”快捷按钮。
- 自动根据券池大小调整图例高度与布局。

## 数据维护

- **更新 RQAlpha 数据包**：`momentum-lens update-bundle`
- **安装 Plotly**：`momentum-lens install-deps`（或在设置菜单执行）
- **清理输出**：设置菜单中的“清理生成文件”，按需删除 `results/`、导出的策略等。

## GitHub 仓库发布

推荐仓库名称：`momentum-lens`

```bash
# 添加远程（示例）
git remote add origin git@github.com:<your-user>/momentum-lens.git

# 首次推送
git add .
git commit -m "Initial commit"
git push -u origin main
```

> 当前环境网络受限，如需推送至 GitHub，请在具备网络访问的环境中执行上述命令。

## 目录结构

```
momentum-lens/
├── momentum_lens.sh           # CLI 入口
├── momentum_cli/              # 动量分析核心 Python 包
├── scripts/
│   ├── setup.sh               # 创建虚拟环境并安装依赖
│   └── link_cli.sh            # 将 momentum-lens CLI 链接到 PATH
├── requirements.txt
├── README.md
└── .gitignore
```

## 许可证

请根据您的项目需求添加许可。若未指定，默认保留所有权利。
