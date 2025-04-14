"""
手动蒙版物体移除服务 - 通过手动绘制蒙版来精确移除图片中的物体
"""

import comfyui_gradio.utils as utils
from comfyui_gradio.utils.error_reporter import ErrorReporter
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.config import Config
from typing import Tuple, Dict, Any
import numpy as np
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
logger = setup_logger("manual-remove-object-logs")
error_reporter = ErrorReporter("manual-remove-object", logger)


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
        root_dir = Path(__file__).parent.parent.parent
        workflow_path = root_dir / "workflows" / "Remove_Object_Manual_Mask.json"
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

    def process_image(self,
                      input_data: dict,
                      mask_expand: int = 30) -> Tuple[Image.Image, str]:
        try:
            if input_data is None or 'background' not in input_data:
                return utils.create_error_image(), "未上传图片"

            if 'layers' not in input_data or not input_data['layers']:
                return utils.create_error_image(), "请先绘制要移除的区域"

            # 生成唯一请求ID
            request_id = f"manual_remove_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始手动蒙版物体移除 [请求ID: {request_id}]")
            logger.info(f"蒙版扩展值: {mask_expand}")

            # 获取原图和蒙版图像
            background = Image.fromarray(input_data['background'])
            mask_layer = Image.fromarray(input_data['layers'][0])

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
            workflow_combined_path = f"{clipspace_relative}/{combined_filename}"

            # 更新工作流配置
            # 更新LoadImage节点的图像路径
            self.workflow["36"]["inputs"]["image"] = workflow_combined_path

            # 更新MaskExpand节点的扩展值
            self.workflow["47"]["inputs"]["expand"] = mask_expand

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
                error_context = {
                    "请求ID": request_id,
                    "蒙版扩展值": mask_expand
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
                "输出路径": str(self.output_dir),
                "蒙版扩展值": mask_expand
            }
            error_reporter.report("处理超时", None, error_context)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_reporter.report("处理失败", e, {"蒙版扩展值": mask_expand})
            return utils.create_error_image(), f"处理失败: {str(e)}"


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = RemoveObjectApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_editor = gr.ImageEditor(
                label="输入图片",
                type="numpy",
                brush=gr.Brush(colors=["#000000"], default_size=12),
                interactive=True,
            )
            mask_expand = gr.Slider(
                minimum=0,
                maximum=100,
                value=30,
                step=1,
                label="蒙版扩展值",
                info="调整蒙版扩展的像素值，值越大扩展越多 (0 到 100)"
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
            mask_expand,
        ],
        outputs=[
            output_image,
            status_text,
        ]
    )

    return {
        "input_editor": input_editor,
        "mask_expand": mask_expand,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="手动蒙版物体移除工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>手动蒙版物体移除工具</h1>
            </div>
            上传图片并绘制要移除的区域，调整蒙版扩展值，然后点击开始处理。
        """)

        # 创建界面组件
        create_interface()

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get(
        "gradio_server.manual_remove_object_server_port", 7881)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
