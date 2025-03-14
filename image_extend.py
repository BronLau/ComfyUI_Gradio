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
import utils
from utils import DingTalkBot

# 设置日志
logger = setup_logger("image-extend-logs")


class ImageExtendApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        workflow_path = Path("workflows/Image_Extend.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)
            self.default_expand = (
                self.workflow.get("47", {})
                .get("inputs", {})
                .get("expand", 12)
            )

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(
        self, input_image, text_input: str,
        left: int, top: int, right: int, bottom: int
    ) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            # 生成唯一请求ID
            request_id = f"extend_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始扩展图片 [请求ID: {request_id}]")
            logger.info(f"用户输入文本: {text_input}")
            logger.info(f"扩展像素: 左={left}, 上={top}, 右={right}, 下={bottom}")

            # 保存上传的图片
            image = Image.fromarray(input_image)
            filename = utils.save_upload_image(image, self.input_dir)
            logger.info(f"保存输入图片: {filename}, 大小: {image.size}")

            # 更新工作流
            self.workflow["141"]["inputs"]["image"] = filename
            self.workflow["268"]["inputs"]["text"] = text_input
            self.workflow["237"]["inputs"].update({
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom
            })
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
                error_msg = (
                    f"ComfyUI请求失败\n"
                    f"请求ID: {request_id}\n"
                    f"输入文件: {filename}\n"
                    f"错误信息: {str(e)}\n"
                    f"扩展内容描述: {text_input}\n"
                    f"扩展像素: 左={left}, 上={top}, 右={right}, 下={bottom}"
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
                f"输入文件: {filename}\n"
                f"已等待: {retry_count}秒\n"
                f"最后检查的输出路径: {str(self.output_dir)}\n"
                f"扩展内容描述: {text_input}\n"
                f"扩展像素: 左={left}, 上={top}, 右={right}, 下={bottom}"
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
    app = ImageExtendApp()

    with gr.Blocks(title="图像扩展工具") as demo:
        gr.Markdown(
            """
            <div style="text-align: center;">
                <h1>图像扩展工具</h1>
            </div>
            """)
        gr.Markdown("上传图片并输入需要扩展内容的描述以及扩展像素值（上、下、左、右）")

        with gr.Row():
            with gr.Column():
                input_image = gr.Image(
                    type="numpy",
                    label="输入图片",
                    sources=["upload"]
                )
                text_input = gr.Textbox(
                    label="扩展内容描述",
                    placeholder="描述要扩展的场景内容，例如：极简室内场景",
                    value=""
                )

                with gr.Row():
                    left = gr.Number(
                        value=0,
                        label="左侧扩展像素",
                        precision=0
                    )
                    top = gr.Number(
                        value=0,
                        label="上方扩展像素",
                        precision=0
                    )
                    right = gr.Number(
                        value=0,
                        label="右侧扩展像素",
                        precision=0
                    )
                    bottom = gr.Number(
                        value=0,
                        label="下方扩展像素",
                        precision=0
                    )

                process_btn = gr.Button(
                    "开始处理",
                    variant="primary",
                    elem_classes="orange-button"
                )

            with gr.Column():
                output_image = gr.Image(
                    type="pil",
                    label="处理结果",
                    format="png",
                    show_label=True
                )
                status_text = gr.Textbox(label="处理状态")

        # 添加校验函数，检查扩展内容描述是否已填写
        def validate_and_process(image, text, left, top, right, bottom):
            if text is None or text.strip() == "":
                gr.Warning("请输入扩展内容描述后再开始处理！")
                return None, "请输入扩展内容描述"
            return app.process_image(image, text, left, top, right, bottom)

        process_btn.click(
            fn=validate_and_process,
            inputs=[
                input_image,
                text_input,
                left,
                top,
                right,
                bottom
            ],
            outputs=[
                output_image,
                status_text
            ]
        )

    # 启动服务
    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get("gradio_server.image_extend_server_port"),
        allowed_paths=[str(app.input_dir), str(app.output_dir)],
        show_error=True,
        max_threads=1
    )


demo = None

if __name__ == "__main__":
    main()
