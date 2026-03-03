"""
爬虫适配器
将多任务系统的 Task 转换为 MediaCrawler 可执行的爬虫任务
支持两种执行模式：
1. 子进程模式（推荐）：隔离性好，适合生产环境
2. 进程内模式：共享浏览器，适合开发调试
"""
import asyncio
import os
import sys
import json
import tempfile
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime
from pathlib import Path

from api.schemas.task import Task, TaskConfig
from api.services.task_executor import TaskContext

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class CrawlerAdapter:
    """爬虫适配器 - 将多任务 Task 转换为 MediaCrawler 执行"""
    
    # 平台映射
    PLATFORM_MAP = {
        "xhs": "xhs",
        "dy": "dy", 
        "bili": "bili",
        "wb": "wb",
        "wechat": "wechat",
        "ks": "ks",
        "tieba": "tieba",
        "zhihu": "zhihu",
    }
    
    # 爬虫类型映射
    CRAWLER_TYPE_MAP = {
        "search": "search",
        "detail": "detail",
        "creator": "creator",
        "creator_vip": "creator_vip",
        "album": "album",
    }
    
    def __init__(self, task: Task, ctx: TaskContext):
        self.task = task
        self.ctx = ctx
        self.process: Optional[asyncio.subprocess.Process] = None
    
    async def run(self) -> Dict[str, Any]:
        """
        执行爬虫任务
        
        Returns:
            执行结果 {
                "success": bool,
                "items_crawled": int,
                "error": Optional[str],
                "output_path": Optional[str]
            }
        """
        await self.ctx.info(f"正在准备爬虫任务: {self.task.config.platform}")
        
        # 生成临时配置文件
        config_path = await self._generate_config_file()
        
        try:
            # 使用子进程执行爬虫
            result = await self._run_subprocess(config_path)
            return result
        finally:
            # 清理临时配置文件
            if config_path and os.path.exists(config_path):
                try:
                    os.unlink(config_path)
                except Exception:
                    pass
    
    async def _generate_config_file(self) -> str:
        """生成临时配置文件"""
        config = self.task.config
        
        # 构建配置内容
        config_content = self._build_config_content(config)
        
        # 写入临时文件
        fd, config_path = tempfile.mkstemp(suffix=".py", prefix="mc_task_config_")
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(config_content)
        except Exception:
            os.close(fd)
            raise
        
        await self.ctx.debug(f"生成配置文件: {config_path}")
        return config_path
    
    def _build_config_content(self, config: TaskConfig) -> str:
        """构建 Python 配置文件内容"""
        platform = self.PLATFORM_MAP.get(config.platform, config.platform)
        crawler_type = self.CRAWLER_TYPE_MAP.get(config.crawler_type, "search")
        
        # 如果有 cookies，使用 cookie 登录；否则使用保存的登录状态
        login_type = "cookie" if config.cookies else (config.login_type or "cookie")
        
        # 基础配置
        lines = [
            "# -*- coding: utf-8 -*-",
            "# Auto-generated config for multi-task",
            f"# Task ID: {self.task.task_id}",
            f"# Generated at: {datetime.now().isoformat()}",
            "",
            f'PLATFORM = "{platform}"',
            f'CRAWLER_TYPE = "{crawler_type}"',
            f'LOGIN_TYPE = "{login_type}"',
            "",
        ]
        
        # 关键词配置
        keywords = config.keywords or []
        if keywords:
            lines.append(f'KEYWORDS = "{",".join(keywords)}"')
        else:
            lines.append('KEYWORDS = ""')
        
        # 爬取数量配置
        lines.extend([
            "",
            f"CRAWLER_MAX_NOTES_COUNT = {config.max_notes}",
            f"CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = {config.max_comments_per_note}",
            f"MAX_CONCURRENCY_NUM = {min(config.concurrency, 5)}",
            f"CRAWLER_MAX_SLEEP_SEC = {config.crawl_interval}",
            "",
        ])
        
        # 功能开关
        lines.extend([
            f"ENABLE_GET_COMMENTS = {config.enable_comments}",
            f"ENABLE_GET_MEIDAS = {config.enable_media}",
            "ENABLE_GET_WORDCLOUD = False",
            "",
        ])
        
        # 数据存储配置
        save_option = config.save_option or "json"
        lines.extend([
            f'SAVE_DATA_OPTION = "{save_option}"',
            "",
        ])

        # 反爬增强配置
        if config.enable_anti_detect:
            anti_detect_cfg = config.anti_detect_config or {}
            lines.extend([
                "# Anti-detect settings",
                f"ENABLE_ANTI_DETECT = True",
                f"ENABLE_FINGERPRINT = {anti_detect_cfg.get('enable_fingerprint', True)}",
                f"ENABLE_RATE_LIMIT = {anti_detect_cfg.get('enable_rate_limit', True)}",
                f"ENABLE_HUMAN_BEHAVIOR = {anti_detect_cfg.get('enable_human_behavior', True)}",
                f"ENABLE_ACCOUNT_HEALTH = {anti_detect_cfg.get('enable_account_health', True)}",
                f"ENABLE_BINDING = {anti_detect_cfg.get('enable_binding', True)}",
                f"RATE_LIMIT_MIN_INTERVAL = {anti_detect_cfg.get('rate_limit_min_interval', 3.0)}",
                f"RATE_LIMIT_MAX_INTERVAL = {anti_detect_cfg.get('rate_limit_max_interval', 10.0)}",
                f"RATE_LIMIT_HOURLY_LIMIT = {anti_detect_cfg.get('rate_limit_hourly_limit', 150)}",
                f"RATE_LIMIT_DAILY_LIMIT = {anti_detect_cfg.get('rate_limit_daily_limit', 1500)}",
                "",
            ])
        else:
            lines.extend([
                "# Anti-detect settings",
                "ENABLE_ANTI_DETECT = False",
                "",
            ])

        # Cookie 配置
        if config.cookies:
            # 转义引号
            cookies_escaped = config.cookies.replace('"', '\\"')
            lines.append(f'COOKIES = "{cookies_escaped}"')
        else:
            lines.append('COOKIES = ""')
        
        # 从 extra 字段提取平台特有参数
        extra = config.extra or {}

        # 平台特定配置
        if platform == "xhs":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            sort_type = extra.get("sort_type", "general")
            lines.extend([
                "",
                f'SORT_TYPE = "{sort_type}"',
                f"XHS_CREATOR_ID_LIST = {json.dumps(creator_ids)}",
                f"XHS_SPECIFIED_NOTE_URL_LIST = {json.dumps(note_urls)}",
            ])
        elif platform == "dy":
            creator_ids = config.creator_ids or []
            video_urls = config.note_urls or []
            publish_time = extra.get("publish_time_type", 0)
            lines.extend([
                "",
                f"PUBLISH_TIME_TYPE = {publish_time}",
                f"DY_CREATOR_ID_LIST = {json.dumps(creator_ids)}",
                f"DY_SPECIFIED_ID_LIST = {json.dumps(video_urls)}",
            ])
        elif platform == "bili":
            creator_ids = config.creator_ids or []
            video_urls = config.note_urls or []
            bili_qn = extra.get("bili_qn", 80)
            bili_search_mode = extra.get("bili_search_mode", "normal")
            lines.extend([
                "",
                f"BILI_QN = {bili_qn}",
                f'BILI_SEARCH_MODE = "{bili_search_mode}"',
                f"BILI_CREATOR_ID_LIST = {json.dumps(creator_ids)}",
                f"BILI_SPECIFIED_ID_LIST = {json.dumps(video_urls)}",
            ])
        elif platform == "wb":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            weibo_search_type = extra.get("weibo_search_type", "default")
            enable_full_text = extra.get("enable_full_text", True)
            vip_creator_ids = extra.get("vip_creator_ids", [])
            lines.extend([
                "",
                f'WEIBO_SEARCH_TYPE = "{weibo_search_type}"',
                f"ENABLE_WEIBO_FULL_TEXT = {enable_full_text}",
                f"WEIBO_CREATOR_ID_LIST = {json.dumps(creator_ids)}",
                f"WEIBO_SPECIFIED_ID_LIST = {json.dumps(note_urls)}",
                f"WEIBO_VIP_CREATOR_ID_LIST = {json.dumps(vip_creator_ids)}",
            ])
        elif platform == "wechat":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            album_ids_raw = extra.get("wechat_album_ids", "")
            album_ids = []
            if isinstance(album_ids_raw, str) and album_ids_raw.strip():
                for line in album_ids_raw.strip().split("\n"):
                    line = line.strip()
                    if ":" in line:
                        parts = line.split(":", 1)
                        album_ids.append(f"{parts[0]}:{parts[1]}")
            enable_content = extra.get("wechat_enable_content", False)
            enable_reading = extra.get("wechat_enable_reading_stats", False)
            lines.extend([
                "",
                f"WECHAT_ACCOUNT_IDS = {json.dumps(creator_ids)}",
                f"WECHAT_ARTICLE_URLS = {json.dumps(note_urls)}",
                f"WECHAT_ALBUM_IDS = {json.dumps(album_ids)}",
                f"ENABLE_GET_ARTICLE_CONTENT = {enable_content}",
                f"ENABLE_GET_READING_STATS = {enable_reading}",
            ])
        elif platform == "tieba":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            tieba_names_raw = extra.get("tieba_name_list", "")
            tieba_names = []
            if isinstance(tieba_names_raw, str) and tieba_names_raw.strip():
                tieba_names = [n.strip() for n in tieba_names_raw.split("\n") if n.strip()]
            lines.extend([
                "",
                f"TIEBA_NAME_LIST = {json.dumps(tieba_names)}",
                f"TIEBA_CREATOR_URL_LIST = {json.dumps(creator_ids)}",
                f"TIEBA_SPECIFIED_ID_LIST = {json.dumps(note_urls)}",
            ])
        elif platform == "zhihu":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            lines.extend([
                "",
                f"ZHIHU_CREATOR_URL_LIST = {json.dumps(creator_ids)}",
                f"ZHIHU_SPECIFIED_ID_LIST = {json.dumps(note_urls)}",
            ])
        elif platform == "ks":
            creator_ids = config.creator_ids or []
            note_urls = config.note_urls or []
            lines.extend([
                "",
                f"KS_CREATOR_ID_LIST = {json.dumps(creator_ids)}",
                f"KS_SPECIFIED_ID_LIST = {json.dumps(note_urls)}",
            ])
        
        # 其他默认配置
        lines.extend([
            "",
            "# Browser settings",
            "HEADLESS = True",  # 无头模式，适合服务器运行
            "SAVE_LOGIN_STATE = True",  # 保存登录状态
            'USER_DATA_DIR = "browser_data/%s"',  # 浏览器数据目录
            "",
            "# Proxy settings",
            "ENABLE_IP_PROXY = False",
            "IP_PROXY_POOL_COUNT = 2",
            "",
            "# Resume crawl settings",
            "ENABLE_RESUME_CRAWL = False",
            "",
            "# Multi-account settings",
            "ENABLE_MULTI_ACCOUNT = False",
            "",
            "# Incremental crawl settings",
            "ENABLE_INCREMENTAL_CRAWL = False",
            "",
            "# CDP settings - 使用标准模式以复用登录状态",
            "ENABLE_CDP_MODE = False",
            "CDP_HEADLESS = True",
            "",
            "START_PAGE = 1",
        ])
        
        return "\n".join(lines)
    
    async def _run_subprocess(self, config_path: str) -> Dict[str, Any]:
        """使用子进程执行爬虫"""
        await self.ctx.info("启动爬虫子进程...")
        
        # 构建命令
        # 使用 PYTHONPATH 和自定义配置运行
        env = os.environ.copy()
        env["PYTHONPATH"] = str(PROJECT_ROOT)
        env["MC_TASK_CONFIG"] = config_path
        env["MC_TASK_ID"] = self.task.task_id
        
        # 构建执行脚本
        script = f'''
import sys
import os
sys.path.insert(0, "{PROJECT_ROOT}")

# 加载任务配置覆盖默认配置
task_config_path = os.environ.get("MC_TASK_CONFIG")
if task_config_path and os.path.exists(task_config_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("task_config", task_config_path)
    task_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(task_config)
    
    # 覆盖 config 模块的属性
    import config
    for attr in dir(task_config):
        if not attr.startswith("_"):
            setattr(config, attr, getattr(task_config, attr))

# 运行爬虫
import asyncio
from main import main, async_cleanup

async def run():
    try:
        await main()
    finally:
        await async_cleanup()

asyncio.run(run())
'''
        
        # 创建子进程
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, "-c", script,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        
        items_crawled = 0
        error_message = None
        last_output_time = asyncio.get_event_loop().time()
        no_output_timeout = 300  # 5 分钟无输出视为卡住
        
        # 读取输出并更新进度
        try:
            while True:
                try:
                    line_bytes = await asyncio.wait_for(
                        self.process.stdout.readline(),
                        timeout=30.0
                    )
                except asyncio.TimeoutError:
                    self.ctx.check_cancelled()
                    elapsed = asyncio.get_event_loop().time() - last_output_time
                    if elapsed > no_output_timeout:
                        await self.ctx.error(f"爬虫进程超过 {no_output_timeout} 秒无输出，可能卡在登录环节，正在终止")
                        await self._terminate_process()
                        return {
                            "success": False,
                            "items_crawled": items_crawled,
                            "error": "爬虫进程无响应（可能需要配置有效的 Cookie 或登录状态）",
                        }
                    continue

                if not line_bytes:
                    break

                try:
                    line = line_bytes.decode("utf-8", errors="replace").rstrip()
                except Exception:
                    continue

                last_output_time = asyncio.get_event_loop().time()
                
                # 解析日志行
                parsed = self._parse_log_line(line)
                
                # 记录日志
                if parsed["level"] == "ERROR":
                    await self.ctx.error(parsed["message"])
                    if not error_message:
                        error_message = parsed["message"]
                elif parsed["level"] == "WARNING":
                    await self.ctx.warning(parsed["message"])
                else:
                    await self.ctx.info(parsed["message"])
                
                # 提取进度信息
                progress_info = self._extract_progress(line)
                if progress_info:
                    items_crawled = progress_info.get("items", items_crawled)
                    await self.ctx.update_progress(
                        current=items_crawled,
                        total=self.task.config.max_notes,
                        items_crawled=items_crawled
                    )
        
        except asyncio.CancelledError:
            await self.ctx.warning("任务被取消，正在终止爬虫进程...")
            await self._terminate_process()
            raise
        
        # 等待进程结束
        try:
            return_code = await asyncio.wait_for(self.process.wait(), timeout=30.0)
        except asyncio.TimeoutError:
            await self.ctx.error("等待进程退出超时，强制终止")
            await self._terminate_process()
            return_code = -1
        
        if return_code == 0:
            await self.ctx.info("爬虫任务执行完成")
            
            # 兜底：日志未匹配到进度时，从输出文件统计数量
            if items_crawled == 0:
                items_crawled = self._count_output_files()
            
            if items_crawled > 0:
                await self.ctx.update_progress(
                    current=items_crawled,
                    total=max(items_crawled, self.task.config.max_notes),
                    items_crawled=items_crawled
                )
            
            return {
                "success": True,
                "items_crawled": items_crawled,
                "error": None,
            }
        else:
            error_message = error_message or f"爬虫进程异常退出，返回码: {return_code}"
            await self.ctx.error(error_message)
            return {
                "success": False,
                "items_crawled": items_crawled,
                "error": error_message,
            }
    
    def _parse_log_line(self, line: str) -> Dict[str, str]:
        """解析日志行"""
        # 尝试解析标准日志格式
        # 格式: [时间] [级别] 消息
        line = line.strip()
        
        level = "INFO"
        message = line
        
        if "[ERROR]" in line or "Error" in line:
            level = "ERROR"
        elif "[WARNING]" in line or "Warning" in line:
            level = "WARNING"
        elif "[DEBUG]" in line:
            level = "DEBUG"
        
        return {"level": level, "message": message}
    
    def _extract_progress(self, line: str) -> Optional[Dict[str, int]]:
        """从日志行提取进度信息"""
        import re
        
        # 模式1: "Crawled item X/Y" 或 "已爬取 X/Y"
        match = re.search(r"(?:Crawled|爬取|处理)\s*(?:item)?\s*(\d+)\s*/\s*(\d+)", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1)), "total": int(match.group(2))}
        
        # 模式2: "X notes crawled" 或 "已爬取 X 条"
        match = re.search(r"(\d+)\s*(?:notes?|条|items?)\s*(?:crawled|爬取|完成)", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1))}
        
        # 模式3: Progress saved: X notes
        match = re.search(r"Progress.*?(\d+)\s*notes", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1))}
        
        # 模式4: 微博 "total items: X"（Finished processing VIP creator xxx, total items: 100）
        match = re.search(r"total items:\s*(\d+)", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1))}
        
        # 模式5: 微博 "Total VIP content count: X"
        match = re.search(r"Total VIP content count:\s*(\d+)", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1))}
        
        # 模式6: 微博滚动进度 "collected X/Y items" 或 "collected X/? items"
        match = re.search(r"collected\s+(\d+)/(\d+)\s+items", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1)), "total": int(match.group(2))}
        
        # 模式7: 通用 "total: X" 或 "total_count: X"
        match = re.search(r"\btotal(?:_count)?\s*[:=]\s*(\d+)", line, re.IGNORECASE)
        if match:
            return {"items": int(match.group(1))}
        
        return None
    
    def _count_output_files(self) -> int:
        """
        兜底方案：统计本次任务输出的数据文件数量
        当日志中无法匹配到进度时使用
        """
        platform = self.task.config.platform
        crawler_type = self.task.config.crawler_type
        
        # 各平台输出目录映射
        platform_dirs = {
            "wb": "weibo",
            "xhs": "xhs",
            "dy": "douyin",
            "ks": "kuaishou",
            "bili": "bilibili",
            "tieba": "tieba",
            "zhihu": "zhihu",
        }
        platform_name = platform_dirs.get(platform, platform)
        
        try:
            # vip 类型：统计 vip_contents 目录下的文件
            if "vip" in crawler_type:
                vip_dir = PROJECT_ROOT / "data" / platform_name / "vip_contents"
                if vip_dir.exists():
                    # 统计 JSON/CSV 文件中的记录数
                    return self._count_records_in_dir(vip_dir)
            
            # creator 类型：统计 creator_content 目录
            if "creator" in crawler_type:
                creator_dir = PROJECT_ROOT / "data" / platform_name / "creator_content"
                if creator_dir.exists():
                    return self._count_records_in_dir(creator_dir)
            
            # search 类型：统计 contents 目录
            data_dir = PROJECT_ROOT / "data" / platform_name
            if data_dir.exists():
                return self._count_records_in_dir(data_dir)
        except Exception as e:
            logger.debug(f"统计输出文件失败: {e}")
        
        return 0

    def _count_records_in_dir(self, directory: Path) -> int:
        """统计目录下 JSON 文件中的记录总数"""
        total = 0
        try:
            for json_file in directory.glob("*.json"):
                try:
                    content = json_file.read_text(encoding="utf-8")
                    data = json.loads(content)
                    if isinstance(data, list):
                        total += len(data)
                    elif isinstance(data, dict):
                        total += 1
                except Exception:
                    continue
        except Exception:
            pass
        return total

    async def _terminate_process(self):
        """终止子进程"""
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                try:
                    await asyncio.wait_for(self.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.process.kill()
                    await self.process.wait()
            except Exception as e:
                logger.error(f"终止进程失败: {e}")


async def run_crawler_task(task: Task, ctx: TaskContext) -> None:
    """
    执行爬虫任务的入口函数
    
    Args:
        task: 任务对象
        ctx: 任务上下文
    """
    adapter = CrawlerAdapter(task, ctx)
    
    try:
        result = await adapter.run()
        
        if result["success"]:
            await ctx.info(f"任务完成，共爬取 {result['items_crawled']} 条数据")
        else:
            raise Exception(result["error"] or "爬虫执行失败")
    
    except asyncio.CancelledError:
        await ctx.warning("任务已取消")
        raise
    except Exception as e:
        await ctx.error(f"任务执行失败: {str(e)}")
        raise

