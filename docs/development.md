# 开发指南

## 项目结构

```
ComfyUI_Gradio/
├── comfyui_gradio/        # 主源代码目录
│   ├── __init__.py
│   ├── app.py             # 集成应用
│   ├── server.py          # 服务器启动
│   ├── services/          # 服务模块
│   │   ├── __init__.py
│   │   ├── fill_repaint.py
│   │   ├── fill_replace.py
│   │   ├── image_extend.py
│   │   ├── image_upscale.py
│   │   ├── manual_remove_object.py
│   │   ├── remove_background.py
│   │   └── remove_object.py
│   └── utils/             # 工具函数
│       ├── __init__.py
│       ├── logger.py
│       ├── stats.py
│       ├── dingtalk.py
│       └── error_reporter.py
├── config/                # 配置文件
│   ├── __init__.py
│   ├── config.py
│   └── config.yaml.example
├── docs/                  # 文档
│   ├── installation.md
│   ├── usage.md
│   └── development.md
├── logs/                  # 日志文件目录
│   └── .gitkeep
├── scripts/               # 脚本工具
│   ├── log_manager.py
│   └── daily_stats.py
├── tests/                 # 测试代码
│   ├── __init__.py
│   ├── test_fill_repaint.py
│   └── test_fill_replace.py
├── workflows/             # ComfyUI 工作流
│   ├── Fill_Repaint.json
│   └── Fill_Replace.json
├── .gitignore             # Git忽略文件
├── LICENSE                # 许可证文件
├── README.md              # 项目说明
├── requirements.txt       # 依赖项
├── setup.py               # 安装脚本
└── start.py               # 启动脚本
```

## 开发环境设置

1. **克隆项目**
```bash
git clone https://github.com/your-username/ComfyUI_Gradio.git
cd ComfyUI_Gradio
```

2. **创建虚拟环境**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **安装开发依赖**
```bash
pip install -e ".[dev]"
```

4. **配置开发环境**
```bash
cp config/config.yaml.example config/config.yaml
# 编辑配置文件
```

## 添加新功能

### 1. 创建新的服务模块

在 `comfyui_gradio/services/` 目录下创建新的服务模块，例如 `new_feature.py`：

```python
"""
新功能服务 - 功能描述
"""

import gradio as gr
from PIL import Image
from typing import Tuple, Dict, Any

from config import Config
from utils.logger import setup_logger
from utils.error_reporter import ErrorReporter

# 设置日志
logger = setup_logger("new-feature-logs")
error_reporter = ErrorReporter("new-feature", logger)


class NewFeatureApp:
    def __init__(self):
        # 初始化代码
        pass
        
    def process_image(self, input_image, param1, param2):
        # 处理图片的代码
        pass


def create_interface() -> Dict[str, Any]:
    """创建Gradio界面组件"""
    # 创建应用实例
    app = NewFeatureApp()

    # 创建界面组件
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(label="输入图片")
            param1 = gr.Slider(label="参数1")
            param2 = gr.Textbox(label="参数2")
            process_btn = gr.Button("开始处理", variant="primary")

        with gr.Column():
            output_image = gr.Image(label="处理结果")
            status_text = gr.Textbox(label="处理状态")

    # 设置事件处理
    process_btn.click(
        fn=app.process_image,
        inputs=[input_image, param1, param2],
        outputs=[output_image, status_text]
    )

    return {
        "input_image": input_image,
        "param1": param1,
        "param2": param2,
        "process_btn": process_btn,
        "output_image": output_image,
        "status_text": status_text
    }


def main():
    """独立运行时的入口函数"""
    # 创建 Gradio 界面
    with gr.Blocks(title="新功能工具") as demo:
        gr.Markdown("""
            <div style="text-align: center;">
                <h1>新功能工具</h1>
            </div>
            功能描述
        """)

        # 创建界面组件
        interface_components = create_interface()

    # 从配置中获取端口
    server_port = Config.get("gradio_server.new_feature_server_port", 7900)

    demo.launch(
        share=Config.get("gradio_server.share"),
        server_name=Config.get("gradio_server.server_name"),
        server_port=server_port,
    )


if __name__ == "__main__":
    main()
```

### 2. 更新集成应用

在 `comfyui_gradio/app.py` 中添加新功能：

```python
from comfyui_gradio.services import (
    fill_repaint, fill_replace, image_extend, image_upscale,
    manual_remove_object, remove_background, remove_object,
    new_feature  # 导入新功能
)

def create_integrated_app():
    """创建集成应用界面"""
    with gr.Blocks(title="ComfyUI Gradio 图像处理工具集") as demo:
        # ...
        
        with gr.Tabs() as tabs:
            # ...
            
            with gr.TabItem("新功能"):
                new_feature_interface = new_feature.create_interface()
                
    return demo
```

### 3. 更新服务管理器

在 `comfyui_gradio/server.py` 中添加新功能的配置：

```python
self.service_configs = [
    # ...
    {
        "name": "新功能",
        "script": "comfyui_gradio/services/new_feature.py",
        "port": Config.get("gradio_server.new_feature_server_port", 7900)
    },
    # ...
]
```

### 4. 更新配置文件示例

在 `config/config.yaml.example` 中添加新功能的配置：

```yaml
gradio_server:
  # ...
  new_feature_server_port: 7900
  # ...
```

## 测试

### 单元测试

在 `tests/` 目录下创建测试文件，例如 `test_new_feature.py`：

```python
import unittest
from PIL import Image
import numpy as np
from comfyui_gradio.services.new_feature import NewFeatureApp

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        self.app = NewFeatureApp()
        
    def test_process_image(self):
        # 创建测试图片
        test_image = Image.new('RGB', (100, 100), color='red')
        
        # 调用处理函数
        result_image, status = self.app.process_image(test_image, 0.5, "test")
        
        # 验证结果
        self.assertIsInstance(result_image, Image.Image)
        self.assertEqual(status, "处理成功")
        
if __name__ == '__main__':
    unittest.main()
```

### 运行测试

```bash
python -m unittest discover tests
```

## 贡献代码

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request
