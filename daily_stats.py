from utils import UsageStats


def main():
    try:
        stats = UsageStats()
        print("启动统计服务...")
        stats.start_scheduler()
    except KeyboardInterrupt:
        print("\n统计服务已停止")
    except Exception as e:
        print(f"统计服务启动失败: {e}")


if __name__ == "__main__":
    main()
