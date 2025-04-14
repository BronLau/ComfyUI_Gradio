from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="comfyui_gradio",
    version="1.1.0",
    author="ComfyUI Gradio Contributors",
    author_email="your-email@example.com",
    description="基于 Gradio 开发的 ComfyUI 图像处理工具集",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-username/ComfyUI_Gradio",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "gradio>=3.50.0",
        "pillow>=10.0.0",
        "requests>=2.31.0",
        "numpy>=1.24.0",
        "psutil>=5.9.0",
        "schedule>=1.2.0",
    ],
    entry_points={
        "console_scripts": [
            "comfyui-gradio=comfyui_gradio.server:main",
        ],
    },
)
