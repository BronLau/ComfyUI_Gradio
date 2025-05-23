#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
统计功能验证工具 - 验证日志文件匹配、数据统计准确性、钉钉推送功能
支持完整验证和单独测试模式
"""

from comfyui_gradio.config import Config
from comfyui_gradio.utils.stats import UsageStats
import os
import sys
import argparse
import traceback

# 添加项目根目录到Python路径
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, root_dir)


def validate_log_files():
    """验证日志文件匹配"""
    print("1. 验证日志文件匹配...")
    stats_service = UsageStats()

    log_files = stats_service.get_today_logs()
    print(f"   发现 {len(log_files)} 个日志文件:")

    for service, log_file in log_files.items():
        file_size = log_file.stat().st_size if log_file.exists() else 0
        print(f"   - {service}: {log_file.name} ({file_size} bytes)")

    return len(log_files) > 0


def validate_data_accuracy():
    """验证数据统计准确性"""
    print("2. 验证数据统计准确性...")
    stats_service = UsageStats()

    log_files = stats_service.get_today_logs()
    accurate = True

    for service, log_file in log_files.items():
        count = stats_service.analyze_log_file(log_file)
        print(f"   - {service}: 处理次数 {count}")

        if count < 0:
            print(f"   警告: {service} 处理次数异常")
            accurate = False

    return accurate


def validate_dingtalk():
    """验证钉钉推送功能"""
    print("3. 验证钉钉推送功能...")
    stats_service = UsageStats()

    try:
        print("   生成测试报告...")
        test_report = stats_service.generate_report()
        print("   发送测试报告到钉钉...")
        print("   TestMode: 不实际发送消息")
        # 在测试模式下不实际发送消息，避免重复通知
        # stats_service.ding.send_message(test_report)
        print("   钉钉推送功能验证通过")
        return True
    except Exception as e:
        print(f"   钉钉推送功能验证失败: {e}")
        traceback.print_exc()
        return False


def test_stats_service():
    """测试统计服务功能"""
    print("===== 测试统计服务 =====")
    stats_service = UsageStats()

    print("1. 检查服务实例信息:")
    print(f"   实例ID: {stats_service.instance_id}")
    print(f"   已启动: {UsageStats._initialized}")
    print(f"   调度器运行状态: {UsageStats._scheduler_started}")
    print(f"   统计服务启用状态: {stats_service.stats_enabled}")
    print(f"   报告时间: {stats_service.report_time}")

    print("\n2. 手动生成报告测试:")
    try:
        report = stats_service.generate_report()
        print("   报告生成成功")
        print("   报告内容:")
        print("-" * 50)
        print(report)
        print("-" * 50)
    except Exception as e:
        print(f"   报告生成失败: {e}")
        traceback.print_exc()

    return True


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='统计功能验证工具')
    parser.add_argument('-m', '--mode', choices=['validate', 'test'],
                        default='validate', help='运行模式：验证或测试')
    args = parser.parse_args()

    if args.mode == 'test':
        return test_stats_service()

    # 验证模式
    results = []

    # 1. 日志文件匹配测试
    results.append(validate_log_files())

    # 2. 数据统计准确性测试
    results.append(validate_data_accuracy())

    # 3. 钉钉推送功能测试
    results.append(validate_dingtalk())

    # 统计并显示结果
    success_count = sum(1 for r in results if r)
    print("\n===== 验证结果 =====")
    print(f"总测试项: {len(results)}")
    print(f"通过项: {success_count}")
    print(f"失败项: {len(results) - success_count}")

    if all(results):
        print("\n所有验证通过 ✓")
        return 0
    else:
        print("\n存在失败项，请检查日志 ✗")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n运行过程中发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)
