# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/cmd_arg/arg.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


from __future__ import annotations


import sys
from enum import Enum
from types import SimpleNamespace
from typing import Iterable, Optional, Sequence, Type, TypeVar

import typer
from typing_extensions import Annotated

import config
from tools.utils import str2bool


EnumT = TypeVar("EnumT", bound=Enum)


class PlatformEnum(str, Enum):
    """Supported media platform enumeration"""

    XHS = "xhs"
    DOUYIN = "dy"
    KUAISHOU = "ks"
    BILIBILI = "bili"
    WEIBO = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"
    WECHAT = "wechat"


class LoginTypeEnum(str, Enum):
    """Login type enumeration"""

    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"


class CrawlerTypeEnum(str, Enum):
    """Crawler type enumeration"""

    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"
    CREATOR_VIP = "creator_vip"  # VIP exclusive content from creators (Weibo only)
    ALBUM = "album"  # WeChat album mode


class SaveDataOptionEnum(str, Enum):
    """Data save option enumeration"""

    CSV = "csv"
    DB = "db"
    JSON = "json"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    EXCEL = "excel"
    POSTGRES = "postgres"


class InitDbOptionEnum(str, Enum):
    """Database initialization option"""

    SQLITE = "sqlite"
    MYSQL = "mysql"
    POSTGRES = "postgres"


def _to_bool(value: bool | str) -> bool:
    if isinstance(value, bool):
        return value
    return str2bool(value)


def _coerce_enum(
    enum_cls: Type[EnumT],
    value: EnumT | str,
    default: EnumT,
) -> EnumT:
    """Safely convert a raw config value to an enum member."""

    if isinstance(value, enum_cls):
        return value

    try:
        return enum_cls(value)
    except ValueError:
        typer.secho(
            f"⚠️ Config value '{value}' is not within the supported range of {enum_cls.__name__}, falling back to default value '{default.value}'.",
            fg=typer.colors.YELLOW,
        )
        return default


def _normalize_argv(argv: Optional[Sequence[str]]) -> Iterable[str]:
    if argv is None:
        return list(sys.argv[1:])
    return list(argv)


def _inject_init_db_default(args: Sequence[str]) -> list[str]:
    """Ensure bare --init_db defaults to sqlite for backward compatibility."""

    normalized: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        normalized.append(arg)

        if arg == "--init_db":
            next_arg = args[i + 1] if i + 1 < len(args) else None
            if not next_arg or next_arg.startswith("-"):
                normalized.append(InitDbOptionEnum.SQLITE.value)
        i += 1

    return normalized


async def parse_cmd(argv: Optional[Sequence[str]] = None):
    """Parse command line arguments using Typer."""

    app = typer.Typer(add_completion=False)

    @app.callback(invoke_without_command=True)
    def main(
        platform: Annotated[
            PlatformEnum,
            typer.Option(
                "--platform",
                help="Media platform selection (xhs=XiaoHongShu | dy=Douyin | ks=Kuaishou | bili=Bilibili | wb=Weibo | tieba=Baidu Tieba | zhihu=Zhihu)",
                rich_help_panel="Basic Configuration",
            ),
        ] = _coerce_enum(PlatformEnum, config.PLATFORM, PlatformEnum.XHS),
        lt: Annotated[
            LoginTypeEnum,
            typer.Option(
                "--lt",
                help="Login type (qrcode=QR Code | phone=Phone | cookie=Cookie)",
                rich_help_panel="Account Configuration",
            ),
        ] = _coerce_enum(LoginTypeEnum, config.LOGIN_TYPE, LoginTypeEnum.QRCODE),
        crawler_type: Annotated[
            CrawlerTypeEnum,
            typer.Option(
                "--type",
                help="Crawler type (search=Search | detail=Detail | creator=Creator | creator_vip=VIP Content)",
                rich_help_panel="Basic Configuration",
            ),
        ] = _coerce_enum(CrawlerTypeEnum, config.CRAWLER_TYPE, CrawlerTypeEnum.SEARCH),
        start: Annotated[
            int,
            typer.Option(
                "--start",
                help="Starting page number",
                rich_help_panel="Basic Configuration",
            ),
        ] = config.START_PAGE,
        keywords: Annotated[
            str,
            typer.Option(
                "--keywords",
                help="Enter keywords, multiple keywords separated by commas",
                rich_help_panel="Basic Configuration",
            ),
        ] = config.KEYWORDS,
        get_comment: Annotated[
            str,
            typer.Option(
                "--get_comment",
                help="Whether to crawl first-level comments, supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Comment Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_COMMENTS),
        get_sub_comment: Annotated[
            str,
            typer.Option(
                "--get_sub_comment",
                help="Whether to crawl second-level comments, supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Comment Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_GET_SUB_COMMENTS),
        headless: Annotated[
            str,
            typer.Option(
                "--headless",
                help="Whether to enable headless mode (applies to both Playwright and CDP), supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Runtime Configuration",
                show_default=True,
            ),
        ] = str(config.HEADLESS),
        save_data_option: Annotated[
            SaveDataOptionEnum,
            typer.Option(
                "--save_data_option",
                help="Data save option (csv=CSV file | db=MySQL database | json=JSON file | sqlite=SQLite database | mongodb=MongoDB database | excel=Excel file | postgres=PostgreSQL database)",
                rich_help_panel="Storage Configuration",
            ),
        ] = _coerce_enum(
            SaveDataOptionEnum, config.SAVE_DATA_OPTION, SaveDataOptionEnum.JSON
        ),
        init_db: Annotated[
            Optional[InitDbOptionEnum],
            typer.Option(
                "--init_db",
                help="Initialize database table structure (sqlite | mysql | postgres)",
                rich_help_panel="Storage Configuration",
            ),
        ] = None,
        cookies: Annotated[
            str,
            typer.Option(
                "--cookies",
                help="Cookie value used for Cookie login method",
                rich_help_panel="Account Configuration",
            ),
        ] = config.COOKIES,
        specified_id: Annotated[
            str,
            typer.Option(
                "--specified_id",
                help="Post/video ID list in detail mode, multiple IDs separated by commas (supports full URL or ID)",
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        creator_id: Annotated[
            str,
            typer.Option(
                "--creator_id",
                help="Creator ID list in creator mode, multiple IDs separated by commas (supports full URL or ID)",
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        vip_creator_id: Annotated[
            str,
            typer.Option(
                "--vip_creator_id",
                help="VIP Creator ID list in creator_vip mode (Weibo only), multiple IDs separated by commas",
                rich_help_panel="Basic Configuration",
            ),
        ] = "",
        max_comments_count_singlenotes: Annotated[
            int,
            typer.Option(
                "--max_comments_count_singlenotes",
                help="Maximum number of first-level comments to crawl per post/video",
                rich_help_panel="Comment Configuration",
            ),
        ] = config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
        enable_incremental: Annotated[
            str,
            typer.Option(
                "--enable_incremental",
                help="Enable incremental crawling (only crawl new content), supports yes/true/t/y/1 or no/false/f/n/0",
                rich_help_panel="Incremental Configuration",
                show_default=True,
            ),
        ] = str(config.ENABLE_INCREMENTAL_CRAWL),
        incremental_threshold: Annotated[
            int,
            typer.Option(
                "--incremental_threshold",
                help="Early stop threshold for creator mode (stop after N consecutive existing items)",
                rich_help_panel="Incremental Configuration",
            ),
        ] = config.CREATOR_EARLY_STOP_THRESHOLD,
        # 微信专用参数
        wechat_enable_content: Annotated[
            str,
            typer.Option(
                "--wechat_enable_content",
                help="[WeChat] Whether to download article HTML content",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "false",
        wechat_enable_stats: Annotated[
            str,
            typer.Option(
                "--wechat_enable_stats",
                help="[WeChat] Whether to fetch reading stats (requires credentials)",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "false",
        wechat_enable_export: Annotated[
            str,
            typer.Option(
                "--wechat_enable_export",
                help="[WeChat] Whether to enable article export",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "false",
        wechat_export_format: Annotated[
            str,
            typer.Option(
                "--wechat_export_format",
                help="[WeChat] Export format (html | markdown | txt | docx)",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "html",
        wechat_album_ids: Annotated[
            str,
            typer.Option(
                "--wechat_album_ids",
                help="[WeChat] Album IDs for album mode, format: biz:album_id, comma-separated",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "",
        wechat_uin: Annotated[
            str,
            typer.Option(
                "--wechat_uin",
                help="[WeChat] Credential uin for fetching comments and stats",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "",
        wechat_key: Annotated[
            str,
            typer.Option(
                "--wechat_key",
                help="[WeChat] Credential key for fetching comments and stats",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "",
        wechat_pass_ticket: Annotated[
            str,
            typer.Option(
                "--wechat_pass_ticket",
                help="[WeChat] Credential pass_ticket for fetching comments and stats",
                rich_help_panel="WeChat Configuration",
            ),
        ] = "",
    ) -> SimpleNamespace:
        """MediaCrawler 命令行入口"""

        enable_comment = _to_bool(get_comment)
        enable_sub_comment = _to_bool(get_sub_comment)
        enable_headless = _to_bool(headless)
        enable_incremental_crawl = _to_bool(enable_incremental)
        init_db_value = init_db.value if init_db else None

        # Parse specified_id, creator_id and vip_creator_id into lists
        specified_id_list = [id.strip() for id in specified_id.split(",") if id.strip()] if specified_id else []
        creator_id_list = [id.strip() for id in creator_id.split(",") if id.strip()] if creator_id else []
        vip_creator_id_list = [id.strip() for id in vip_creator_id.split(",") if id.strip()] if vip_creator_id else []

        # override global config
        config.PLATFORM = platform.value
        config.LOGIN_TYPE = lt.value
        config.CRAWLER_TYPE = crawler_type.value
        config.START_PAGE = start
        config.KEYWORDS = keywords
        config.ENABLE_GET_COMMENTS = enable_comment
        config.ENABLE_GET_SUB_COMMENTS = enable_sub_comment
        config.HEADLESS = enable_headless
        config.CDP_HEADLESS = enable_headless
        config.SAVE_DATA_OPTION = save_data_option.value
        config.COOKIES = cookies
        config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = max_comments_count_singlenotes
        # 增量爬取配置
        config.ENABLE_INCREMENTAL_CRAWL = enable_incremental_crawl
        config.CREATOR_EARLY_STOP_THRESHOLD = incremental_threshold

        # Set platform-specific ID lists for detail/creator mode
        if specified_id_list:
            if platform == PlatformEnum.XHS:
                config.XHS_SPECIFIED_NOTE_URL_LIST = specified_id_list
            elif platform == PlatformEnum.BILIBILI:
                config.BILI_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.DOUYIN:
                config.DY_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.WEIBO:
                config.WEIBO_SPECIFIED_ID_LIST = specified_id_list
            elif platform == PlatformEnum.KUAISHOU:
                config.KS_SPECIFIED_ID_LIST = specified_id_list

        if creator_id_list:
            if platform == PlatformEnum.XHS:
                config.XHS_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.BILIBILI:
                config.BILI_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.DOUYIN:
                config.DY_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.WEIBO:
                config.WEIBO_CREATOR_ID_LIST = creator_id_list
            elif platform == PlatformEnum.KUAISHOU:
                config.KS_CREATOR_ID_LIST = creator_id_list

        # Set VIP creator ID list for creator_vip mode (Weibo only)
        if vip_creator_id_list:
            if platform == PlatformEnum.WEIBO:
                config.WEIBO_VIP_CREATOR_ID_LIST = vip_creator_id_list

        # 微信参数处理
        enable_wechat_content = _to_bool(wechat_enable_content)
        enable_wechat_stats = _to_bool(wechat_enable_stats)
        enable_wechat_export = _to_bool(wechat_enable_export)
        
        # 如果是微信平台，设置相关配置
        if platform == PlatformEnum.WECHAT:
            try:
                from config import wechat_config
                wechat_config.ENABLE_GET_ARTICLE_HTML = enable_wechat_content
                wechat_config.ENABLE_GET_READING_STATS = enable_wechat_stats
                wechat_config.ENABLE_EXPORT = enable_wechat_export
                wechat_config.EXPORT_FORMAT = wechat_export_format
                if wechat_album_ids:
                    wechat_config.WECHAT_ALBUM_IDS = [aid.strip() for aid in wechat_album_ids.split(",") if aid.strip()]
                if wechat_uin:
                    wechat_config.WECHAT_CREDENTIALS_UIN = wechat_uin
                if wechat_key:
                    wechat_config.WECHAT_CREDENTIALS_KEY = wechat_key
                if wechat_pass_ticket:
                    wechat_config.WECHAT_CREDENTIALS_PASS_TICKET = wechat_pass_ticket
            except ImportError:
                pass

        return SimpleNamespace(
            platform=config.PLATFORM,
            lt=config.LOGIN_TYPE,
            type=config.CRAWLER_TYPE,
            start=config.START_PAGE,
            keywords=config.KEYWORDS,
            get_comment=config.ENABLE_GET_COMMENTS,
            get_sub_comment=config.ENABLE_GET_SUB_COMMENTS,
            headless=config.HEADLESS,
            save_data_option=config.SAVE_DATA_OPTION,
            init_db=init_db_value,
            cookies=config.COOKIES,
            specified_id=specified_id,
            creator_id=creator_id,
            vip_creator_id=vip_creator_id,
            enable_incremental=config.ENABLE_INCREMENTAL_CRAWL,
            incremental_threshold=config.CREATOR_EARLY_STOP_THRESHOLD,
            # 微信相关
            wechat_enable_content=enable_wechat_content,
            wechat_enable_stats=enable_wechat_stats,
            wechat_enable_export=enable_wechat_export,
            wechat_export_format=wechat_export_format,
            wechat_album_ids=wechat_album_ids,
        )

    command = typer.main.get_command(app)

    cli_args = _normalize_argv(argv)
    cli_args = _inject_init_db_default(cli_args)

    try:
        result = command.main(args=cli_args, standalone_mode=False)
        if isinstance(result, int):  # help/options handled by Typer; propagate exit code
            raise SystemExit(result)
        return result
    except typer.Exit as exc:  # pragma: no cover - CLI exit paths
        raise SystemExit(exc.exit_code) from exc
