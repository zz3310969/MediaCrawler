# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
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

"""
微信公众号爬虫测试文件

使用方法：
1. 配置 config/base_config.py 中的 PLATFORM = "wechat"
2. 配置 config/wechat_config.py 中的相关参数
3. 运行测试：
   uv run python test/test_wechat.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_import():
    """测试模块导入"""
    print("Testing module imports...")
    
    try:
        from media_platform.wechat import WeChatCrawler
        print("✓ WeChatCrawler imported successfully")
        
        from media_platform.wechat.client import WeChatClient
        print("✓ WeChatClient imported successfully")
        
        from media_platform.wechat.login import WeChatLogin
        print("✓ WeChatLogin imported successfully")
        
        from media_platform.wechat.field import LoginType, CrawlerType
        print("✓ Field enums imported successfully")
        
        from media_platform.wechat.exception import WeChatException
        print("✓ Exceptions imported successfully")
        
        from model.m_wechat import WeChatAccount, WeChatArticle
        print("✓ Models imported successfully")
        
        from store import wechat as wechat_store
        print("✓ Store module imported successfully")
        
        print("\n✓ All imports successful!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Import failed: {e}\n")
        return False


def test_config():
    """测试配置文件"""
    print("Testing configuration...")
    
    try:
        import config
        from config import wechat_config
        
        print(f"  Platform: {config.PLATFORM}")
        print(f"  Login Type: {config.LOGIN_TYPE}")
        print(f"  Crawler Type: {config.CRAWLER_TYPE}")
        print(f"  Save Data Option: {config.SAVE_DATA_OPTION}")
        
        print("\n✓ Configuration loaded successfully!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Configuration test failed: {e}\n")
        return False


def test_factory():
    """测试爬虫工厂"""
    print("Testing CrawlerFactory...")
    
    try:
        from main import CrawlerFactory
        
        # 检查wechat是否在支持的平台列表中
        if "wechat" in CrawlerFactory.CRAWLERS:
            print("✓ WeChat platform registered in CrawlerFactory")
            
            # 尝试创建爬虫实例
            crawler = CrawlerFactory.create_crawler("wechat")
            print(f"✓ WeChatCrawler instance created: {type(crawler).__name__}")
            
            print("\n✓ Factory test successful!\n")
            return True
        else:
            print("✗ WeChat platform not found in CrawlerFactory")
            return False
            
    except Exception as e:
        print(f"\n✗ Factory test failed: {e}\n")
        return False


def test_help_functions():
    """测试辅助函数"""
    print("Testing helper functions...")
    
    try:
        from media_platform.wechat.help import (
            extract_article_url_params,
            extract_fakeid_from_url,
        )
        
        # 测试URL参数提取
        test_url = "https://mp.weixin.qq.com/s?__biz=MzAwNDk4NjkzNw==&mid=2247484567&idx=1&sn=abc123"
        params = extract_article_url_params(test_url)
        
        if params and params.get("__biz") == "MzAwNDk4NjkzNw==":
            print("✓ extract_article_url_params works correctly")
        else:
            print("✗ extract_article_url_params failed")
            return False
        
        # 测试fakeid提取
        fakeid = extract_fakeid_from_url(test_url)
        if fakeid == "MzAwNDk4NjkzNw==":
            print("✓ extract_fakeid_from_url works correctly")
        else:
            print("✗ extract_fakeid_from_url failed")
            return False
        
        print("\n✓ Helper functions test successful!\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Helper functions test failed: {e}\n")
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("WeChat Crawler Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        ("Import Test", test_import),
        ("Configuration Test", test_config),
        ("Factory Test", test_factory),
        ("Helper Functions Test", test_help_functions),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        print("-" * 60)
        result = test_func()
        results.append((test_name, result))
        print()
    
    print("=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

