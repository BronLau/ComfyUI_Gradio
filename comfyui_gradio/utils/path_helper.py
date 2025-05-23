#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
路径辅助工具 - 提供项目路径处理和环境设置功能
"""

import sys
from pathlib import Path


def setup_project_path():
    """将项目根目录添加到Python路径"""
    # 获取当前文件的目录
    current_dir = Path(__file__).parent.absolute()
    # 获取项目根目录（假设是utils的上上级目录）
    root_dir = current_dir.parent.parent
    # 将项目根目录添加到Python路径
    if str(root_dir) not in sys.path:
        sys.path.insert(0, str(root_dir))
    return root_dir


def get_project_root():
    """获取项目根目录的Path对象"""
    current_dir = Path(__file__).parent.absolute()
    return current_dir.parent.parent


def get_logs_dir():
    """获取日志目录的Path对象"""
    root_dir = get_project_root()
    logs_dir = root_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    return logs_dir 