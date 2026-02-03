#!/usr/bin/env python3
"""
AutoCCF - 百度贴吧互联网踪迹存档系统

统一入口，提供交互式菜单界面。

用法：
    python main.py              # 交互模式
    python main.py --user 用户名 # 直接操作指定用户
"""
import sys
import os
from pathlib import Path
from typing import Optional

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

from AutoCCF.cli import CLI, Colors
from AutoCCF.config import config_manager, UnifiedConfig

VERSION = "2.0.0"


class MainMenu:
    """主菜单界面"""
    
    def __init__(self):
        self.cli = CLI("AutoCCF - 互联网踪迹存档系统", VERSION)
        self.config: Optional[UnifiedConfig] = None
    
    def run(self):
        """运行主程序"""
        self.cli.print_banner("百度贴吧数据存档工具")
        
        # 加载或创建配置
        self.config = config_manager.load_or_setup()
        
        # 确保数据目录存在
        self.config.ensure_database_dir()
        
        # 主循环
        while True:
            try:
                action = self.show_main_menu()
                if action == "quit":
                    break
            except KeyboardInterrupt:
                print()
                self.cli.info("再见！")
                break
    
    def show_main_menu(self) -> str:
        """显示主菜单"""
        self.cli.print_section("主菜单")
        
        # 显示当前状态
        users = config_manager.list_users()
        db_path = self.config.get_database_path()
        
        print(f"  {Colors.GRAY}数据目录:{Colors.RESET} {db_path}")
        print(f"  {Colors.GRAY}已存档用户:{Colors.RESET} {len(users)}")
        print()
        
        # 菜单选项
        options = [
            ("1", "获取用户发言列表", "APoU - 爬取指定用户的所有发言"),
            ("2", "获取帖子详情", "DoPJ - 爬取帖子的完整内容"),
            ("3", "查看用户列表", "浏览已存档的用户数据"),
            ("4", "配置设置", "修改配置和账户信息"),
            ("0", "退出", ""),
        ]
        
        for key, title, desc in options:
            if desc:
                print(f"  {Colors.CYAN}[{key}]{Colors.RESET} {title}")
                print(f"      {Colors.DIM}{desc}{Colors.RESET}")
            else:
                print(f"  {Colors.CYAN}[{key}]{Colors.RESET} {title}")
        
        print()
        
        try:
            choice = input(f"{Colors.CYAN}? 请选择操作 [1-4, 0]: {Colors.RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            return "quit"
        
        if choice == "1":
            self.run_apou()
        elif choice == "2":
            self.run_dopj()
        elif choice == "3":
            self.show_users()
        elif choice == "4":
            self.show_settings()
        elif choice == "0":
            return "quit"
        else:
            self.cli.warning("无效选择")
        
        return "continue"
    
    def run_apou(self):
        """运行 APoU 模块"""
        self.cli.print_section("APoU - 获取用户发言列表")
        
        try:
            username = input(f"{Colors.CYAN}? 请输入要爬取的用户名: {Colors.RESET}").strip()
            if not username:
                self.cli.warning("已取消")
                return
            
            # 创建用户目录
            user_dir = self.config.get_user_dir(username)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            # 检查是否已有数据，询问是否增量更新
            posts_file = user_dir / "posts.json"
            incremental = False
            
            if posts_file.exists():
                choice = input(
                    f"{Colors.YELLOW}? 检测到已有数据，是否只获取新发言？[Y/n]: {Colors.RESET}"
                ).strip().lower()
                incremental = choice != "n"
                if incremental:
                    self.cli.info("将使用增量模式，只获取新发言")
            
            # 导入并运行 APoU
            from APoU import UserPostsCrawler
            from APoU.config import CrawlerConfig
            
            apou_config = CrawlerConfig(
                page_delay=self.config.apou.page_delay,
                max_retries=self.config.apou.max_retries,
            )
            
            mode_text = "增量更新" if incremental else "完整获取"
            self.cli.print_config([
                ("目标用户", username),
                ("输出目录", str(user_dir)),
                ("页间延迟", f"{self.config.apou.page_delay} 秒"),
                ("模式", mode_text),
            ])
            
            print()
            
            import time
            start_time = time.time()
            
            with UserPostsCrawler(apou_config, cli=self.cli) as crawler:
                posts = crawler.crawl(
                    username=username,
                    save_raw=self.config.apou.save_raw,
                    save_incremental=True,
                    output_dir=str(user_dir),
                    incremental=incremental,
                )
                
                elapsed = time.time() - start_time
                
                if posts:
                    # crawler.crawl 已经保存到 output_dir/posts.json
                    output_file = user_dir / "posts.json"
                    self.cli.success(f"已保存 {len(posts)} 条发言到 {output_file}")
                    self.cli.info(f"耗时: {self.cli.format_duration(elapsed)}")
                else:
                    self.cli.warning("未获取到任何发言")
        
        except KeyboardInterrupt:
            print()
            self.cli.warning("已取消")
        except Exception as e:
            self.cli.error(f"爬取失败: {e}")
    
    def run_dopj(self):
        """运行 DoPJ 模块"""
        self.cli.print_section("DoPJ - 获取帖子详情")
        
        # 检查账户配置
        if not self.config.has_valid_accounts():
            self.cli.error("未配置有效的 BDUSS，请先在配置中添加账户")
            print(f"  {Colors.DIM}编辑 config.json 添加 BDUSS{Colors.RESET}")
            return
        
        # 查找可用的 APoU 输出
        apou_outputs = config_manager.find_apou_outputs()
        
        if not apou_outputs:
            self.cli.warning("未找到任何用户数据，请先运行 APoU 获取用户发言列表")
            return
        
        # 显示用户选择
        print()
        print(f"  {Colors.GRAY}可用的用户数据:{Colors.RESET}")
        print()
        
        for i, item in enumerate(apou_outputs, 1):
            status = ""
            if item["has_index"]:
                status = f"{Colors.GREEN}[已完成]{Colors.RESET}"
            else:
                status = f"{Colors.YELLOW}[待处理]{Colors.RESET}"
            
            print(f"  {Colors.CYAN}[{i}]{Colors.RESET} {item['username']} "
                  f"{Colors.DIM}({item['posts_count']} 条发言){Colors.RESET} {status}")
        
        print()
        
        try:
            choice = input(f"{Colors.CYAN}? 请选择用户 [1-{len(apou_outputs)}]: {Colors.RESET}").strip()
            
            if not choice:
                self.cli.warning("已取消")
                return
            
            idx = int(choice) - 1
            if idx < 0 or idx >= len(apou_outputs):
                self.cli.error("无效选择")
                return
            
            selected = apou_outputs[idx]
            
        except (ValueError, KeyboardInterrupt):
            print()
            self.cli.warning("已取消")
            return
        
        # 运行 DoPJ
        self._run_dopj_for_user(selected["username"], selected["path"])
    
    def _run_dopj_for_user(self, username: str, posts_file: str):
        """为指定用户运行 DoPJ"""
        from DoPJ.cli import DoPJRunner
        
        user_dir = self.config.get_user_dir(username)
        
        self.cli.print_config([
            ("目标用户", username),
            ("输入文件", posts_file),
            ("输出目录", str(user_dir)),
            ("并发线程", str(self.config.dopj.threads)),
        ])
        
        # 构建账户配置
        accounts_config = {
            "accounts": [
                {"name": acc.name, "bduss": acc.bduss}
                for acc in self.config.accounts
            ],
            "min_interval": self.config.dopj.min_interval,
            "max_fails": self.config.dopj.max_fails,
        }
        
        # 临时保存配置文件
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(accounts_config, f, ensure_ascii=False)
            temp_config = f.name
        
        try:
            runner = DoPJRunner(
                input_json=posts_file,
                config_file=temp_config,
                output_dir=str(user_dir),
                threads=self.config.dopj.threads,
                max_retries=self.config.dopj.max_retries,
                cli=self.cli,
            )
            
            # 默认启用增量模式（跳过已存档的帖子）
            runner.load_tasks(incremental=True)
            runner.run()
            
        except Exception as e:
            self.cli.error(f"爬取失败: {e}")
        finally:
            # 清理临时文件
            os.unlink(temp_config)
    
    def show_users(self):
        """显示用户列表"""
        self.cli.print_section("已存档用户")
        
        users = config_manager.list_users()
        
        if not users:
            print(f"  {Colors.GRAY}暂无数据{Colors.RESET}")
            return
        
        # 表格显示
        headers = ["用户名", "发言数", "帖子数", "状态"]
        rows = []
        
        for user in users:
            if user["has_index"]:
                status = "已完成"
            elif user["has_posts"]:
                status = "待详情"
            else:
                status = "空目录"
            
            rows.append([
                user["name"],
                str(user["posts_count"]),
                str(user["threads_count"]),
                status,
            ])
        
        self.cli.print_table(headers, rows, ["cyan", "white", "white", "green"])
        
        print()
        
        # 选择用户查看详情或操作
        try:
            choice = input(
                f"{Colors.CYAN}? 输入用户名查看详情，或按回车返回: {Colors.RESET}"
            ).strip()
            
            if choice:
                self._show_user_detail(choice)
                
        except (EOFError, KeyboardInterrupt):
            print()
    
    def _show_user_detail(self, username: str):
        """显示用户详情"""
        user_dir = self.config.get_user_dir(username)
        
        if not user_dir.exists():
            self.cli.error(f"用户 {username} 不存在")
            return
        
        self.cli.print_section(f"用户详情: {username}")
        
        # 显示文件列表
        print(f"  {Colors.GRAY}目录: {user_dir}{Colors.RESET}")
        print()
        
        for item in sorted(user_dir.iterdir()):
            if item.is_file():
                size = item.stat().st_size
                size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
                print(f"  {Colors.WHITE}{item.name}{Colors.RESET} {Colors.DIM}({size_str}){Colors.RESET}")
            elif item.is_dir():
                count = len(list(item.iterdir()))
                print(f"  {Colors.CYAN}{item.name}/{Colors.RESET} {Colors.DIM}({count} 项){Colors.RESET}")
    
    def show_settings(self):
        """显示设置"""
        self.cli.print_section("配置设置")
        
        config_path = self.config._config_path or "config.json"
        
        self.cli.print_config([
            ("配置文件", config_path),
            ("数据目录", self.config.database_dir),
            ("账户数量", str(len(self.config.accounts))),
        ])
        
        print()
        print(f"  {Colors.GRAY}APoU 设置:{Colors.RESET}")
        print(f"    页间延迟: {self.config.apou.page_delay} 秒")
        print(f"    重试次数: {self.config.apou.max_retries}")
        
        print()
        print(f"  {Colors.GRAY}DoPJ 设置:{Colors.RESET}")
        print(f"    并发线程: {self.config.dopj.threads}")
        print(f"    请求间隔: {self.config.dopj.min_interval} 秒")
        
        print()
        print(f"  {Colors.GRAY}账户列表:{Colors.RESET}")
        for acc in self.config.accounts:
            bduss_preview = acc.bduss[:20] + "..." if len(acc.bduss) > 20 else acc.bduss
            valid = len(acc.bduss) > 50 and not acc.bduss.startswith("你的")
            status = f"{Colors.GREEN}有效{Colors.RESET}" if valid else f"{Colors.RED}无效{Colors.RESET}"
            print(f"    {acc.name}: {bduss_preview} [{status}]")
        
        print()
        print(f"  {Colors.DIM}编辑 {config_path} 修改配置{Colors.RESET}")


def main():
    """主入口"""
    menu = MainMenu()
    menu.run()


if __name__ == "__main__":
    main()
