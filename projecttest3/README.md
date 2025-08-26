# Momentum Lens - A股ETF动量决策系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.48+-red)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

## 📊 项目简介

Momentum Lens 是一套完整的 A股 ETF 动量投资决策系统，集成了数据抓取、指标计算、策略引擎、回测评估和可视化决策台。系统采用 Core/Satellite 配置策略，结合可转债网格交易，提供半自动化的投资决策支持。

### 🎯 核心功能

- **动量策略引擎**：基于双窗口（3个月/6个月）动量因子的ETF选择
- **智能状态机**：根据市场环境自动切换进攻/中性/防守模式
- **Core/Satellite配置**：动态调整核心资产与卫星资产比例
- **可转债网格交易**：多维度评分系统筛选可转债，自动计算网格参数
- **数据源降级机制**：AkShare → 新浪财经 → 东方财富，确保系统高可用
- **实时可视化界面**：基于Streamlit的Web决策台
- **一键导出功能**：生成周二下单清单（CSV/PDF）

## 🚀 快速开始

### 环境要求

- Python 3.11+
- pip 或 conda
- Git

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/momentum-lens.git
cd momentum-lens/projecttest3
```

2. **安装依赖**
```bash
# 使用setup脚本（推荐）
./setup.sh

# 或手动安装
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **启动应用**
```bash
# 使用Makefile
make app

# 或直接运行
streamlit run backend/app_enhanced.py
```

4. **访问界面**
打开浏览器访问：http://localhost:8502

## 🏗️ 项目结构

```
momentum-lens/
├── backend/
│   ├── adapters/          # 数据源适配器
│   │   ├── base.py        # 抽象基类
│   │   ├── akshare_adapter.py
│   │   ├── sina_adapter.py
│   │   └── eastmoney_adapter.py
│   ├── indicators/        # 技术指标计算
│   │   ├── technical.py  # MA, ATR, RSI等
│   │   ├── market_env.py # 市场环境分析
│   │   ├── momentum.py   # 动量计算
│   │   ├── correlation.py # 相关性分析
│   │   └── convertible.py # 可转债评分
│   ├── engine/           # 策略引擎
│   │   ├── state_machine.py # 三态状态机
│   │   ├── strategy.py   # 动量策略
│   │   └── rotation.py   # 轮动管理
│   ├── data/
│   │   └── convertible_bonds.py # 可转债数据
│   ├── config/           # 配置文件
│   │   ├── config.yaml   # 主配置
│   │   └── etf_universe.yaml # ETF池
│   └── app_enhanced.py   # Streamlit应用
├── tests/                # 测试用例
├── docker/              # Docker配置
├── exports/             # 导出文件
├── logs/                # 日志文件
└── requirements.txt     # 依赖包
```

## 🔧 核心算法

### 动量评分公式
```python
Score = 0.6 * rank(r63) + 0.4 * rank(r126) + Bonus_div - Penalty
```
- r63: 3个月收益率
- r126: 6个月收益率
- Bonus_div: 多样性加分（低相关性）
- Penalty: 费率和溢价扣分

### CHOP震荡指标
```python
CHOP = 100 * log10(sum(TR,N) / (High(N)-Low(N))) / log10(N)
```
- N=30天
- CHOP ≥ 61 视为震荡市

### 可转债网格步长
```python
g = clamp(2% + 1.5*(ATR10/close - 2%), 2%, 5%)
```

## 📈 策略说明

### 市场状态机

| 状态 | 条件 | Core比例 | Satellite比例 | 持仓数 |
|------|------|----------|--------------|--------|
| OFFENSE | MA200上方、低CHOP、低波动 | 30% | 70% | 4 |
| NEUTRAL | 中性市场环境 | 50% | 50% | 3 |
| DEFENSE | MA200下方或高回撤 | 70% | 30% | 2 |

### 两条腿策略
- 选择动量得分最高的两个ETF
- 相关性约束：ρ ≤ 0.7
- 最短持有期：2周（震荡市4周）
- 止损线：-10%（进攻）/-12%（中性）/-15%（防守）

## 📊 ETF候选池

系统包含80+个ETF，覆盖以下类别：
- 🎮 游戏动漫文娱
- 💻 科技创新
- ⚡ 新能源产业链
- 🛍️ 消费行业
- 💊 医药健康
- 🏦 金融地产
- 🏭 周期资源
- 🛡️ 军工安防
- 🏗️ 基建出口

## 🔄 可转债评分体系

| 维度 | 权重 | 说明 |
|------|------|------|
| 溢价率 | 25% | 负溢价得高分 |
| 双低值 | 20% | 价格+溢价率越低越好 |
| 信用评级 | 15% | AAA到A-分级 |
| 规模 | 10% | 10-50亿最优 |
| YTM | 10% | 2-4%最优 |
| 流动性 | 10% | 成交量越大越好 |
| PB比率 | 10% | 0.8-1.5最优 |

## 🛠️ 命令说明

```bash
# 开发命令
make setup      # 初始化环境
make app        # 启动应用
make test       # 运行测试
make backtest   # 运行回测
make export     # 导出清单

# Docker部署
make docker-build  # 构建镜像
make docker-up     # 启动容器
make docker-down   # 停止容器
```

## 📱 界面功能

1. **环境灯**：实时显示市场状态（进攻🟢/中性🟡/防守🔴）
2. **动量排名**：Top 20 ETF动量排名，含相关性分析
3. **推荐组合**：智能推荐两条腿配置，显示选择理由
4. **可转债网格**：50+可转债筛选评分，网格参数计算
5. **回测分析**：2020-2025完整回测，月度收益热力图
6. **导出清单**：一键生成周二下单清单

## 🔒 风险提示

- 本系统仅供学习研究使用，不构成投资建议
- 历史业绩不代表未来表现
- 投资有风险，入市需谨慎

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 作者：[Your Name]
- Email：[your.email@example.com]
- 项目链接：[https://github.com/yourusername/momentum-lens](https://github.com/yourusername/momentum-lens)

## 🙏 致谢

- [AkShare](https://github.com/akfamily/akshare) - A股数据接口
- [Streamlit](https://streamlit.io/) - Web应用框架
- [Backtrader](https://www.backtrader.com/) - 回测引擎

---
⭐ 如果这个项目对你有帮助，请给个Star支持一下！