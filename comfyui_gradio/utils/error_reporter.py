#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统一的错误报告工具，用于收集和报告错误信息
"""

import os
import sys
import traceback
import logging
import inspect
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from comfyui_gradio.utils.dingtalk import DingTalkBot


class ErrorReporter:
    """统一的错误报告工具类"""

    def __init__(self, service_name: str,
                 logger: Optional[logging.Logger] = None):
        """
        初始化错误报告工具

        Args:
            service_name: 服务名称
            logger: 日志记录器，如果为None则创建一个新的
        """
        self.service_name = service_name
        self.logger = logger or logging.getLogger(service_name)
        self.ding = DingTalkBot()

    def report(self, error_msg: str, error: Optional[Exception] = None,
               context: Optional[Dict[str, Any]] = None,
               notify: bool = True) -> None:
        """
        报告错误

        Args:
            error_msg: 错误消息
            error: 异常对象
            context: 上下文信息
            notify: 是否发送通知
        """
        # 获取调用栈信息
        stack_info = self._get_stack_info()

        # 格式化错误消息
        formatted_msg = self._format_error_message(
            error_msg, error, stack_info, context)

        # 记录日志
        self.logger.error(formatted_msg)

        # 发送通知
        if notify:
            self.ding.send_message(formatted_msg, error)

    def _get_stack_info(self) -> List[Tuple[str, int, str, str]]:
        """
        获取调用栈信息

        Returns:
            调用栈信息列表，每个元素为(文件名, 行号, 函数名, 代码行)
        """
        stack_info = []
        try:
            # 获取当前调用栈
            frame = inspect.currentframe()
            # 跳过当前函数和report函数
            frame = frame.f_back.f_back if frame and frame.f_back else None

            # 收集调用栈信息
            while frame:
                filename = frame.f_code.co_filename
                lineno = frame.f_lineno
                function = frame.f_code.co_name

                # 获取代码行
                lines, start_line = inspect.getsourcelines(frame)
                if lineno - start_line < len(lines):
                    code_line = lines[lineno - start_line].strip()
                else:
                    code_line = "<source code not available>"

                # 添加到调用栈信息
                stack_info.append((filename, lineno, function, code_line))

                # 获取上一层调用栈
                frame = frame.f_back
        except Exception:
            # 如果获取调用栈信息失败，使用traceback模块获取
            try:
                stack_frames = traceback.extract_stack()
                if stack_frames and len(stack_frames) > 2:
                    stack_info = [
                        (frame_info.filename, frame_info.lineno,
                         frame_info.name, "<source code not available>")
                        for frame_info in stack_frames[:-2]
                    ]
            except Exception:
                # 如果仍然失败，添加一个空的调用栈信息
                stack_info = [
                    ("未知文件", 0, "未知函数",
                     "<source code not available>")
                ]

        return stack_info

    def _format_error_message(self, error_msg: str, error: Optional[Exception],
                              stack_info: List[Tuple[str, int, str, str]],
                              context: Optional[Dict[str, Any]]) -> str:
        """
        格式化错误消息

        Args:
            error_msg: 错误消息
            error: 异常对象
            stack_info: 调用栈信息
            context: 上下文信息

        Returns:
            格式化后的错误消息
        """
        # 基本错误信息
        formatted_msg = f"[{self.service_name}] {error_msg}"

        # 添加异常信息
        if error:
            formatted_msg += f"\n异常类型: {type(error).__name__}"
            formatted_msg += f"\n异常信息: {str(error)}"

        # 添加调用栈信息
        if stack_info:
            formatted_msg += "\n\n调用栈信息:"
            # 只显示前3层调用栈
            for i, (filename, lineno,
                    function, code_line) in enumerate(stack_info[:3]):
                # 获取相对路径
                rel_path = os.path.relpath(
                    filename, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
                formatted_msg += (f"\n  {i+1}. 文件: {rel_path}, "
                                  f"行号: {lineno}, 函数: {function}")
                formatted_msg += f"\n     代码: {code_line}"

        # 添加上下文信息
        if context:
            formatted_msg += "\n\n上下文信息:"
            for key, value in context.items():
                # 如果值太长，截断显示
                str_value = str(value)
                if len(str_value) > 100:
                    str_value = str_value[:100] + "..."
                formatted_msg += f"\n  {key}: {str_value}"

        # 添加系统信息
        formatted_msg += (f"\n\n时间: "
                          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        formatted_msg += f"\n平台: {sys.platform}"
        formatted_msg += f"\nPython版本: {sys.version.split()[0]}"

        return formatted_msg
