import re
from datetime import datetime
from pathlib import Path
import schedule
import time
import threading
from typing import Dict

from comfyui_gradio.utils.logger import setup_logger
from comfyui_gradio.utils.dingtalk import DingTalkBot
from comfyui_gradio.config import Config


class UsageStats:
    # 单例模式实现
    _instance = None
    _initialized = False
    _scheduler_started = False
    _scheduler_lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(UsageStats, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        # 确保初始化代码只执行一次
        if UsageStats._initialized:
            return
            
        UsageStats._initialized = True
        self.log_dir = Path("logs")
        self.ding = DingTalkBot()
        self.logger = setup_logger("stats-service")
        
        # 添加实例ID用于调试
        self.instance_id = id(self)
        self.logger.debug(f"初始化统计服务实例 ID:{self.instance_id}")

        # 从配置获取参数
        self.stats_enabled = Config.get("stats.enabled", True)
        self.report_time = Config.get("stats.report_time", "17:30")
        self.retry_count = Config.get("stats.retry_count", 3)
        self.retry_delay = Config.get("stats.retry_delay", 60)

        # 增强的日志文件名到服务名称的映射
        self.log_service_map = {
            "comfyui_gradio_services_image_extend.py": "image-extend",
            "comfyui_gradio_services_image_upscale.py": "image-upscale",
            "comfyui_gradio_services_remove_object.py": "remove-object",
            "comfyui_gradio_services_manual_remove_object.py": (
                "manual-remove-object"),
            "comfyui_gradio_services_remove_background.py": "rmbg",
            "comfyui_gradio_services_fill_repaint.py": "local-repaint",
            "comfyui_gradio_services_fill_replace.py": "object-replace",
            # 服务名称映射
            "image-extend": "image-extend",
            "image-upscale": "image-upscale",
            "remove-object": "remove-object",
            "manual-remove-object": "manual-remove-object",
            "rmbg": "rmbg",
            "local-repaint": "local-repaint",
            "object-replace": "object-replace",
            "test-service": "test-service"
        }

        # 服务名称显示映射
        self.service_display_names = {
            "image-extend": "图片扩展",
            "image-upscale": "图片放大",
            "remove-object": "物体移除",
            "manual-remove-object": "手动蒙版物体移除",
            "rmbg": "背景移除",
            "local-repaint": "局部重绘",
            "object-replace": "物体替换",
            "test-service": "测试服务"
        }

    def get_today_logs(self) -> Dict[str, Path]:
        """获取当天的日志文件"""
        today = datetime.now().strftime("%Y%m%d")
        log_files = {}

        try:
            # 使用标准化的日志文件名格式匹配
            pattern = f"*_{today}.log"
            
            for file in self.log_dir.glob(pattern):
                # 从文件名中提取服务名称
                service_name = self._extract_service_name_from_standard_format(file)
                if service_name and service_name not in log_files:
                    log_files[service_name] = file
                    self.logger.debug(
                        f"找到日志文件: {file.name} -> {service_name}")
                        
            # 兼容旧的日志文件格式(仅作为备用)
            if not log_files:
                self.logger.info("未找到标准格式日志文件，尝试使用旧格式匹配")
                for file in self.log_dir.glob("*.log"):
                    # 检查文件修改日期是否为今天
                    today_start = datetime.now().replace(
                        hour=0, minute=0, second=0).timestamp()
                    if file.stat().st_mtime >= today_start:
                        # 尝试匹配服务名称
                        service_name = self._extract_service_name(file)
                        if service_name and service_name not in log_files:
                            log_files[service_name] = file
                            self.logger.debug(
                                f"找到旧格式日志文件: {file.name} -> {service_name}")
        except Exception as e:
            self.logger.error(f"扫描日志文件失败: {e}")

        return log_files
        
    def _extract_service_name_from_standard_format(self, file_path: Path) -> str:
        """从标准格式文件名中提取服务名称"""
        # 标准格式: service-name_YYYYMMDD.log
        file_name = file_path.name
        parts = file_name.split('_')
        if len(parts) >= 2:
            service_prefix = parts[0]
            # 检查服务名映射
            if service_prefix in self.log_service_map:
                return self.log_service_map[service_prefix]
            return service_prefix
        return None

    def _extract_service_name(self, file_path: Path) -> str:
        """从文件路径提取服务名称（旧方法，用于兼容）"""
        file_name = file_path.name

        # 精确匹配
        if file_name in self.log_service_map:
            return self.log_service_map[file_name]

        # 前缀匹配
        for key, service_name in self.log_service_map.items():
            if key in file_name:
                return service_name

        return None

    def analyze_log_file(self, file_path: Path) -> int:
        """分析单个日志文件中的处理次数"""
        # 增强的匹配模式
        success_patterns = [
            re.compile(r"处理完成.*?请求ID.*?耗时"),  # 原模式
            re.compile(r"成功.*?处理.*?图片"),  # 成功处理模式
            re.compile(r"请求.*?处理完成"),  # 请求完成模式
        ]
        count = 0

        try:
            if not file_path.exists() or file_path.stat().st_size == 0:
                return 0

            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 检查当天的日志
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    if today_str not in line:
                        continue

                    # 应用所有匹配模式
                    for pattern in success_patterns:
                        if pattern.search(line):
                            count += 1
                            break  # 避免重复计数

            self.logger.debug(
                f"分析日志文件 {file_path.name}: 处理次数 {count}")
        except Exception as e:
            self.logger.error(f"读取日志文件失败 {file_path}: {e}")

        return count

    def generate_report(self) -> str:
        """生成增强的统计报告"""
        log_files = self.get_today_logs()
        today = datetime.now().strftime("%Y-%m-%d")
        current_time = datetime.now().strftime("%H:%M:%S")

        # 统计每个服务的使用次数
        stats = {}
        total = 0
        for service, log_file in log_files.items():
            count = self.analyze_log_file(log_file)
            stats[service] = count
            total += count

        # 生成优化的 Markdown 格式报告
        report = (
            f"### 🎯 ComfyUI Gradio 每日使用统计\n\n"
            f"> **📅 统计日期：** {today}\n"
            f"> **⏰ 报告时间：** {current_time}\n"
            f"> **📊 总处理量：** {total} 张图片\n\n"
            "---\n"
        )

        if total > 0:
            report += "#### 📈 功能使用详情\n\n"
            # 按使用量排序
            sorted_stats = sorted(
                stats.items(), key=lambda x: x[1], reverse=True)
            for service, count in sorted_stats:
                if count > 0:
                    display_name = self.service_display_names.get(
                        service, service)
                    percentage = (count / total * 100) if total > 0 else 0
                    report += (
                        f"- **{display_name}：** {count} 次 "
                        f"({percentage:.1f}%)\n")
        else:
            report += "#### 📝 今日暂无处理记录\n\n"
            report += "> 系统运行正常，等待用户使用\n"

        # 添加系统信息
        report += "\n---\n"
        server_name = Config.get('gradio_server.server_name')
        report += f"💻 **服务器：** {server_name}\n"
        integrated_port = Config.get(
            'gradio_server.integrated_app_port', 7899)
        report += f"🔧 **集成端口：** {integrated_port}"

        self.logger.info(f"生成统计报告: 总处理量 {total} 张图片")
        return report

    def send_daily_report(self):
        """发送每日统计报告（增强错误处理和重试机制）"""
        if not self.stats_enabled:
            self.logger.info("统计服务已禁用，跳过报告发送")
            return

        # 添加实例ID日志，便于调试
        self.logger.info(
            f"实例 ID:{self.instance_id} 开始发送每日统计报告")

        for attempt in range(self.retry_count):
            try:
                self.logger.info(
                    f"开始发送每日统计报告 "
                    f"(尝试 {attempt + 1}/{self.retry_count})")

                report = self.generate_report()
                self.ding.send_message(report)

                self.logger.info("每日统计报告发送成功")
                return

            except Exception as e:
                self.logger.error(
                    f"发送统计报告失败 "
                    f"(尝试 {attempt + 1}/{self.retry_count}): {e}")

                if attempt < self.retry_count - 1:
                    self.logger.info(f"等待 {self.retry_delay} 秒后重试...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error("所有重试都失败，放弃发送统计报告")

    def _scheduler_thread(self):
        """调度器线程函数"""
        try:
            # 从配置获取报告时间
            report_time = self.report_time

            # 设置在工作日执行统计任务
            weekdays = [
                'monday', 'tuesday', 'wednesday', 'thursday', 'friday']
            for day in weekdays:
                (schedule.every()
                 .__getattribute__(day)
                 .at(report_time)
                 .do(self.send_daily_report))

            self.logger.info(
                f"统计服务线程已启动，实例 ID:{self.instance_id}，"
                f"将在工作日 {report_time} 发送统计报告...")

            # 运行定时任务
            while True:
                try:
                    schedule.run_pending()
                    # 使用更短的检查间隔，提高响应性
                    time.sleep(10)  # 每10秒检查一次
                except Exception as e:
                    self.logger.error(f"定时任务执行出错: {e}")
                    time.sleep(10)  # 发生错误后等待10秒继续
        except Exception as e:
            self.logger.error(f"调度器线程启动失败: {e}")

    def start_scheduler(self):
        """启动定时任务"""
        if not self.stats_enabled:
            self.logger.info("统计服务已禁用，不启动调度器")
            return
            
        # 使用锁确保只有一个线程能执行此关键部分
        with UsageStats._scheduler_lock:
            # 检查调度器是否已启动
            if UsageStats._scheduler_started:
                self.logger.info(
                    f"统计服务调度器已经在运行，实例 ID:{self.instance_id}，"
                    f"跳过启动")
                return
                
            try:
                # 创建并启动调度器线程
                scheduler_thread = threading.Thread(
                    target=self._scheduler_thread,
                    daemon=True  # 设置为守护线程，主线程结束时自动结束
                )
                scheduler_thread.start()
                UsageStats._scheduler_started = True
                self.logger.info(
                    f"统计服务已启动，实例 ID:{self.instance_id}，"
                    f"调度器运行在独立线程中")
            except Exception as e:
                self.logger.error(f"启动统计服务失败: {e}")

    def manual_report(self):
        """手动触发统计报告（用于测试）"""
        self.logger.info(f"手动触发统计报告，实例 ID:{self.instance_id}")
        self.send_daily_report() 