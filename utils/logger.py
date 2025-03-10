import logging
import sys
from pathlib import Path
from datetime import datetime

# 确保 Windows 环境下的标准输出使用 UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def setup_logger(name: str, log_dir: str = "logs",
                 level: int = logging.INFO) -> logging.Logger:
    """
    配置日志记录器

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        level: 日志级别
    Returns:
        logging.Logger对象
    """
    # 创建日志目录
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    # 获取或创建logger
    logger = logging.getLogger(name)

    # 如果logger已经有处理器，说明已经配置过，直接返回
    if logger.handlers:
        return logger

    # 设置日志级别
    logger.setLevel(level)

    # 创建日志文件路径
    log_file = log_dir / f"{name}_{datetime.now():%Y%m%d}.log"

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建并配置文件处理器
    file_handler = logging.FileHandler(
        log_file,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)

    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 添加处理器到logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # 防止日志向上传递
    logger.propagate = False

    return logger
