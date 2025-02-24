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
        if input_image is None:
            raise ValueError("未上传图片")

        with open("2_Image_Upscale_TTP.json", "r", 
                  encoding='utf-8') as file_json:
            prompt = json.load(file_json)

        # 保存上传的图片
        image = Image.fromarray(input_image)
        timestamp = int(time.time())
        image_filename = f"input_{timestamp}.jpg"
        image_path = os.path.join(INPUT_DIR, image_filename)
        image.save(image_path, format='JPEG', quality=95)

        # 更新工作流中的输入图片路径
        prompt["10"]["inputs"]["image"] = image_filename

        previous_image = get_latest_image(OUTPUT_DIR)
        
        # 发送请求到ComfyUI
        response = requests.post(URL, json={"prompt": prompt})
        if response.status_code != 200:
            raise Exception(f"ComfyUI请求失败: {response.status_code}")

        # 等待生成结果
        max_retries = 500  # 10分钟超时
        retry_count = 0

        while retry_count < max_retries:
            latest_image = get_latest_image(OUTPUT_DIR)
            if latest_image and latest_image != previous_image:
                try:
                    output_image = Image.open(latest_image)
                    output_image.load()  # 确保图片完整加载
                    return output_image
                except Exception as img_err:
                    print(f"图片加载错误: {str(img_err)}")
                    continue
            time.sleep(1)
            retry_count += 1

        raise TimeoutError("图像生成超时")

    except Exception as e:
        print(f"错误: {str(e)}")
        return None


# 更新Gradio接口配置
demo = gr.Interface(
    fn=generate_image,
    inputs=gr.Image(type="numpy", label="输入图片"),
    outputs=gr.Image(type="pil", label="处理结果", format="png"),
    title="图片放大工具"
)

# 启动服务
if __name__ == "__main__":
    demo.launch(
        share=True,
        allowed_paths=[OUTPUT_DIR],
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True
    )
