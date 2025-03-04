import re
from datetime import datetime
from pathlib import Path
import schedule
import time
from typing import Dict

from utils.logger import setup_logger
from .dingtalk import DingTalkBot


class UsageStats:
    def __init__(self):
        self.log_dir = Path("logs")
        self.ding = DingTalkBot()
        self.logger = setup_logger("stats-service")

        # 日志文件名到服务名称的映射
        self.log_service_map = {
            "image-extend-logs": "image-extend",
            "image-upscale-logs": "image-upscale",
            "remove-object-logs": "remove-object",
            "rmbg-logs": "rmbg"
        }

        # 服务名称显示映射
        self.service_display_names = {
            "image-extend": "图片扩展",
            "image-upscale": "图片放大",
            "remove-object": "物体移除",
            "rmbg": "背景移除"
        }

    def get_today_logs(self) -> Dict[str, Path]:
        """获取当天的日志文件"""
        today = datetime.now().strftime("%Y%m%d")
        log_files = {}

        for file in self.log_dir.glob(f"*_{today}.log"):
            # 提取日志文件名前缀（不包含日期和扩展名）
            log_prefix = file.name.split('_')[0]
            if log_prefix in self.log_service_map:
                service_name = self.log_service_map[log_prefix]
                log_files[service_name] = file
                self.logger.debug(f"找到日志文件: {file.name} -> {service_name}")

        return log_files

    def analyze_log_file(self, file_path: Path) -> int:
        """分析单个日志文件中的处理次数"""
        success_pattern = re.compile(r"处理完成,耗时:")
        count = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if success_pattern.search(line):
                        count += 1
            self.logger.debug(f"分析日志文件 {file_path.name}: 处理次数 {count}")
        except Exception as e:
            self.logger.error(f"读取日志文件失败: {e}")

        return count

    def generate_report(self) -> str:
        """生成统计报告"""
        log_files = self.get_today_logs()
        today = datetime.now().strftime("%Y-%m-%d")

        # 统计每个服务的使用次数
        stats = {}
        total = 0
        for service, log_file in log_files.items():
            count = self.analyze_log_file(log_file)
            stats[service] = count
            total += count

        # 生成 Markdown 格式的报告
        report = (
            f"### 4090 ComfyUI 每日使用统计 📊\n\n"
            f"> **统计日期：** {today}\n\n"
            "---\n"
            "#### 📈 功能使用情况\n\n"
        )

        # 添加每个服务的统计
        for service, count in stats.items():
            display_name = self.service_display_names.get(service, service)
            report += f"- **{display_name}：** {count} 次\n"

        # 添加总计
        report += f"\n**总计处理：** {total} 张图片"

        self.logger.info(f"生成统计报告: 总处理量 {total} 张图片")
        return report

    def send_daily_report(self):
        """发送每日统计报告"""
        try:
            report = self.generate_report()
            self.ding.send_message(report)
            self.logger.info("每日统计报告发送成功")
        except Exception as e:
            self.logger.error(f"发送统计报告失败: {e}")

    def start_scheduler(self):
        """启动定时任务"""
        # 设置在工作日（周一至周五）下午 17:30 执行统计任务
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
            (schedule.every()
             .__getattribute__(day)
             .at("17:30")
             .do(self.send_daily_report))

        self.logger.info("统计服务已启动，将在工作日下午 17:30 发送统计报告...")

        # 运行定时任务
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"定时任务执行出错: {e}")
                time.sleep(60)  # 发生错误后等待一分钟继续
