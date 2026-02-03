"""
APoU - All Posts of User
百度贴吧用户发言列表爬虫模块
"""

from APoU.crawler import UserPostsCrawler
from APoU.exceptions import (
    APoUError,
    APIError,
    NetworkError,
    ParseError,
    RateLimitError,
)

__version__ = "2.0.0"
__all__ = [
    "UserPostsCrawler",
    "APoUError",
    "APIError",
    "NetworkError",
    "ParseError",
    "RateLimitError",
]


def main():
    """APoU 命令行入口点（从 APoU.py 调用）"""
    # 延迟导入避免循环依赖
    import argparse
    import sys
    import time

    from APoU import UserPostsCrawler
    from APoU.config import CrawlerConfig
    from AutoCCF.cli import CLI, Colors

    VERSION = "2.0.0"

    def parse_args() -> argparse.Namespace:
        """解析命令行参数"""
        parser = argparse.ArgumentParser(
            description="百度贴吧用户发言爬虫 - 获取指定用户的所有发言列表",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
    python APoU.py -u 张三
    python APoU.py --username 张三 --forum 某贴吧
    python APoU.py -u 张三 --delay 3.0 --no-raw
            """,
        )

        parser.add_argument(
            "-u", "--username",
            type=str,
            help="要爬取的用户名",
        )
        parser.add_argument(
            "-f", "--forum",
            type=str,
            default="",
            help="指定贴吧名（留空表示所有贴吧）",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=2.0,
            help="每页之间的延迟秒数（默认: 2.0）",
        )
        parser.add_argument(
            "--retries",
            type=int,
            default=3,
            help="失败重试次数（默认: 3）",
        )
        parser.add_argument(
            "--no-raw",
            action="store_true",
            help="不保存原始 API 响应数据",
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="开启调试模式",
        )

        return parser.parse_args()

    def get_username(args: argparse.Namespace, cli: CLI) -> str:
        """获取用户名（命令行参数或交互输入）"""
        if args.username:
            return args.username

        try:
            username = input(f"{Colors.CYAN}? 请输入要爬取的用户名: {Colors.RESET}").strip()
            if not username:
                cli.error("必须提供用户名")
                print(f"  {Colors.DIM}使用示例：python APoU.py -u 用户名{Colors.RESET}")
                sys.exit(1)
            return username
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    def print_statistics(crawler: UserPostsCrawler, cli: CLI, elapsed: float) -> None:
        """打印爬取统计信息"""
        stats = crawler.get_statistics()

        cli.print_section("爬取统计")

        # 基础统计
        cli.print_stats_box([
            ("总发言数", cli.format_number(stats["total_posts"]), "green"),
            ("总页数", str(stats["total_pages"]), "cyan"),
            ("耗时", cli.format_duration(elapsed), "yellow"),
        ])

        # 贴吧分布
        if stats["forum_distribution"]:
            print()
            print(f"  {Colors.GRAY}各贴吧发言分布:{Colors.RESET}")
            sorted_forums = sorted(
                stats["forum_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            # 显示前 10 个贴吧
            for forum, count in sorted_forums[:10]:
                bar_len = min(20, int(count / max(1, stats["total_posts"]) * 40))
                bar = "█" * bar_len
                print(f"    {Colors.CYAN}{forum:16}{Colors.RESET} "
                      f"{Colors.DIM}{bar}{Colors.RESET} {count}")

            if len(sorted_forums) > 10:
                print(f"    {Colors.DIM}... 还有 {len(sorted_forums) - 10} 个贴吧{Colors.RESET}")

    # 主逻辑
    cli = CLI("APoU - All Posts of User", VERSION)
    args = parse_args()
    cli.print_banner("百度贴吧用户发言爬虫")
    username = get_username(args, cli)

    config = CrawlerConfig(
        page_delay=args.delay,
        max_retries=args.retries,
        debug=args.debug,
    )

    cli.print_section("爬取配置")
    cli.print_config([
        ("目标用户", username),
        ("指定贴吧", args.forum or "(全部)"),
        ("页间延迟", f"{args.delay} 秒"),
        ("重试次数", str(args.retries)),
        ("保存原始数据", "否" if args.no_raw else "是"),
        ("调试模式", "是" if args.debug else "否"),
    ])

    cli.print_section("开始爬取")
    start_time = time.time()

    with UserPostsCrawler(config, cli=cli) as crawler:
        try:
            posts = crawler.crawl(
                username=username,
                forum=args.forum,
                save_raw=not args.no_raw,
                save_incremental=True,
            )

            elapsed = time.time() - start_time

            if posts:
                print_statistics(crawler, cli, elapsed)
                cli.print_footer("爬取成功完成！")
            else:
                cli.warning("未获取到任何发言")
                cli.print_footer()

        except KeyboardInterrupt:
            elapsed = time.time() - start_time
            print()
            cli.warning("用户中断，已保存当前进度")
            if crawler.total_count > 0:
                print_statistics(crawler, cli, elapsed)
            cli.print_footer()
            sys.exit(0)
        except Exception as e:
            cli.error(f"爬取失败: {e}")
            if args.debug:
                raise
            sys.exit(1)
