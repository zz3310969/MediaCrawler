# -*- coding: utf-8 -*-
# @Desc    : 腾讯云COS上传工具
#
# 配置优先级: WebUI 数据库配置 > 环境变量 > config 模块默认值

import importlib
import os
from typing import Optional

import config
from tools import utils

_COS_SDK_AVAILABLE = importlib.util.find_spec("qcloud_cos") is not None


def check_cos_dependency():
    """启动时校验：如果配置了 COS 但未安装 SDK，给出明确提示"""
    cos_configured = bool(
        getattr(config, 'COS_SECRET_ID', '') and
        getattr(config, 'COS_SECRET_KEY', '') and
        getattr(config, 'COS_BUCKET_NAME', '')
    )
    if cos_configured and not _COS_SDK_AVAILABLE:
        utils.logger.warning(
            "[COSUploader] COS 已配置但 cos-python-sdk-v5 未安装，COS 上传功能将不可用。"
            "请运行: uv sync --extra cos  或  pip install cos-python-sdk-v5"
        )
    return _COS_SDK_AVAILABLE


async def _load_cos_config_from_db() -> dict:
    """从 WebUI 数据库加载 COS 配置（system_config 表）"""
    try:
        from database.db_session import get_session
        from api.services.crud.system_config import system_config_crud

        keys = {
            "secret_id": "external.cos_secret_id",
            "secret_key": "external.cos_secret_key",
            "region": "external.cos_region",
            "bucket_name": "external.cos_bucket_name",
            "path_prefix": "external.cos_path_prefix",
            "save_mode": "external.cos_save_mode",
        }

        result = {}
        async with get_session() as session:
            for attr, db_key in keys.items():
                val = await system_config_crud.get_value(session, db_key)
                if val is not None and val != "":
                    result[attr] = val
        return result
    except Exception as e:
        utils.logger.debug(f"[COSUploader] 从数据库读取 COS 配置失败（可能尚未初始化）: {e}")
        return {}


class COSUploader:
    """腾讯云COS上传工具类
    
    配置加载优先级：WebUI 数据库 > 环境变量 > config 模块默认值
    首次 upload 时自动从数据库加载最新配置。
    """

    def __init__(self):
        self.secret_id = getattr(config, 'COS_SECRET_ID', '')
        self.secret_key = getattr(config, 'COS_SECRET_KEY', '')
        self.region = getattr(config, 'COS_REGION', '')
        self.bucket_name = getattr(config, 'COS_BUCKET_NAME', '')
        self.path_prefix = getattr(config, 'COS_PATH_PREFIX', 'vip_posters/')
        self.save_mode = getattr(config, 'VIP_POSTER_SAVE_MODE', 'local')
        self._client = None
        self._sdk_available = _COS_SDK_AVAILABLE
        self._db_loaded = False

    async def _ensure_db_config(self) -> None:
        """确保已从数据库加载最新配置（仅加载一次，配置变更通过 reload 刷新）"""
        if self._db_loaded:
            return
        self._db_loaded = True

        db_conf = await _load_cos_config_from_db()
        if not db_conf:
            return

        if db_conf.get("secret_id"):
            self.secret_id = db_conf["secret_id"]
        if db_conf.get("secret_key"):
            self.secret_key = db_conf["secret_key"]
        if db_conf.get("region"):
            self.region = db_conf["region"]
        if db_conf.get("bucket_name"):
            self.bucket_name = db_conf["bucket_name"]
        if db_conf.get("path_prefix"):
            self.path_prefix = db_conf["path_prefix"]
        if db_conf.get("save_mode"):
            self.save_mode = db_conf["save_mode"]

        self._client = None
        utils.logger.info(
            f"[COSUploader] 已从 WebUI 配置加载 COS 参数 "
            f"(region={self.region}, bucket={self.bucket_name})"
        )

    def reload(self) -> None:
        """标记配置需重新从数据库加载（下次 upload 时生效）"""
        self._db_loaded = False
        self._client = None

    def _get_client(self):
        """获取COS Client实例（懒加载）"""
        if self._client is None:
            if not self._sdk_available:
                raise ImportError(
                    "cos-python-sdk-v5 未安装。请运行: uv sync --extra cos  或  pip install cos-python-sdk-v5"
                )
            try:
                from qcloud_cos import CosConfig, CosS3Client

                cos_config = CosConfig(
                    Region=self.region,
                    SecretId=self.secret_id,
                    SecretKey=self.secret_key,
                )
                self._client = CosS3Client(cos_config)
            except Exception as e:
                utils.logger.error(f"[COSUploader] Failed to initialize COS client: {e}")
                raise
        return self._client

    def is_configured(self) -> bool:
        """检查COS是否已配置"""
        return bool(
            self.secret_id and
            self.secret_key and
            self.region and
            self.bucket_name
        )

    async def upload_bytes(self, content: bytes, filename: str, content_type: str = "image/jpeg") -> Optional[str]:
        """
        上传字节内容到COS

        Returns:
            成功返回COS URL，失败返回None
        """
        await self._ensure_db_config()

        if not self.is_configured():
            utils.logger.warning("[COSUploader] COS not configured, skipping upload")
            return None

        try:
            from io import BytesIO

            client = self._get_client()
            object_key = f"{self.path_prefix}{filename}"

            file_body = BytesIO(content)

            response = client.put_object(
                Bucket=self.bucket_name,
                Body=file_body,
                Key=object_key,
                ContentType=content_type,
            )

            if response and response.get('ETag'):
                cos_url = f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{object_key}"
                utils.logger.info(f"[COSUploader] Successfully uploaded to COS: {cos_url}")
                return cos_url
            else:
                utils.logger.error(f"[COSUploader] Upload failed, response: {response}")
                return None

        except ImportError:
            utils.logger.error(
                "[COSUploader] cos-python-sdk-v5 未安装。请运行: uv sync --extra cos  或  pip install cos-python-sdk-v5"
            )
            return None
        except Exception as e:
            utils.logger.error(f"[COSUploader] Upload failed: {e}")
            return None

    async def upload_file(self, file_path: str, filename: Optional[str] = None) -> Optional[str]:
        """
        上传本地文件到COS

        Returns:
            成功返回COS URL，失败返回None
        """
        await self._ensure_db_config()

        if not self.is_configured():
            utils.logger.warning("[COSUploader] COS not configured, skipping upload")
            return None

        if not os.path.exists(file_path):
            utils.logger.error(f"[COSUploader] File not found: {file_path}")
            return None

        try:
            client = self._get_client()

            if filename is None:
                filename = os.path.basename(file_path)

            object_key = f"{self.path_prefix}{filename}"

            response = client.upload_file(
                Bucket=self.bucket_name,
                Key=object_key,
                LocalFilePath=file_path,
            )

            if response and response.get('ETag'):
                cos_url = f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{object_key}"
                utils.logger.info(f"[COSUploader] Successfully uploaded to COS: {cos_url}")
                return cos_url
            else:
                utils.logger.error(f"[COSUploader] Upload failed, response: {response}")
                return None

        except ImportError:
            utils.logger.error(
                "[COSUploader] cos-python-sdk-v5 未安装。请运行: uv sync --extra cos  或  pip install cos-python-sdk-v5"
            )
            return None
        except Exception as e:
            utils.logger.error(f"[COSUploader] Upload failed: {e}")
            return None

    async def get_save_mode(self) -> str:
        """获取当前保存模式（会自动从数据库加载最新值）"""
        await self._ensure_db_config()
        return self.save_mode


# 全局单例
oss_uploader = COSUploader()
