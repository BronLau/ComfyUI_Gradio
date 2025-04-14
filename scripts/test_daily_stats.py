#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试每日统计服务
"""

import os
import sys

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

from scripts.daily_stats import DailyStats

# 创建每日统计服务
stats_service = DailyStats()

# 手动触发每日报告
stats_service.send_daily_report()

print("测试完成，请检查钉钉是否收到消息")
