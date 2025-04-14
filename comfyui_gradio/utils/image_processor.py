"""
图像处理工具 - 提供图像预处理功能
"""

from PIL import Image
import numpy as np
from typing import Union, Tuple, Dict, Any
import logging

logger = logging.getLogger("image-processor")

class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def resize_if_needed(image: Union[Image.Image, np.ndarray], 
                         max_size: int = 1600, 
                         keep_aspect_ratio: bool = True) -> Tuple[Union[Image.Image, np.ndarray], bool, Dict[str, Any]]:
        """
        如果图像尺寸超过指定大小，则进行缩放
        
        Args:
            image: 输入图像，可以是PIL Image或numpy数组
            max_size: 图像的最大尺寸（宽度或高度）
            keep_aspect_ratio: 是否保持宽高比
            
        Returns:
            Tuple[Union[Image.Image, np.ndarray], bool, Dict[str, Any]]: 
                - 处理后的图像
                - 是否进行了缩放
                - 图像信息（原始尺寸、新尺寸等）
        """
        # 检查图像类型
        is_numpy = isinstance(image, np.ndarray)
        
        # 如果是numpy数组，转换为PIL Image进行处理
        if is_numpy:
            pil_image = Image.fromarray(image)
        else:
            pil_image = image
            
        original_width, original_height = pil_image.size
        info = {
            "original_size": (original_width, original_height),
            "resized": False,
            "new_size": (original_width, original_height)
        }
        
        # 检查是否需要缩放
        if original_width <= max_size and original_height <= max_size:
            # 不需要缩放
            return image, False, info
            
        # 需要缩放
        if keep_aspect_ratio:
            # 保持宽高比
            if original_width > original_height:
                new_width = max_size
                new_height = int(original_height * (max_size / original_width))
            else:
                new_height = max_size
                new_width = int(original_width * (max_size / original_height))
        else:
            # 不保持宽高比，直接缩放到最大尺寸
            new_width = max_size
            new_height = max_size
            
        # 执行缩放
        resized_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
        
        # 更新信息
        info["resized"] = True
        info["new_size"] = (new_width, new_height)
        info["scale_factor"] = (original_width / new_width, original_height / new_height)
        
        logger.info(f"图像已缩放: {original_width}x{original_height} -> {new_width}x{new_height}")
        
        # 如果原始输入是numpy数组，则转换回numpy数组
        if is_numpy:
            return np.array(resized_image), True, info
        else:
            return resized_image, True, info
