import os
import logging
from pathlib import Path
from structlog import get_logger
from logging.handlers import TimedRotatingFileHandler
BASE_DIR = Path(__file__).parent.parent.parent


logger = get_logger("suwen-news-mcp-server")
# === 文件日志处理器 ===
LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_DIR, "logs"))
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "es_news_mcp_server.log")

# === 标准库日志根配置 ===
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# 控制台 Handler（保留 JSON 格式）
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(message)s"))

# 文件 Handler：每日 0 点轮转，保留 7 天
file_handler = TimedRotatingFileHandler(LOG_FILE, when="midnight", backupCount=7, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(message)s"))

# 仅在首次配置时添加（防止重复）
if not root_logger.handlers:
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
