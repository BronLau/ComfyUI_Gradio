#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统计服务测试脚本 - 已合并到validate_stats.py
此脚本保留用于向后兼容
"""

import sys
import os

# 获取项目根目录
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# 添加项目根目录到Python路径
sys.path.insert(0, root_dir)

# 从validate_stats.py导入测试函数
try:
    from scripts.validate_stats import test_stats_service

    if __name__ == "__main__":
        print("统计服务测试脚本 - 调用validate_stats.py中的测试功能")
        # 直接调用测试函数，而不是通过subprocess启动
        test_stats_service()
        print("测试完成")
except ImportError:
    print("无法导入test_stats_service函数，尝试使用subprocess方式调用")
    import subprocess
    if __name__ == "__main__":
        validate_script = os.path.join(
            root_dir, "scripts", "validate_stats.py")
        subprocess.run([sys.executable, validate_script, "-m", "test"])
