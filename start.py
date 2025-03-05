import subprocess
import sys
from pathlib import Path
import time
from typing import Dict
import psutil
import atexit
from utils.logger import setup_logger

logger = setup_logger("services")


class ServiceManager:
    def __init__(self):
        self.services: Dict[str, subprocess.Popen] = {}
        self.service_configs = [
            {
                "name": "背景移除",
                "script": "remove_background.py",
                "port": 7860
            },
            {
                "name": "图片放大",
                "script": "image_upscale.py",
                "port": 7870
            },
            {
                "name": "物体移除",
                "script": "remove_object.py",
                "port": 7880
            },
            {
                "name": "图片扩展",
                "script": "image_extend.py",
                "port": 7890
            },
            {
                "name": "使用统计",
                "script": "daily_stats.py",
                "port": None
            }
        ]

    def is_port_in_use(self, port: int) -> bool:
        if port is None:
            return False
        for conn in psutil.net_connections():
            if conn.laddr.port == port:
                return True
        return False

    def start_service(self, config: dict):
        if self.is_port_in_use(config["port"]):
            logger.warning(f'{config["name"]} 服务端口 {config["port"]} 已被占用')
            return False

        try:
            # 创建日志文件
            log_file = Path('logs') / f'{config["script"]}.log'

            # 使用 subprocess.CREATE_NO_WINDOW 替代 CREATE_NEW_CONSOLE
            process = subprocess.Popen(
                [sys.executable, config["script"]],
                cwd=Path(__file__).parent,
                stdout=open(log_file, 'a', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW  # 不创建新窗口
            )
            self.services[config["name"]] = process
            logger.info(f'{config["name"]} 服务启动成功')
            return True
        except Exception as e:
            logger.error(f'{config["name"]} 服务启动失败: {e}')
            return False

    def start_all(self):
        logger.info("开始启动所有服务...")
        success_count = 0

        for config in self.service_configs:
            if self.start_service(config):
                success_count += 1
                # 给每个服务一些启动时间
                time.sleep(2)

        logger.info(
            f"服务启动完成: {success_count}/{len(self.service_configs)} 个服务运行中")
        return success_count

    def stop_all(self):
        logger.info("正在停止所有服务...")
        for name, process in self.services.items():
            try:
                process.terminate()
                logger.info(f'{name} 服务已停止')
            except Exception as e:
                logger.error(f'{name} 服务停止失败: {e}')


def main():
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)

    manager = ServiceManager()

    # 注册退出处理
    atexit.register(manager.stop_all)

    try:
        manager.start_all()
        logger.info("按 Ctrl+C 停止所有服务")
        # 保持主进程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        manager.stop_all()


if __name__ == "__main__":
    main()
