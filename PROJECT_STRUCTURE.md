# 项目结构说明

## 目录结构

```
momentum-lens/
├── backend/              # 后端服务 (FastAPI)
│   ├── api/             # API路由
│   ├── core/            # 核心业务逻辑
│   ├── config/          # 配置管理
│   ├── middleware/      # 中间件（认证、限流）
│   ├── models/          # 数据模型
│   ├── routers/         # API路由
│   ├── schemas/         # Pydantic模式
│   └── utils/           # 工具函数
│
├── frontend/            # 前端应用 (React)
│   ├── public/          # 静态资源
│   ├── src/             # 源代码
│   │   ├── components/  # React组件
│   │   ├── hooks/       # 自定义Hooks
│   │   ├── pages/       # 页面组件
│   │   ├── services/    # API服务
│   │   └── utils/       # 工具函数
│   └── package.json     # 依赖配置
│
├── docs/                # 文档目录
│   ├── guides/          # 使用指南
│   │   ├── PRD.md      # 产品需求文档
│   │   ├── README-DEPLOYMENT.md  # 部署指南
│   │   └── FEEDBACK.md # 反馈记录
│   ├── improvements/    # 改进文档
│   │   ├── CODE_IMPROVEMENTS.md  # 代码改进
│   │   ├── BUG_FIXES_SUMMARY.md  # Bug修复
│   │   └── IMPROVEMENT_PLAN.md   # 改进计划
│   └── technical/       # 技术文档
│       └── CLAUDE.md    # 架构文档
│
├── tests/               # 测试文件
│   ├── scripts/         # 测试脚本
│   └── html/            # 测试页面
│
├── scripts/             # 实用脚本
│   ├── fix_all.sh      # 修复脚本
│   └── ...             # 其他脚本
│
├── monitoring/          # 监控配置
├── nginx/              # Nginx配置
├── data/               # 数据文件
│
├── .env.example        # 环境变量示例
├── .gitignore          # Git忽略文件
├── docker-compose.yml  # Docker配置
├── README.md           # 项目说明
├── start.sh            # 启动脚本
├── quickstart.sh       # 快速启动
└── stop-all.sh         # 停止脚本
```

## 主要脚本说明

### 启动脚本
- `start.sh` - 标准启动脚本，包含依赖检查
- `quickstart.sh` - 快速启动脚本，跳过依赖安装
- `stop-all.sh` - 停止所有服务

### Docker相关
- `docker-compose.yml` - 主要Docker配置
- `docker-compose.monitoring.yml` - 监控服务配置

## 快速开始

1. **开发环境启动**
```bash
./quickstart.sh
```

2. **生产环境启动**
```bash
docker-compose up -d
```

3. **停止服务**
```bash
./stop-all.sh
```

## 访问地址

- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs