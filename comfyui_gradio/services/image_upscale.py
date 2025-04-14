"""
图片放大服务 - 提高图片分辨率和清晰度
"""

import comfyui_gradio.utils as utils
from comfyui_gradio.utils.error_reporter import ErrorReporter
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.image_processor import ImageProcessor
from comfyui_gradio.config import Config
from typing import Tuple, Dict, Any
import requests
import json
import time
from PIL import Image
import gradio as gr
from pathlib import Path
import sys
import os

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, root_dir)


# 设置日志
logger = setup_logger("image-upscale-logs")
error_reporter = ErrorReporter("image-upscale", logger)


class ImageUpscaleApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        root_dir = Path(__file__).parent.parent.parent
        workflow_path = root_dir / "workflows" / "2_Image_Upscale_TTP.json"
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

    def process_image(
            self, input_image: Image.Image, denoise: float = 0.25) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            # 生成唯一请求ID
            request_id = f"upscale_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始图片放大 [请求ID: {request_id}]")

            # 检查图像尺寸，如果太大则自动缩放
            max_size = Config.get("image_processing.max_size", 1600)
            original_width, original_height = input_image.size
            logger.info(f"原始图像尺寸: {original_width}x{original_height}")

            # 如果图像尺寸超过限制，进行缩放
            if original_width > max_size or original_height > max_size:
                processed_image, resized, info = ImageProcessor.resize_if_needed(
                    input_image, max_size=max_size, keep_aspect_ratio=True)
                if resized:
                    input_image = processed_image
                    logger.info(f"图像已缩放: {info['original_size']} -> {info['new_size']}")
                    # 添加提示信息
                    resize_msg = f"图像已自动缩放: {info['original_size'][0]}x{info['original_size'][1]} -> {info['new_size'][0]}x{info['new_size'][1]}"
                else:
                    resize_msg = ""
            else:
                resize_msg = ""

            # 保存上传的图片
            input_filename = f"{request_id}_input.png"
            input_path = self.input_dir / input_filename
            input_image.save(input_path)
            logger.info(f"保存输入图片 [请求ID: {request_id}]: {input_path}")

            # 更新工作流中的路径和参数
            # 更新LoadImage节点的图像路径
            self.workflow["10"]["inputs"]["image"] = input_filename

            # 设置SaveImage节点的filename_prefix参数
            self.workflow["34"]["inputs"]["filename_prefix"] = request_id

            # 更新BasicScheduler节点的denoise参数
            self.workflow["9"]["inputs"]["denoise"] = float(denoise)
            logger.info(f"重绘幅度: {denoise}")

            # 发送请求到ComfyUI
            try:
                response = requests.post(
                    self.url,
                    json={"prompt": self.workflow},
                    timeout=Config.get("comfyui_server.timeout", 3000)
                )
                response.raise_for_status()
                logger.info(f"已发送请求到ComfyUI [请求ID: {request_id}]")
            except requests.exceptions.RequestException as e:
                error_context = {
                    "请求ID": request_id,
                    "输入图片": input_filename,
                    "重绘幅度": denoise
                }
                error_reporter.report("ComfyUI请求失败", e, error_context)
                return utils.create_error_image(), f"ComfyUI请求失败: {str(e)}"

            # 等待处理结果
            max_retries = 6000
            retry_count = 0

            while retry_count < max_retries:
                try:
                    # 查找以请求ID为前缀的输出文件
                    output_files = list(
                        self.output_dir.glob(f"{request_id}*.png"))
                    if output_files:
                        output_path = output_files[0]
                        # 确保文件写入完成
                        time.sleep(0.5)

                        with Image.open(output_path) as img:
                            output_image = img.copy()

                        process_time = time.time() - start_time
                        logger.info(
                            f"处理完成 [请求ID: {request_id}], "
                            f"耗时: {process_time:.2f}秒")
                        logger.info(f"输出图片: {output_path}")

                        # 构建状态信息
                        status_msg = "处理成功"
                        if resize_msg:
                            status_msg = f"{resize_msg}\n{status_msg}"

                        return output_image, status_msg

                except Exception as e:
                    logger.error(f"图片加载失败 [请求ID: {request_id}]: {e}")
                    time.sleep(1)
                    retry_count += 1
                    continue

                time.sleep(1)
                retry_count += 1
                if retry_count % 10 == 0:
                    logger.info(
                        f"等待处理结果 [请求ID: {request_id}]: "
                        f"{retry_count}/{max_retries}")

            error_context = {
                "请求ID": request_id,
                "已等待": f"{retry_count}秒",
                "输出路径": str(self.output_dir),
                "重绘幅度": denoise
            }
            error_reporter.report("处理超时", None, error_context)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_reporter.report("处理失败", e, {"重绘幅度": denoise})
            return utils.create_error_image(), f"处理失败: {str(e)}"


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = ImageUpscaleApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(
                label="输入图片",
                type="pil",
                elem_id="upscale_input_image"
            )

            denoise_slider = gr.Slider(
                minimum=0,
                maximum=1,
                value=0.25,
                step=0.05,
                label="重绘幅度",
                info="调整放大图像后细节改变的幅度，值越大细节改变幅度越大 (0 到 1)"
            )
            process_btn = gr.Button("开始处理", variant="primary")

        with gr.Column(scale=1):
            output_image = gr.Image(
                type="pil",
                label="处理结果",
                format="png",
                show_label=True,
            )
            status_text = gr.Textbox(label="处理状态")

    # 设置事件处理
    process_btn.click(
        fn=app.process_image,
        inputs=[input_image, denoise_slider],
        outputs=[output_image, status_text]
    )

    return {
        "input_image": input_image,
        "denoise_slider": denoise_slider,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="图片放大工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>图片放大工具</h1>
            </div>
            上传图片，点击开始处理，等待处理完成后查看结果。
        """)

        # 创建界面组件
        create_interface()

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.image_upscale_server_port", 7870)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
