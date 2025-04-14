# 安装指南

## 环境要求

- Python >= 3.10
- ComfyUI 服务

## 安装步骤

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
  input_dir: "D:/ComfyUI/input"  # ComfyUI输入目录
  output_dir: "D:/ComfyUI/output"  # ComfyUI输出目录
  clipspace_dir: "D:/ComfyUI/input/clipspace"  # ComfyUI剪贴板目录

gradio_server:
  server_name: "127.0.0.1"  # 服务器地址，使用0.0.0.0可以从外部访问
  share: false  # 是否共享到公网
```

4. **启动服务**
```bash
python start.py
```

启动后，访问 `http://127.0.0.1:7899` 打开集成应用界面。

## 开发安装

如果您想要进行开发，可以使用以下命令安装项目：

```bash
pip install -e .
```

这将以可编辑模式安装项目，您对代码的修改会立即生效。

## 故障排除

1. **端口被占用**

如果启动服务时提示端口被占用，可以在配置文件中修改端口号：

```yaml
gradio_server:
  integrated_app_port: 7899  # 修改为其他未被占用的端口
```

2. **ComfyUI服务无法连接**

确保ComfyUI服务已经启动，并且配置文件中的URL正确：

```yaml
comfyui_server:
  url: "http://127.0.0.1:8188/prompt"  # 确保端口号与ComfyUI服务一致
```

3. **日志文件查看**

如果遇到问题，可以查看日志文件了解详细信息：

```bash
# 查看集成应用日志
cat logs/comfyui_gradio_app.py.log

# 查看服务管理日志
cat logs/services.log
```
