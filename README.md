<div align="center">

# ComfyUI_Gradio 图像处理工具集

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/Python-≥3.10-blue)
![Node](https://img.shields.io/badge/Node.js-≥20.0.0-green)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

</div>

## 📝 项目介绍

基于 Gradio 开发的 ComfyUI 图像处理工具集，提供直观的 Web 界面进行图像处理操作。

## ✨ 核心功能

- 🎯 背景移除
- 🔍 图片放大
- ✂️ 物体移除
- 🎨 手动蒙版物体移除 
- 📐 图片扩展
- 📊 使用统计

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 20.0.0
- NPM >= 10.0.0
- ComfyUI 服务

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/yourusername/ComfyUI_Gradio.git
cd ComfyUI_Gradio
```

2. **安装依赖**
```bash
pip install -r requirements.txt
npm install
```

3. **配置服务**

编辑 `config/config.yaml`:
```yaml
comfyui_server:
  url: "http://127.0.0.1:8188/prompt"
  timeout: 30

paths:
  input_dir: "{REPLEASE_YOUR_COMFYUI_INPUT_DIR}"
  output_dir: "{REPLEASE_YOUR_COMFYUI_OUTPUT_DIR}"
  clipspace_dir: "{REPLEASE_YOUR_COMFYUI_CLIPSPACE_DIR}"

gradio_server:
  server_name: "127.0.0.1"
  share: true
```

4. **启动服务**
```bash
python start.py
```

## 📚 项目结构

```
ComfyUI_Gradio/
├── config/              # 配置文件
│   ├── __init__.py
│   ├── config.py
│   └── config.yaml
├── logs/               # 日志文件
├── utils/              # 工具函数
│   ├── __init__.py
│   ├── logger.py
│   ├── stats.py
│   ├── dingtalk.py
│   └── image_utils.py
├── workflows/          # ComfyUI 工作流
└── services/          # 服务模块
```

## 🔧 服务端口

| 服务 | 端口 |
|------|------|
| 背景移除 | 7860 |
| 图片放大 | 7870 |
| 物体移除 | 7880 |
| 手动蒙版 | 7881 |
| 图片扩展 | 7890 |

## 📈 监控与统计

- 📁 日志文件位于 `logs` 目录
- 🔔 支持钉钉通知
  - 错误告警
  - 每日统计报告 (17:30)
- 📊 使用量统计
  - 各功能调用次数
  - 处理成功率

## 📄 开源协议

MIT License © 2024

## 🔗 相关链接

- [ComfyUI 项目](https://github.com/comfyanonymous/ComfyUI)
- [Gradio 文档](https://gradio.app/)