"""
API Key 管理路由
"""
import json
import logging
from typing import List
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends

from api.schemas.api_key import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyInfo,
)
from api.middleware.session import require_session_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/api-keys", tags=["api-keys"])


@router.post("/", response_model=ApiKeyCreateResponse)
async def create_api_key(
    request: ApiKeyCreateRequest,
    session_id: str = Depends(require_session_id),
):
    """创建 API Key"""
    from database.db_session import get_session as get_db_session
    from api.services.crud.api_key import api_key_crud

    expires_at = 0
    expires_dt = None
    if request.expire_days:
        expires_dt = datetime.utcnow() + timedelta(days=request.expire_days)
        expires_at = int(expires_dt.timestamp())

    async with get_db_session() as db_session:
        if db_session is None:
            raise HTTPException(status_code=500, detail="Database not available")

        model, raw_key = await api_key_crud.create(
            db_session,
            name=request.name,
            scopes=request.scopes,
            rate_limit=request.rate_limit,
            user_id=session_id,
            expires_at=expires_at,
        )

    logger.info(f"API Key created: {model.key_prefix}... name={request.name}")

    return ApiKeyCreateResponse(
        key_id=model.key_id,
        api_key=raw_key,
        name=model.name,
        scopes=request.scopes,
        rate_limit=model.rate_limit,
        expires_at=expires_dt,
        created_at=datetime.fromtimestamp(model.created_at),
    )


@router.get("/", response_model=List[ApiKeyInfo])
async def list_api_keys(
    session_id: str = Depends(require_session_id),
):
    """列出当前用户的 API Keys"""
    from database.db_session import get_session as get_db_session
    from api.services.crud.api_key import api_key_crud

    async with get_db_session() as db_session:
        if db_session is None:
            return []

        models = await api_key_crud.list_keys(db_session, user_id=session_id)

    return [
        ApiKeyInfo(
            key_id=m.key_id,
            key_prefix=m.key_prefix,
            name=m.name,
            scopes=json.loads(m.scopes) if m.scopes else [],
            rate_limit=m.rate_limit,
            is_active=bool(m.is_active),
            expires_at=datetime.fromtimestamp(m.expires_at) if m.expires_at else None,
            last_used_at=datetime.fromtimestamp(m.last_used_at) if m.last_used_at else None,
            created_at=datetime.fromtimestamp(m.created_at),
        )
        for m in models
    ]


@router.delete("/{key_id}")
async def delete_api_key(
    key_id: str,
    session_id: str = Depends(require_session_id),
):
    """删除 API Key"""
    from database.db_session import get_session as get_db_session
    from api.services.crud.api_key import api_key_crud

    async with get_db_session() as db_session:
        if db_session is None:
            raise HTTPException(status_code=500, detail="Database not available")

        success = await api_key_crud.delete(db_session, key_id)

    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")

    return {"message": "API Key deleted"}


@router.post("/{key_id}/deactivate")
async def deactivate_api_key(
    key_id: str,
    session_id: str = Depends(require_session_id),
):
    """停用 API Key"""
    from database.db_session import get_session as get_db_session
    from api.services.crud.api_key import api_key_crud

    async with get_db_session() as db_session:
        if db_session is None:
            raise HTTPException(status_code=500, detail="Database not available")

        success = await api_key_crud.deactivate(db_session, key_id)

    if not success:
        raise HTTPException(status_code=404, detail="API Key not found")

    return {"message": "API Key deactivated"}
