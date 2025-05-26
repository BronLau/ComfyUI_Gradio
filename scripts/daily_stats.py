#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
每日统计服务 - 收集和报告每日使用统计数据
"""

# 必须先导入os和sys，然后添加项目根目录到Python路径，才能导入comfyui_gradio模块
from pathlib import Path
from datetime import datetime, timedelta
import re
import schedule
import logging
import json
import time
from comfyui_gradio.utils.dingtalk import DingTalkBot
from comfyui_gradio.config import Config
import os
import sys

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)

# 现在可以导入comfyui_gradio模块

# 导入其他模块

# 导入其他模块

# 导入项目模块


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join('logs', 'daily_stats.log'),
            encoding='utf-8'
        )
    ]
)
logger = logging.getLogger('daily_stats')


class DailyStats:
    def __init__(self, log_dir='logs'):
        """初始化每日统计

        Args:
            log_dir: 日志目录
        """
        self.log_dir = Path(log_dir)
        self.ding = DingTalkBot()

        # 确保日志目录存在
        self.log_dir.mkdir(exist_ok=True)

        logger.info(f"每日统计服务初始化完成，日志目录：{self.log_dir}")

    def collect_stats(self, days=1):
        """收集统计数据

        Args:
            days: 收集最近几天的数据

        Returns:
            统计数据字典
        """
        logger.info(f"开始收集最近 {days} 天的统计数据...")

        # 计算起始日期
        start_date = datetime.now() - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')

        # 初始化统计数据
        stats = {
            "总调用次数": 0,
            "成功次数": 0,
            "失败次数": 0,
            "服务统计": {
                "背景移除": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "图片放大": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "物体移除": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "手动蒙版物体移除": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "图片扩展": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "局部重绘": {"调用次数": 0, "成功次数": 0, "失败次数": 0},
                "物体替换": {"调用次数": 0, "成功次数": 0, "失败次数": 0}
            }
        }

        # 服务名称映射
        service_name_map = {
            "rmbg": "背景移除",
            "upscale": "图片放大",
            "remove-object": "物体移除",
            "manual-remove": "手动蒙版物体移除",
            "extend": "图片扩展",
            "repaint": "局部重绘",
            "replace": "物体替换"
        }

        # 遍历日志文件
        for log_file in self.log_dir.glob('*.log'):
            try:
                service_name = None
                for key, name in service_name_map.items():
                    if key in log_file.name:
                        service_name = name
                        break

                if not service_name:
                    continue

                # 读取日志文件
                with log_file.open('r', encoding='utf-8') as f:
                    for line in f:
                        # 检查日期
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                        if not date_match:
                            continue

                        log_date = date_match.group(1)
                        if log_date < start_date_str:
                            continue

                        # 统计调用次数
                        if "开始处理" in line or "开始" in line:
                            stats["总调用次数"] += 1
                            stats["服务统计"][service_name]["调用次数"] += 1

                        # 统计成功次数
                        if "处理完成" in line or "成功" in line:
                            stats["成功次数"] += 1
                            stats["服务统计"][service_name]["成功次数"] += 1

                        # 统计失败次数
                        if "失败" in line or "错误" in line:
                            stats["失败次数"] += 1
                            stats["服务统计"][service_name]["失败次数"] += 1
            except Exception as e:
                logger.error(f"处理日志文件失败：{log_file}，错误：{e}")

        # 计算成功率
        if stats["总调用次数"] > 0:
            stats["成功率"] = f"{stats['成功次数'] / stats['总调用次数'] * 100:.2f}%"
        else:
            stats["成功率"] = "0.00%"

        # 计算各服务成功率
        for service_name, service_stats in stats["服务统计"].items():
            if service_stats["调用次数"] > 0:
                success_count = service_stats['成功次数']
                call_count = service_stats['调用次数']
                success_rate = success_count / call_count * 100
                service_stats["成功率"] = f"{success_rate:.2f}%"
            else:
                service_stats["成功率"] = "0.00%"

        logger.info(
            f"统计数据收集完成：{json.dumps(stats, ensure_ascii=False, indent=2)}")
        return stats

    def generate_report(self, stats):
        """生成报告

        Args:
            stats: 统计数据

        Returns:
            报告文本
        """
        report = "# ComfyUI Gradio 每日统计报告\n\n"
        report += "## 总体统计\n\n"
        report += f"- 总调用次数：{stats['总调用次数']}\n"
        report += f"- 成功次数：{stats['成功次数']}\n"
        report += f"- 失败次数：{stats['失败次数']}\n"
        report += f"- 成功率：{stats['成功率']}\n\n"

        report += "## 服务统计\n\n"
        for service_name, service_stats in stats["服务统计"].items():
            if service_stats["调用次数"] > 0:
                report += f"### {service_name}\n\n"
                report += f"- 调用次数：{service_stats['调用次数']}\n"
                report += f"- 成功次数：{service_stats['成功次数']}\n"
                report += f"- 失败次数：{service_stats['失败次数']}\n"
                report += f"- 成功率：{service_stats['成功率']}\n\n"

        report += "## 系统信息\n\n"
        report += f"- 报告时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"- 服务器：{Config.get('gradio_server.server_name')}\n"

        return report

    def send_daily_report(self):
        """发送每日报告"""
        logger.info("开始生成并发送每日报告...")

        try:
            # 收集统计数据
            stats = self.collect_stats(days=1)

            # 生成报告
            report = self.generate_report(stats)

            # 发送报告
            self.ding.send_message(report)

            logger.info("每日报告发送成功")
        except Exception as e:
            logger.error(f"发送每日报告失败，错误：{e}")

    def run(self):
        """运行每日统计服务"""
        logger.info("每日统计服务启动...")

        # 设置定时任务，每个工作日17:30发送报告
        schedule.every().monday.at("17:30").do(self.send_daily_report)
        schedule.every().tuesday.at("17:30").do(self.send_daily_report)
        schedule.every().wednesday.at("17:30").do(self.send_daily_report)
        schedule.every().thursday.at("17:30").do(self.send_daily_report)
        schedule.every().friday.at("17:30").do(self.send_daily_report)

        logger.info("定时任务已设置，每个工作日17:30发送报告")

        # 运行定时任务
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次


def main():
    """主函数"""
    # 创建每日统计服务
    stats_service = DailyStats()

    # 运行服务
    stats_service.run()


if __name__ == '__main__':
    main()
