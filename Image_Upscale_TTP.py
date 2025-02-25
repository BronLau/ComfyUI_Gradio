import json
import os
import time
import logging
from datetime import datetime

import gradio as gr
import requests
from PIL import Image

# 配置日志
LOG_DIR = "image-upscale-logs"
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

URL = "http://127.0.0.1:8188/prompt"
INPUT_DIR = "D:\AIGC\ComfyUI\input"
OUTPUT_DIR = "D:\AIGC\ComfyUI\output"


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
            raise ValueError("未上传图片")

        start_time = time.time()
        logging.info("开始处理新的图片请求")

        with open("2_Image_Upscale_TTP.json", "r",
                  encoding='utf-8') as file_json:
            prompt = json.load(file_json)

        # 保存上传的图片
        image = Image.fromarray(input_image)
        timestamp = int(time.time())
        image_filename = f"input_{timestamp}.jpg"
        image_path = os.path.join(INPUT_DIR, image_filename)
        image.save(image_path, format='JPEG', quality=95)

        logging.info(f"保存输入图片: {image_filename}, 大小: {image.size}")

        # 更新工作流中的输入图片路径
        prompt["10"]["inputs"]["image"] = image_filename

        previous_image = get_latest_image(OUTPUT_DIR)

        # 发送请求到ComfyUI并等待响应
        try:
            response = requests.post(URL, json={"prompt": prompt}, timeout=30)
            response.raise_for_status()  # 检查响应状态
        except requests.exceptions.RequestException as e:
            raise Exception(f"ComfyUI请求失败: {str(e)}")

        # 等待生成结果
        max_retries = 600  # 10分钟超时
        retry_count = 0

        while retry_count < max_retries:
            latest_image = get_latest_image(OUTPUT_DIR)
            if latest_image and latest_image != previous_image:
                try:
                    # 确保文件完全写入
                    time.sleep(0.5)
                    output_image = Image.open(latest_image)
                    # 转换为RGB模式避免透明通道问题
                    if output_image.mode in ('RGBA', 'LA'):
                        output_image = output_image.convert('RGB')
                    # 确保图片完整加载
                    output_image.load()

                    process_time = time.time() - start_time
                    logging.info(f"处理耗时: {process_time:.2f}秒")

                    return output_image
                except Exception as img_err:
                    logging.error(f"图片加载错误: {str(img_err)}")
                    time.sleep(1)
                    retry_count += 1
                    continue
            time.sleep(1)
            retry_count += 1

        logging.error(f"处理超时: 输入图片 {image_filename}")
        raise TimeoutError("图像生成超时")

    except Exception as e:
        logging.error(f"处理错误: {str(e)}")
        return None


# 更新Gradio接口配置
demo = gr.Interface(
    fn=generate_image,
    inputs=gr.Image(type="numpy", label="输入图片"),
    outputs=gr.Image(type="pil", label="处理结果", format="png"),  # 指定输出格式为PNG
    title="图片放大工具",
)


demo.launch(
    share=True,
    allowed_paths=[OUTPUT_DIR],
    server_name="127.0.0.1",
    server_port=7860
)
