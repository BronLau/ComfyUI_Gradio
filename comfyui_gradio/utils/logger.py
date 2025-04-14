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


def get_log_manager():
    """
    动态导入 log_manager.py 并返回 LogManager 实例
    """
    try:
        # 获取项目根目录
        root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
        log_manager_path = os.path.join(root_dir, 'scripts', 'log_manager.py')

        # 动态导入 log_manager.py
        spec = importlib.util.spec_from_file_location("log_manager", log_manager_path)
        log_manager_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(log_manager_module)

        # 创建 LogManager 实例
        return log_manager_module.LogManager(
            log_dir='logs',
            max_size_mb=MAX_LOG_SIZE // (1024 * 1024),  # 转换为 MB
            max_days=LOG_RETENTION_DAYS
        )
    except Exception as e:
        print(f"导入 log_manager.py 失败: {e}")
        return None


def clean_old_logs(log_dir: str = "logs",
                   retention_days: int = LOG_RETENTION_DAYS) -> None:
    """
    清理超过保留天数的日志文件

    Args:
        log_dir: 日志文件目录
        retention_days: 日志保留天数
    """
    # 使用 log_manager.py 中的机制
    log_manager = get_log_manager()
    if log_manager:
        try:
            removed_count = log_manager.clean_old_logs()
            print(f"清理旧日志文件完成，共删除 {removed_count} 个文件")
        except Exception as e:
            print(f"清理旧日志文件失败: {e}")
    else:
        # 如果无法导入 log_manager.py，则使用原来的机制
        try:
            log_dir_path = Path(log_dir)
            if not log_dir_path.exists():
                return

            # 计算删除日期的时间戳
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cutoff_timestamp = cutoff_date.timestamp()

            # 创建存档目录（如果不存在）
            archive_dir = Path(ARCHIVE_DIR)
            archive_dir.mkdir(parents=True, exist_ok=True)

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
                    except Exception as e:
                        print(f"移动日志文件失败: {e}")
        except Exception as e:
            print(f"清理旧日志文件失败: {e}")


def compress_archive_logs(archive_dir: str = ARCHIVE_DIR) -> None:
    """
    压缩存档目录中的日志文件

    Args:
        archive_dir: 存档目录
    """
    # 使用 log_manager.py 中的机制
    log_manager = get_log_manager()
    if log_manager:
        try:
            log_manager.compress_logs()
            print("压缩存档日志完成")
        except Exception as e:
            print(f"压缩存档日志失败: {e}")
    else:
        # 如果无法导入 log_manager.py，则使用原来的机制
        try:
            archive_path = Path(archive_dir)
            if not archive_path.exists():
                return

            # 按月份对日志文件进行分组
            monthly_logs = {}

            for file_path in archive_path.glob("*.log*"):
                # 尝试从文件名中提取日期
                try:
                    # 假设文件名格式为 name_YYYYMMDD.log
                    date_part = file_path.stem.split('_')[-1]
                    if len(date_part) == 8 and date_part.isdigit():
                        year_month = date_part[:6]  # YYYYMM
                        if year_month not in monthly_logs:
                            monthly_logs[year_month] = []
                        monthly_logs[year_month].append(file_path)
                except Exception:
                    # 如果无法从文件名中提取日期，跳过该文件
                    continue

            # 对每个月份的日志文件进行压缩
            for year_month, files in monthly_logs.items():
                # 如果该月份的压缩文件已存在，跳过
                zip_file = archive_path / f"logs_{year_month}.zip"
                if zip_file.exists():
                    continue

                # 创建一个临时目录来存放要压缩的文件
                temp_dir = archive_path / f"temp_{year_month}"
                temp_dir.mkdir(exist_ok=True)

                # 复制文件到临时目录
                for file_path in files:
                    try:
                        shutil.copy2(str(file_path), str(
                            temp_dir / file_path.name))
                    except Exception as e:
                        print(f"复制文件失败: {e}")
                        continue

                # 压缩临时目录
                try:
                    shutil.make_archive(
                        str(zip_file.with_suffix('')), 'zip', str(temp_dir))
                    print(f"已创建压缩文件: {zip_file}")

                    # 删除原始文件
                    for file_path in files:
                        try:
                            os.remove(str(file_path))
                        except Exception as e:
                            print(f"删除文件失败: {e}")
                except Exception as e:
                    print(f"压缩文件失败: {e}")

                # 删除临时目录
                try:
                    shutil.rmtree(str(temp_dir))
                except Exception as e:
                    print(f"删除临时目录失败: {e}")
        except Exception as e:
            print(f"压缩存档日志失败: {e}")


def setup_logger(name: str, log_dir: str = "logs",
                 level: int = logging.INFO,
                 max_bytes: int = MAX_LOG_SIZE,
                 backup_count: int = BACKUP_COUNT) -> logging.Logger:
    """
    配置日志记录器，支持日志轮转

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        level: 日志级别
        max_bytes: 日志文件的最大大小（字节）
        backup_count: 日志文件的最大备份数量
    Returns:
        logging.Logger对象
    """
    # 使用 log_manager.py 中的机制进行日志维护
    log_manager = get_log_manager()
    if log_manager:
        try:
            # 运行日志维护任务
            log_manager.run_maintenance()
        except Exception as e:
            print(f"日志维护失败: {e}")
    else:
        # 如果无法导入 log_manager.py，则使用原来的机制
        # 清理旧日志文件
        clean_old_logs(log_dir)

        # 压缩存档日志
        compress_archive_logs()

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

    # 创建日期目录
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    date_dir = log_dir / date_str
    date_dir.mkdir(exist_ok=True)

    # 创建日志文件路径，使用当前日期作为后缀
    log_file = date_dir / f"{name}_{today:%Y%m%d}.log"

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 创建并配置日志轮转文件处理器
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
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
