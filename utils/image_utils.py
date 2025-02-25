from pathlib import Path
from PIL import Image
import time
import logging


def get_latest_image(folder: str) -> str:
    """
    获取指定文件夹中最新的图片路径
    Args:
        folder: 文件夹路径
    Returns:
        最新图片的完整路径,如果没有图片则返回None
    """
    try:
        folder_path = Path(folder)
        image_files = []
        for ext in ['jpg', 'jpeg', 'png']:
            image_files.extend(folder_path.glob(f"*.{ext}"))

        if not image_files:
            return None

        latest_image = max(image_files, key=lambda x: x.stat().st_mtime)
        return str(latest_image)  # 返回路径字符串
    except Exception as e:
        logging.error(f"获取最新图片失败: {str(e)}")
        return None


def create_error_image(text: str = "错误") -> Image:
    """
    创建错误提示图片
    Args:
        text: 错误提示文本
    Returns:
        PIL.Image对象
    """
    return Image.new('RGB', (400, 200), color=(255, 255, 255))


def save_upload_image(image: Image, input_dir: str) -> str:
    """
    保存上传的图片
    Args:
        image: PIL.Image对象
        input_dir: 保存目录
    Returns:
        保存的文件名
    """
    timestamp = int(time.time())
    filename = f"input_{timestamp}.jpg"
    filepath = Path(input_dir) / filename
    image.save(filepath, format='JPEG', quality=95)
    return filename
