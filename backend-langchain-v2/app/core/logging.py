import logging
import sys


def setup_logging(debug: bool = False) -> None:
    """配置系统标准输出的结构化日志格式"""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """获取标准 Logger"""
    return logging.getLogger(name)
