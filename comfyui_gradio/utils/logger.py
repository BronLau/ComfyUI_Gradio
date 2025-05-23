import logging
import logging.handlers
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import importlib.util

# 确保 Windows 环境下的标准输出使用 UTF-8
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# 导入路径辅助工具
from comfyui_gradio.utils.path_helper import setup_project_path, get_logs_dir

# 设置项目路径
setup_project_path()

# 日志文件的标准格式
LOG_FILENAME_FORMAT = "{service_name}_{date}.log"

# 日志文件的最大大小（字节）
# 10MB
MAX_LOG_SIZE = 10 * 1024 * 1024

# 日志文件的最大备份数量
# 当日志文件达到最大大小时，会创建一个新的日志文件，旧的日志文件会被重命名为 .1, .2 等
# 当备份数量超过这个值时，最旧的备份会被删除
BACKUP_COUNT = 5

# 日志保留天数，超过这个天数的日志文件会被删除
LOG_RETENTION_DAYS = 30

# 日志存档目录
ARCHIVE_DIR = "logs/archive"

# 全局日志管理器实例
_log_manager = None


def get_log_manager():
    """获取LogManager实例"""
    global _log_manager
    if _log_manager is None:
        try:
            # 获取项目根目录
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
            log_manager_path = os.path.join(root_dir, 'scripts', 'log_manager.py')

            # 动态导入 log_manager.py
            spec = importlib.util.spec_from_file_location("log_manager", log_manager_path)
            log_manager_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(log_manager_module)

            # 创建 LogManager 实例
            _log_manager = log_manager_module.LogManager(
                log_dir='logs',
                max_size_mb=MAX_LOG_SIZE // (1024 * 1024),  # 转换为 MB
                max_days=LOG_RETENTION_DAYS
            )
        except Exception as e:
            print(f"导入 log_manager.py 失败: {e}")
            _log_manager = None
    
    return _log_manager


def clean_old_logs():
    """清理旧日志文件（委托给LogManager）"""
    log_manager = get_log_manager()
    if log_manager:
        try:
            removed_count = log_manager.clean_old_logs()
            print(f"清理旧日志文件完成，共删除 {removed_count} 个文件")
            return removed_count
        except Exception as e:
            print(f"清理旧日志文件失败: {e}")
    else:
        # 使用原来的清理机制，简化代码，只保留主要功能
        try:
            log_dir_path = get_logs_dir()
            if not log_dir_path.exists():
                return 0

            # 计算删除日期的时间戳
            cutoff_date = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
            cutoff_timestamp = cutoff_date.timestamp()

            # 创建存档目录（如果不存在）
            archive_dir = Path(ARCHIVE_DIR)
            archive_dir.mkdir(parents=True, exist_ok=True)

            removed_count = 0
            # 遍历日志目录中的所有文件
            for file_path in log_dir_path.glob("*.log*"):
                # 如果是当天的日志文件，跳过
                if datetime.now().strftime("%Y%m%d") in file_path.name:
                    continue

                # 获取文件的修改时间
                file_mtime = file_path.stat().st_mtime

                # 如果文件的修改时间早于删除日期
                if file_mtime < cutoff_timestamp:
                    # 将文件移动到存档目录
                    archive_path = archive_dir / file_path.name
                    try:
                        shutil.move(str(file_path), str(archive_path))
                        print(f"已将过期日志文件 {file_path.name} 移动到存档目录")
                        removed_count += 1
                    except Exception as e:
                        print(f"移动日志文件失败: {e}")
            
            return removed_count
        except Exception as e:
            print(f"清理旧日志文件失败: {e}")
            return 0


def compress_logs():
    """压缩日志文件（委托给LogManager）"""
    log_manager = get_log_manager()
    if log_manager:
        try:
            compressed_count = log_manager.compress_logs()
            print(f"压缩存档日志完成，共压缩 {compressed_count} 个文件")
            return compressed_count
        except Exception as e:
            print(f"压缩存档日志失败: {e}")
            return 0
    else:
        print("未找到LogManager，跳过压缩日志")
        return 0


def run_log_maintenance():
    """执行日志维护（委托给LogManager）"""
    log_manager = get_log_manager()
    if log_manager:
        return log_manager.run_maintenance()
    else:
        # 简单执行清理和压缩
        clean_old_logs()
        compress_logs()
        return True


def setup_logger(name: str, log_dir: str = "logs",
                 level: int = logging.INFO,
                 max_bytes: int = MAX_LOG_SIZE,
                 backup_count: int = BACKUP_COUNT) -> logging.Logger:
    """配置日志记录器，支持日志轮转，使用标准化的文件名格式"""
    # 创建日志目录
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 清除现有的处理器
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(console_handler)

    # 生成标准格式的日志文件名
    date_str = datetime.now().strftime("%Y%m%d")
    log_filename = LOG_FILENAME_FORMAT.format(
        service_name=name,
        date=date_str
    )
    log_path = log_dir / log_filename

    # 文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)

    return logger

# 保留原函数用于向后兼容
def compress_archive_logs(archive_dir: str = ARCHIVE_DIR) -> None:
    """
    压缩存档目录中的日志文件
    
    已废弃，请使用compress_logs()函数
    
    Args:
        archive_dir: 存档目录
    """
    return compress_logs()
