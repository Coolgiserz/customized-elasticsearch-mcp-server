# 使用Python 3.12 精简版镜像
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/ghcr.io/astral-sh/uv:python3.12-bookworm-slim
# 设置工作目录
WORKDIR /app

# 重写 apt 源为 USTC 镜像并安装 curl
RUN echo "deb http://mirrors.ustc.edu.cn/debian bookworm main contrib non-free" > /etc/apt/sources.list \
    && echo "deb http://mirrors.ustc.edu.cn/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list \
    && echo "deb http://mirrors.ustc.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock /app

ENV UV_PYPI_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
# 安装 Python 依赖
# 优先使用 uv（如有 uv.lock），否则用 pip 安装 requirements.txt
RUN pip install -i https://mirrors.aliyun.com/pypi/simple uv  && uv sync

# 复制项目文件到容器
COPY ./src/ /app
# 暴露服务端口
EXPOSE 8000

# 启动 MCP Server
CMD ["/app/.venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
