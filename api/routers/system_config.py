# -*- coding: utf-8 -*-
"""
系统配置管理路由
提供系统配置的CRUD接口
"""
import json
import logging
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from database.db_session import get_session
from api.services.crud.system_config import system_config_crud, ConfigKeys, DEFAULT_CONFIGS, CONFIG_TYPE_MAP

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


# ==================== 按分组的配置接口 ====================

def _defaults_for_type(config_type: str) -> Dict[str, Any]:
    """根据 config_type 返回对应的默认值子集"""
    prefix = CONFIG_TYPE_MAP.get(config_type, f"{config_type}.")
    return {k: v for k, v in DEFAULT_CONFIGS.items() if k.startswith(prefix)}


async def _get_group_configs(config_type: str) -> Dict[str, Any]:
    async with get_session() as session:
        configs = await system_config_crud.get_configs_as_dict(session, config_type)
        for key, default in _defaults_for_type(config_type).items():
            if key not in configs:
                configs[key] = default
        return configs


async def _update_group_configs(config_type: str, configs: Dict[str, Any]) -> dict:
    async with get_session() as session:
        await system_config_crud.batch_set_values(
            session, configs=configs, config_type=config_type
        )
        return {"message": f"{config_type} 配置已更新"}


# -- 爬虫默认设置 (Tab1) --

@router.get("/crawler", summary="获取爬虫配置")
async def get_crawler_configs():
    return await _get_group_configs("crawler")


@router.put("/crawler", summary="更新爬虫配置")
async def update_crawler_configs(configs: Dict[str, Any]):
    return await _update_group_configs("crawler", configs)


# -- 浏览器与反检测 (Tab2) --

@router.get("/browser", summary="获取浏览器配置")
async def get_browser_configs():
    return await _get_group_configs("browser")


@router.put("/browser", summary="更新浏览器配置")
async def update_browser_configs(configs: Dict[str, Any]):
    return await _update_group_configs("browser", configs)


# -- 代理池设置 (Tab3) --

@router.get("/proxy", summary="获取代理配置")
async def get_proxy_configs():
    return await _get_group_configs("proxy")


@router.put("/proxy", summary="更新代理配置")
async def update_proxy_configs(configs: Dict[str, Any]):
    return await _update_group_configs("proxy", configs)


# -- 多账号策略 (Tab4) --

@router.get("/account", summary="获取多账号配置")
async def get_account_configs():
    return await _get_group_configs("account")


@router.put("/account", summary="更新多账号配置")
async def update_account_configs(configs: Dict[str, Any]):
    return await _update_group_configs("account", configs)


# -- 系统运维 (Tab5) --

@router.get("/system", summary="获取系统配置")
async def get_system_configs():
    return await _get_group_configs("system")


@router.put("/system", summary="更新系统配置")
async def update_system_configs(configs: Dict[str, Any]):
    return await _update_group_configs("system", configs)


# -- Webhook 通知 (Tab6) --

@router.get("/webhook", summary="获取Webhook配置")
async def get_webhook_configs():
    return await _get_group_configs("webhook")


@router.put("/webhook", summary="更新Webhook配置")
async def update_webhook_configs(configs: Dict[str, Any]):
    return await _update_group_configs("webhook", configs)


# -- 外部服务 (Tab7) --

@router.get("/external", summary="获取外部服务配置")
async def get_external_configs():
    return await _get_group_configs("external")


@router.put("/external", summary="更新外部服务配置")
async def update_external_configs(configs: Dict[str, Any]):
    result = await _update_group_configs("external", configs)
    try:
        from tools.oss_uploader import oss_uploader
        oss_uploader.reload()
    except Exception:
        pass
    return result


# ==================== COS 连通性测试 ====================

class CosTestRequest(BaseModel):
    """COS 连通性测试请求（使用当前表单值，无需先保存）"""
    secret_id: str = Field(..., description="SecretId")
    secret_key: str = Field(..., description="SecretKey")
    region: str = Field(..., description="地域")
    bucket_name: str = Field(..., description="Bucket 名称")


@router.post("/test-cos", summary="测试 COS 连通性")
async def test_cos_connection(req: CosTestRequest):
    """
    使用提供的凭证测试腾讯云 COS 是否可连通。
    会尝试调用 list_objects (MaxKeys=1) 验证权限和网络。
    """
    import importlib
    if importlib.util.find_spec("qcloud_cos") is None:
        raise HTTPException(
            status_code=400,
            detail="cos-python-sdk-v5 未安装，请运行: uv sync --extra cos"
        )

    if not all([req.secret_id, req.secret_key, req.region, req.bucket_name]):
        raise HTTPException(status_code=400, detail="请填写完整的 COS 配置")

    try:
        from qcloud_cos import CosConfig, CosS3Client

        cos_config = CosConfig(
            Region=req.region,
            SecretId=req.secret_id,
            SecretKey=req.secret_key,
        )
        cos_client = CosS3Client(cos_config)

        resp = cos_client.list_objects(Bucket=req.bucket_name, MaxKeys=1)
        return {
            "success": True,
            "message": f"连接成功！Bucket「{req.bucket_name}」可正常访问",
            "bucket": req.bucket_name,
            "region": req.region,
        }
    except Exception as e:
        error_msg = str(e)
        if "NoSuchBucket" in error_msg:
            detail = f"Bucket「{req.bucket_name}」不存在，请检查名称和地域"
        elif "AccessDenied" in error_msg or "SignatureDoesNotMatch" in error_msg:
            detail = "认证失败，请检查 SecretId 和 SecretKey 是否正确"
        elif "could not be resolved" in error_msg or "ConnectionError" in error_msg:
            detail = f"无法连接到 COS 服务（地域: {req.region}），请检查网络和地域配置"
        else:
            detail = f"连接失败: {error_msg}"

        logger.warning(f"COS test failed: {error_msg}")
        raise HTTPException(status_code=400, detail=detail)


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
