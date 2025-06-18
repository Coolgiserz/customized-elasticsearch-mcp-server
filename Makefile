# Makefile for Customized ElasticSearch MCP Server

# 镜像名称和标签
IMAGE_NAME ?= customized-elasticsearch-mcp-server
TAG ?= latest

.PHONY: help init sync dev test lint format build docker-build docker-up docker-down docker-logs clean

help:
	@echo "Usage:"
	@echo "  make init         初始化项目依赖 (uv init)"
	@echo "  make sync         同步依赖 (uv sync)"
	@echo "  make dev          启动开发服务器 (uvicorn 热重载)"
	@echo "  make test         运行单元测试"
	@echo "  make lint         代码检查 (flake8)"
	@echo "  make format       代码格式化 (isort & black)"
	@echo "  make build        本地构建 Docker 镜像"
	@echo "  make docker-build 使用 docker-compose 构建镜像"
	@echo "  make docker-up    使用 docker-compose 启动服务"
	@echo "  make docker-down  使用 docker-compose 停止服务"
	@echo "  make docker-logs  查看服务日志"
	@echo "  make clean        清理 Python 缓存和临时文件"

init:
	uv init

sync:
	uv sync

dev:
	uv run uvicorn src.news_mcp_server.app:app --reload --host 0.0.0.0 --port 9009

test:
	uv run pytest --maxfail=1 --disable-warnings -q

lint:
	uv run flake8 src tests

format:
	uv run isort .
	uv run black .

build:
	docker build -t $(IMAGE_NAME):$(TAG) .

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

clean:
	@find . -type f -name "*.py[co]" -delete || true
	@find . -type d -name "__pycache__" -exec rm -rf {} + || true 