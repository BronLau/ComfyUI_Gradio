from pathlib import Path
import yaml
import logging
import os
from typing import Any, Optional, Dict


class Config:
    _instance = None
    _config = None
    _config_path = None
    _last_modified_time = 0

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> None:
        """
        加载配置文件
        Args:
            config_path: 配置文件路径,默认为None使用默认路径
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        # 将路径转换为Path对象
        config_path = Path(config_path)
        cls._config_path = config_path

        if not config_path.exists():
            logging.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            # 记录文件修改时间
            cls._last_modified_time = os.path.getmtime(config_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)

            # 验证必要的配置项
            cls._validate_config()

            logging.info(f"成功加载配置文件: {config_path}")
        except yaml.YAMLError as e:
            logging.error(f"配置文件YAML格式错误: {str(e)}")
            raise
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    @classmethod
    def _validate_config(cls) -> None:
        """验证必要的配置项"""
        required_configs = [
            "comfyui_server.url",
            "paths.input_dir",
            "paths.output_dir",
            "gradio_server.server_name"
        ]

        missing_configs = []
        for config_key in required_configs:
            if cls._get_nested_value(config_key) is None:
                missing_configs.append(config_key)

        if missing_configs:
            error_msg = f"缺少必要的配置项: {', '.join(missing_configs)}"
            logging.error(error_msg)
            raise ValueError(error_msg)

    @classmethod
    def _get_nested_value(cls, key: str) -> Any:
        """获取嵌套配置值，不带默认值和错误处理"""
        keys = key.split('.')
        value = cls._config

        for k in keys:
            if not isinstance(value, dict) or k not in value:
                return None
            value = value[k]

        return value

    @classmethod
    def _check_config_updated(cls) -> bool:
        """检查配置文件是否已更新"""
        if cls._config_path is None:
            return False

        try:
            current_mtime = os.path.getmtime(cls._config_path)
            if current_mtime > cls._last_modified_time:
                logging.info(f"配置文件已更新: {cls._config_path}")
                return True
        except Exception as e:
            logging.error(f"检查配置文件更新失败: {str(e)}")

        return False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        获取配置值
        Args:
            key: 配置键名,支持点号访问嵌套配置
            default: 默认值
        Returns:
            配置值
        """
        # 如果配置未加载，先加载配置
        if cls._config is None:
            cls.load()
        # 如果配置文件已更新，重新加载
        elif cls._check_config_updated():
            cls.load(cls._config_path)

        try:
            keys = key.split('.')
            value = cls._config

            for k in keys:
                if not isinstance(value, dict):
                    return default
                value = value.get(k, default)
                if value is None:
                    return default
            return value
        except Exception as e:
            logging.error(f"获取配置项'{key}'失败: {str(e)}")
            return default

    @classmethod
    def get_all(cls) -> Dict:
        """获取所有配置"""
        if cls._config is None:
            cls.load()
        elif cls._check_config_updated():
            cls.load(cls._config_path)

        return cls._config.copy() if cls._config else {}
