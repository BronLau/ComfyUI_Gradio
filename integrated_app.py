from fill_replace import FillReplaceApp
from fill_repaint import FillRepaintApp
from image_extend import ImageExtendApp
from manual_remove_object import RemoveObjectApp as ManualRemoveObjectApp
from remove_object import RemoveObjectApp
from image_upscale import ImageUpscaleApp
from remove_background import RmbgApp
import gradio as gr

from config import Config
from utils.logger import setup_logger

# 设置日志
logger = setup_logger("integrated-app")

# 导入各功能模块的应用类


def create_integrated_app():
    """创建集成应用"""
    # 初始化各功能模块的应用实例
    rmbg_app = RmbgApp()
    upscale_app = ImageUpscaleApp()
    remove_obj_app = RemoveObjectApp()
    manual_remove_obj_app = ManualRemoveObjectApp()
    image_extend_app = ImageExtendApp()
    fill_repaint_app = FillRepaintApp()
    fill_replace_app = FillReplaceApp()

    # 创建Gradio界面
    with gr.Blocks(title="ComfyUI 图像处理工具集") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>ComfyUI 图像处理工具集</h1>
            </div>
        """)

        # 创建顶部选择栏（Tabs组件）
        with gr.Tabs():
            # 背景移除功能
            with gr.Tab("背景移除"):
                with gr.Row():
                    with gr.Column():
                        rmbg_input = gr.Image(
                            type="numpy",
                            label="输入图片",
                            sources=["upload"]
                        )
                        rmbg_mask_offset = gr.Slider(
                            minimum=-10,
                            maximum=10,
                            value=rmbg_app.default_mask_offset,
                            step=0.1,
                            label="遮罩偏移量（像素收缩）",
                            info="调整遮罩边缘的偏移量 (-10 到 10)"
                        )
                        rmbg_process_btn = gr.Button("开始处理", variant="primary")

                    with gr.Column():
                        rmbg_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        rmbg_status = gr.Textbox(label="处理状态")

                # 绑定处理函数
                rmbg_process_btn.click(
                    fn=rmbg_app.process_image,
                    inputs=[rmbg_input, rmbg_mask_offset],
                    outputs=[rmbg_output, rmbg_status]
                )

            # 图片放大功能
            with gr.Tab("图片放大"):
                with gr.Row():
                    with gr.Column():
                        upscale_input = gr.Image(
                            type="numpy",
                            label="输入图片",
                            sources=["upload"]
                        )
                        upscale_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        upscale_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        upscale_status = gr.Textbox(label="处理状态")

                # 绑定处理函数
                upscale_process_btn.click(
                    fn=upscale_app.process_image,
                    inputs=[upscale_input],
                    outputs=[upscale_output, upscale_status]
                )

            # 物体移除功能
            with gr.Tab("物体移除"):
                with gr.Row():
                    with gr.Column():
                        remove_obj_input = gr.Image(
                            type="numpy",
                            label="输入图片",
                            sources=["upload"]
                        )
                        remove_obj_desc = gr.Textbox(
                            label="要移除的物体描述",
                            placeholder="例如：watch, text, table等",
                            value=""
                        )
                        remove_obj_expand = gr.Slider(
                            minimum=0,
                            maximum=24,
                            value=remove_obj_app.default_expand,
                            step=1,
                            label="遮罩扩展值",
                            info="调整遮罩扩展范围 (0 到 24)"
                        )
                        remove_obj_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        remove_obj_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        remove_obj_status = gr.Textbox(label="处理状态")

                # 绑定处理函数
                remove_obj_process_btn.click(
                    fn=remove_obj_app.process_image,
                    inputs=[remove_obj_input,
                            remove_obj_desc, remove_obj_expand],
                    outputs=[remove_obj_output, remove_obj_status]
                )

            # 手动蒙版物体移除功能
            with gr.Tab("手动蒙版物体移除"):
                with gr.Row():
                    with gr.Column():
                        manual_remove_obj_input = gr.ImageEditor(
                            label="输入图片",
                            type="numpy",
                            brush=gr.Brush(
                                colors=["#000000"], default_size=12),
                            interactive=True,
                        )
                        manual_remove_obj_expand = gr.Slider(
                            minimum=0,
                            maximum=24,
                            value=12,
                            step=1,
                            label="遮罩扩展值",
                            info="调整遮罩扩展范围 (0 到 24)"
                        )
                        manual_remove_obj_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        manual_remove_obj_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        manual_remove_obj_status = gr.Textbox(label="处理状态")

                # 绑定处理函数
                manual_remove_obj_process_btn.click(
                    fn=manual_remove_obj_app.process_image,
                    inputs=[
                        manual_remove_obj_input,
                        manual_remove_obj_expand,
                    ],
                    outputs=[
                        manual_remove_obj_output,
                        manual_remove_obj_status,
                    ]
                )

            # 图片扩展功能
            with gr.Tab("图片扩展"):
                with gr.Row():
                    with gr.Column():
                        extend_input = gr.Image(
                            type="numpy",
                            label="输入图片",
                            sources=["upload"]
                        )
                        extend_text = gr.Textbox(
                            label="扩展内容描述",
                            placeholder="描述要在扩展区域生成的内容",
                            value=""
                        )

                        with gr.Row():
                            with gr.Column():
                                extend_left = gr.Slider(
                                    minimum=0,
                                    maximum=512,
                                    value=0,
                                    step=8,
                                    label="左侧扩展像素"
                                )
                                extend_top = gr.Slider(
                                    minimum=0,
                                    maximum=512,
                                    value=0,
                                    step=8,
                                    label="顶部扩展像素"
                                )
                            with gr.Column():
                                extend_right = gr.Slider(
                                    minimum=0,
                                    maximum=512,
                                    value=0,
                                    step=8,
                                    label="右侧扩展像素"
                                )
                                extend_bottom = gr.Slider(
                                    minimum=0,
                                    maximum=512,
                                    value=0,
                                    step=8,
                                    label="底部扩展像素"
                                )

                        extend_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        extend_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        extend_status = gr.Textbox(label="处理状态")

                # 添加校验函数，检查扩展内容描述是否已填写
                def validate_and_process(image, text, left, top,
                                         right, bottom):
                    if text is None or text.strip() == "":
                        gr.Warning("请输入扩展内容描述后再开始处理！")
                        return None, "请输入扩展内容描述"
                    return image_extend_app.process_image(
                        image, text, left, top, right, bottom)

                # 绑定处理函数
                extend_process_btn.click(
                    fn=validate_and_process,
                    inputs=[
                        extend_input,
                        extend_text,
                        extend_left,
                        extend_top,
                        extend_right,
                        extend_bottom
                    ],
                    outputs=[
                        extend_output,
                        extend_status
                    ]
                )

            # 局部重绘功能
            with gr.Tab("局部重绘"):
                with gr.Row():
                    with gr.Column():
                        repaint_input = gr.ImageEditor(
                            label="输入图片",
                            type="numpy",
                            brush=gr.Brush(
                                colors=["#000000"], default_size=12),
                            interactive=True,
                        )
                        repaint_text = gr.Textbox(
                            label="提示词",
                            placeholder="描述你希望重绘的内容（可选）",
                            value=""
                        )
                        repaint_denoise = gr.Slider(
                            minimum=0.1,
                            maximum=1.0,
                            value=0.3,
                            step=0.05,
                            label="重绘幅度",
                            info="调整重绘的强度，值越大重绘越强 (0.1 到 1.0)"
                        )
                        repaint_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        repaint_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        repaint_status = gr.Textbox(label="处理状态")

                # 处理函数，允许用户不输入提示词
                def validate_and_process_repaint(image, text, denoise):
                    # 允许用户不输入提示词，使用系统生成的提示词
                    if text is None:
                        text = ""
                    return fill_repaint_app.process_image(image, text, denoise)

                # 绑定处理函数
                repaint_process_btn.click(
                    fn=validate_and_process_repaint,
                    inputs=[
                        repaint_input,
                        repaint_text,
                        repaint_denoise
                    ],
                    outputs=[
                        repaint_output,
                        repaint_status
                    ]
                )

            # 物体替换功能
            with gr.Tab("物体替换"):
                with gr.Row():
                    with gr.Column():
                        replace_input = gr.ImageEditor(
                            label="源图片",
                            type="numpy",
                            brush=gr.Brush(
                                colors=["#000000"], default_size=12),
                            interactive=True,
                        )
                        replace_target = gr.Image(
                            type="numpy",
                            label="目标图片",
                            sources=["upload"]
                        )
                        replace_prompt = gr.Textbox(
                            label="物体描述",
                            placeholder="描述要替换的物体类型，例如：clothes, furniture等",
                            value=""
                        )
                        replace_process_btn = gr.Button(
                            "开始处理", variant="primary")

                    with gr.Column():
                        replace_output = gr.Image(
                            type="pil",
                            label="处理结果",
                            format="png",
                            show_label=True
                        )
                        replace_status = gr.Textbox(label="处理状态")

                # 添加校验函数
                def validate_and_process_replace(input_data,
                                                 target_image, prompt):
                    if prompt is None or prompt.strip() == "":
                        gr.Warning("请输入物体描述后再开始处理！")
                        return None, "请输入物体描述"
                    if target_image is None:
                        gr.Warning("请上传目标图片后再开始处理！")
                        return None, "请上传目标图片"
                    return fill_replace_app.process_image(
                        input_data, target_image, prompt)

                # 绑定处理函数
                replace_process_btn.click(
                    fn=validate_and_process_replace,
                    inputs=[
                        replace_input,
                        replace_target,
                        replace_prompt
                    ],
                    outputs=[
                        replace_output,
                        replace_status
                    ]
                )

    return demo


def main():
    # 创建集成应用
    demo = create_integrated_app()

    # 启动服务
    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=Config.get(
            "gradio_server.integrated_app_port", 7850),  # 使用新端口
        show_error=True,
        max_threads=1  # 限制并发处理数
    )


if __name__ == "__main__":
    main()
