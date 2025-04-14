"""
局部重绘服务 - 通过提示词重绘图片区域
"""

import sys
import os

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, root_dir)

from pathlib import Path
import gradio as gr
from PIL import Image
import time
import json
import requests
import numpy as np
from typing import Tuple, Dict, Any

from comfyui_gradio.config import Config
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.error_reporter import ErrorReporter
from comfyui_gradio.utils.image_processor import ImageProcessor
import comfyui_gradio.utils as utils

# 设置日志
logger = setup_logger("local-repaint-logs")
error_reporter = ErrorReporter("local-repaint", logger)


class FillRepaintApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))
        self.clipspace_dir = Path(Config.get("paths.clipspace_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.clipspace_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        root_dir = Path(__file__).parent.parent.parent
        workflow_path = root_dir / "workflows" / "Fill_Repaint.json"
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

    def process_image(self,
                      input_data: dict,
                      prompt: str,
                      denoise: float = 0.3) -> Tuple[Image.Image, str]:
        try:
            if input_data is None or 'background' not in input_data:
                return utils.create_error_image(), "未上传图片"

            if 'layers' not in input_data or not input_data['layers']:
                return utils.create_error_image(), "请先绘制要重绘的区域"

            # 生成唯一请求ID
            request_id = f"local_repaint_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始局部重绘 [请求ID: {request_id}]")
            logger.info(f"提示词: {prompt}")
            logger.info(f"重绘幅度: {denoise}")

            # 获取原图和蒙版图像
            background = Image.fromarray(input_data['background'])
            mask_layer = Image.fromarray(input_data['layers'][0])

            # 检查图像尺寸，如果太大则自动缩放
            max_size = Config.get("image_processing.max_size", 1600)
            original_width, original_height = background.size
            logger.info(f"原始图像尺寸: {original_width}x{original_height}")

            # 如果图像尺寸超过限制，进行缩放
            resize_msg = ""
            if original_width > max_size or original_height > max_size:
                processed_image, resized, info = ImageProcessor.resize_if_needed(
                    background, max_size=max_size, keep_aspect_ratio=True)
                if resized:
                    background = processed_image
                    # 同时缩放蒙版图像
                    mask_layer = mask_layer.resize(background.size, Image.NEAREST)
                    logger.info(f"图像已缩放: {info['original_size']} -> {info['new_size']}")
                    # 添加提示信息
                    resize_msg = f"图像已自动缩放: {info['original_size'][0]}x{info['original_size'][1]} -> {info['new_size'][0]}x{info['new_size'][1]}"

            # 提取alpha通道并创建二值化蒙版
            mask_array = np.array(mask_layer)
            alpha_channel = mask_array[:, :, 3]
            binary_mask = (alpha_channel > 0).astype(np.uint8) * 255

            # 将蒙版转换为PIL图像
            mask_image = Image.fromarray(binary_mask, mode='L')

            # 确保蒙版与原图尺寸一致
            if mask_image.size != background.size:
                mask_image = mask_image.resize(background.size, Image.NEAREST)

            # 创建合成图像，将蒙版区域设为透明
            combined_image = background.copy()
            combined_image.putalpha(255)  # 初始化为完全不透明
            alpha = combined_image.split()[3]  # 获取alpha通道
            # 将蒙版区域的alpha值设为0（完全透明）
            alpha = Image.composite(
                Image.new('L', background.size, 0), alpha, mask_image)
            combined_image.putalpha(alpha)  # 将修改后的alpha通道应用回合成图像

            # 保存合成后的图片（用于传递给ComfyUI）
            combined_filename = f"{request_id}_combined.png"
            combined_path = self.clipspace_dir / combined_filename
            combined_image.save(combined_path)
            logger.info(f"保存合并后的图片 [请求ID: {request_id}]: {combined_path}")

            # 更新工作流中的路径和参数
            clipspace_relative = "clipspace"
            workflow_combined_path = (
                f"{clipspace_relative}/{combined_filename}")

            # 更新工作流配置
            # 更新LoadImage节点的图像路径
            self.workflow["54"]["inputs"]["image"] = workflow_combined_path

            # 处理提示词并设置相关节点
            if prompt and prompt.strip():
                # 用户输入了提示词，设置BaiduTranslateNode的text参数，覆盖默认值"empty"
                self.workflow["175"]["inputs"]["text"] = prompt
                # 设置Text Switch的input为2，使用用户输入的提示词
                self.workflow["170"]["inputs"]["input"] = 2
            else:
                # 用户没有输入提示词，设置Text Switch的input为1，使用自动生成的提示词
                self.workflow["170"]["inputs"]["input"] = 1

            # 更新KSampler节点的denoise参数
            self.workflow["50"]["inputs"]["denoise"] = float(denoise)

            # 设置SaveImage节点的filename_prefix参数
            self.workflow["168"]["inputs"]["filename_prefix"] = request_id

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
                    "图片": combined_filename,
                    "提示词": prompt,
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
                        logger.info(f"图片模式: {output_image.mode}")
                        logger.info(f"图片大小: {output_image.size}")

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
                "图片": combined_filename,
                "已等待": f"{retry_count}秒",
                "输出路径": str(self.output_dir),
                "提示词": prompt,
                "重绘幅度": denoise
            }
            error_reporter.report("处理超时", None, error_context)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_reporter.report("处理失败", e, {"提示词": prompt, "重绘幅度": denoise})
            return utils.create_error_image(), f"处理失败: {str(e)}"


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = FillRepaintApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_editor = gr.ImageEditor(
                label="输入图片",
                type="numpy",
                brush=gr.Brush(colors=["#000000"], default_size=12),
                interactive=True,
                elem_id="repaint_input_image"
            )

            prompt_text = gr.Textbox(
                label="提示词",
                info="描述重绘区域的内容，留空将自动生成",
                placeholder="输入提示词以指导重绘内容"
            )
            denoise_slider = gr.Slider(
                minimum=0,
                maximum=1,
                value=0.3,
                step=0.05,
                label="重绘幅度",
                info="调整重绘的幅度，值越大重绘效果越明显 (0 到 1)"
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
        inputs=[
            input_editor,
            prompt_text,
            denoise_slider,
        ],
        outputs=[
            output_image,
            status_text,
        ]
    )

    return {
        "input_editor": input_editor,
        "prompt_text": prompt_text,
        "denoise_slider": denoise_slider,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="局部重绘工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>局部重绘工具</h1>
            </div>
            上传图片并绘制要重绘的区域，输入提示词后开始处理。
        """)

        # 创建界面组件
        create_interface()

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.fill_repaint_server_port", 7891)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
