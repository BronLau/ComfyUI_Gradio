import json
import os
import time
import logging
from datetime import datetime

import gradio as gr
import requests
from PIL import Image

import Config

# 配置日志
LOG_DIR = "cutout-logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 生成日志文件名
log_filename = f'upscale_{datetime.now().strftime("%Y%m%d")}.log'
log_filepath = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filepath, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# 获取配置
URL = Config.get("comfyui_server.url")
INPUT_DIR = Config.get("paths.input_dir")
OUTPUT_DIR = Config.get("paths.output_dir")
SERVER_NAME = Config.get("gradio_server.server_name")
SERVER_PORT = Config.get("gradio_server.server_port")

# 验证配置
if not all([URL, INPUT_DIR, OUTPUT_DIR]):
    raise ValueError("配置加载失败，请检查配置文件")


def get_latest_image(folder):
    files = os.listdir(folder)
    image_files = [f for f in files if f.lower().endswith(
        ('.png', '.jpg', '.jpeg'))]
    image_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))
    latest_image = os.path.join(
        folder, image_files[-1]) if image_files else None
    return latest_image


def start_queue(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    requests.post(URL, data=data)


def generate_image(input_image):
    try:
        if input_image is None:
            # 返回错误图像而不是None
            error_img = Image.new('RGB', (400, 200), color=(255, 255, 255))
            return error_img, "未上传图片"

        start_time = time.time()
        logging.info("开始移除背景")

        with open("Cutout.json", "r", encoding='utf-8') as file_json:
            prompt = json.load(file_json)

        # 保存上传的图片
        image = Image.fromarray(input_image)
        timestamp = int(time.time())
        image_filename = f"input_{timestamp}.jpg"
        image_path = os.path.join(INPUT_DIR, image_filename)
        image.save(image_path, format='JPEG', quality=95)

        logging.info(f"保存输入图片: {image_filename}, 大小: {image.size}")

        # 更新工作流中的输入图片路径
        prompt["79"]["inputs"]["image"] = image_filename

        previous_image = get_latest_image(OUTPUT_DIR)

        # 发送请求到ComfyUI并等待响应
        try:
            response = requests.post(URL, json={"prompt": prompt}, timeout=30)
            response.raise_for_status()  # 检查响应状态
        except requests.exceptions.RequestException as e:
            error_img = Image.new('RGB', (400, 200), color=(255, 255, 255))
            return error_img, f"ComfyUI请求失败: {str(e)}"

        # 等待生成结果
        max_retries = 60  # 60秒超时
        retry_count = 0

        while retry_count < max_retries:
            latest_image = get_latest_image(OUTPUT_DIR)
            if latest_image and latest_image != previous_image:
                try:
                    # 确保文件完全写入
                    time.sleep(0.5)
                    output_image = Image.open(latest_image)
                    # 确保图片完整加载
                    output_image.load()

                    process_time = time.time() - start_time
                    logging.info(f"处理耗时: {process_time:.2f}秒")

                    return output_image, "处理成功"
                except Exception as img_err:
                    logging.error(f"图片加载错误: {str(img_err)}")
                    time.sleep(1)
                    retry_count += 1
                    continue
            time.sleep(1)
            retry_count += 1

        logging.error(f"处理超时: 输入图片 {image_filename}")
        error_img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        return error_img, "图像生成超时"

    except Exception as e:
        logging.error(f"处理错误: {str(e)}")
        error_img = Image.new('RGB', (400, 200), color=(255, 255, 255))
        return error_img, f"处理错误: {str(e)}"


# 更新Gradio接口配置
demo = gr.Interface(
    fn=generate_image,
    inputs=gr.Image(
        type="numpy",
        label="输入图片",
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
    title="背景移除工具",
    cache_examples=False  # 禁用示例缓存
)


# 启动服务器
if __name__ == "__main__":
    demo.launch(
        share=True,
        allowed_paths=[INPUT_DIR, OUTPUT_DIR],
        server_name=SERVER_NAME,
        server_port=SERVER_PORT,
        show_error=True,  # 显示详细错误信息
        max_threads=1  # 限制并发处理数
    )
