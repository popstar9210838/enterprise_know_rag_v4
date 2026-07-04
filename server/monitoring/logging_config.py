"""
统一日志配置 —— 替换所有模块中的裸 print()。

控制点（config.yaml → monitoring）：
  - log_level         → root logger 输出阈值
  - log_format         → "text" 或 "json"
  - log_file           → 日志文件路径（空字符串 = 不写文件）
  - log_max_bytes      → 单个日志文件最大字节数，超出提前轮转
  - log_backup_count   → 保留的历史日志文件数量
"""

import json
import logging
import logging.handlers
import os
import sys


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({
            "ts": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }, ensure_ascii=False)


class _DateSizeRotatingHandler(logging.handlers.TimedRotatingFileHandler):
    """按日期轮转 + 大小上限：优先每日切分，当天文件超 max_bytes 也提前切。"""

    def __init__(self, filename, max_bytes=0, **kwargs):
        super().__init__(filename, **kwargs)
        self.max_bytes = max_bytes

    def shouldRollover(self, record):
        if super().shouldRollover(record):
            return True
        if self.max_bytes > 0 and self.stream is not None:
            try:
                if os.path.getsize(self.baseFilename) >= self.max_bytes:
                    return True
            except OSError:
                pass
        return False


def setup_logging(config) -> None:
    """配置根 logger，所有模块（含第三方库）自动继承。"""
    level = getattr(logging, config.monitoring.log_level.upper(), logging.INFO)

    fmt = config.monitoring.log_format
    if fmt == "json":
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )

    root = logging.getLogger()
    root.setLevel(level)

    # 控制台输出
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        root.addHandler(console)

    # 文件持久化（可选）
    log_file = config.monitoring.log_file
    if log_file:
        log_dir = os.path.dirname(os.path.abspath(log_file))
        os.makedirs(log_dir, exist_ok=True)
        file_handler = _DateSizeRotatingHandler(
            filename=log_file,
            max_bytes=config.monitoring.log_max_bytes,
            when="midnight",
            interval=1,
            backupCount=config.monitoring.log_backup_count,
            encoding="utf-8",
            utc=False,
        )
        file_handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        ))
        file_handler.setLevel(level)
        root.addHandler(file_handler)

    # uvicorn 自带独立的日志配置，清除其 handler 让它走我们的根 logger
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv = logging.getLogger(name)
        uv.handlers.clear()
        uv.propagate = True

    # 第三方库压到 WARNING，避免刷屏
    logging.getLogger("llama_index").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("jieba").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("huggingface_hub").setLevel(logging.WARNING)
    logging.getLogger("tokenizers").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    logging.getLogger("llama_index.core.readers.file.base").setLevel(logging.ERROR)