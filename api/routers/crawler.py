# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/api/routers/crawler.py
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

from fastapi import APIRouter, HTTPException

from ..schemas import CrawlerStartRequest, CrawlerStatusResponse
from ..services import crawler_manager

router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.post("/start")
async def start_crawler(request: CrawlerStartRequest):
    """Start crawler task"""
    success = await crawler_manager.start(request)
    if not success:
        # Handle concurrent/duplicate requests: if process is already running, return 400 instead of 500
        if crawler_manager.process and crawler_manager.process.poll() is None:
            raise HTTPException(status_code=400, detail="Crawler is already running")
        raise HTTPException(status_code=500, detail="Failed to start crawler")

    return {"status": "ok", "message": "Crawler started successfully"}


@router.post("/stop")
async def stop_crawler():
    """Stop crawler task"""
    success = await crawler_manager.stop()
    if not success:
        # Handle concurrent/duplicate requests: if process already exited/doesn't exist, return 400 instead of 500
        if not crawler_manager.process or crawler_manager.process.poll() is not None:
            raise HTTPException(status_code=400, detail="No crawler is running")
        raise HTTPException(status_code=500, detail="Failed to stop crawler")

    return {"status": "ok", "message": "Crawler stopped successfully"}


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status():
    """Get crawler status"""
    return crawler_manager.get_status()


@router.get("/logs")
async def get_logs(limit: int = 100):
    """Get recent logs"""
    logs = crawler_manager.logs[-limit:] if limit > 0 else crawler_manager.logs
    return {"logs": [log.model_dump() for log in logs]}


@router.post("/reset_browser")
async def reset_browser():
    """Reset browser data (clear login state)"""
    try:
        import shutil
        import os
        import config
        
        # Determine user data directory based on platform
        platforms = ["wechat", "xhs", "dy", "bilibili", "ks", "wb"]
        
        cleared_count = 0
        base_dir = os.path.join(os.getcwd(), "browser_data")
        
        if os.path.exists(base_dir):
            for platform in platforms:
                # 尝试匹配各种可能的目录名格式
                # config.USER_DATA_DIR 通常是 "%s_user_data_dir"
                dir_name = config.USER_DATA_DIR % platform
                user_data_dir = os.path.join(base_dir, dir_name)
                
                if os.path.exists(user_data_dir):
                    shutil.rmtree(user_data_dir)
                    cleared_count += 1
                
                # 同时也尝试清理 cdp_ 前缀的目录（如果存在）
                cdp_dir_name = f"cdp_{dir_name}"
                cdp_user_data_dir = os.path.join(base_dir, cdp_dir_name)
                if os.path.exists(cdp_user_data_dir):
                    shutil.rmtree(cdp_user_data_dir)
                    cleared_count += 1
        
        # Clear in-memory state in crawler_manager
        crawler_manager.new_cookies = None
        crawler_manager.new_token = None
        crawler_manager.qrcode_img = None
        
        # Log the reset action
        crawler_manager._logs.append(crawler_manager._create_log_entry("Browser data and login state reset", "info"))
                
        return {"status": "ok", "message": f"已清除 {cleared_count} 个平台的浏览器数据"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
