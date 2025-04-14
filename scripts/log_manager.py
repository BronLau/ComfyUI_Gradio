#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
日志管理工具 - 用于管理日志文件，包括轮转、压缩和清理
"""

import os
import sys
import time
import shutil
import gzip
from pathlib import Path
from datetime import datetime, timedelta
import argparse
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join('logs', 'log_manager.log'),
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('log_manager')


class LogManager:
    def __init__(self, log_dir='logs', max_size_mb=10, max_days=30):
        """初始化日志管理器

        Args:
            log_dir: 日志目录
            max_size_mb: 日志文件最大大小（MB）
            max_days: 日志文件最大保留天数
        """
        self.log_dir = Path(log_dir)
        self.max_size_mb = max_size_mb
        self.max_days = max_days

        # 确保日志目录存在
        self.log_dir.mkdir(exist_ok=True)

        logger.info(f"日志管理器初始化完成，日志目录：{self.log_dir}")
        logger.info(f"日志文件最大大小：{self.max_size_mb}MB")
        logger.info(f"日志文件最大保留天数：{self.max_days}天")

    def get_log_files(self):
        """获取所有日志文件"""
        # 获取根目录下的日志文件
        root_logs = list(self.log_dir.glob('*.log'))

        # 获取日期子目录下的日志文件
        date_dir_logs = []
        for date_dir in self.log_dir.glob('????-??-??'):
            if date_dir.is_dir():
                date_dir_logs.extend(list(date_dir.glob('*.log')))

        return root_logs + date_dir_logs

    def get_archive_files(self):
        """获取所有归档文件"""
        # 获取根目录下的归档文件
        root_archives = list(self.log_dir.glob('*.gz'))

        # 获取日期子目录下的归档文件
        date_dir_archives = []
        for date_dir in self.log_dir.glob('????-??-??'):
            if date_dir.is_dir():
                date_dir_archives.extend(list(date_dir.glob('*.gz')))

        return root_archives + date_dir_archives

    def get_date_from_filename(self, filename):
        """从文件名中提取日期

        尝试从文件名中提取日期，格式可能是：
        1. name_YYYYMMDD.log
        2. name_YYYY-MM-DD.log
        3. 其他包含日期的格式

        Args:
            filename: 文件名

        Returns:
            str: 日期字符串（YYYY-MM-DD格式），如果无法提取则返回None
        """
        try:
            # 尝试从文件名中提取日期
            stem = Path(filename).stem

            # 尝试匹配 name_YYYYMMDD 格式
            date_part = stem.split('_')[-1]
            if len(date_part) == 8 and date_part.isdigit():
                # 转换为 YYYY-MM-DD 格式
                return f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"

            # 尝试匹配 name_YYYY-MM-DD 格式
            for part in stem.split('_'):
                if len(part) == 10 and part[4] == '-' and part[7] == '-':
                    return part

            # 如果无法提取，则使用当前日期
            return datetime.now().strftime('%Y-%m-%d')
        except Exception:
            # 如果出现异常，则使用当前日期
            return datetime.now().strftime('%Y-%m-%d')

    def organize_logs_by_date(self):
        """按日期组织日志文件

        将根目录下的日志文件移动到对应的日期目录中
        """
        logger.info("开始按日期组织日志文件...")

        organized_count = 0
        # 只处理根目录下的日志文件
        for log_file in list(self.log_dir.glob('*.log')):
            try:
                # 从文件名中提取日期
                date_str = self.get_date_from_filename(log_file)

                # 创建日期目录
                date_dir = self.log_dir / date_str
                date_dir.mkdir(exist_ok=True)

                # 移动文件到日期目录
                new_path = date_dir / log_file.name
                if not new_path.exists():  # 避免覆盖已存在的文件
                    shutil.move(str(log_file), str(new_path))
                    logger.info(f"已将日志文件移动到日期目录：{log_file} -> {new_path}")
                    organized_count += 1
            except Exception as e:
                logger.error(f"组织日志文件失败：{log_file}，错误：{e}")

        logger.info(f"日志文件组织完成，共组织 {organized_count} 个文件")
        return organized_count

    def rotate_logs(self):
        """轮转日志文件"""
        logger.info("开始轮转日志文件...")

        # 先按日期组织日志文件
        self.organize_logs_by_date()

        rotated_count = 0
        for log_file in self.get_log_files():
            # 检查文件大小
            file_size_mb = log_file.stat().st_size / (1024 * 1024)
            if file_size_mb >= self.max_size_mb:
                # 从文件名中提取日期
                date_str = self.get_date_from_filename(log_file)
                date_dir = self.log_dir / date_str
                date_dir.mkdir(exist_ok=True)

                # 创建归档文件名
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive_name = f"{log_file.stem}_{timestamp}.log.gz"
                archive_path = date_dir / archive_name

                # 压缩日志文件
                try:
                    with log_file.open('rb') as f_in:
                        with gzip.open(archive_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)

                    # 清空原日志文件
                    log_file.write_text('')

                    logger.info(f"已轮转日志文件：{log_file} -> {archive_path}")
                    rotated_count += 1
                except Exception as e:
                    logger.error(f"轮转日志文件失败：{log_file}，错误：{e}")

        logger.info(f"日志轮转完成，共轮转 {rotated_count} 个文件")
        return rotated_count

    def clean_old_logs(self):
        """清理旧日志文件"""
        logger.info("开始清理旧日志文件...")

        # 计算截止日期
        cutoff_date = datetime.now() - timedelta(days=self.max_days)
        cutoff_date_str = cutoff_date.strftime('%Y-%m-%d')

        removed_count = 0

        # 清理旧的日期目录
        for date_dir in self.log_dir.glob('????-??-??'):
            if date_dir.is_dir():
                try:
                    dir_date_str = date_dir.name
                    # 如果目录日期早于截止日期，则删除整个目录
                    if dir_date_str < cutoff_date_str:
                        # 先删除目录中的所有文件
                        for file in date_dir.glob('*'):
                            file.unlink()
                        # 然后删除目录
                        date_dir.rmdir()
                        logger.info(f"已删除旧日期目录：{date_dir}")
                        removed_count += 1
                except Exception as e:
                    logger.warning(f"删除日期目录失败：{date_dir}，错误：{e}")

        # 清理归档文件
        for archive_file in self.get_archive_files():
            try:
                # 如果归档文件在日期目录中，则跳过（已经在上面的步骤中处理过）
                if any(parent.name.replace('-', '') == parent.name for parent in archive_file.parents):
                    continue

                # 从文件名中提取日期
                date_str = self.get_date_from_filename(archive_file)
                try:
                    file_date = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    # 如果无法解析日期，尝试从文件名中提取日期
                    try:
                        date_part = archive_file.stem.split('_')[-2]
                        file_date = datetime.strptime(date_part, '%Y%m%d')
                    except (ValueError, IndexError):
                        # 如果仍然无法提取日期，则跳过该文件
                        continue

                # 如果文件日期早于截止日期，则删除
                if file_date < cutoff_date:
                    archive_file.unlink()
                    logger.info(f"已删除旧归档文件：{archive_file}")
                    removed_count += 1
            except Exception as e:
                logger.warning(f"处理归档文件失败：{archive_file}，错误：{e}")

        logger.info(f"旧日志清理完成，共删除 {removed_count} 个文件/目录")
        return removed_count

    def compress_all_logs(self):
        """压缩所有日志文件"""
        logger.info("开始压缩所有日志文件...")

        compressed_count = 0
        for log_file in self.get_log_files():
            # 跳过空文件
            if log_file.stat().st_size == 0:
                continue

            # 创建归档文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_name = f"{log_file.stem}_{timestamp}.log.gz"
            archive_path = self.log_dir / archive_name

            # 压缩日志文件
            try:
                with log_file.open('rb') as f_in:
                    with gzip.open(archive_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # 清空原日志文件
                log_file.write_text('')

                logger.info(f"已压缩日志文件：{log_file} -> {archive_path}")
                compressed_count += 1
            except Exception as e:
                logger.error(f"压缩日志文件失败：{log_file}，错误：{e}")

        logger.info(f"日志压缩完成，共压缩 {compressed_count} 个文件")
        return compressed_count

    def run_maintenance(self):
        """运行日志维护任务"""
        logger.info("开始日志维护任务...")

        # 轮转日志
        rotated = self.rotate_logs()

        # 清理旧日志
        removed = self.clean_old_logs()

        logger.info(f"日志维护任务完成，轮转 {rotated} 个文件，删除 {removed} 个文件")
        return rotated, removed


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='日志管理工具')
    parser.add_argument('--log-dir', default='logs', help='日志目录')
    parser.add_argument('--max-size', type=int, default=10, help='日志文件最大大小（MB）')
    parser.add_argument('--max-days', type=int, default=30, help='日志文件最大保留天数')
    parser.add_argument('--compress-all', action='store_true', help='压缩所有日志文件')
    parser.add_argument('--clean-old', action='store_true', help='清理旧日志文件')

    args = parser.parse_args()

    # 创建日志管理器
    log_manager = LogManager(
        log_dir=args.log_dir,
        max_size_mb=args.max_size,
        max_days=args.max_days
    )

    # 根据参数执行操作
    if args.compress_all:
        log_manager.compress_all_logs()
    elif args.clean_old:
        log_manager.clean_old_logs()
    else:
        log_manager.run_maintenance()


if __name__ == '__main__':
    main()
