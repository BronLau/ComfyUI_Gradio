#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
临时脚本 - 手动触发每日统计
"""

from scripts.daily_stats import DailyStats
import os
import sys
import json
import logging

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, root_dir)

# 必须在添加路径后导入项目模块
# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


# 设置日志级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('daily_stats_trigger')


def main():
    """主函数 - 手动触发每日统计"""
    logger.info("开始手动触发每日统计...")

    # 创建每日统计服务实例
    stats_service = DailyStats()

    # 收集统计数据（启用调试输出）
    stats = stats_service.collect_stats(days=1, debug=True)

    # 在控制台输出统计结果
    logger.info("统计数据:")
    logger.info(json.dumps(stats, ensure_ascii=False, indent=2))

    # 发送每日报告
    logger.info("正在发送每日报告...")
    stats_service.send_daily_report(debug=True)

    logger.info("每日统计触发完成")


if __name__ == "__main__":
    main()
