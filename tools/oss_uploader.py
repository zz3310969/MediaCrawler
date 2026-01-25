# -*- coding: utf-8 -*-
# @Desc    : 腾讯云COS上传工具

import os
from typing import Optional

import config
from tools import utils


class COSUploader:
    """腾讯云COS上传工具类"""

    def __init__(self):
        self.secret_id = getattr(config, 'COS_SECRET_ID', '')
        self.secret_key = getattr(config, 'COS_SECRET_KEY', '')
        self.region = getattr(config, 'COS_REGION', '')
        self.bucket_name = getattr(config, 'COS_BUCKET_NAME', '')
        self.path_prefix = getattr(config, 'COS_PATH_PREFIX', 'vip_posters/')
        self._client = None

    def _get_client(self):
        """获取COS Client实例（懒加载）"""
        if self._client is None:
            try:
                from qcloud_cos import CosConfig, CosS3Client

                cos_config = CosConfig(
                    Region=self.region,
                    SecretId=self.secret_id,
                    SecretKey=self.secret_key,
                )
                self._client = CosS3Client(cos_config)
            except ImportError:
                utils.logger.error("[COSUploader] cos-python-sdk-v5 library not installed. Please run: pip install cos-python-sdk-v5")
                raise
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
        Args:
            content: 文件内容（字节）
            filename: 文件名（不含路径）
            content_type: 内容类型

        Returns:
            成功返回COS URL，失败返回None
        """
        if not self.is_configured():
            utils.logger.warning("[COSUploader] COS not configured, skipping upload")
            return None

        try:
            from io import BytesIO

            client = self._get_client()
            object_key = f"{self.path_prefix}{filename}"

            # 使用 BytesIO 包装字节内容
            file_body = BytesIO(content)

            # 上传文件
            response = client.put_object(
                Bucket=self.bucket_name,
                Body=file_body,
                Key=object_key,
                ContentType=content_type,
            )

            # 检查上传结果
            if response and response.get('ETag'):
                # 构建访问URL
                cos_url = f"https://{self.bucket_name}.cos.{self.region}.myqcloud.com/{object_key}"
                utils.logger.info(f"[COSUploader] Successfully uploaded to COS: {cos_url}")
                return cos_url
            else:
                utils.logger.error(f"[COSUploader] Upload failed, response: {response}")
                return None

        except ImportError:
            utils.logger.error("[COSUploader] cos-python-sdk-v5 library not installed. Please run: pip install cos-python-sdk-v5")
            return None
        except Exception as e:
            utils.logger.error(f"[COSUploader] Upload failed: {e}")
            return None

    async def upload_file(self, file_path: str, filename: Optional[str] = None) -> Optional[str]:
        """
        上传本地文件到COS
        Args:
            file_path: 本地文件路径
            filename: COS上的文件名（可选，默认使用原文件名）

        Returns:
            成功返回COS URL，失败返回None
        """
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

            # 上传文件
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
            utils.logger.error("[COSUploader] cos-python-sdk-v5 library not installed. Please run: pip install cos-python-sdk-v5")
            return None
        except Exception as e:
            utils.logger.error(f"[COSUploader] Upload failed: {e}")
            return None


# 全局单例
oss_uploader = COSUploader()
