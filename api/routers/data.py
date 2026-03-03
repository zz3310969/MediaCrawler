# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/data.py
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

import os
import json
import sys
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

# Add project root to sys.path
project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

router = APIRouter(prefix="/data", tags=["data"])

PLATFORM_TABLES = {
    "xhs": [
        {"table": "xhs_note", "model": "XhsNote", "label": "小红书笔记"},
        {"table": "xhs_note_comment", "model": "XhsNoteComment", "label": "小红书评论"},
        {"table": "xhs_creator", "model": "XhsCreator", "label": "小红书创作者"},
    ],
    "dy": [
        {"table": "douyin_aweme", "model": "DouyinAweme", "label": "抖音视频"},
        {"table": "douyin_aweme_comment", "model": "DouyinAwemeComment", "label": "抖音评论"},
        {"table": "dy_creator", "model": "DyCreator", "label": "抖音创作者"},
    ],
    "bili": [
        {"table": "bilibili_video", "model": "BilibiliVideo", "label": "B站视频"},
        {"table": "bilibili_video_comment", "model": "BilibiliVideoComment", "label": "B站评论"},
        {"table": "bilibili_up_info", "model": "BilibiliUpInfo", "label": "B站UP主"},
    ],
    "wb": [
        {"table": "weibo_note", "model": "WeiboNote", "label": "微博笔记"},
        {"table": "weibo_note_comment", "model": "WeiboNoteComment", "label": "微博评论"},
        {"table": "weibo_vip_note", "model": "WeiboVipNote", "label": "微博VIP内容"},
        {"table": "weibo_creator", "model": "WeiboCreator", "label": "微博创作者"},
    ],
    "tieba": [
        {"table": "tieba_note", "model": "TiebaNote", "label": "贴吧帖子"},
        {"table": "tieba_comment", "model": "TiebaComment", "label": "贴吧评论"},
        {"table": "tieba_creator", "model": "TiebaCreator", "label": "贴吧用户"},
    ],
    "zhihu": [
        {"table": "zhihu_content", "model": "ZhihuContent", "label": "知乎内容"},
        {"table": "zhihu_comment", "model": "ZhihuComment", "label": "知乎评论"},
        {"table": "zhihu_creator", "model": "ZhihuCreator", "label": "知乎用户"},
    ],
    "ks": [
        {"table": "kuaishou_video", "model": "KuaishouVideo", "label": "快手视频"},
        {"table": "kuaishou_video_comment", "model": "KuaishouVideoComment", "label": "快手评论"},
    ],
    "wechat": [
        {"table": "wechat_article", "model": "WechatArticle", "label": "微信文章"},
        {"table": "wechat_comment", "model": "WechatComment", "label": "微信评论"},
        {"table": "wechat_account", "model": "WechatAccount", "label": "微信公众号"},
    ],
}

# Data directory
DATA_DIR = Path(__file__).parent.parent.parent / "data"


def get_file_info(file_path: Path) -> dict:
    """Get file information"""
    stat = file_path.stat()
    record_count = None

    # Try to get record count
    try:
        if file_path.suffix == ".json":
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    record_count = len(data)
        elif file_path.suffix == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                record_count = sum(1 for _ in f) - 1  # Subtract header row
    except Exception:
        pass

    return {
        "name": file_path.name,
        "path": str(file_path.relative_to(DATA_DIR)),
        "size": stat.st_size,
        "modified_at": stat.st_mtime,
        "record_count": record_count,
        "type": file_path.suffix[1:] if file_path.suffix else "unknown"
    }


@router.get("/files")
async def list_data_files(platform: Optional[str] = None, file_type: Optional[str] = None):
    """Get data file list"""
    if not DATA_DIR.exists():
        return {"files": []}

    files = []
    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            # Platform filter
            if platform:
                rel_path = str(file_path.relative_to(DATA_DIR))
                if platform.lower() not in rel_path.lower():
                    continue

            # Type filter
            if file_type and file_path.suffix[1:].lower() != file_type.lower():
                continue

            try:
                files.append(get_file_info(file_path))
            except Exception:
                continue

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x["modified_at"], reverse=True)

    return {"files": files}


@router.get("/files/{file_path:path}")
async def get_file_content(file_path: str, preview: bool = True, limit: int = 100):
    """Get file content or preview"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check: ensure within DATA_DIR
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if preview:
        # Return preview data
        try:
            if full_path.suffix == ".json":
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"data": data[:limit], "total": len(data)}
                    return {"data": data, "total": 1}
            elif full_path.suffix == ".csv":
                import csv
                with open(full_path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    rows = []
                    for i, row in enumerate(reader):
                        if i >= limit:
                            break
                        rows.append(row)
                    # Re-read to get total count
                    f.seek(0)
                    total = sum(1 for _ in f) - 1
                    return {"data": rows, "total": total}
            elif full_path.suffix.lower() in (".xlsx", ".xls"):
                import pandas as pd
                # Read first limit rows
                df = pd.read_excel(full_path, nrows=limit)
                # Get total row count (only read first column to save memory)
                df_count = pd.read_excel(full_path, usecols=[0])
                total = len(df_count)
                # Convert to list of dictionaries, handle NaN values
                rows = df.where(pd.notnull(df), None).to_dict(orient='records')
                return {
                    "data": rows,
                    "total": total,
                    "columns": list(df.columns)
                }
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type for preview")
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    else:
        # Return file download
        return FileResponse(
            path=full_path,
            filename=full_path.name,
            media_type="application/octet-stream"
        )


@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """Download file"""
    full_path = DATA_DIR / file_path

    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not full_path.is_file():
        raise HTTPException(status_code=400, detail="Not a file")

    # Security check
    try:
        full_path.resolve().relative_to(DATA_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(
        path=full_path,
        filename=full_path.name,
        media_type="application/octet-stream"
    )


@router.get("/stats")
async def get_data_stats():
    """Get data statistics"""
    if not DATA_DIR.exists():
        return {"total_files": 0, "total_size": 0, "by_platform": {}, "by_type": {}}

    stats = {
        "total_files": 0,
        "total_size": 0,
        "by_platform": {},
        "by_type": {}
    }

    supported_extensions = {".json", ".csv", ".xlsx", ".xls"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            try:
                stat = file_path.stat()
                stats["total_files"] += 1
                stats["total_size"] += stat.st_size

                # Statistics by type
                file_type = file_path.suffix[1:].lower()
                stats["by_type"][file_type] = stats["by_type"].get(file_type, 0) + 1

                # Statistics by platform (inferred from path)
                rel_path = str(file_path.relative_to(DATA_DIR))
                for platform in ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]:
                    if platform in rel_path.lower():
                        stats["by_platform"][platform] = stats["by_platform"].get(platform, 0) + 1
                        break
            except Exception:
                continue

    return stats


@router.get("/export")
async def export_task_data(
    task_id: Optional[str] = None,
    platform: Optional[str] = None,
    format: str = "json",
    limit: int = 1000,
):
    """
    导出爬取数据（面向 AI Agent 的结构化数据导出）。
    支持按 task_id、platform 过滤，支持 JSON/CSV 格式。
    """
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'.")

    if not DATA_DIR.exists():
        if format == "csv":
            from fastapi.responses import Response
            return Response(content="", media_type="text/csv")
        return {"data": [], "total": 0, "task_id": task_id, "platform": platform}

    all_records = []
    supported_extensions = {".json", ".csv"}

    for root, dirs, filenames in os.walk(DATA_DIR):
        root_path = Path(root)
        for filename in filenames:
            file_path = root_path / filename
            if file_path.suffix.lower() not in supported_extensions:
                continue

            rel_path = str(file_path.relative_to(DATA_DIR))
            if platform and platform.lower() not in rel_path.lower():
                continue
            if task_id and task_id not in rel_path:
                continue

            try:
                if file_path.suffix == ".json":
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            for item in data:
                                item["_source_file"] = rel_path
                            all_records.extend(data)
                        elif isinstance(data, dict):
                            data["_source_file"] = rel_path
                            all_records.append(data)
                elif file_path.suffix == ".csv":
                    import csv
                    with open(file_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            row["_source_file"] = rel_path
                            all_records.append(row)
            except Exception:
                continue

            if len(all_records) >= limit:
                break
        if len(all_records) >= limit:
            break

    all_records = all_records[:limit]

    if format == "csv":
        import csv
        import io
        from fastapi.responses import Response

        if not all_records:
            return Response(content="", media_type="text/csv")

        all_keys = set()
        for record in all_records:
            all_keys.update(record.keys())
        fieldnames = sorted(all_keys)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(all_records)

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=export.csv"},
        )

    return {
        "data": all_records,
        "total": len(all_records),
        "task_id": task_id,
        "platform": platform,
    }


def _get_model_class(model_name: str):
    """Get SQLAlchemy model class by name"""
    import database.models as models
    model_cls = getattr(models, model_name, None)
    if model_cls is None:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_name}")
    return model_cls


@router.get("/db/tables")
async def list_db_tables(platform: Optional[str] = None):
    """List database tables with record counts"""
    import config
    save_option = getattr(config, "SAVE_DATA_OPTION", "json")
    if save_option in ("json", "csv", "excel"):
        return {"tables": [], "db_type": save_option, "available": False}

    try:
        from database.db_session import get_session
        from sqlalchemy import func, select

        tables_to_query = []
        if platform:
            tables_to_query = PLATFORM_TABLES.get(platform, [])
        else:
            for p_tables in PLATFORM_TABLES.values():
                tables_to_query.extend(p_tables)

        results = []
        async with get_session() as session:
            if session is None:
                return {"tables": [], "db_type": save_option, "available": False}
            for table_info in tables_to_query:
                try:
                    model_cls = _get_model_class(table_info["model"])
                    stmt = select(func.count()).select_from(model_cls)
                    res = await session.execute(stmt)
                    count = res.scalar() or 0
                    if count > 0:
                        results.append({
                            "table": table_info["table"],
                            "label": table_info["label"],
                            "model": table_info["model"],
                            "platform": next(
                                (p for p, ts in PLATFORM_TABLES.items() if table_info in ts), ""
                            ),
                            "record_count": count,
                        })
                except Exception:
                    continue

        results.sort(key=lambda x: x["record_count"], reverse=True)
        return {"tables": results, "db_type": save_option, "available": True}

    except Exception as e:
        return {"tables": [], "db_type": save_option, "available": False, "error": str(e)}


@router.get("/db/query")
async def query_db_table(
    table: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
):
    """Query database table with pagination"""
    table_info = None
    for p_tables in PLATFORM_TABLES.values():
        for t in p_tables:
            if t["table"] == table:
                table_info = t
                break
        if table_info:
            break

    if not table_info:
        raise HTTPException(status_code=400, detail=f"Unknown table: {table}")

    try:
        from database.db_session import get_session
        from sqlalchemy import func, select, inspect, or_, cast, String

        model_cls = _get_model_class(table_info["model"])
        mapper = inspect(model_cls)
        columns = [col.key for col in mapper.column_attrs]

        async with get_session() as session:
            if session is None:
                raise HTTPException(status_code=500, detail="Database not available")

            count_stmt = select(func.count()).select_from(model_cls)
            query_stmt = select(model_cls)

            if search:
                search_conditions = []
                for col in mapper.columns:
                    if col.type.python_type in (str,):
                        search_conditions.append(col.ilike(f"%{search}%"))
                if search_conditions:
                    count_stmt = count_stmt.where(or_(*search_conditions))
                    query_stmt = query_stmt.where(or_(*search_conditions))

            total_res = await session.execute(count_stmt)
            total = total_res.scalar() or 0

            query_stmt = query_stmt.order_by(model_cls.id.desc())
            query_stmt = query_stmt.offset((page - 1) * page_size).limit(page_size)

            result = await session.execute(query_stmt)
            rows = result.scalars().all()

            data = []
            for row in rows:
                row_dict = {}
                for col in columns:
                    val = getattr(row, col, None)
                    if val is not None:
                        row_dict[col] = val
                    else:
                        row_dict[col] = None
                data.append(row_dict)

            return {
                "data": data,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
                "columns": columns,
                "table": table,
                "label": table_info["label"],
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/db/stats")
async def get_db_stats():
    """Get database statistics - total records across all tables"""
    import config
    save_option = getattr(config, "SAVE_DATA_OPTION", "json")
    if save_option in ("json", "csv", "excel"):
        return {"total_records": 0, "by_platform": {}, "db_type": save_option, "available": False}

    try:
        from database.db_session import get_session
        from sqlalchemy import func, select

        total_records = 0
        by_platform = {}

        async with get_session() as session:
            if session is None:
                return {"total_records": 0, "by_platform": {}, "db_type": save_option, "available": False}

            for platform, tables in PLATFORM_TABLES.items():
                platform_count = 0
                for table_info in tables:
                    try:
                        model_cls = _get_model_class(table_info["model"])
                        stmt = select(func.count()).select_from(model_cls)
                        res = await session.execute(stmt)
                        count = res.scalar() or 0
                        platform_count += count
                    except Exception:
                        continue
                if platform_count > 0:
                    by_platform[platform] = platform_count
                    total_records += platform_count

        return {
            "total_records": total_records,
            "by_platform": by_platform,
            "db_type": save_option,
            "available": True,
        }

    except Exception as e:
        return {"total_records": 0, "by_platform": {}, "db_type": save_option, "available": False, "error": str(e)}


@router.get("/cos/check")
async def check_cos_config():
    """检查腾讯云COS配置状态（使用全局 oss_uploader，自动从 WebUI 数据库加载配置）"""
    try:
        from tools.oss_uploader import oss_uploader

        oss_uploader.reload()
        await oss_uploader._ensure_db_config()

        config_items = {
            "secret_id": oss_uploader.secret_id,
            "secret_key": oss_uploader.secret_key,
            "region": oss_uploader.region,
            "bucket_name": oss_uploader.bucket_name,
            "path_prefix": oss_uploader.path_prefix,
        }

        is_configured = oss_uploader.is_configured()

        config_status = {}
        for key, value in config_items.items():
            if key in ["secret_id", "secret_key"]:
                if value:
                    config_status[key] = {
                        "configured": True,
                        "value": f"{value[:8]}..." if len(value) > 8 else "***",
                        "length": len(value)
                    }
                else:
                    config_status[key] = {"configured": False, "value": "", "error": "未配置"}
            else:
                config_status[key] = {"configured": bool(value), "value": value or ""}

        save_mode = await oss_uploader.get_save_mode()

        return {
            "is_configured": is_configured,
            "config_status": config_status,
            "save_mode": save_mode,
            "config_source": "webui_db",
            "message": "COS配置完整，可以正常使用" if is_configured else "COS配置不完整，请在「系统设置 → 外部服务」中配置",
        }

    except ImportError as e:
        return {
            "is_configured": False,
            "error": "cos-python-sdk-v5 未安装",
            "message": "请运行: pip install cos-python-sdk-v5",
            "detail": str(e)
        }
    except Exception as e:
        return {
            "is_configured": False,
            "error": str(e),
            "message": "检查COS配置时发生错误"
        }
