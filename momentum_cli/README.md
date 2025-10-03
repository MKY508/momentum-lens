# Momentum CLI

命令行工具，基于本地 RQAlpha 数据包，对 ETF 券池做动量/趋势分析。

## 一键交互模式

```bash
cd /Users/maokaiyue/rqalpha_project
./momentum.sh
```

脚本会自动使用虚拟环境（若存在 `~/rqalpha_env/bin/python`）。进入后按照提示输入编号即可：

- `1` 快速分析（默认核心+卫星券池 + slow-core 预设）
- `2` 自定义运行动量分析（可设置券池、窗口、导出等）
- `3` 动量回溯 / 图表（需已有分析，可查看历史排名、生成交互线图）
- `4` 最近分析操作（摘要、回测、导出策略脚本）
- `5` 模板管理（列出/使用/保存/删除模板）
- `6` 设置与工具（查看预设、下载数据包、清理生成文件等）

分析过程中可选择核心/卫星/自定义券池、挑选分析预设、调整日期、导出 CSV、生成图表，执行完成后还可在同一菜单里继续回测、导出策略或保存模板，整个流程均提供中文提示。新增/剔除 ETF 时也可直接从核心或卫星预设中按编号挑选，操作更直观。快速分析会自动回溯 ≥400 个自然日以保障 200 日均线、动量窗口等指标有效。

### 动量回溯 / 图表

- 查看指定日期的动量排名快照（包含动量得分、收盘价、MA200）。
- 一键生成交互式动量折线图 / 排名折线图（基于 Plotly，默认仅展示最新排名靠前的 ETF，并附带“全部 / 仅核心 / 仅卫星 / 仅其他”快捷按钮）。
- 命令行会提示图表路径，可选择自动在浏览器打开；若未安装 Plotly，请先执行 `pip install plotly`。

### 设置与工具

- `配置图表样式` 可切换 Plotly 主题（如 `plotly_dark`、`ggplot2` 等）并调整曲线宽度，定制交互图观感。
- `安装/修复依赖（Plotly 等）` 会尝试从官方 PyPI 与清华镜像安装 `plotly==5.24.0`，并在失败时提示手动下载 whl 的备用方案。
- `下载/更新 RQAlpha 数据包` 会优先执行 `rqalpha download-bundle`，落地到 `~/.rqalpha/bundle`（包含 ETF/股票/指数的日线历史数据，可回溯至最早可用日期），并在失败时回退至 `rqalpha update-bundle`。
- `清理生成文件` 支持逐项删除 `results/` 图表、导出的策略脚本及模板缓存。

### 模板与自动化输出（命令行）

- `--save-template my-core`：把当前参数保存为模板，方便复用。
- `--load-template my-core` / `--list-templates` / `--delete-template my-core`：加载、查看或删除模板。
- `--output-format text|json|markdown`：输出文本、结构化 JSON 或 Markdown，便于 MCP/自动化流程消费。
- `--output-file out.md`：把主输出写入文件；`--save-state result.json` 可持久化完整分析结果。
- `--print-config`：打印实际生效的参数（JSON），便于审计。
- `--color` / `--no-color`：强制启用或关闭彩色输出（默认仅在终端支持时启用）。
- `--quiet`：仅输出必要提示，适合管道 / 批处理使用。

Markdown / JSON 输出可直接被 MCP server、dashboards 或二次处理脚本引用，减少解析成本。

## 快速开始（命令行参数模式）

```bash
# 建议使用仓库中的虚拟环境
source ~/rqalpha_env/bin/activate
cd /Users/maokaiyue/rqalpha_project
python -m momentum_cli --preset core,satellite --start 2023-01-01 --end 2024-12-31 --export-csv

# 示例：加载模板并输出 JSON，落盘 JSON 与完整分析状态
python -m momentum_cli --load-template my-core --output-format json \
  --output-file report.json --save-state analysis.json --print-config
```

如果仅想查看可用的券池预设，可执行：

```bash
python -m momentum_cli --list-presets
```

目前内置两个分组：

- `core`（核心仓）：沪深300ETF、红利ETF、短融ETF、国债ETF5-10年、黄金ETF、标普500ETF。
- `satellite`（卫星仓）：创业板ETF、创业板50ETF、有色金属ETF、游戏动漫ETF、券商ETF、银行ETF、新能源车ETF、新能源ETF、光伏ETF、计算机ETF、芯片ETF、科创50ETF。

## 分析预设 & 参数

### 预设概览

| 预设键值 | 名称 | 动量窗口（权重） | 其他配置 |
| --- | --- | --- | --- |
| `slow-core` | 慢腿·核心监控 | 63-21 / 126-21（0.5/0.5） | Corr 60 · Chop 14 · 趋势 90 · 排名回溯 5 |
| `blend-dual` | 双窗·综合视角 | 63-21 / 126-21 / 252-21（0.4/0.3/0.3） | Corr 60 · Chop 14 · 趋势 60 · 回溯 5 |
| `macro-oversight` | 宏观长波 | 120-21 / 240-21（等权） | Corr 90 · Chop 20 · 趋势 120 · 回溯 10 |
| `twelve-minus-one` | 12M-1M 长周期 | 252-21（等权） | Corr 120 · Chop 20 · 趋势 180 · 回溯 10 |

> 备注：选择预设后仍可覆盖任意参数（窗口、权重、Chop、趋势、排名回溯等），命令行和交互模式都会套用更新值。

### 命令行参数

- `--preset`: 选择预设券池，可多选，例如 `--preset core,satellite`。
- `--etfs`: 自定义 ETF 列表（会与预设合并）。
- `--exclude`: 排除不想统计的 ETF。
- `--analysis-preset`: 选择分析预设（如 `slow-core`、`blend-dual`、`twelve-minus-one`）。
- `--start` / `--end`: 分析区间。
- `--momentum-windows`: 自定义动量窗口（默认沿用预设或 `60,120`）。
- `--momentum-weights`: 对应权重，权重之和会自动归一化。
- `--corr-window` / `--chop-window` / `--trend-window` / `--rank-lookback`: 覆盖预设的高级参数。
- `--no-plot`: 仅输出文本，不生成图表。
- `--export-csv`: 将汇总表和相关矩阵导出到 `results/` 目录。
- `--run-backtest`: 使用所选预设执行简易动量回测。
- `--lang`: 输出语言（`zh` 或 `en`），默认中文。

## 输出内容

1. 最新动量得分、排名、排名变动、200 日均线、Choppiness、趋势斜率、ATR、VWAP 等指标（中文列名）。
2. ETF 之间的滚动收益率相关系数矩阵。
3. 运行耗时估计、生成的图表路径（如启用）。

图表默认保存在 `results/momentum_scores.png` 等文件中，可用于后续前端展示。
