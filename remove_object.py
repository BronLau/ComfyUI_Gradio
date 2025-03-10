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
logger = setup_logger("remove-object-logs")


class RemoveObjectApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        workflow_path = Path("workflows/Remove_Object.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)
            self.default_expand = (
                self.workflow.get("47", {})
                .get("inputs", {})
                .get("expand", 12)
            )

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(self, input_image,
                      text_input: str,
                      expand: float) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            # 生成唯一请求ID
            request_id = f"rmobj_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始移除物体 [请求ID: {request_id}]")
            logger.info(f"用户输入文本: {text_input}")
            logger.info(f"扩展遮罩值: {expand}")

            # 保存上传的图片
            image = Image.fromarray(input_image)
            filename = utils.save_upload_image(image, self.input_dir)
            logger.info(f"保存输入图片: {filename}, 大小: {image.size}")

            # 更新工作流
            self.workflow["36"]["inputs"]["image"] = filename
            self.workflow["146"]["inputs"]["text_input"] = text_input
            # 更新扩展遮罩值
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
                    f"输入文件: {filename}\n"
                    f"错误信息: {str(e)}\n"
                    f"要移除的物体: {text_input}\n"
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
                f"输入文件: {filename}\n"
                f"已等待: {retry_count}秒\n"
                f"最后检查的输出路径: {str(self.output_dir)}\n"
                f"要移除的物体: {text_input}\n"
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
    global demo  # 声明全局变量

    # 创建应用实例
    app = RemoveObjectApp()

    # 创建Gradio界面
    demo = gr.Interface(
        fn=app.process_image,
        inputs=[
            gr.Image(
                type="numpy",
                label="输入图片",
                sources=["upload"]
            ),
            gr.Textbox(
                label="要移除的物体描述",
                placeholder="例如：watch, text, table等",
                value=""
            ),
            gr.Slider(
                minimum=0,
                maximum=24,
                value=app.default_expand,  # 使用工作流中的默认值
                step=1,
                label="遮罩扩展值",
                info="调整遮罩扩展范围 (0 到 24)"
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
        title="物体移除工具",
        description="上传图片并输入要移除的物体描述",
        cache_examples=False  # 禁用示例缓存
    )

    # 启动服务
    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get("gradio_server.remove_object_server_port"),
        allowed_paths=[str(app.input_dir), str(app.output_dir)],
        show_error=True,
        max_threads=1  # 限制并发处理数
    )


demo = None

if __name__ == "__main__":
    main()
