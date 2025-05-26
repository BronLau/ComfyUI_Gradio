"""
服务器启动脚本
"""

import sys
import time
import subprocess
from pathlib import Path
import psutil
from datetime import datetime
from typing import Dict, Optional, Tuple

from comfyui_gradio.config import Config
from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.error_reporter import ErrorReporter


logger = setup_logger("services")
error_reporter = ErrorReporter("services", logger)


class ServiceManager:
    def __init__(self):
        # 服务进程字典，键为服务名称，值为进程对象
        self.services: Dict[str, subprocess.Popen] = {}
        # 服务状态字典，键为服务名称，值为(上次检查时间, 重启次数, 是否健康)
        self.service_status: Dict[str, Tuple[datetime, int, bool]] = {}
        # 服务配置列表
        self.service_configs = [
            {
                "name": "背景移除",
                "script": "comfyui_gradio/services/remove_background.py",
                "port": Config.get("gradio_server.rmbg_server_port", 7860)
            },
            {
                "name": "图片放大",
                "script": "comfyui_gradio/services/image_upscale.py",
                "port": Config.get(
                    "gradio_server.image_upscale_server_port", 7870)
            },
            {
                "name": "物体移除",
                "script": "comfyui_gradio/services/remove_object.py",
                "port": Config.get(
                    "gradio_server.remove_object_server_port", 7880)
            },
            {
                "name": "手动蒙版物体移除",
                "script": "comfyui_gradio/services/manual_remove_object.py",
                "port": Config.get(
                    "gradio_server.manual_remove_object_server_port", 7881)
            },
            {
                "name": "图片扩展",
                "script": "comfyui_gradio/services/image_extend.py",
                "port": Config.get(
                    "gradio_server.image_extend_server_port", 7890)
            },
            {
                "name": "局部重绘",
                "script": "comfyui_gradio/services/fill_repaint.py",
                "port": Config.get(
                    "gradio_server.fill_repaint_server_port", 7891)
            },
            {
                "name": "物体替换",
                "script": "comfyui_gradio/services/fill_replace.py",
                "port": Config.get(
                    "gradio_server.fill_replace_server_port", 7892)
            },
            {
                "name": "集成应用",
                "script": "comfyui_gradio/app.py",
                "port": Config.get("gradio_server.integrated_app_port", 7899)
            },
            {
                "name": "每日统计",
                "script": "scripts/daily_stats.py",
                "port": None
            }
        ]

    def is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        if port is None:
            return False
        try:
            for conn in psutil.net_connections():
                if conn.laddr.port == port:
                    return True
        except Exception as e:
            logger.error(f"检查端口占用失败: {e}")
        return False

    def is_process_running(self, process: Optional[subprocess.Popen]) -> bool:
        """检查进程是否还在运行

        注意：由于Gradio服务可能会分离主进程，我们不仅检查进程状态，
        还检查对应的端口是否仍在使用。
        """
        if process is None:
            return False

        # 获取进程对应的服务名称
        service_name = None
        for name, proc in self.services.items():
            if proc == process:
                service_name = name
                break

        if service_name is None:
            return False

        # 获取服务对应的端口
        port = None
        for config in self.service_configs:
            if config["name"] == service_name:
                port = config["port"]
                break

        # 如果找到端口，检查端口是否仍在使用
        if port is not None and self.is_port_in_use(port):
            return True

        try:
            # poll()返回None表示进程还在运行
            return process.poll() is None
        except Exception as e:
            logger.error(f"检查进程状态失败: {e}")
            return False

    def get_process_memory_usage(
            self, process: Optional[subprocess.Popen]) -> float:
        """获取进程的内存使用量（MB）"""
        if process is None:
            return 0.0
        try:
            process_info = psutil.Process(process.pid)
            # 返回内存使用量，单位为MB
            return process_info.memory_info().rss / (1024 * 1024)
        except Exception as e:
            logger.error(f"获取进程内存使用量失败: {e}")
            return 0.0

    def get_process_cpu_usage(
            self, process: Optional[subprocess.Popen]) -> float:
        """获取进程的CPU使用率（%）"""
        if process is None:
            return 0.0
        try:
            process_info = psutil.Process(process.pid)
            # 返回CPU使用率，单位为%
            return process_info.cpu_percent(interval=0.1)
        except Exception as e:
            logger.error(f"获取进程CPU使用率失败: {e}")
            return 0.0

    def start_service(self, config: dict, is_restart: bool = False) -> bool:
        """启动服务

        Args:
            config: 服务配置
            is_restart: 是否是重启操作

        Returns:
            是否启动成功
        """
        service_name = config["name"]

        # 如果是重启操作，先停止现有服务
        if is_restart and service_name in self.services:
            self.stop_service(service_name)

        # 检查端口是否被占用
        if self.is_port_in_use(config["port"]):
            logger.warning(f'{service_name} 服务端口 {config["port"]} 已被占用')
            return False

        try:
            # 创建日志文件
            script_name = config["script"].replace("/", "_")
            log_file = Path('logs') / f'{script_name}.log'

            # 使用 subprocess.CREATE_NO_WINDOW 替代 CREATE_NEW_CONSOLE
            process = subprocess.Popen(
                [sys.executable, config["script"]],
                cwd=Path(__file__).parent.parent,
                stdout=open(log_file, 'a', encoding='utf-8'),
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW  # 不创建新窗口
            )

            # 存储服务进程
            self.services[service_name] = process

            # 初始化服务状态
            restart_count = 0
            if is_restart and service_name in self.service_status:
                # 如果是重启，保留原来的重启计数
                restart_count = self.service_status[service_name][1] + 1

            current_time = datetime.now()
            status = (current_time, restart_count, True)
            self.service_status[service_name] = status

            # 记录日志
            if is_restart:
                logger.info(f'{service_name} 服务重启成功，重启次数: {restart_count}')
            else:
                logger.info(f'{service_name} 服务启动成功')

            return True
        except Exception as e:
            # 使用错误报告工具报告错误
            error_reporter.report(
                f'{service_name} 服务{"重启" if is_restart else "启动"}失败',
                e,
                {
                    "service_name": service_name,
                    "script": config["script"],
                    "port": config["port"],
                    "is_restart": is_restart
                }
            )
            return False

    def stop_service(self, service_name: str) -> bool:
        """停止服务

        Args:
            service_name: 服务名称

        Returns:
            是否停止成功
        """
        if service_name not in self.services:
            logger.warning(f'{service_name} 服务不存在')
            return False

        try:
            process = self.services[service_name]
            process.terminate()
            # 等待进程结束，最多等待5秒
            for _ in range(50):
                if process.poll() is not None:
                    break
                time.sleep(0.1)

            # 如果进程还没结束，强制结束
            if process.poll() is None:
                process.kill()

            # 从服务字典中移除
            del self.services[service_name]
            logger.info(f'{service_name} 服务已停止')
            return True
        except Exception as e:
            # 使用错误报告工具报告错误
            error_reporter.report(
                f'{service_name} 服务停止失败',
                e,
                {"service_name": service_name}
            )
            return False

    def restart_service(self, service_name: str) -> bool:
        """重启服务

        Args:
            service_name: 服务名称

        Returns:
            是否重启成功
        """
        # 查找服务配置
        config = None
        for cfg in self.service_configs:
            if cfg["name"] == service_name:
                config = cfg
                break

        if config is None:
            logger.warning(f'{service_name} 服务配置不存在')
            return False

        # 停止服务
        self.stop_service(service_name)

        # 等待一下，确保资源释放
        time.sleep(1)

        # 重新启动服务
        return self.start_service(config, is_restart=True)

    def check_service_health(self) -> None:
        """检查所有服务的健康状态

        注意：由于Gradio服务的特殊性，我们不再检查进程是否还在运行，
        而是检查端口是否仍然被占用。
        """
        # 记录一条日志，表明健康检查正在运行
        logger.debug("服务健康检查正在运行")

        # 检查每个服务的端口是否仍然被占用
        for config in self.service_configs:
            service_name = config["name"]
            port = config["port"]

            # 如果端口不再被占用，尝试重启服务
            if port is not None and not self.is_port_in_use(port):
                logger.warning(f'{service_name} 服务端口 {port} 不再被占用，尝试重启')

                # 获取服务状态
                current_time = datetime.now()
                _, restart_count, _ = self.service_status.get(
                    service_name, (current_time, 0, False))

                # 如果重启次数超过限制，不再重启
                if restart_count >= 5:
                    error_reporter.report(
                        f'{service_name} 服务已重启{restart_count}次，不再尝试重启',
                        None,
                        {
                            "service_name": service_name,
                            "restart_count": restart_count
                        }
                    )
                    continue

                # 重启服务
                self.restart_service(service_name)
            else:
                # 服务运行正常，更新服务状态
                current_time = datetime.now()
                _, restart_count, _ = self.service_status.get(
                    service_name, (current_time, 0, False))
                status = (current_time, restart_count, True)
                self.service_status[service_name] = status

    def health_check_thread(self) -> None:
        """健康检查线程函数"""
        logger.info("启动服务健康检查线程")

        while True:
            try:
                # 检查服务健康状态
                self.check_service_health()

                # 每30秒检查一次
                time.sleep(30)
            except Exception as e:
                logger.error(f"健康检查线程出错: {e}")
                time.sleep(30)  # 出错后等待一段时间再继续

    def start_health_check(self) -> None:
        """启动健康检查线程

        注意：由于Gradio服务的特殊性，我们禁用了健康检查功能。
        """
        # 不启动健康检查线程
        logger.info("健康检查功能已禁用，不会自动重启服务")

    def start_all(self) -> int:
        """启动所有服务

        Returns:
            成功启动的服务数量
        """
        logger.info("开始启动所有服务...")
        success_count = 0

        for config in self.service_configs:
            if self.start_service(config):
                success_count += 1
                # 给每个服务一些启动时间
                time.sleep(2)

        logger.info(
            f"服务启动完成: {success_count}/{len(self.service_configs)} 个服务运行中")

        # 启动健康检查线程
        self.start_health_check()

        return success_count

    def stop_all(self) -> None:
        """停止所有服务"""
        logger.info("正在停止所有服务...")
        for service_name in list(self.services.keys()):
            self.stop_service(service_name)


def main():
    # 创建日志目录
    Path("logs").mkdir(exist_ok=True)

    manager = ServiceManager()

    # 注册退出处理
    import atexit
    atexit.register(manager.stop_all)

    try:
        # 启动所有服务
        manager.start_all()
        logger.info("按 Ctrl+C 停止所有服务")

        # 保持主进程运行
        while True:
            # 每秒检查一次是否收到停止信号
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    except Exception as e:
        # 使用错误报告工具报告错误
        error_reporter.report(
            "主程序出错",
            e,
            {"location": "main"}
        )
    finally:
        # 停止所有服务
        manager.stop_all()


if __name__ == "__main__":
    main()
