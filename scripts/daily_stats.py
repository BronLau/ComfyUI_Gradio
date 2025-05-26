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
# 未使用的导入
# from comfyui_gradio.config import Config
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

    def collect_stats(self, days=1, debug=False):
        """收集统计数据

        Args:
            days: 收集最近几天的数据
            debug: 是否启用调试输出

        Returns:
            统计数据字典
        """
        logger.info(f"开始收集最近 {days} 天的统计数据...")

        # 计算起始日期
        start_date = datetime.now() - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        start_date_compact = start_date.strftime('%Y%m%d')

        if debug:
            logger.info(f"统计开始日期：{start_date_str}")

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
            # 原始映射
            "rmbg": "背景移除",
            "upscale": "图片放大",
            "remove-object": "物体移除",
            "manual-remove": "手动蒙版物体移除",
            "extend": "图片扩展",
            "repaint": "局部重绘",
            "replace": "物体替换",

            # 新增映射 - 服务脚本日志
            "remove_background": "背景移除",
            "image_upscale": "图片放大",
            "remove_object": "物体移除",
            "manual_remove_object": "手动蒙版物体移除",
            "image_extend": "图片扩展",
            "fill_repaint": "局部重绘",
            "fill_replace": "物体替换",

            # 新增映射 - 带日期后缀的服务日志
            "rmbg-logs_": "背景移除",
            "image-upscale-logs_": "图片放大",
            "remove-object-logs_": "物体移除",
            "manual-remove-object-logs_": "手动蒙版物体移除",
            "image-extend-logs_": "图片扩展",
            "local-repaint-logs_": "局部重绘",
            "object-replace-logs_": "物体替换"
        }

        # 创建请求跟踪字典，用于跟踪每个请求的状态
        requests_tracker = {}

        # 首先扫描日期子目录
        date_dirs = []
        for item in self.log_dir.iterdir():
            if item.is_dir() and re.match(r'\d{4}-\d{2}-\d{2}', item.name):
                # 确保目录名称是有效的日期格式
                dir_date = item.name
                if dir_date >= start_date_str:
                    date_dirs.append(item)
                    if debug:
                        logger.info(f"找到日期目录：{item}")

        # 按日期从新到旧排序
        date_dirs.sort(reverse=True)

        # 处理所有日期目录中的日志文件
        processed_files = 0
        for date_dir in date_dirs:
            if debug:
                logger.info(f"正在处理日期目录：{date_dir}")

            # 从目录名中提取日期
            dir_date = date_dir.name

            # 处理该日期目录下的所有日志文件
            for log_file in date_dir.glob('*.log'):
                processed_files += 1
                self._process_log_file(
                    log_file, service_name_map, stats, start_date_compact,
                    requests_tracker, debug
                )

        # 如果没有找到日期目录或需要额外的日志文件，再扫描根目录中的日志文件
        if processed_files == 0 or debug:
            logger.info("没有找到日期目录或需要扫描额外日志，扫描根目录日志文件")
            for log_file in self.log_dir.glob('*.log'):
                self._process_log_file(
                    log_file, service_name_map, stats, start_date_str,
                    requests_tracker, debug
                )

        # 遍历请求跟踪字典，进行最终统计
        if debug:
            logger.info(f"处理跟踪的请求：总计 {len(requests_tracker)} 个请求")

        for req_id, req_info in requests_tracker.items():
            service_name = req_info.get('service')
            status = req_info.get('status')

            if not service_name or service_name not in stats["服务统计"]:
                continue

            # 增加调用次数
            stats["总调用次数"] += 1
            stats["服务统计"][service_name]["调用次数"] += 1

            # 根据状态增加成功或失败次数
            if status == 'success':
                stats["成功次数"] += 1
                stats["服务统计"][service_name]["成功次数"] += 1
            elif status == 'failed':
                stats["失败次数"] += 1
                stats["服务统计"][service_name]["失败次数"] += 1

        # 计算成功率
        if stats["总调用次数"] > 0:
            stats["成功率"] = f"{(stats['成功次数'] / stats['总调用次数']) * 100:.2f}%"
        else:
            stats["成功率"] = "0.00%"

        # 计算各服务成功率
        for service_name, service_stats in stats["服务统计"].items():
            if service_stats["调用次数"] > 0:
                success_count = service_stats['成功次数']
                call_count = service_stats['调用次数']
                success_rate = (success_count / call_count) * 100
                service_stats["成功率"] = f"{success_rate:.2f}%"
            else:
                # 如果没有调用，成功率为0
                service_stats["成功率"] = "0.00%"

        # 添加统计信息
        stats["统计时间"] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        stats["统计周期"] = f"{days}天"
        stats["开始日期"] = start_date_str
        stats["结束日期"] = datetime.now().strftime('%Y-%m-%d')
        stats["处理的日志文件数"] = processed_files
        stats["跟踪的请求数"] = len(requests_tracker)

        logger.info(
            f"统计数据收集完成：{json.dumps(stats, ensure_ascii=False, indent=2)}")
        return stats

    def _process_log_file(self, log_file, service_name_map, stats, start_date,
                          requests_tracker, debug=False):
        """处理单个日志文件

        Args:
            log_file: 日志文件路径
            service_name_map: 服务名称映射
            stats: 统计数据
            start_date: 开始日期（字符串格式）
            requests_tracker: 请求跟踪字典
            debug: 是否启用调试输出
        """
        try:
            # 识别服务名称
            service_name = None
            file_name = log_file.name

            # 检查是否是带日期后缀的服务日志
            date_suffix_match = re.search(r'_(\d{8})\.log$', file_name)
            if date_suffix_match:
                file_date = date_suffix_match.group(1)
                # 如果文件日期早于开始日期，跳过
                if file_date < start_date:
                    if debug:
                        logger.info(f"跳过日期较早的文件：{file_name}，文件日期：{file_date}")
                    return

            # 尝试匹配服务名称
            for key, name in service_name_map.items():
                if key in file_name:
                    service_name = name
                    break

            if not service_name:
                if debug:
                    logger.info(f"无法识别服务名称：{file_name}")
                return

            if debug:
                logger.info(f"处理日志文件：{log_file}，服务名称：{service_name}")

            # 定义正则表达式模式
            start_pattern = (
                r'(\d{4}-\d{2}-\d{2}.*?)\s+开始(?:处理|图片放大|背景移除|'
                r'物体移除|图片扩展|局部重绘|物体替换).*?请求ID[:\s]+(\w+)'
            )
            success_pattern = (
                r'(\d{4}-\d{2}-\d{2}.*?)\s+(?:处理完成|成功|输出图片)'
                r'.*?请求ID[:\s]+(\w+)'
            )
            failure_pattern = (
                r'(\d{4}-\d{2}-\d{2}.*?)\s+(?:失败|错误|异常|超时处理)'
                r'.*?请求ID[:\s]+(\w+)'
            )

            # 读取日志文件
            with log_file.open('r', encoding='utf-8') as f:
                for line in f:
                    # 检查日期（在行中的日期格式为YYYY-MM-DD）
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                    if not date_match:
                        continue

                    log_date = date_match.group(1)
                    # 如果是YYYY-MM-DD格式的起始日期
                    if len(start_date) == 10 and log_date < start_date:
                        continue
                    # 如果是YYYYMMDD格式的起始日期（用于匹配文件名中的日期）
                    elif (len(start_date) == 8 and
                          log_date.replace('-', '') < start_date):
                        continue

                    # 匹配请求开始
                    start_match = re.search(start_pattern, line)
                    if start_match:
                        req_time, req_id = start_match.groups()
                        if req_id not in requests_tracker:
                            requests_tracker[req_id] = {
                                'service': service_name,
                                'status': 'pending',
                                'start_time': req_time,
                                'end_time': None
                            }
                        continue

                    # 匹配请求成功
                    success_match = re.search(success_pattern, line)
                    if success_match:
                        req_time, req_id = success_match.groups()
                        if req_id in requests_tracker:
                            requests_tracker[req_id]['status'] = 'success'
                            requests_tracker[req_id]['end_time'] = req_time
                        else:
                            # 如果找不到对应的开始记录，创建一个新记录
                            requests_tracker[req_id] = {
                                'service': service_name,
                                'status': 'success',
                                'start_time': None,
                                'end_time': req_time
                            }
                        continue

                    # 匹配请求失败
                    failure_match = re.search(failure_pattern, line)
                    if failure_match:
                        req_time, req_id = failure_match.groups()
                        if req_id in requests_tracker:
                            requests_tracker[req_id]['status'] = 'failed'
                            requests_tracker[req_id]['end_time'] = req_time
                        else:
                            # 如果找不到对应的开始记录，创建一个新记录
                            requests_tracker[req_id] = {
                                'service': service_name,
                                'status': 'failed',
                                'start_time': None,
                                'end_time': req_time
                            }
                        continue

            if debug:
                active_requests = sum(
                    1 for req in requests_tracker.values()
                    if req.get('service') == service_name
                )
                logger.info(f"文件 {log_file} 处理完成，跟踪的请求数：{active_requests}")

        except Exception as e:
            logger.error(f"处理日志文件失败：{log_file}，错误：{e}")

    def generate_report(self, stats):
        """生成报告

        Args:
            stats: 统计数据

        Returns:
            报告文本
        """
        # 获取当前时间
        current_time = datetime.now().strftime('%H:%M:%S')

        # 构建报告标题
        report = "# ComfyUI 每日使用统计\n\n"

        # 统计日期和报告时间
        report += f"📅 统计日期：{stats['开始日期']} | 报告时间：{current_time}\n\n "

        # 总处理量
        report += f"📊 总处理量：{stats['总调用次数']} 张图片\n\n"

        # 添加分隔线
        report += "---\n\n"

        # 功能使用详情
        report += "📈 功能使用详情\n\n"

        # 收集有效的服务
        valid_services = []
        for service_name, service_stats in stats["服务统计"].items():
            if service_stats["调用次数"] > 0:
                valid_services.append((service_name, service_stats))

        # 如果没有任何服务被调用，显示提示信息
        if not valid_services:
            report += "• 今日无使用记录\n"
            return report

        # 计算百分比
        total_calls = stats["总调用次数"]

        # 按照中文服务名称排序
        valid_services.sort(key=lambda x: x[0])

        # 生成报告条目
        for service_name, service_stats in valid_services:
            calls = service_stats["调用次数"]
            percentage = (calls / total_calls * 100) if total_calls > 0 else 0
            report += f"• {service_name}: {calls} 次 ({percentage:.1f}%)\n\n"

        return report

    def send_daily_report(self, debug=False):
        """发送每日报告

        Args:
            debug: 是否启用调试模式
        """
        logger.info("开始生成并发送每日报告...")

        try:
            # 收集统计数据
            stats = self.collect_stats(days=1, debug=debug)

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
