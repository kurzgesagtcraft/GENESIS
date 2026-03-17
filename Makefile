# GENESIS Makefile
# 常用命令集合

.PHONY: help setup install dev-install test lint format clean all

# 默认目标
.DEFAULT_GOAL := help

# 帮助信息
help: ## 显示帮助信息
	@echo "GENESIS - 机器人自复制仿真系统"
	@echo ""
	@echo "可用命令:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# 安装
setup: ## 创建 conda 环境
	@echo "创建 genesis_env 环境..."
	conda env create -f environment.yml || conda env update -f environment.yml

install: ## 安装依赖
	@echo "安装依赖..."
	pip install -e .

dev-install: ## 安装开发依赖
	@echo "安装开发依赖..."
	pip install -e ".[dev]"

# 测试
test: ## 运行所有测试
	@echo "运行测试..."
	pytest tests/ -v --cov=genesis --cov-report=term-missing

test-unit: ## 运行单元测试
	pytest tests/unit/ -v

test-integration: ## 运行集成测试
	pytest tests/integration/ -v --timeout=300

test-gpu: ## 运行 GPU 测试
	pytest tests/ -v -m gpu

# 代码质量
lint: ## 代码检查
	@echo "运行 ruff 检查..."
	ruff check src/ tests/
	@echo "运行 mypy 类型检查..."
	mypy src/genesis/

format: ## 格式化代码
	@echo "格式化代码..."
	black src/ tests/
	ruff check --fix src/ tests/

format-check: ## 检查代码格式
	black --check src/ tests/
	ruff check src/ tests/

# 清理
clean: ## 清理构建产物
	@echo "清理..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .coverage coverage.xml

# 运行
run: ## 启动仿真
	python scripts/launch_world.py

run-headless: ## 无头模式启动
	python scripts/launch_world.py --headless

# Docker
docker-build: ## 构建 Docker 镜像
	docker build -t genesis-sim:latest -f docker/Dockerfile .

docker-run: ## 运行 Docker 容器
	docker run --gpus all -it --rm genesis-sim:latest

# 文档
docs: ## 生成文档
	cd docs && make html

docs-serve: ## 启动文档服务器
	cd docs && make html && python -m http.server 8000 -d _build/html

# 数据
download-assets: ## 下载资产文件
	python scripts/download_assets.py

# 全部
all: clean install test lint ## 运行完整流程
