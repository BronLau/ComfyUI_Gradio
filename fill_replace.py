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
logger = setup_logger("object-replace-logs")


class FillReplaceApp:
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
        workflow_path = Path("workflows/Fill_Replace.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(
            self,
            input_data: dict,
            replace_image: Image.Image,
            prompt: str = "clothes"
    ) -> Tuple[Image.Image, str]:
        try:
            if input_data is None or 'background' not in input_data:
                return utils.create_error_image(), "未上传主图片"

            if 'layers' not in input_data or not input_data['layers']:
                return utils.create_error_image(), "请先绘制要替换的区域"

            if replace_image is None:
                return utils.create_error_image(), "未上传替换物体图片"

            # 生成唯一请求ID
            request_id = (
                f"object_replace_{int(time.time()*1000)}_{os.getpid()}"
            )

            start_time = time.time()
            logger.info(f"开始物体替换 [请求ID: {request_id}]")

            # 获取原图和蒙版图像
            background = Image.fromarray(input_data['background'])
            mask_layer = Image.fromarray(input_data['layers'][0])

            # 提取alpha通道并创建二值化蒙版
            mask_array = np.array(mask_layer)
            alpha_channel = mask_array[:, :, 3]
            # 创建蒙版，标记区域为白色(255)，非标记区域为黑色(0)
            binary_mask = (alpha_channel > 0).astype(np.uint8) * 255

            # 如果工作流期望的替换区域与当前生成的蒙版相反，则反转蒙版
            binary_mask = 255 - binary_mask  # 反转蒙版，使未标记区域为白色(255)，标记区域为黑色(0)

            # 将蒙版转换为PIL图像
            mask_image = Image.fromarray(binary_mask, mode='L')

            # 确保蒙版与原图尺寸一致
            if mask_image.size != background.size:
                mask_image = mask_image.resize(background.size, Image.NEAREST)

            # 保存原图、蒙版和替换图
            bg_filename = f"{request_id}_bg.png"
            mask_filename = f"{request_id}_mask.png"
            replace_filename = f"{request_id}_replace.png"

            bg_path = self.clipspace_dir / bg_filename
            mask_path = self.clipspace_dir / mask_filename
            replace_path = self.clipspace_dir / replace_filename

            background.save(bg_path)
            mask_image.save(mask_path)

            # 确保 replace_image 是 PIL Image 对象
            if isinstance(replace_image, np.ndarray):
                replace_image = Image.fromarray(replace_image)
            replace_image.save(replace_path)

            logger.info(f"保存原图 [请求ID: {request_id}]: {bg_path}")
            logger.info(f"保存蒙版 [请求ID: {request_id}]: {mask_path}")
            logger.info(f"保存替换图 [请求ID: {request_id}]: {replace_path}")

            # 更新工作流中的路径和参数
            clipspace_relative = "clipspace"
            replace_rel_path = f"{clipspace_relative}/{replace_filename}"

            # 更新工作流配置
            # 更新LoadImage节点的图像路径
            mask_id = request_id
            mask_path_fmt = (
                f"{clipspace_relative}/clipspace-mask-{mask_id}.png"
            )
            self.workflow["145"]["inputs"]["image"] = mask_path_fmt

            # 更新替换图的LoadImage节点路径
            self.workflow["257"]["inputs"]["image"] = replace_rel_path

            # 设置SaveImage节点的filename_prefix参数
            self.workflow["259"]["inputs"]["filename_prefix"] = request_id

            # 更新SegmentAnythingUltra节点的prompt参数
            self.workflow["216"]["inputs"]["prompt"] = prompt

            # 创建带蒙版的clipspace图像格式
            # 使用ComfyUI约定的clipspace格式保存原图和蒙版
            combined_filename = f"clipspace-mask-{request_id}.png"
            combined_path = self.clipspace_dir / combined_filename

            # 将原图和蒙版组合成ComfyUI能识别的格式
            combined = Image.new('RGBA', background.size)
            combined.paste(background, (0, 0))

            # 确保蒙版有正确的尺寸和通道
            mask_resized = mask_image.resize(background.size, Image.NEAREST)

            # 设置alpha通道 - 确保标记区域是要替换的区域
            r, g, b = combined.split()[:3]
            combined = Image.merge('RGBA', (r, g, b, mask_resized))
            combined.save(combined_path)

            logger.info(f"保存合并图片 [请求ID: {request_id}]: {combined_path}")

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
                    f"错误信息: {str(e)}"
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
                f"已等待: {retry_count}秒\n"
                f"最后检查的输出路径: {str(self.output_dir)}"
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
    app = FillReplaceApp()

    # 创建 Gradio 界面
    with gr.Blocks(title="物体替换工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>物体替换工具</h1>
            </div>
            上传主图并绘制要替换的区域，然后上传替换物体的图片，点击开始处理。
        """)

        with gr.Row():
            with gr.Column():
                input_editor = gr.ImageEditor(
                    label="主图 (绘制要替换的区域)",
                    type="numpy",
                    brush=gr.Brush(colors=["#000000"], default_size=12),
                    interactive=True,
                )
                replace_image = gr.Image(
                    label="替换物体图片",
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

        process_btn.click(
            fn=app.process_image,
            inputs=[
                input_editor,
                replace_image,
            ],
            outputs=[
                output_image,
                status_text,
            ]
        )

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.object_replace_server_port", 7892)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


demo = None

if __name__ == "__main__":
    main()
