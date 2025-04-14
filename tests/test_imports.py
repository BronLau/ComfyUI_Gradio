"""
测试导入模块
"""

import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestImports(unittest.TestCase):
    """测试导入模块"""

    def test_import_utils(self):
        """测试导入工具函数模块"""
        try:
            import comfyui_gradio.utils
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils 失败: {e}")

    def test_import_logger(self):
        """测试导入日志模块"""
        try:
            from comfyui_gradio.utils.logger import setup_logger
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils.logger 失败: {e}")

    def test_import_error_reporter(self):
        """测试导入错误报告模块"""
        try:
            from comfyui_gradio.utils.error_reporter import ErrorReporter
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils.error_reporter 失败: {e}")

    def test_import_dingtalk(self):
        """测试导入钉钉模块"""
        try:
            from comfyui_gradio.utils.dingtalk import DingTalkBot
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils.dingtalk 失败: {e}")

    def test_import_stats(self):
        """测试导入统计模块"""
        try:
            from comfyui_gradio.utils.stats import UsageStats
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils.stats 失败: {e}")

    def test_import_image_utils(self):
        """测试导入图像工具模块"""
        try:
            from comfyui_gradio.utils.image_utils import create_error_image
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.utils.image_utils 失败: {e}")

    def test_import_services(self):
        """测试导入服务模块"""
        try:
            import comfyui_gradio.services
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.services 失败: {e}")

    def test_import_fill_repaint(self):
        """测试导入局部重绘服务模块"""
        try:
            from comfyui_gradio.services.fill_repaint import FillRepaintApp
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.services.fill_repaint 失败: {e}")

    def test_import_fill_replace(self):
        """测试导入物体替换服务模块"""
        try:
            from comfyui_gradio.services.fill_replace import FillReplaceApp
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"导入 comfyui_gradio.services.fill_replace 失败: {e}")


if __name__ == '__main__':
    unittest.main()
