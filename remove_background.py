from pathlib import Path
import gradio as gr
from PIL import Image
import os
import time
import json
import requests
from typing import Tuple

from config import Config
from utils.logger import setup_logger
from utils import DingTalkBot
import utils

# 设置日志
logger = setup_logger("rmbg-logs")


class RmbgApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        workflow_path = Path("workflows/BRIA_RMBG_2.0.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)
            self.default_mask_offset = (
                self.workflow.get("8", {})
                .get("inputs", {})
                .get("mask_offset", 0)
            )

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(
        self, input_image, mask_offset: float
    ) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            start_time = time.time()
            logger.info("开始移除背景")
            logger.info(f"mask_offset: {mask_offset}")

            # 保存上传的图片
            image = Image.fromarray(input_image)
            filename = utils.save_upload_image(image, self.input_dir)
            logger.info(f"保存输入图片: {filename}, 大小: {image.size}")

            # 更新工作流
            self.workflow["7"]["inputs"]["mask_offset"] = mask_offset
            self.workflow["8"]["inputs"]["image"] = filename

            # 获取处理前的最新图片及其修改时间
            previous_image = utils.get_latest_image(str(self.output_dir))
            previous_time = os.path.getmtime(
                previous_image) if previous_image else 0

            # 发送请求到ComfyUI
            try:
                response = requests.post(
                    self.url,
                    json={"prompt": self.workflow},
                    timeout=Config.get("comfyui_server.timeout", 30)
                )
                response.raise_for_status()
                logger.info("已发送请求到ComfyUI")
            except requests.exceptions.RequestException as e:
                error_msg = f"ComfyUI请求失败: {e}"
                logger.error(error_msg)
                self.ding.send_message(error_msg, e)
                return utils.create_error_image(), error_msg

            # 等待处理结果
            max_retries = 60
            retry_count = 0

            while retry_count < max_retries:
                try:
                    latest_image_path = utils.get_latest_image(
                        str(self.output_dir))
                    if latest_image_path:
                        current_time = os.path.getmtime(latest_image_path)
                        if current_time > previous_time:
                            # 确保文件写入完成
                            time.sleep(0.5)

                            # 使用上下文管理器安全地打开和处理图片
                            with Image.open(latest_image_path) as img:
                                # 创建副本以避免文件句柄问题
                                output_image = img.copy()

                                # 确保是RGBA模式以支持透明通道
                                if output_image.mode != 'RGBA':
                                    output_image = output_image.convert('RGBA')

                            process_time = time.time() - start_time
                            logger.info(f"处理完成,耗时: {process_time:.2f}秒")
                            logger.info(f"输出图片: {latest_image_path}")
                            logger.info(f"图片模式: {output_image.mode}")
                            logger.info(f"图片大小: {output_image.size}")

                            return output_image, "处理成功"

                except Exception as e:
                    logger.error(f"图片加载失败: {e}")
                    time.sleep(1)
                    retry_count += 1
                    continue

                time.sleep(1)
                retry_count += 1
                if retry_count % 10 == 0:
                    logger.info(f"等待处理结果: {retry_count}/{max_retries}")

            logger.error("处理超时")
            self.ding.send_message("处理超时")
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg, e)
            return utils.create_error_image(), error_msg


def main():
    global demo  # 声明全局变量

    # 创建应用实例
    app = RmbgApp()

    # 创建Gradio界面
    demo = gr.Interface(
        fn=app.process_image,
        inputs=[
            gr.Image(
                type="numpy",
                label="输入图片",
                sources=["upload"]
            ),
            gr.Slider(
                minimum=-10,
                maximum=10,
                value=app.default_mask_offset,  # 使用工作流中的默认值
                step=0.1,
                label="遮罩偏移量（像素收缩）",
                info="调整遮罩边缘的偏移量 (-10 到 10)"
            )
        ],
        outputs=[
            gr.Image(
                type="pil",
                label="处理结果",
                format="png",  # 保持PNG格式以支持透明通道
                show_label=True
            ),
            gr.Textbox(label="处理状态")
        ],
        title="背景移除工具",
        cache_examples=False  # 禁用示例缓存
    )

    # 启动服务
    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get("gradio_server.rmbg_server_port"),
        allowed_paths=[str(app.input_dir), str(app.output_dir)],
        show_error=True,
        max_threads=1  # 限制并发处理数
    )


demo = None

if __name__ == "__main__":
    main()
