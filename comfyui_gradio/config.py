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
            # 使用项目根目录下的config/config.yaml
            root_dir = Path(__file__).parent.parent
            config_path = root_dir / "config" / "config.yaml"

        # 将路径转换为Path对象
        config_path = Path(config_path)
        cls._config_path = config_path

        if not config_path.exists():
            logging.error(f"配置文件不存在: {config_path}")
            raise FileNotFoundError(f"配置文件不存在: {config_path}")

        try:
            # 记录文件的最后修改时间
            cls._last_modified_time = os.path.getmtime(config_path)

            # 读取配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                cls._config = yaml.safe_load(f)
                logging.info(f"配置文件加载成功: {config_path}")
        except Exception as e:
            logging.error(f"配置文件加载失败: {e}")
            raise

    @classmethod
    def reload_if_changed(cls) -> bool:
        """
        如果配置文件已经被修改，则重新加载
        Returns:
            是否重新加载了配置文件
        """
        if cls._config_path is None:
            cls.load()
            return True

        try:
            current_mtime = os.path.getmtime(cls._config_path)
            if current_mtime > cls._last_modified_time:
                cls.load(str(cls._config_path))
                return True
        except Exception as e:
            logging.error(f"检查配置文件修改失败: {e}")

        return False

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        """
        获取配置项
        Args:
            key: 配置项键名，支持点号分隔的多级键名，如"server.port"
            default: 默认值，当配置项不存在时返回
        Returns:
            配置项的值
        """
        # 如果配置未加载，则加载配置
        if cls._config is None:
            cls.load()

        # 检查配置文件是否被修改
        cls.reload_if_changed()

        # 分割键名
        keys = key.split('.')
        value = cls._config

        # 逐级查找
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """
        获取所有配置项
        Returns:
            所有配置项的字典
        """
        # 如果配置未加载，则加载配置
        if cls._config is None:
            cls.load()

        # 检查配置文件是否被修改
        cls.reload_if_changed()

        return cls._config
