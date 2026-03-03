# -*- coding: utf-8 -*-
"""
系统配置管理路由
提供系统配置的CRUD接口
"""
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.db_session import get_session
from api.services.crud.system_config import system_config_crud, ConfigKeys, DEFAULT_CONFIGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["system-config"])


# ==================== 请求/响应模型 ====================

class ConfigItem(BaseModel):
    """配置项"""
    config_key: str = Field(..., description="配置键")
    config_value: Any = Field(..., description="配置值")
    config_type: str = Field(default="system", description="配置类型")
    description: str = Field(default="", description="描述")
    created_at: Optional[int] = Field(default=None, description="创建时间戳")
    updated_at: Optional[int] = Field(default=None, description="更新时间戳")


class ConfigSetRequest(BaseModel):
    """设置配置请求"""
    config_key: str = Field(..., description="配置键")
    config_value: Any = Field(..., description="配置值")
    config_type: str = Field(default="system", description="配置类型")
    description: str = Field(default="", description="描述")


class ConfigBatchSetRequest(BaseModel):
    """批量设置配置请求"""
    configs: Dict[str, Any] = Field(..., description="配置字典 {key: value}")
    config_type: str = Field(default="system", description="配置类型")


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    items: List[ConfigItem] = Field(default_factory=list, description="配置列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=50, description="每页数量")


# ==================== 配置CRUD接口 ====================

@router.get("/", response_model=ConfigListResponse, summary="获取配置列表")
async def list_configs(
    config_type: Optional[str] = Query(None, description="配置类型筛选"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量")
):
    """
    获取系统配置列表（分页）
    
    支持按配置类型筛选，以及关键词搜索（配置键/描述）
    """
    async with get_session() as session:
        configs = await system_config_crud.get_all_configs(
            session,
            config_type=config_type,
            keyword=keyword,
            page=page,
            page_size=page_size
        )
        
        total = await system_config_crud.count_configs(
            session,
            config_type=config_type,
            keyword=keyword
        )
        
        items = []
        for config in configs:
            import json
            try:
                value = json.loads(config.config_value)
            except json.JSONDecodeError:
                value = config.config_value
            
            items.append(ConfigItem(
                config_key=config.config_key,
                config_value=value,
                config_type=config.config_type,
                description=config.description,
                created_at=config.created_at,
                updated_at=config.updated_at
            ))
        
        return ConfigListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )


@router.get("/key/{config_key}", summary="获取配置值")
async def get_config_value(config_key: str):
    """
    通过配置键获取配置值
    """
    async with get_session() as session:
        value = await system_config_crud.get_value(session, config_key)
        if value is None:
            # 检查是否有默认值
            default = DEFAULT_CONFIGS.get(config_key)
            if default is not None:
                value = default
            else:
                raise HTTPException(status_code=404, detail="配置不存在")
        
        return {"key": config_key, "value": value}


@router.post("/", summary="设置配置")
async def set_config(request: ConfigSetRequest):
    """
    设置单个配置项
    
    如果配置已存在则更新，不存在则创建
    """
    async with get_session() as session:
        await system_config_crud.set_value(
            session,
            config_key=request.config_key,
            config_value=request.config_value,
            config_type=request.config_type,
            description=request.description
        )
        logger.info(f"Config set: {request.config_key}")
        
        return {"message": "配置已保存"}


@router.post("/batch", summary="批量设置配置")
async def batch_set_configs(request: ConfigBatchSetRequest):
    """
    批量设置配置项
    """
    async with get_session() as session:
        count = await system_config_crud.batch_set_values(
            session,
            configs=request.configs,
            config_type=request.config_type
        )
        logger.info(f"Batch set {count} configs")
        
        return {"message": f"已保存 {count} 个配置"}


@router.delete("/key/{config_key}", summary="删除配置")
async def delete_config(config_key: str):
    """
    删除配置项
    """
    async with get_session() as session:
        deleted = await system_config_crud.delete_config(session, config_key=config_key)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="配置不存在")
        
        logger.info(f"Config deleted: {config_key}")
        
        return {"message": "配置已删除"}


# ==================== 按类型获取配置 ====================

@router.get("/type/{config_type}", summary="获取指定类型配置")
async def get_configs_by_type(config_type: str):
    """
    获取指定类型的所有配置（以字典形式返回）
    """
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session, config_type)
        
        return configs


@router.get("/all", summary="获取所有配置")
async def get_all_configs_dict():
    """
    获取所有配置（以字典形式返回）
    """
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session)
        
        return configs


# ==================== 预定义配置组 ====================

@router.get("/proxy", summary="获取代理配置")
async def get_proxy_configs():
    """
    获取代理相关配置
    """
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session, "proxy")
        
        # 填充默认值
        defaults = {
            ConfigKeys.PROXY_ENABLE: True,
            ConfigKeys.PROXY_POOL_SIZE: 5,
            ConfigKeys.PROXY_VALIDATE_TIMEOUT: 10,
            ConfigKeys.PROXY_BINDING_STICKY: True,
            ConfigKeys.PROXY_AUTO_REBIND: True,
        }
        
        for key, default in defaults.items():
            if key not in configs:
                configs[key] = default
        
        return configs


@router.put("/proxy", summary="更新代理配置")
async def update_proxy_configs(configs: Dict[str, Any]):
    """
    更新代理相关配置
    """
    async with get_session() as session:
        await system_config_crud.batch_set_values(
            session,
            configs=configs,
            config_type="proxy"
        )
        
        return {"message": "代理配置已更新"}


@router.get("/crawler", summary="获取爬虫配置")
async def get_crawler_configs():
    """
    获取爬虫相关配置
    """
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session, "crawler")
        
        # 填充默认值
        defaults = {
            ConfigKeys.CRAWLER_CONCURRENCY: 3,
            ConfigKeys.CRAWLER_REQUEST_INTERVAL: 1.0,
            ConfigKeys.CRAWLER_MAX_RETRIES: 3,
            ConfigKeys.CRAWLER_TIMEOUT: 30,
        }
        
        for key, default in defaults.items():
            if key not in configs:
                configs[key] = default
        
        return configs


@router.put("/crawler", summary="更新爬虫配置")
async def update_crawler_configs(configs: Dict[str, Any]):
    """
    更新爬虫相关配置
    """
    async with get_session() as session:
        await system_config_crud.batch_set_values(
            session,
            configs=configs,
            config_type="crawler"
        )
        
        return {"message": "爬虫配置已更新"}


@router.get("/system", summary="获取系统配置")
async def get_system_configs():
    """
    获取系统相关配置
    """
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session, "system")
        
        # 填充默认值
        defaults = {
            ConfigKeys.SYSTEM_LOG_LEVEL: "INFO",
            ConfigKeys.SYSTEM_DATA_RETENTION_DAYS: 30,
            ConfigKeys.SYSTEM_MAINTENANCE_MODE: False,
        }
        
        for key, default in defaults.items():
            if key not in configs:
                configs[key] = default
        
        return configs


@router.put("/system", summary="更新系统配置")
async def update_system_configs(configs: Dict[str, Any]):
    """
    更新系统相关配置
    """
    async with get_session() as session:
        await system_config_crud.batch_set_values(
            session,
            configs=configs,
            config_type="system"
        )
        
        return {"message": "系统配置已更新"}


# ==================== 配置初始化 ====================

@router.post("/init", summary="初始化默认配置")
async def init_default_configs():
    """
    初始化所有默认配置
    
    只会添加不存在的配置，不会覆盖已有配置
    """
    async with get_session() as session:
        count = 0
        for key, value in DEFAULT_CONFIGS.items():
            existing = await system_config_crud.get_by_key(session, key)
            if not existing:
                config_type = key.split(".")[0] if "." in key else "system"
                await system_config_crud.set_value(
                    session,
                    config_key=key,
                    config_value=value,
                    config_type=config_type
                )
                count += 1
        
        logger.info(f"Initialized {count} default configs")
        
        return {"message": f"已初始化 {count} 个默认配置"}
