# Momentum Lens Makefile
# 项目自动化构建和管理

.PHONY: help setup install clean test run app backtest export docker-build docker-up docker-down

# 默认目标
help:
	@echo "Momentum Lens - 可用命令:"
	@echo ""
	@echo "  make setup      - 初始化项目环境"
	@echo "  make install    - 安装依赖"
	@echo "  make app        - 启动Streamlit应用"
	@echo "  make backtest   - 运行回测"
	@echo "  make export     - 生成交易清单"
	@echo "  make test       - 运行测试"
	@echo "  make clean      - 清理临时文件"
	@echo "  make docker-build - 构建Docker镜像"
	@echo "  make docker-up  - 启动Docker容器"
	@echo "  make docker-down - 停止Docker容器"

# 初始化项目环境
setup:
	@echo "🚀 初始化项目环境..."
	python3 -m venv venv
	./venv/bin/pip install --upgrade pip
	./venv/bin/pip install -r requirements.txt
	@echo "✅ 环境初始化完成"

# 安装依赖
install:
	@echo "📦 安装项目依赖..."
	pip install -r requirements.txt
	@echo "✅ 依赖安装完成"

# 启动Streamlit应用
app:
	@echo "🎯 启动Momentum Lens应用..."
	python -m backend --server.port 8501 --server.address 0.0.0.0

# 运行回测
backtest:
	@echo "📊 运行策略回测..."
	python backend/backtests/run_backtest.py
	@echo "✅ 回测完成，报告已生成"

# 生成交易清单
export:
	@echo "📋 生成周二交易清单..."
	python backend/orders/generate_orders.py
	@echo "✅ 交易清单已导出到 exports/ 目录"

# 运行测试
test:
	@echo "🧪 运行测试套件..."
	pytest tests/ -v --cov=backend --cov-report=html --cov-report=term
	@echo "✅ 测试完成，覆盖率报告已生成"

# 运行特定测试
test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

# 代码质量检查
lint:
	@echo "🔍 检查代码质量..."
	flake8 backend/ --max-line-length=120
	black backend/ --check
	mypy backend/ --ignore-missing-imports

# 格式化代码
format:
	@echo "✨ 格式化代码..."
	black backend/
	@echo "✅ 代码格式化完成"

# 清理临时文件
clean:
	@echo "🧹 清理临时文件..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf exports/*.csv exports/*.pdf
	@echo "✅ 清理完成"

# Docker相关命令
docker-build:
	@echo "🐳 构建Docker镜像..."
	docker-compose build
	@echo "✅ Docker镜像构建完成"

docker-up:
	@echo "🚀 启动Docker容器..."
	docker-compose up -d
	@echo "✅ 服务已启动"
	@echo "访问: http://localhost:8501"

docker-down:
	@echo "🛑 停止Docker容器..."
	docker-compose down
	@echo "✅ 服务已停止"

# 开发模式
dev:
	@echo "💻 启动开发模式..."
	python run_app.py

# 数据库初始化
db-init:
	@echo "🗄️ 初始化数据库..."
	python backend/utils/init_db.py
	@echo "✅ 数据库初始化完成"

# 生成文档
docs:
	@echo "📚 生成项目文档..."
	sphinx-build -b html docs/ docs/_build/
	@echo "✅ 文档已生成到 docs/_build/"

# 部署到生产环境
deploy:
	@echo "🚀 部署到生产环境..."
	./scripts/deploy.sh
	@echo "✅ 部署完成"

# 版本信息
version:
	@echo "Momentum Lens v1.0.0"
	@python --version
	@pip show streamlit | grep Version