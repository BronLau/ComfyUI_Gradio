"""
图片扩展服务 - 向图片四周扩展内容
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
from typing import Tuple, Dict, Any

from comfyui_gradio.config import Config
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.error_reporter import ErrorReporter
import comfyui_gradio.utils as utils

# 设置日志
logger = setup_logger("image-extend-logs")
error_reporter = ErrorReporter("image-extend", logger)


class ImageExtendApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        root_dir = Path(__file__).parent.parent.parent
        workflow_path = root_dir / "workflows" / "Image_Extend.json"
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

    def process_image(self,
                      input_image: Image.Image,
                      prompt: str,
                      left: int = 0,
                      right: int = 0,
                      top: int = 0,
                      bottom: int = 0) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            if not prompt or prompt.strip() == "":
                return utils.create_error_image(), "请输入扩展内容描述"

            # 检查扩展值是否有效
            if left <= 0 and right <= 0 and top <= 0 and bottom <= 0:
                return utils.create_error_image(), "请至少在一个方向上设置大于0的扩展值"

            # 生成唯一请求ID
            request_id = f"extend_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始图片扩展 [请求ID: {request_id}]")
            logger.info(f"扩展值: 左={left}, 右={right}, 上={top}, 下={bottom}")
            logger.info(f"扩展内容描述: {prompt}")

            # 保存上传的图片
            input_filename = f"{request_id}_input.png"
            input_path = self.input_dir / input_filename
            input_image.save(input_path)
            logger.info(f"保存输入图片 [请求ID: {request_id}]: {input_path}")

            # 更新工作流中的路径和参数
            # 更新LoadImage节点的图像路径
            self.workflow["141"]["inputs"]["image"] = input_filename

            # 更新CLIPTextEncode节点的文本
            self.workflow["142"]["inputs"]["text"] = prompt

            # 更新扩展值
            self.workflow["237"]["inputs"]["left"] = left
            self.workflow["237"]["inputs"]["right"] = right
            self.workflow["237"]["inputs"]["top"] = top
            self.workflow["237"]["inputs"]["bottom"] = bottom

            # 设置SaveImage节点的filename_prefix参数
            self.workflow["273"]["inputs"]["filename_prefix"] = request_id

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
                    "扩展值": f"左={left}, 右={right}, 上={top}, 下={bottom}",
                    "扩展内容描述": prompt
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
                "扩展值": f"左={left}, 右={right}, 上={top}, 下={bottom}",
                "扩展内容描述": prompt
            }
            error_reporter.report("处理超时", None, error_context)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_context = {
                "扩展值": f"左={left}, 右={right}, 上={top}, 下={bottom}",
                "扩展内容描述": prompt
            }
            error_reporter.report("处理失败", e, error_context)
            return utils.create_error_image(), f"处理失败: {str(e)}"


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = ImageExtendApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(
                label="输入图片",
                type="pil",
            )
            prompt = gr.Textbox(
                label="扩展内容描述",
                info="描述要扩展的内容，例如：'蓝天白云'、'绿色草地'等",
                placeholder="输入扩展内容描述（必填）"
            )
            with gr.Row():
                left = gr.Number(
                    label="左侧扩展像素",
                    value=0,
                    precision=0,
                    minimum=0,
                    maximum=2048,
                )
                right = gr.Number(
                    label="右侧扩展像素",
                    value=0,
                    precision=0,
                    minimum=0,
                    maximum=2048,
                )
            with gr.Row():
                top = gr.Number(
                    label="上方扩展像素",
                    value=0,
                    precision=0,
                    minimum=0,
                    maximum=2048,
                )
                bottom = gr.Number(
                    label="下方扩展像素",
                    value=0,
                    precision=0,
                    minimum=0,
                    maximum=2048,
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
            input_image,
            prompt,
            left,
            right,
            top,
            bottom,
        ],
        outputs=[
            output_image,
            status_text,
        ]
    )

    return {
        "input_image": input_image,
        "prompt": prompt,
        "left": left,
        "right": right,
        "top": top,
        "bottom": bottom,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="图片扩展工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>图片扩展工具</h1>
            </div>
            上传图片，输入扩展内容描述，设置四个方向的扩展像素值，然后点击开始处理。
        """)

        # 创建界面组件
        create_interface()

    # 添加到config中的配置端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.image_extend_server_port", 7890)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
