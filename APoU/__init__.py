"""
APoU - All Posts of User
百度贴吧用户发言列表爬虫模块

使用 aiotieba 通过百度贴吧官方 protobuf API 获取用户数据。
"""

from APoU.crawler import UserPostsCrawler
from APoU.exceptions import APoUError, AuthError, NetworkError, EngineError, FallbackError

__version__ = "3.0.0"
__all__ = [
    "UserPostsCrawler",
    "APoUError",
    "AuthError",
    "NetworkError",
    "EngineError",
    "FallbackError",
]


def main():
    """APoU 命令行入口点（从 APoU.py 调用）"""
    import argparse
    import asyncio
    import sys
    import time

    from APoU import UserPostsCrawler
    from APoU.config import CrawlerConfig
    from AutoCCF.cli import CLI, Colors, safe_str
    from AutoCCF.config import config_manager

    VERSION = "3.0.0"

    def parse_args() -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="百度贴吧用户发言爬虫 - 获取指定用户的所有发言列表",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
    python APoU.py -u 张三
    python APoU.py --username 张三 --forum 某贴吧
    python APoU.py -u 张三 --bduss YOUR_BDUSS
            """,
        )

        parser.add_argument("-u", "--username", type=str, help="要爬取的用户名")
        parser.add_argument("-f", "--forum", type=str, default="", help="指定贴吧名（留空表示所有贴吧）")
        parser.add_argument("--bduss", type=str, default="", help="百度账号的 BDUSS cookie")
        parser.add_argument("--delay", type=float, default=2.0, help="每页之间的延迟秒数（默认: 2.0）")
        parser.add_argument("--retries", type=int, default=3, help="失败重试次数（默认: 3）")
        parser.add_argument("--debug", action="store_true", help="开启调试模式")

        return parser.parse_args()

    def get_username(args: argparse.Namespace, cli: CLI) -> str:
        if args.username:
            return args.username
        try:
            username = input(f"{Colors.CYAN}? 请输入要爬取的用户名: {Colors.RESET}").strip()
            if not username:
                cli.error("必须提供用户名")
                sys.exit(1)
            return username
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)

    def get_bduss(args: argparse.Namespace, cli: CLI) -> str:
        """获取 BDUSS（命令行参数 > 配置文件）"""
        if args.bduss:
            return args.bduss

        # 尝试从配置文件读取
        try:
            config = config_manager.load_or_setup()
            for acc in config.accounts:
                from AutoCCF.utils import is_valid_bduss
                if is_valid_bduss(acc.bduss):
                    cli.info(f"使用配置文件中的账户: {acc.name}")
                    return acc.bduss
        except Exception:
            pass

        cli.error("未找到有效的 BDUSS")
        print(f"  {Colors.DIM}请通过 --bduss 参数或配置文件提供 BDUSS{Colors.RESET}")
        sys.exit(1)

    def print_statistics(crawler: UserPostsCrawler, cli: CLI, elapsed: float) -> None:
        stats = crawler.get_statistics()

        cli.print_section("爬取统计")

        cli.print_stats_box([
            ("总发言数", cli.format_number(stats["total_posts"]), "green"),
            ("主题帖", str(stats["thread_count"]), "cyan"),
            ("回复", str(stats["reply_count"]), "cyan"),
            ("耗时", cli.format_duration(elapsed), "yellow"),
        ])

        if stats["forum_distribution"]:
            print()
            print(f"  {Colors.GRAY}各贴吧发言分布:{Colors.RESET}")
            sorted_forums = sorted(
                stats["forum_distribution"].items(),
                key=lambda x: x[1],
                reverse=True,
            )
            for forum, count in sorted_forums[:10]:
                bar_len = min(20, int(count / max(1, stats["total_posts"]) * 40))
                bar = safe_str("█" * bar_len) if bar_len > 0 else ""
                forum_display = safe_str(forum)
                print(f"    {Colors.CYAN}{forum_display:16}{Colors.RESET} "
                      f"{Colors.DIM}{bar}{Colors.RESET} {count}")

            if len(sorted_forums) > 10:
                print(f"    {Colors.DIM}... 还有 {len(sorted_forums) - 10} 个贴吧{Colors.RESET}")

    # 主逻辑
    cli = CLI("APoU - All Posts of User", VERSION)
    args = parse_args()
    cli.print_banner("百度贴吧用户发言爬虫")
    username = get_username(args, cli)
    bduss = get_bduss(args, cli)

    config = CrawlerConfig(
        bduss=bduss,
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
        ("API", "aiotieba (protobuf)"),
    ])

    cli.print_section("开始爬取")
    start_time = time.time()

    crawler = UserPostsCrawler(config, cli=cli)
    try:
        posts = asyncio.run(crawler.crawl(
            username=username,
            forum=args.forum,
            save_incremental=True,
        ))

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
