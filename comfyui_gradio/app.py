"""
集成应用 - 将所有功能整合到一个界面
"""

import os
import sys

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

import gradio as gr
from comfyui_gradio.config import Config
from comfyui_gradio.utils.stats import UsageStats
from comfyui_gradio.services import (
    fill_repaint, fill_replace, image_extend, image_upscale,
    manual_remove_object, remove_background, remove_object
)


def create_integrated_app():
    """创建集成应用界面"""
    with gr.Blocks(title="ComfyUI Gradio 图像处理工具集") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>ComfyUI Gradio 图像处理工具集</h1>
            </div>
        """)

        with gr.Tabs():
            with gr.TabItem("背景移除"):
                remove_background.create_interface()

            with gr.TabItem("图片放大"):
                image_upscale.create_interface()

            with gr.TabItem("物体移除"):
                remove_object.create_interface()

            with gr.TabItem("手动蒙版物体移除"):
                manual_remove_object.create_interface()

            with gr.TabItem("图片扩展"):
                image_extend.create_interface()

            with gr.TabItem("局部重绘"):
                fill_repaint.create_interface()

            with gr.TabItem("物体替换"):
                fill_replace.create_interface()

    return demo


def launch_app(is_standalone=True):
    """启动集成应用
    
    Args:
        is_standalone: 是否是独立运行模式，如果是由server.py调用则为False
    """
    demo = create_integrated_app()

    # 从配置中获取端口，如果没有则使用默认值
    server_port = Config.get("gradio_server.integrated_app_port", 7899)

    # 只有在独立运行模式下才启动统计服务
    # 避免与server.py中的统计服务冲突
    if is_standalone:
        try:
            stats_service = UsageStats()
            stats_service.start_scheduler()
            print("统计服务启动成功")
        except Exception as e:
            print(f"统计服务启动失败: {e}")

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    # 作为主程序运行时，使用独立模式
    launch_app(is_standalone=True)
