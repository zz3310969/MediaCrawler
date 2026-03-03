# -*- coding: utf-8 -*-
"""
爬虫账号管理路由
提供爬虫账号的CRUD接口
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database.db_session import get_session
from api.schemas.account import (
    Account, AccountWithCookie, AccountCreate, AccountUpdate,
    AccountCookieUpdate, AccountStatus, Platform, LoginMethod,
    AccountListResponse, AccountBatchDelete, AccountBatchStatusUpdate, 
    AccountStats, CookieValidateRequest, CookieValidateResponse
)
from api.services.crud.account import account_crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ==================== 账号CRUD接口 ====================

@router.post("/", response_model=Account, summary="创建账号")
async def create_account(request: AccountCreate):
    """
    创建新的爬虫账号
    
    - **platform**: 平台（xhs/dy/bili/wb/wechat/ks/tieba/zhihu）
    - **username**: 用户名（可选）
    - **nickname**: 昵称（可选）
    - **login_method**: 登录方式（qrcode/cookie/phone）
    - **cookies**: Cookie数据（可选）
    - **remark**: 备注（可选）
    """
    async with get_session() as session:
        # 如果提供了用户名，检查是否已存在
        if request.username:
            platform_value = request.platform.value if isinstance(request.platform, Platform) else request.platform
            existing = await account_crud.get_by_platform_username(
                session, platform_value, request.username
            )
            if existing:
                raise HTTPException(status_code=400, detail="该平台账号已存在")
        
        account = await account_crud.create_account(session, obj_in=request)
        logger.info(f"Account created: {account.platform} - {account.username or account.nickname}")
        
        return Account.model_validate(account)


@router.get("/", response_model=AccountListResponse, summary="获取账号列表")
async def list_accounts(
    platform: Optional[Platform] = Query(None, description="平台筛选"),
    status: Optional[AccountStatus] = Query(None, description="状态筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    """
    获取爬虫账号列表（分页）
    
    支持按平台、状态筛选，以及关键词搜索（用户名/昵称/备注）
    """
    async with get_session() as session:
        platform_value = platform.value if platform else None
        status_value = status.value if status else None
        
        accounts = await account_crud.get_accounts_list(
            session,
            platform=platform_value,
            status=status_value,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        
        total = await account_crud.count_accounts(
            session,
            platform=platform_value,
            status=status_value,
            keyword=keyword
        )
        
        return AccountListResponse(
            items=[Account.model_validate(a) for a in accounts],
            total=total,
            page=page,
            page_size=page_size
        )


@router.get("/stats", response_model=AccountStats, summary="获取账号统计")
async def get_account_stats():
    """
    获取账号统计数据
    
    返回各状态和各平台的账号数量
    """
    async with get_session() as session:
        stats = await account_crud.get_stats(session)
        return AccountStats(**stats)


@router.get("/{account_id}", response_model=Account, summary="获取账号详情")
async def get_account(account_id: str):
    """
    通过账号ID获取账号详情
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        return Account.model_validate(account)


@router.get("/{account_id}/with-cookie", response_model=AccountWithCookie, summary="获取账号详情（含Cookie）")
async def get_account_with_cookie(account_id: str):
    """
    通过账号ID获取账号详情（含Cookie，仅管理员）
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        return AccountWithCookie.model_validate(account)


@router.put("/{account_id}", response_model=Account, summary="更新账号信息")
async def update_account(account_id: str, request: AccountUpdate):
    """
    更新账号信息
    
    - **nickname**: 昵称
    - **status**: 状态
    - **cookies**: Cookie数据
    - **remark**: 备注
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        account = await account_crud.update_account(session, db_obj=account, obj_in=request)
        logger.info(f"Account updated: {account.platform} - {account.username or account.nickname}")
        
        return Account.model_validate(account)


@router.delete("/{account_id}", summary="删除账号")
async def delete_account(account_id: str):
    """
    删除账号
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        await account_crud.delete_account(session, account_id=account_id)
        logger.info(f"Account deleted: {account.platform} - {account.username or account.nickname}")
        
        return {"message": "账号已删除"}


# ==================== Cookie管理接口 ====================

@router.put("/{account_id}/cookie", response_model=Account, summary="更新Cookie")
async def update_account_cookie(account_id: str, request: AccountCookieUpdate):
    """
    更新账号的Cookie
    
    - **cookies**: 新的Cookie数据
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        account = await account_crud.update_cookies(
            session, 
            db_obj=account, 
            cookies=request.cookies
        )
        logger.info(f"Account cookie updated: {account.platform} - {account.username or account.nickname}")
        
        return Account.model_validate(account)


@router.post("/{account_id}/validate", response_model=CookieValidateResponse, summary="验证Cookie")
async def validate_account_cookie(account_id: str):
    """
    验证账号的Cookie是否有效
    
    TODO: 实现各平台的Cookie验证逻辑
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        # TODO: 调用各平台的验证接口
        # 这里先返回模拟结果
        is_valid = bool(account.cookies and len(account.cookies) > 50)
        
        if is_valid:
            account.cookie_valid = 1
            account.status = AccountStatus.ACTIVE.value
        else:
            account.cookie_valid = 0
            account.status = AccountStatus.EXPIRED.value
        
        from api.services.crud.base import get_timestamp_seconds
        account.last_validated_at = get_timestamp_seconds()
        session.add(account)
        
        return CookieValidateResponse(
            valid=is_valid,
            username=account.username,
            nickname=account.nickname,
            avatar=account.avatar,
            message="Cookie有效" if is_valid else "Cookie无效或已过期"
        )


@router.post("/validate", response_model=CookieValidateResponse, summary="验证Cookie（不保存）")
async def validate_cookie(request: CookieValidateRequest):
    """
    验证Cookie是否有效（不保存到数据库）
    
    - **platform**: 平台
    - **cookies**: Cookie数据
    
    TODO: 实现各平台的Cookie验证逻辑
    """
    # TODO: 调用各平台的验证接口
    # 这里先返回模拟结果
    is_valid = bool(request.cookies and len(request.cookies) > 50)
    
    return CookieValidateResponse(
        valid=is_valid,
        message="Cookie格式有效" if is_valid else "Cookie格式无效"
    )


# ==================== 批量操作接口 ====================

@router.post("/batch-delete", summary="批量删除账号")
async def batch_delete_accounts(request: AccountBatchDelete):
    """
    批量删除账号
    
    - **account_ids**: 账号ID列表
    """
    async with get_session() as session:
        deleted_count = await account_crud.batch_delete(
            session, 
            account_ids=request.account_ids
        )
        logger.info(f"Batch deleted {deleted_count} accounts")
        
        return {"message": f"已删除 {deleted_count} 个账号"}


@router.post("/batch-status", summary="批量更新状态")
async def batch_update_status(request: AccountBatchStatusUpdate):
    """
    批量更新账号状态
    
    - **account_ids**: 账号ID列表
    - **status**: 目标状态
    """
    async with get_session() as session:
        status_value = request.status.value if isinstance(request.status, AccountStatus) else request.status
        updated_count = await account_crud.batch_update_status(
            session,
            account_ids=request.account_ids,
            status=status_value
        )
        logger.info(f"Batch updated {updated_count} accounts status to {status_value}")
        
        return {"message": f"已更新 {updated_count} 个账号状态"}


# ==================== 账号状态管理 ====================

@router.post("/{account_id}/activate", summary="激活账号")
async def activate_account(account_id: str):
    """
    激活账号
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        account.status = AccountStatus.ACTIVE.value
        session.add(account)
        
        return {"message": "账号已激活"}


@router.post("/{account_id}/deactivate", summary="停用账号")
async def deactivate_account(account_id: str):
    """
    停用账号
    """
    async with get_session() as session:
        account = await account_crud.get_by_account_id(session, account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账号不存在")
        
        account.status = AccountStatus.INACTIVE.value
        session.add(account)
        
        return {"message": "账号已停用"}


# ==================== 平台相关接口 ====================

@router.get("/platform/{platform}/active", summary="获取平台有效账号")
async def get_active_accounts_by_platform(platform: Platform):
    """
    获取指定平台的有效账号列表
    """
    async with get_session() as session:
        platform_value = platform.value if isinstance(platform, Platform) else platform
        accounts = await account_crud.get_active_accounts_by_platform(session, platform_value)
        
        return {
            "items": [Account.model_validate(a) for a in accounts],
            "total": len(accounts)
        }
