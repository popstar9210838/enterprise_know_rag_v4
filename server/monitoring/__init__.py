"""
监控与日志模块。

Usage:
    from server.monitoring import setup_logging
    setup_logging(config)
"""
from .logging_config import setup_logging

__all__ = ["setup_logging"]