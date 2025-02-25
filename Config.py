import os
import yaml
import logging


class ConfigLoader:
    _instance = None
    _config = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load_config()

    def load_config(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__),
                                       'Config.yaml')
            if not os.path.exists(config_path):
                raise FileNotFoundError(f"配置文件不存在: {config_path}")
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)

            logging.info(f"成功加载配置文件: {config_path}")
        except Exception as e:
            logging.error(f"加载配置文件失败: {str(e)}")
            raise

    @staticmethod
    def get(key_path, default=None):
        """
        获取配置值，支持使用点号访问嵌套配置
        例如: Config.get('comfyui_server.url')
        """
        try:
            instance = ConfigLoader.get_instance()
            keys = key_path.split('.')
            value = instance._config

            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key, default)
                else:
                    return default
            return value
        except Exception as e:
            logging.error(f"获取配置项 '{key_path}' 失败: {str(e)}")
            return default


def get(key_path, default=None):
    return ConfigLoader.get(key_path, default)
