"""
API Key CRUD 操作
"""
import json
import time
import hashlib
import secrets
import logging
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.webui_models import ApiKeyModel

logger = logging.getLogger(__name__)

API_KEY_PREFIX = "mc_"


def generate_api_key() -> str:
    """生成 API Key: mc_ + 48 字符随机串"""
    return API_KEY_PREFIX + secrets.token_urlsafe(36)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def get_key_prefix(raw_key: str) -> str:
    """取前 8 字符作为前缀用于识别"""
    return raw_key[:8]


class ApiKeyCRUD:
    async def create(
        self,
        db: AsyncSession,
        *,
        name: str,
        scopes: List[str],
        rate_limit: int = 60,
        user_id: str = "",
        expires_at: int = 0,
    ) -> tuple[ApiKeyModel, str]:
        """创建 API Key，返回 (model, raw_key)"""
        raw_key = generate_api_key()
        now = int(time.time())

        model = ApiKeyModel(
            key_id=secrets.token_urlsafe(16),
            key_hash=hash_api_key(raw_key),
            key_prefix=get_key_prefix(raw_key),
            name=name,
            user_id=user_id,
            scopes=json.dumps(scopes),
            rate_limit=rate_limit,
            is_active=1,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        db.add(model)
        await db.flush()
        return model, raw_key

    async def get_by_key_id(self, db: AsyncSession, key_id: str) -> Optional[ApiKeyModel]:
        result = await db.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_id == key_id)
        )
        return result.scalars().first()

    async def verify_key(self, db: AsyncSession, raw_key: str) -> Optional[ApiKeyModel]:
        """验证 API Key，返回匹配的 model 或 None"""
        key_hash = hash_api_key(raw_key)
        result = await db.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.key_hash == key_hash,
                ApiKeyModel.is_active == 1,
            )
        )
        model = result.scalars().first()
        if not model:
            return None

        if model.expires_at > 0 and model.expires_at < int(time.time()):
            return None

        now = int(time.time())
        await db.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.id == model.id)
            .values(last_used_at=now)
        )
        return model

    async def list_keys(self, db: AsyncSession, user_id: str = "") -> List[ApiKeyModel]:
        query = select(ApiKeyModel).order_by(ApiKeyModel.created_at.desc())
        if user_id:
            query = query.where(ApiKeyModel.user_id == user_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def deactivate(self, db: AsyncSession, key_id: str) -> bool:
        result = await db.execute(
            update(ApiKeyModel)
            .where(ApiKeyModel.key_id == key_id)
            .values(is_active=0, updated_at=int(time.time()))
        )
        return result.rowcount > 0

    async def delete(self, db: AsyncSession, key_id: str) -> bool:
        model = await self.get_by_key_id(db, key_id)
        if model:
            await db.delete(model)
            return True
        return False


api_key_crud = ApiKeyCRUD()
