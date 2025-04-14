from comfyui_gradio.services.fill_repaint import FillRepaintApp
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image
import numpy as np
import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))


class TestFillRepaintApp(unittest.TestCase):

    def setUp(self):
        # 创建测试目录
        os.makedirs('test_input', exist_ok=True)
        os.makedirs('test_output', exist_ok=True)
        os.makedirs('test_clipspace', exist_ok=True)

        # 模拟配置
        self.config_patcher = patch('config.Config.get')
        self.mock_config_get = self.config_patcher.start()
        self.mock_config_get.side_effect = self._mock_config_get

        # 模拟工作流文件
        self.workflow_patcher = patch('pathlib.Path.open')
        self.mock_open = self.workflow_patcher.start()
        self.mock_open.return_value.__enter__.return_value.read.return_value = '{}'

        # 创建测试应用
        self.app = FillRepaintApp()

        # 模拟工作流
        self.app.workflow = {
            "54": {"inputs": {"image": ""}},
            "175": {"inputs": {"text": ""}},
            "170": {"inputs": {"input": 1}},
            "50": {"inputs": {"denoise": 0.5}},
            "168": {"inputs": {"filename_prefix": ""}}
        }

    def tearDown(self):
        # 停止所有模拟
        self.config_patcher.stop()
        self.workflow_patcher.stop()

        # 清理测试目录
        for file in os.listdir('test_output'):
            os.remove(os.path.join('test_output', file))
        for file in os.listdir('test_clipspace'):
            os.remove(os.path.join('test_clipspace', file))

        os.rmdir('test_input')
        os.rmdir('test_output')
        os.rmdir('test_clipspace')

    def _mock_config_get(self, key, default=None):
        """模拟配置获取函数"""
        config = {
            "comfyui_server.url": "http://localhost:8188/prompt",
            "paths.input_dir": "test_input",
            "paths.output_dir": "test_output",
            "paths.clipspace_dir": "test_clipspace",
            "comfyui_server.timeout": 30
        }
        return config.get(key, default)

    @patch('requests.post')
    @patch('time.sleep')
    @patch('pathlib.Path.glob')
    def test_process_image_success(self, mock_glob, mock_sleep, mock_post):
        """测试图片处理成功的情况"""
        # 创建测试输入数据
        background = np.zeros((100, 100, 3), dtype=np.uint8)
        mask = np.zeros((100, 100, 4), dtype=np.uint8)
        mask[25:75, 25:75, 3] = 255  # 创建中心区域的蒙版

        input_data = {
            'background': background,
            'layers': [mask]
        }

        # 模拟请求成功
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        # 模拟输出文件
        test_output_file = os.path.join('test_output', 'test_output.png')
        test_image = Image.new('RGB', (100, 100), color='green')
        test_image.save(test_output_file)
        mock_glob.return_value = [test_output_file]

        # 调用处理函数
        result_image, status = self.app.process_image(
            input_data, "test prompt", 0.5)

        # 验证结果
        self.assertIsInstance(result_image, Image.Image)
        self.assertEqual(status, "处理成功")
        self.assertEqual(result_image.size, (100, 100))

        # 验证工作流更新
        self.assertEqual(
            self.app.workflow["175"]["inputs"]["text"], "test prompt")
        self.assertEqual(self.app.workflow["170"]["inputs"]["input"], 2)
        self.assertEqual(self.app.workflow["50"]["inputs"]["denoise"], 0.5)

    @patch('requests.post')
    def test_process_image_request_error(self, mock_post):
        """测试请求失败的情况"""
        # 创建测试输入数据
        background = np.zeros((100, 100, 3), dtype=np.uint8)
        mask = np.zeros((100, 100, 4), dtype=np.uint8)
        mask[25:75, 25:75, 3] = 255  # 创建中心区域的蒙版

        input_data = {
            'background': background,
            'layers': [mask]
        }

        # 模拟请求失败
        mock_post.side_effect = Exception("Connection error")

        # 调用处理函数
        result_image, status = self.app.process_image(
            input_data, "test prompt", 0.5)

        # 验证结果
        self.assertIn("ComfyUI请求失败", status)

    def test_process_image_no_input(self):
        """测试没有输入图片的情况"""
        # 调用处理函数
        result_image, status = self.app.process_image(None, "test prompt", 0.5)

        # 验证结果
        self.assertEqual(status, "未上传图片")

    def test_process_image_no_mask(self):
        """测试没有蒙版的情况"""
        # 创建测试输入数据，但没有蒙版
        background = np.zeros((100, 100, 3), dtype=np.uint8)

        input_data = {
            'background': background,
            'layers': []
        }

        # 调用处理函数
        result_image, status = self.app.process_image(
            input_data, "test prompt", 0.5)

        # 验证结果
        self.assertEqual(status, "请先绘制要重绘的区域")


if __name__ == '__main__':
    unittest.main()
