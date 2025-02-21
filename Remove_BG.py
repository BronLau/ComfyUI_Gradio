import json
import os
import time

import gradio as gr
import requests
from PIL import Image

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
        with open("Cutout.json", "r", encoding='utf-8') as file_json:
            prompt = json.load(file_json)

        # 保存上传的图片
        image = Image.fromarray(input_image)
        timestamp = int(time.time())
        image_filename = f"input_{timestamp}.jpg"  # 添加时间戳避免文件名冲突
        image_path = os.path.join(INPUT_DIR, image_filename)
        image.save(image_path)

        # 更新工作流中的输入图片路径
        prompt["79"]["inputs"]["image"] = image_filename

        previous_image = get_latest_image(OUTPUT_DIR)
        start_queue(prompt)

        # 添加超时机制
        max_retries = 30  # 30秒超时
        retry_count = 0

        while retry_count < max_retries:
            latest_image = get_latest_image(OUTPUT_DIR)
            if latest_image and latest_image != previous_image:
                # 直接返回PIL图像对象而不是路径
                return Image.open(latest_image)
            time.sleep(1)
            retry_count += 1

        raise TimeoutError("图像生成超时")

    except Exception as e:
        print(f"生成图像时出错: {str(e)}")
        return None


# 更新Gradio接口配置
demo = gr.Interface(
    fn=generate_image,
    inputs=gr.Image(type="numpy"),
    outputs=gr.Image(type="pil"),
    title="背景移除工具",
)

demo.launch(
    share=True,
    allowed_paths=[OUTPUT_DIR],
    server_name="127.0.0.1",
    server_port=7860
)
