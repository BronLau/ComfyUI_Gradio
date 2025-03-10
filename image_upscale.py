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
logger = setup_logger("image-upscale-logs")


class ImageUpscaleApp:
    def __init__(self):
        self.url = Config.get("comfyui_server.url")
        self.input_dir = Path(Config.get("paths.input_dir"))
        self.output_dir = Path(Config.get("paths.output_dir"))

        # 确保目录存在
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载工作流
        workflow_path = Path("workflows/2_Image_Upscale_TTP.json")
        with workflow_path.open('r', encoding='utf-8') as f:
            self.workflow = json.load(f)

        # 初始化钉钉机器人
        self.ding = DingTalkBot()

    def process_image(self, input_image) -> Tuple[Image.Image, str]:
        try:
            if input_image is None:
                return utils.create_error_image(), "未上传图片"

            # 生成唯一请求ID
            request_id = f"upscale_{int(time.time()*1000)}_{os.getpid()}"

            start_time = time.time()
            logger.info(f"开始放大图片 [请求ID: {request_id}]")

            # 保存上传的图片
            image = Image.fromarray(input_image)
            filename = utils.save_upload_image(image, self.input_dir)
            filepath = str(self.input_dir / filename)
            logger.info(f"保存输入图片: {filename}, 大小: {image.size}")

            # 更新工作流配置
            try:
                # 查找并更新LoadImage节点
                for node_id, node in self.workflow.items():
                    if ("class_type" in node and
                            node["class_type"] == "LoadImage"):
                        logger.info(f"找到LoadImage节点: {node_id}")
                        node["inputs"]["image"] = filepath
                        logger.info(f"已更新节点输入路径: {filepath}")
                        break
                else:
                    raise ValueError("未找到LoadImage节点")

                # 设置SaveImage节点的filename_prefix参数
                self.workflow["34"]["inputs"]["filename_prefix"] = request_id

                logger.debug(
                    f"更新后的工作流配置: {json.dumps(self.workflow, indent=2)}")
            except Exception as e:
                logger.error(f"更新工作流配置失败: {e}")
                return utils.create_error_image(), f"更新工作流配置失败: {str(e)}"

            # 发送请求到ComfyUI
            try:
                response = requests.post(
                    self.url,
                    json={"prompt": self.workflow},
                    timeout=Config.get("comfyui_server.timeout", 6000)
                )
                response.raise_for_status()
                logger.info(f"已发送请求到ComfyUI [请求ID: {request_id}]")
            except requests.exceptions.RequestException as e:
                error_msg = (
                    f"ComfyUI请求失败\n"
                    f"请求ID: {request_id}\n"
                    f"输入文件: {filepath}\n"
                    f"错误信息: {str(e)}\n"
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
                f"输入文件: {filepath}\n"
                f"已等待: {retry_count}秒\n"
                f"最后检查的输出路径: {str(self.output_dir)}"
            )
            logger.error(error_msg)
            self.ding.send_message(error_msg)
            return utils.create_error_image(), "处理超时"

        except Exception as e:
            error_msg = f"处理失败 [请求ID: {request_id}]: {str(e)}"
            logger.error(error_msg)
            self.ding.send_message(error_msg, e)
            return utils.create_error_image(), error_msg


def main():
    global demo  # 声明全局变量

    # 创建应用实例
    app = ImageUpscaleApp()

    # 创建Gradio界面
    demo = gr.Interface(
        fn=app.process_image,
        inputs=gr.Image(
            type="numpy",
            label="输入图片",
            sources=["upload"]
        ),
        outputs=[
            gr.Image(
                type="pil",
                label="处理结果",
                format="png",
                show_label=True
            ),
            gr.Textbox(label="处理状态")
        ],
        title="图片放大工具",
        cache_examples=False  # 禁用示例缓存
    )

    # 启动服务
    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get("gradio_server.image_upscale_server_port"),
        allowed_paths=[str(app.input_dir), str(app.output_dir)],
        show_error=True,
        max_threads=1  # 限制并发处理数
    )


demo = None

if __name__ == "__main__":
    main()
