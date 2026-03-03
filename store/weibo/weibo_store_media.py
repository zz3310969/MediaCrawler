# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/store/weibo/weibo_store_media.py
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

# -*- coding: utf-8 -*-
# @Author  : Erm
# @Time    : 2024/4/9 17:35
# @Desc    : Weibo media storage
import pathlib
from typing import Dict, Optional, Tuple

import aiofiles

import config
from base.base_crawler import AbstractStoreImage, AbstractStoreVideo
from tools import utils
from tools.oss_uploader import oss_uploader


class WeiboStoreImage(AbstractStoreImage):
    image_store_path: str = "data/weibo/images"

    async def store_image(self, image_content_item: Dict):
        """
        store content

        Args:
            image_content_item:

        Returns:

        """
        await self.save_image(image_content_item.get("pic_id"), image_content_item.get("pic_content"), image_content_item.get("extension_file_name"))

    def make_save_file_name(self, picid: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            picid: image id
            extension_file_name: video filename with extension

        Returns:

        """
        return f"{self.image_store_path}/{picid}.{extension_file_name}"

    async def save_image(self, picid: str, pic_content: str, extension_file_name="jpg"):
        """
        save image to local

        Args:
            picid: image id
            pic_content: image content
            extension_file_name: image filename with extension

        Returns:

        """
        pathlib.Path(self.image_store_path).mkdir(parents=True, exist_ok=True)
        save_file_name = self.make_save_file_name(picid, extension_file_name)
        async with aiofiles.open(save_file_name, 'wb') as f:
            await f.write(pic_content)
            utils.logger.info(f"[WeiboImageStoreImplement.save_image] save image {save_file_name} success ...")


class WeiboVipPosterStoreImage(AbstractStoreImage):
    """Store VIP content poster images with local and OSS support"""
    image_store_path: str = "data/weibo/vip_posters"

    async def store_image(self, image_content_item: Dict) -> Tuple[Optional[str], Optional[str]]:
        """
        store VIP poster image to local and/or OSS based on config

        Args:
            image_content_item: Dict containing pic_id, pic_content, extension_file_name

        Returns:
            Tuple of (local_path, oss_url) - either can be None if not saved to that location

        """
        return await self.save_image(
            image_content_item.get("pic_id"),
            image_content_item.get("pic_content"),
            image_content_item.get("extension_file_name")
        )

    def make_save_file_name(self, picid: str, extension_file_name: str) -> str:
        """
        make save file name by store type

        Args:
            picid: image id
            extension_file_name: image filename with extension

        Returns:

        """
        return f"{self.image_store_path}/{picid}.{extension_file_name}"

    async def save_image(self, picid: str, pic_content: bytes, extension_file_name: str = "jpg") -> Tuple[Optional[str], Optional[str]]:
        """
        save VIP poster image to local and/or OSS

        Args:
            picid: image id
            pic_content: image content bytes
            extension_file_name: image filename with extension

        Returns:
            Tuple of (local_path, oss_url)

        """
        local_path: Optional[str] = None
        oss_url: Optional[str] = None
        save_mode = await oss_uploader.get_save_mode()

        need_local = save_mode in ("local", "both")
        need_oss = save_mode in ("oss", "both")

        if need_oss and not oss_uploader.is_configured():
            utils.logger.warning(
                "[WeiboVipPosterStoreImage] COS 未配置，自动回退到本地保存"
            )
            need_local = True
            need_oss = False

        if need_local:
            pathlib.Path(self.image_store_path).mkdir(parents=True, exist_ok=True)
            save_file_name = self.make_save_file_name(picid, extension_file_name)
            async with aiofiles.open(save_file_name, 'wb') as f:
                await f.write(pic_content)
                local_path = save_file_name
                utils.logger.info(f"[WeiboVipPosterStoreImage.save_image] Saved VIP poster to local: {save_file_name}")

        if need_oss:
            filename = f"{picid}.{extension_file_name}"
            content_type = self._get_content_type(extension_file_name)
            oss_url = await oss_uploader.upload_bytes(pic_content, filename, content_type)
            if oss_url:
                utils.logger.info(f"[WeiboVipPosterStoreImage.save_image] Uploaded VIP poster to OSS: {oss_url}")

        return local_path, oss_url

    @staticmethod
    def _get_content_type(extension: str) -> str:
        """Get content type based on file extension"""
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        return content_types.get(extension.lower(), "image/jpeg")
