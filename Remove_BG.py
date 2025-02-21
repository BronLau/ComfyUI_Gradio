import json
import os
import time
import random

import gradio as gr
import numpy as np
import requests
from PIL import Image

URL = "http://127.0.0.1:8188/prompt"
INPUT_DIR = "D:\AIGC\ComfyUI\input"
OUTPUT_DIR = "D:\AIGC\ComfyUI\output"

def get_latest_image(folder):
    files = os.listdir(folder)
    image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    image_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))
    latest_image = os.path.join(folder, image_files[-1]) if image_files else None
    return latest_image

def start_queue(prompt_workflow):
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    requests.post(URL, data=data)

def generate_image(input_image):   
    with open("Cutout.json", "r", encoding='utf-8') as file_json:
        prompt = json.load(file_json)
    
    # 保存上传的图片
    image = Image.fromarray(input_image)
    image_filename = "input_image.jpg"
    image.save(os.path.join(INPUT_DIR, image_filename))
    
    # 更新工作流中的输入图片路径
    prompt["79"]["inputs"]["image"] = image_filename
    
    previous_image = get_latest_image(OUTPUT_DIR)
    start_queue(prompt)

    while True:
        latest_image = get_latest_image(OUTPUT_DIR)
        if latest_image != previous_image:
            return latest_image
        time.sleep(1)

demo = gr.Interface(fn=generate_image, inputs=["image"], outputs=["image"])

demo.launch(
    share=True,
    allowed_paths=[OUTPUT_DIR]
)
