from __future__ import annotations

"""
简单的日志工具封装。

基于标准库 logging，提供统一的 logger 初始化函数，
便于后续扩展为 JSON 行日志等。
"""

import logging
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str = "alleschools",
    level: str = "INFO",
    log_to_stderr: bool = True,
    json_log_path: Optional[Path] = None,
) -> logging.Logger:
    """
    初始化并返回一个 logger。

    - 默认输出到 stderr，格式为 "[LEVEL] message"
    - 如提供 json_log_path，则额外写入一份简单 JSON 行日志
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False

    if not logger.handlers and log_to_stderr:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(stream_handler)

    if json_log_path is not None:
        json_log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(json_log_path, encoding="utf-8")
        fmt = '{"ts": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}'
        file_handler.setFormatter(
            logging.Formatter(fmt, datefmt="%Y-%m-%dT%H:%M:%S")
        )
        logger.addHandler(file_handler)

    return logger


__all__ = ["setup_logger"]

