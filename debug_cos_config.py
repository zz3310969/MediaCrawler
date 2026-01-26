#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
COS配置调试脚本 - 详细显示每个配置项的状态
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 强制重新加载config模块
if 'config' in sys.modules:
    del sys.modules['config']
if 'config.weibo_config' in sys.modules:
    del sys.modules['config.weibo_config']

import config


def check_cos_config():
    """详细检查COS配置"""
    print("=" * 70)
    print("腾讯云COS配置详细调试")
    print("=" * 70)
    
    # 1. 检查环境变量
    print("\n📌 第一步：检查环境变量")
    print("-" * 70)
    
    env_vars = {
        "COS_SECRET_ID": os.getenv("COS_SECRET_ID", ""),
        "COS_SECRET_KEY": os.getenv("COS_SECRET_KEY", ""),
        "COS_REGION": os.getenv("COS_REGION", ""),
        "COS_BUCKET_NAME": os.getenv("COS_BUCKET_NAME", ""),
        "COS_PATH_PREFIX": os.getenv("COS_PATH_PREFIX", ""),
    }
    
    for key, value in env_vars.items():
        if value:
            if "SECRET" in key or "KEY" in key:
                print(f"✅ {key:20s}: {value[:8]}... (长度: {len(value)})")
            else:
                print(f"✅ {key:20s}: {value}")
        else:
            print(f"❌ {key:20s}: 未设置")
    
    # 2. 检查config模块读取的值
    print("\n📌 第二步：检查config模块读取的值")
    print("-" * 70)
    
    config_values = {
        "COS_SECRET_ID": getattr(config, 'COS_SECRET_ID', ''),
        "COS_SECRET_KEY": getattr(config, 'COS_SECRET_KEY', ''),
        "COS_REGION": getattr(config, 'COS_REGION', ''),
        "COS_BUCKET_NAME": getattr(config, 'COS_BUCKET_NAME', ''),
        "COS_PATH_PREFIX": getattr(config, 'COS_PATH_PREFIX', ''),
    }
    
    for key, value in config_values.items():
        if value:
            if "SECRET" in key or "KEY" in key:
                print(f"✅ config.{key:20s}: {value[:8]}... (长度: {len(value)})")
            else:
                print(f"✅ config.{key:20s}: {value}")
        else:
            print(f"❌ config.{key:20s}: 空值")
    
    # 3. 检查COSUploader实例
    print("\n📌 第三步：检查COSUploader实例")
    print("-" * 70)
    
    try:
        from tools.oss_uploader import COSUploader
        
        uploader = COSUploader()
        
        uploader_values = {
            "secret_id": uploader.secret_id,
            "secret_key": uploader.secret_key,
            "region": uploader.region,
            "bucket_name": uploader.bucket_name,
            "path_prefix": uploader.path_prefix,
        }
        
        for key, value in uploader_values.items():
            if value:
                if "secret" in key or "key" in key:
                    print(f"✅ uploader.{key:15s}: {value[:8]}... (长度: {len(value)})")
                else:
                    print(f"✅ uploader.{key:15s}: {value}")
            else:
                print(f"❌ uploader.{key:15s}: 空值")
        
        # 4. 检查is_configured()结果
        print("\n📌 第四步：检查is_configured()判断")
        print("-" * 70)
        
        is_configured = uploader.is_configured()
        print(f"结果: {'✅ 配置完整' if is_configured else '❌ 配置不完整'}")
        
        # 详细检查每个必需项
        print("\n必需项检查（所有项都必须为True）:")
        checks = {
            "secret_id": bool(uploader.secret_id),
            "secret_key": bool(uploader.secret_key),
            "region": bool(uploader.region),
            "bucket_name": bool(uploader.bucket_name),
        }
        
        for key, status in checks.items():
            symbol = "✅" if status else "❌"
            print(f"  {symbol} {key:15s}: {status}")
        
        # 5. 给出建议
        print("\n📌 诊断建议")
        print("-" * 70)
        
        if is_configured:
            print("✅ COS配置完整，可以正常使用")
            print("\n下一步：运行完整测试")
            print("  python test_cos_config.py")
        else:
            print("❌ COS配置不完整，缺少以下配置项:")
            for key, status in checks.items():
                if not status:
                    env_key = f"COS_{key.upper()}"
                    print(f"\n  {key}:")
                    print(f"    - 环境变量: export {env_key}='your_value'")
                    print(f"    - 或在config/weibo_config.py中设置: {env_key} = 'your_value'")
            
            print("\n⚠️  特别提醒：")
            print("  1. 如果通过环境变量设置，需要重启终端或服务")
            print("  2. 如果修改了config文件，需要重启爬虫进程")
            print("  3. 最容易遗漏的是 COS_BUCKET_NAME（必需项）")
        
        # 6. VIP海报保存模式
        print("\n📌 VIP海报保存模式")
        print("-" * 70)
        vip_mode = getattr(config, 'VIP_POSTER_SAVE_MODE', 'local')
        print(f"VIP_POSTER_SAVE_MODE: {vip_mode}")
        
        if vip_mode in ['oss', 'both']:
            if is_configured:
                print("✅ 海报将上传到COS")
            else:
                print("⚠️  海报保存模式设置为OSS，但COS未配置，将跳过上传")
        else:
            print("ℹ️  当前为local模式，不会上传到COS")
        
    except Exception as e:
        print(f"❌ 检查过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    check_cos_config()

