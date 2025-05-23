<div align="center">

# ComfyUI_Gradio 图像处理工具集

![Version](https://img.shields.io/badge/version-1.1.0-blue)
![Python](https://img.shields.io/badge/Python-≥3.10-blue)
![License](https://img.shields.io/badge/license-MIT-brightgreen)

基于 Gradio 开发的 ComfyUI 图像处理工具集，提供直观的 Web 界面进行图像处理操作。
集成多种图像处理功能，支持背景移除、图像放大、物体移除、局部重绘等操作。

</div>

## 📋 目录

- [功能概览](#-功能概览)
- [快速开始](#-快速开始)
- [详细功能说明](#-详细功能说明)
- [项目结构](#-项目结构)
- [监控与统计](#-监控与统计)
- [开发者信息](#-开发者信息)
- [相关链接](#-相关链接)

## ✨ 功能概览

本工具集提供以下图像处理功能：

| 功能 | 描述 | 端口 |
|------|------|------|
| 集成应用 | 将所有功能整合到一个界面，通过顶部图标切换 | 7899 |
| 背景移除 | 自动识别并移除图片背景 | 7860 |
| 图片放大 | 提高图片分辨率和清晰度，支持重绘幅度调整 | 7870 |
| 物体移除 | 通过文本描述自动移除图片中的物体 | 7880 |
| 手动蒙版物体移除 | 手动绘制蒙版移除物体 | 7881 |
| 图片扩展 | 向图片四周扩展内容 | 7890 |
| 局部重绘 | 通过提示词重绘图片区域，支持中文输入 | 7891 |
| 物体替换 | 将图片中的物体替换为新物体，支持中文输入 | 7892 |

## 🚀 快速开始

### 环境要求

- Python >= 3.10
- ComfyUI 服务

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/ComfyUI_Gradio.git
cd ComfyUI_Gradio
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置服务**
```bash
# 创建配置文件
cp config/config.yaml.example config/config.yaml
# 编辑配置文件
notepad config/config.yaml
```

编辑 `config/config.yaml`，设置以下关键配置：
```yaml
comfyui_server:
  url: "http://127.0.0.1:8188/prompt"  # ComfyUI API地址
  timeout: 30  # 请求超时时间(秒)

paths:
  input_dir: "{YOUR_ComfyUI_Input_Dir}"  # ComfyUI输入目录
  output_dir: "{YOUR_ComfyUI_Output_Dir}"  # ComfyUI输出目录
  clipspace_dir: "{YOUR_ComfyUI_Input_Clipspace_Dir}"  # ComfyUI剪贴板目录

gradio_server:
  server_name: "0.0.0.0"  # 服务器地址，使用0.0.0.0可以从外部访问
  share: false  # 是否共享到公网

# 图像处理配置
image_processing:
  max_size: 1600  # 图像的最大尺寸（宽度或高度），超过这个尺寸将自动缩放
  keep_aspect_ratio: true  # 缩放时是否保持宽高比

# 钩钉推送配置
dingtalk:
   enabled: true  # 是否启用钩钉推送
   webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
   secret: "xxx"  # 安全设置的签名密钥

# 统计服务配置
stats:
   enabled: true  # 是否启用统计服务
   report_time: "17:30"  # 每日报告发送时间
   retry_count: 3  # 发送失败重试次数
   retry_delay: 60  # 重试间隔时间(秒)
```

4. **启动服务**
```bash
python start.py
```

启动后，访问 `http://127.0.0.1:7899` 打开集成应用界面。

## 📖 详细功能说明

### 集成应用

集成应用将所有功能整合到一个界面，通过顶部选择栏可以方便地切换不同功能。

**使用方法**：
1. 在顶部选择栏中选择需要使用的功能
2. 上传图片并设置相应参数
3. 点击"开始处理"按钮
4. 等待处理完成后查看结果

### 背景移除

自动识别并移除图片背景，生成透明背景图片。

**使用方法**：
1. 上传需要移除背景的图片
2. 调整遮罩偏移量（可选，范围-10到10）
3. 点击"开始处理"按钮
4. 处理完成后可下载透明背景的图片

### 图片放大

提高图片分辨率和清晰度，支持重绘幅度调整。

**使用方法**：
1. 上传需要放大的图片
2. 调整重绘幅度滑块（可选），值越大重绘越强（0-1，默认0.25）
3. 点击"开始处理"按钮
4. 处理完成后可下载高清放大后的图片

**注意**：大尺寸图片（超过1600像素）会自动缩放以提高性能

### 物体移除

通过文本描述自动识别并移除图片中的物体。

**使用方法**：
1. 上传图片
2. 在文本框中输入要移除的物体描述（例如："watch"、"text"、"table"等）
3. 调整遮罩扩展值（可选）
4. 点击"开始处理"按钮
5. 处理完成后可下载移除物体后的图片

### 手动蒙版物体移除

通过手动绘制蒙版来精确移除图片中的物体。

**使用方法**：
1. 上传图片
2. 使用绘图工具在需要移除的区域上绘制蒙版
3. 调整遮罩扩展值（可选）
4. 点击"开始处理"按钮
5. 处理完成后可下载移除物体后的图片

### 图片扩展

向图片四周扩展内容，生成更大尺寸的图片。

**使用方法**：
1. 上传图片
2. 输入扩展内容描述（必填）
3. 设置四个方向的扩展像素值
4. 点击"开始处理"按钮
5. 处理完成后可下载扩展后的图片

### 局部重绘

通过提示词重绘图片中的内容，支持中文输入。

**使用方法**：
1. 上传图片
2. 用黑色画笔在图片上标记需要重绘的区域
3. 输入提示词，描述你希望重绘的内容（支持中文）
4. 调整重绘幅度，值越大重绘越强
5. 点击"开始处理"按钮
6. 处理完成后可下载重绘后的图片

### 物体替换

将图片中的物体替换为另一张图片中的物体，支持中文输入。

**使用方法**：
1. 上传源图片
2. 在源图片上绘制要替换的区域
3. 上传目标图片（用于替换标记区域）
4. 输入物体描述（支持中文）
5. 点击"开始处理"按钮
6. 处理完成后可下载替换后的图片

## 📚 项目结构

```
ComfyUI_Gradio/
├── comfyui_gradio/        # 主程序包
│   ├── services/          # 服务模块
│   │   ├── fill_repaint.py    # 局部重绘服务
│   │   ├── fill_replace.py    # 物体替换服务
│   │   ├── image_extend.py    # 图片扩展服务
│   │   ├── image_upscale.py   # 图片放大服务
│   │   ├── manual_remove_object.py # 手动蒙版物体移除
│   │   ├── remove_background.py   # 背景移除服务
│   │   └── remove_object.py       # 物体移除服务
│   ├── utils/             # 工具函数
│   │   ├── logger.py          # 日志管理
│   │   ├── dingtalk.py        # 钉钉通知
│   │   └── error_reporter.py  # 错误报告
│   ├── app.py             # 集成应用
│   └── config.py          # 配置管理
├── config/                # 配置文件
│   └── config.yaml.example # 配置文件示例
├── logs/                  # 日志文件目录
│   └── archive/           # 日志存档目录
├── scripts/               # 脚本文件
│   ├── log_manager.py     # 日志管理工具
│   ├── test_stats_service.py  # 统计服务测试脚本
│   ├── validate_stats.py  # 统计功能验证工具
│   └── run_log_maintenance.bat # 日志维护脚本
├── workflows/             # ComfyUI 工作流
│   ├── Fill_Repaint.json  # 局部重绘工作流
│   ├── Fill_Replace.json  # 物体替换工作流
│   └── 2_Image_Upscale_TTP.json # 图片放大工作流
└── start.py               # 启动脚本
```

## 📊 监控与统计

### 日志管理

- 日志文件位于 `logs` 目录，按日期组织存储
- 每天的日志保存在对应日期的文件夹中（如 `logs/2025-04-14/`）
- 支持日志轮转，防止日志文件过大
- 自动清理超过 30 天的旧日志
- 自动压缩存档日志，节省存储空间
- 提供 `scripts/log_manager.py` 脚本进行手动管理
- 可通过 `scripts/run_log_maintenance.bat` 设置定时任务

### 错误报告

- 统一的错误报告工具 `utils/error_reporter.py`
- 详细的错误信息，包含文件路径、行号、函数名等
- 自动收集调用栈信息，方便定位错误
- 支持添加上下文信息，包含相关参数和状态
- 支持钉钉通知，实时报告错误

### 钉钉通知

- 错误告警：实时推送错误信息
- 每日统计报告：工作日17:30自动发送使用统计
- 支持自定义消息格式和通知规则

### 使用量统计

- 各功能调用次数统计
- 处理成功率分析
- 自动集成到主服务中，无需单独启动
- 工作日17:30自动发送钉钉统计报告
- 支持手动测试和验证功能

## 👨‍💻 开发者信息

### 注意事项

1. 所有处理都依赖于ComfyUI服务，请确保ComfyUI服务正常运行
2. 处理大图片可能需要较长时间，请耐心等待
3. 大尺寸图片（超过1600像素）会自动缩放以提高性能
4. 如果处理失败，请查看日志文件了解详细错误信息

### 贡献代码

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开一个 Pull Request

## 📄 开源协议

MIT License © 2024

## 🔗 相关链接

- [ComfyUI 项目](https://github.com/comfyanonymous/ComfyUI)
- [Gradio 文档](https://gradio.app/)
