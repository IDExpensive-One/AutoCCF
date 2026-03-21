"""
AutoCCF 统一配置管理

管理共享配置文件，支持首次运行向导。
"""
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from AutoCCF.utils import is_valid_bduss


# 配置文件位置（按优先级）
CONFIG_SEARCH_PATHS = [
    "./config.json",
    "./autoccf.json",
    os.path.expanduser("~/.autoccf/config.json"),
]

DEFAULT_CONFIG_PATH = "./config.json"


@dataclass
class APoUConfig:
    """APoU 模块配置"""
    page_delay: float = 2.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        """验证配置参数"""
        if not 0.5 <= self.page_delay <= 60:
            raise ValueError(f"page_delay 必须在 0.5-60 之间，当前值: {self.page_delay}")
        if not 1 <= self.max_retries <= 10:
            raise ValueError(f"max_retries 必须在 1-10 之间，当前值: {self.max_retries}")


@dataclass
class DoPJConfig:
    """DoPJ 模块配置"""
    threads: int = 3
    max_retries: int = 3
    min_interval: float = 2.0
    max_fails: int = 5

    def __post_init__(self) -> None:
        """验证配置参数"""
        if not 1 <= self.threads <= 50:
            raise ValueError(f"threads 必须在 1-50 之间，当前值: {self.threads}")
        if not 1 <= self.max_retries <= 10:
            raise ValueError(f"max_retries 必须在 1-10 之间，当前值: {self.max_retries}")
        if not 0.5 <= self.min_interval <= 60:
            raise ValueError(f"min_interval 必须在 0.5-60 之间，当前值: {self.min_interval}")
        if not 1 <= self.max_fails <= 20:
            raise ValueError(f"max_fails 必须在 1-20 之间，当前值: {self.max_fails}")


@dataclass
class Account:
    """账户信息"""
    name: str
    bduss: str


@dataclass
class UnifiedConfig:
    """统一配置类"""
    database_dir: str = "./database"
    accounts: List[Account] = field(default_factory=list)
    apou: APoUConfig = field(default_factory=APoUConfig)
    dopj: DoPJConfig = field(default_factory=DoPJConfig)
    
    # 内部使用
    _config_path: str = ""

    @property
    def config_path(self) -> str:
        """获取当前配置文件路径"""
        return self._config_path or DEFAULT_CONFIG_PATH

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "database_dir": self.database_dir,
            "accounts": [
                {"name": acc.name, "bduss": acc.bduss}
                for acc in self.accounts
            ],
            "apou": {
                "page_delay": self.apou.page_delay,
                "max_retries": self.apou.max_retries,
            },
            "dopj": {
                "threads": self.dopj.threads,
                "max_retries": self.dopj.max_retries,
                "min_interval": self.dopj.min_interval,
                "max_fails": self.dopj.max_fails,
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], config_path: str = "") -> "UnifiedConfig":
        """从字典创建配置"""
        accounts = [
            Account(name=acc.get("name", f"账户{i+1}"), bduss=acc.get("bduss", ""))
            for i, acc in enumerate(data.get("accounts", []))
        ]
        
        apou_data = data.get("apou", {})
        apou = APoUConfig(
            page_delay=apou_data.get("page_delay", 2.0),
            max_retries=apou_data.get("max_retries", 3),
        )
        
        dopj_data = data.get("dopj", {})
        dopj = DoPJConfig(
            threads=dopj_data.get("threads", 3),
            max_retries=dopj_data.get("max_retries", 3),
            min_interval=dopj_data.get("min_interval", 2.0),
            max_fails=dopj_data.get("max_fails", 5),
        )
        
        config = cls(
            database_dir=data.get("database_dir", "./database"),
            accounts=accounts,
            apou=apou,
            dopj=dopj,
        )
        config._config_path = config_path
        return config
    
    def save(self, path: Optional[str] = None) -> str:
        """保存配置到文件"""
        save_path = path or self._config_path or DEFAULT_CONFIG_PATH
        
        # 确保目录存在
        parent = os.path.dirname(save_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        self._config_path = save_path
        return save_path
    
    def get_database_path(self) -> Path:
        """获取数据库目录的绝对路径"""
        return Path(self.database_dir).resolve()
    
    def get_user_dir(self, username: str) -> Path:
        """获取用户数据目录"""
        return self.get_database_path() / username
    
    def ensure_database_dir(self) -> Path:
        """确保数据库目录存在"""
        db_path = self.get_database_path()
        db_path.mkdir(parents=True, exist_ok=True)
        return db_path
    
    def has_valid_accounts(self) -> bool:
        """检查是否有有效的账户配置"""
        return any(is_valid_bduss(acc.bduss) for acc in self.accounts)


class ConfigManager:
    """配置管理器"""
    
    def __init__(self):
        self.config: Optional[UnifiedConfig] = None
        self._cli = None  # 延迟导入
    
    def _get_cli(self):
        """获取 CLI 实例"""
        if self._cli is None:
            from AutoCCF.cli import CLI
            self._cli = CLI("AutoCCF", "2.0.0")
        return self._cli
    
    def find_config(self) -> Optional[str]:
        """查找配置文件"""
        for path in CONFIG_SEARCH_PATHS:
            if os.path.exists(path):
                return path
        return None
    
    def load(self, path: Optional[str] = None) -> UnifiedConfig:
        """加载配置"""
        config_path = path or self.find_config()
        
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config = UnifiedConfig.from_dict(data, config_path)
        else:
            # 创建默认配置
            self.config = UnifiedConfig()
        
        return self.config
    
    def setup_wizard(self) -> UnifiedConfig:
        """首次运行配置向导"""
        from AutoCCF.cli import CLI, Colors
        
        cli = self._get_cli()
        
        print()
        cli.print_section("首次运行配置")
        print(f"  {Colors.GRAY}欢迎使用 AutoCCF！让我们进行一些初始设置。{Colors.RESET}")
        print()
        
        # 1. 询问数据库目录
        default_db = "./database"
        try:
            db_input = input(
                f"{Colors.CYAN}? 请输入数据存储目录 [{default_db}]: {Colors.RESET}"
            ).strip()
            database_dir = db_input if db_input else default_db
        except (EOFError, KeyboardInterrupt):
            print()
            database_dir = default_db
        
        # 确保目录存在
        db_path = Path(database_dir).resolve()
        db_path.mkdir(parents=True, exist_ok=True)
        print(f"  {Colors.GREEN}+ 数据目录: {db_path}{Colors.RESET}")
        
        # 2. 询问 BDUSS
        print()
        print(f"  {Colors.GRAY}APoU 和 DoPJ 都需要贴吧账户的 BDUSS 来获取数据。{Colors.RESET}")
        print(f"  {Colors.GRAY}获取方法: 浏览器 F12 → Application → Cookies → BDUSS{Colors.RESET}")
        print()
        
        accounts = []
        try:
            while True:
                acc_num = len(accounts) + 1
                bduss = input(
                    f"{Colors.CYAN}? 请输入 BDUSS #{acc_num} (留空完成): {Colors.RESET}"
                ).strip()
                
                if not bduss:
                    break
                
                name = input(
                    f"{Colors.CYAN}? 账户名称 [账户{acc_num}]: {Colors.RESET}"
                ).strip() or f"账户{acc_num}"
                
                accounts.append(Account(name=name, bduss=bduss))
                print(f"  {Colors.GREEN}+ 已添加: {name}{Colors.RESET}")
        except (EOFError, KeyboardInterrupt):
            print()
        
        if not accounts:
            # 添加占位账户
            accounts.append(Account(name="账户1", bduss="请填入你的BDUSS"))
            print(f"  {Colors.YELLOW}! 未配置账户，稍后请编辑配置文件添加 BDUSS{Colors.RESET}")
        
        # 创建配置
        self.config = UnifiedConfig(
            database_dir=str(database_dir),
            accounts=accounts,
        )
        
        # 保存配置
        config_path = self.config.save(DEFAULT_CONFIG_PATH)
        print()
        print(f"  {Colors.GREEN}+ 配置已保存: {config_path}{Colors.RESET}")
        
        return self.config
    
    def load_or_setup(self) -> UnifiedConfig:
        """加载配置，如果不存在则运行向导"""
        config_path = self.find_config()
        
        if config_path:
            return self.load(config_path)
        else:
            return self.setup_wizard()
    
    def list_users(self) -> List[Dict[str, Any]]:
        """列出所有用户及其状态（兼容新旧路径）"""
        if not self.config:
            return []

        users = []
        db_path = self.config.get_database_path()

        if not db_path.exists():
            return []

        for item in sorted(db_path.iterdir()):
            if not item.is_dir():
                continue

            # 检测新旧路径
            has_posts_new = (item / "apou" / "posts.json").exists()
            has_posts_legacy = (item / "posts.json").exists()
            has_index_new = (item / "dopj" / "index.json").exists()
            has_index_legacy = (item / "index.json").exists()
            has_threads_new = (item / "dopj").exists()
            has_threads_legacy = (item / "threads").exists()

            user_info = {
                "name": item.name,
                "path": str(item),
                "has_posts": has_posts_new or has_posts_legacy,
                "has_index": has_index_new or has_index_legacy,
                "has_threads": has_threads_new or has_threads_legacy,
                "posts_count": 0,
                "threads_count": 0,
            }

            # 读取帖子数量（优先新路径）
            posts_file = (item / "apou" / "posts.json") if has_posts_new else (item / "posts.json")
            if posts_file.exists():
                try:
                    with open(posts_file, "r", encoding="utf-8") as f:
                        posts = json.load(f)
                    user_info["posts_count"] = len(posts) if isinstance(posts, list) else 0
                except Exception:
                    pass

            # 读取索引信息（优先新路径）
            index_file = (item / "dopj" / "index.json") if has_index_new else (item / "index.json")
            if index_file.exists():
                try:
                    with open(index_file, "r", encoding="utf-8") as f:
                        index = json.load(f)
                    user_info["threads_count"] = index.get("success_count", 0)
                except Exception:
                    pass

            # 统计帖子详情目录
            dopj_dir = item / "dopj"
            if dopj_dir.exists():
                user_info["threads_count"] = sum(
                    1 for d in dopj_dir.iterdir()
                    if d.is_dir() and d.name.isdigit()
                )
            elif has_threads_legacy:
                threads_dir = item / "threads"
                user_info["threads_count"] = len(list(threads_dir.iterdir()))

            users.append(user_info)

        return users
    
    def find_apou_outputs(self) -> List[Dict[str, Any]]:
        """查找所有 APoU 输出的 JSON 文件（兼容新旧路径）"""
        if not self.config:
            return []

        results = []
        db_path = self.config.get_database_path()

        if not db_path.exists():
            return []

        for user_dir in db_path.iterdir():
            if not user_dir.is_dir():
                continue

            # 优先新路径，回退旧路径
            posts_file = user_dir / "apou" / "posts.json"
            if not posts_file.exists():
                posts_file = user_dir / "posts.json"
            if not posts_file.exists():
                continue

            try:
                with open(posts_file, "r", encoding="utf-8") as f:
                    posts = json.load(f)

                has_index = (
                    (user_dir / "dopj" / "index.json").exists()
                    or (user_dir / "index.json").exists()
                )

                results.append({
                    "username": user_dir.name,
                    "path": str(posts_file),
                    "posts_count": len(posts) if isinstance(posts, list) else 0,
                    "has_index": has_index,
                })
            except Exception:
                pass

        return results


# 全局配置管理器实例
config_manager = ConfigManager()


def get_config() -> UnifiedConfig:
    """获取当前配置"""
    if config_manager.config is None:
        config_manager.load_or_setup()
    assert config_manager.config is not None, "配置加载失败"
    return config_manager.config


def ensure_config() -> UnifiedConfig:
    """确保配置已加载"""
    return get_config()
