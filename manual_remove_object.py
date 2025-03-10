from pathlib import Path
import gradio as gr
from PIL import Image
import os
import time
import json
import requests
import numpy as np
from typing import Tuple

from config import Config
from utils.logger import setup_logger
import utils
from utils import DingTalkBot

# 设置日志
logger = setup_logger("manual-remove-object-logs")


class RemoveObjectApp:
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
        workflow_path = Path("workflows/Remove_Object_Manual_Mask.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(self,
                      input_data: dict,
                      expand: float) -> Tuple[Image.Image, str]:
        try:
            if input_data is None or 'background' not in input_data:
                return utils.create_error_image(), "未上传图片"

            if 'layers' not in input_data or not input_data['layers']:
                return utils.create_error_image(), "请先绘制要移除的区域"

            # 生成唯一请求ID
            request_id = f"manual_rmobj_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始手动移除物体 [请求ID: {request_id}]")
            logger.info(f"扩展遮罩值: {expand}")

            # 获取原图和蒙版图像
            background = Image.fromarray(input_data['background'])
            mask_layer = Image.fromarray(input_data['layers'][0])

            # 修改：提取alpha通道并创建二值化蒙版
            mask_array = np.array(mask_layer)
            alpha_channel = mask_array[:, :, 3]
            binary_mask = (alpha_channel > 0).astype(np.uint8) * 255

            # 修改：将蒙版转换为PIL图像
            mask_image = Image.fromarray(binary_mask, mode='L')

            # 确保蒙版与原图尺寸一致
            if mask_image.size != background.size:
                mask_image = mask_image.resize(background.size, Image.NEAREST)

            # 修改：创建合成图像，将蒙版区域设为透明
            combined_image = background.copy()
            combined_image.putalpha(255)
            alpha = combined_image.split()[3]
            alpha = Image.composite(
                Image.new('L', background.size, 0), alpha, mask_image)
            combined_image.putalpha(alpha)

            # 保存合成后的图片（用于传递给ComfyUI）
            combined_filename = f"{request_id}_combined.png"
            combined_path = self.clipspace_dir / combined_filename
            combined_image.save(combined_path)
            logger.info(f"保存合并后的图片 [请求ID: {request_id}]: {combined_path}")

            # 更新工作流中的路径和参数
            clipspace_relative = "clipspace"
            workflow_combined_path = (
                f"{clipspace_relative}/{combined_filename}")
            self.workflow["36"]["inputs"]["image"] = workflow_combined_path
            self.workflow["47"]["inputs"]["expand"] = float(expand)
            # 设置SaveImage节点的filename_prefix参数
            self.workflow["154"]["inputs"]["filename_prefix"] = request_id

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
                error_msg = (
                    f"ComfyUI请求失败\n"
                    f"请求ID: {request_id}\n"
                    f"合并图片: {combined_filename}\n"
                    f"错误信息: {str(e)}\n"
                    f"遮罩扩展值: {expand}"
                )
                logger.error(error_msg)
                self.ding.send_message(error_msg, e)
                return utils.create_error_image(), error_msg

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
                            if output_image.mode != 'RGBA':
                                output_image = output_image.convert('RGBA')

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

            error_msg = (
                f"处理超时\n"
                f"请求ID: {request_id}\n"
                f"合并图片: {combined_filename}\n"
                f"已等待: {retry_count}秒\n"
                f"最后检查的输出路径: {str(self.output_dir)}\n"
                f"遮罩扩展值: {expand}"
            )
            logger.error(error_msg)
            self.ding.send_message(error_msg)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_msg = f"处理失败: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg, e)
            return utils.create_error_image(), error_msg


def main():
    global demo

    # 创建应用实例
    app = RemoveObjectApp()

    # 创建 Gradio 界面
    with gr.Blocks(title="手绘蒙版物体移除工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>手绘蒙版物体移除工具</h1>
            </div>
            上传图片并绘制要移除的区域。
        """)

        with gr.Row():
            with gr.Column():
                input_editor = gr.ImageEditor(
                    label="输入图片",
                    type="numpy",
                    brush=gr.Brush(colors=["#000000"], default_size=12),
                    interactive=True,
                )
                expand_slider = gr.Slider(
                    minimum=0,
                    maximum=24,
                    value=12,
                    step=1,
                    label="遮罩扩展值",
                    info="调整遮罩扩展范围 (0 到 24)"
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

        process_btn.click(
            fn=app.process_image,
            inputs=[
                input_editor,
                expand_slider,
            ],
            outputs=[
                output_image,
                status_text,
            ]
        )

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get(
            "gradio_server.manual_remove_object_server_port"),
    )


demo = None

if __name__ == "__main__":
    main()
