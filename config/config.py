from pathlib import Path
import yaml
import logging
from typing import Any, Optional


class Config:
    _instance = None
    _config = None

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> None:
        """
        加载配置文件
        Args:
            config_path: 配置文件路径,默认为None使用默认路径
        """
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
            logging.info(f"成功加载配置文件: {config_path}")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

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
        if cls._config is None:
            cls.load()

        try:
            keys = key.split('.')
            value = cls._config

            for k in keys:
                value = value.get(k, default)
            return value
        except Exception as e:
            logging.error(f"获取配置项'{key}'失败: {str(e)}")
            return default
