"""
人脸替换服务 - 将图片中的人脸替换为另一张图片中的人脸
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Tuple, Dict, Any

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, root_dir)

import gradio as gr
import requests
import numpy as np
from PIL import Image

from comfyui_gradio.config import Config
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.error_reporter import ErrorReporter
import comfyui_gradio.utils as utils

# 设置日志
logger = setup_logger("face-swap-logs")
error_reporter = ErrorReporter("face-swap", logger)


class SwapFaceApp:
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
        workflow_path = root_dir / "workflows" / "Fill_Replace_Swap_Face.json"
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

    def process_image(
            self,
            input_data: dict,  # 源图像(带绘制的面部区域)
            face_image: Image.Image,   # 目标人脸图像
    ) -> Tuple[Image.Image, str]:
        try:
            if input_data is None or 'background' not in input_data:
                return utils.create_error_image(), "未上传源图片"

            if 'layers' not in input_data or not input_data['layers']:
                return utils.create_error_image(), "请先在源图片上绘制要替换的面部区域"

            if face_image is None:
                return utils.create_error_image(), "未上传目标人脸图片"

            # 生成唯一请求ID
            request_id = (
                f"face_swap_{int(time.time()*1000)}_{os.getpid()}"
            )

            start_time = time.time()
            logger.info(f"开始人脸替换 [请求ID: {request_id}]")

            # 获取原图和蒙版图像
            background = Image.fromarray(input_data['background'])
            mask_layer = Image.fromarray(input_data['layers'][0])

            # 提取alpha通道并创建二值化蒙版
            mask_array = np.array(mask_layer)
            alpha_channel = mask_array[:, :, 3]
            # 创建蒙版，标记区域为白色(255)，非标记区域为黑色(0)
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
            
            # 保存合成后的图片和替换图
            combined_filename = f"{request_id}_combined.png"
            face_filename = f"{request_id}_face.png"
            
            combined_path = self.clipspace_dir / combined_filename
            face_path = self.clipspace_dir / face_filename
            
            combined_image.save(combined_path)
            
            # 确保 face_image 是 PIL Image 对象
            if isinstance(face_image, np.ndarray):
                face_image = Image.fromarray(face_image)
            face_image.save(face_path)
            
            logger.info(f"保存合并后的图片 [请求ID: {request_id}]: {combined_path}")
            logger.info(f"保存目标人脸图片 [请求ID: {request_id}]: {face_path}")

            # 更新工作流中的路径和参数
            clipspace_relative = "clipspace"
            combined_rel_path = f"{clipspace_relative}/{combined_filename}"
            face_rel_path = f"{clipspace_relative}/{face_filename}"
            
            # 更新工作流配置
            # 更新LoadImage节点的图像路径 - 源图像
            self.workflow["145"]["inputs"]["image"] = combined_rel_path
            
            # 更新LoadImage节点的图像路径 - 目标人脸图像
            self.workflow["257"]["inputs"]["image"] = face_rel_path
            
            # 更新人脸检测相关参数
            if "216" in self.workflow:
                # 使用"face"作为提示词，帮助模型识别面部区域
                self.workflow["216"]["inputs"]["prompt"] = "face"
            
            # 设置SaveImage节点的filename_prefix参数
            self.workflow["259"]["inputs"]["filename_prefix"] = request_id
            
            # 创建带蒙版的clipspace图像格式
            # 使用ComfyUI约定的clipspace格式保存原图和蒙版
            clipspace_filename = f"clipspace-mask-{request_id}.png"
            clipspace_path = self.clipspace_dir / clipspace_filename
            
            # 将原图和蒙版组合成ComfyUI能识别的格式
            combined = Image.new('RGBA', background.size)
            combined.paste(background, (0, 0))
            
            # 确保蒙版有正确的尺寸和通道
            mask_resized = mask_image.resize(background.size, Image.NEAREST)
            
            # 设置alpha通道 - 确保标记区域是要替换的区域
            r, g, b = combined.split()[:3]
            combined = Image.merge('RGBA', (r, g, b, mask_resized))
            combined.save(clipspace_path)
            
            logger.info(f"保存clipspace图片 [请求ID: {request_id}]: {clipspace_path}")

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
                    "请求ID": request_id
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

                        return output_image, "处理成功"

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
                "输出路径": str(self.output_dir)
            }
            error_reporter.report("处理超时", None, error_context)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_reporter.report("处理失败", e, {})
            return utils.create_error_image(), f"处理失败: {str(e)}"


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = SwapFaceApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_editor = gr.ImageEditor(
                label="源图像 (请在面部区域涂抹标记要替换的部分)",
                type="numpy",
                brush=gr.Brush(colors=["#000000"], default_size=12),
                interactive=True,
            )
            face_image = gr.Image(
                label="目标人脸图片",
                type="pil",
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
            face_image,
        ],
        outputs=[
            output_image,
            status_text,
        ]
    )

    return {
        "input_editor": input_editor,
        "face_image": face_image,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="人脸替换工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>人脸替换工具</h1>
            </div>
            上传源图片并绘制要替换的面部区域，然后上传目标人脸图片，点击开始处理。
        """)

        # 创建界面组件
        create_interface()

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.swap_face_server_port", 7893)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
