#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
健康检查 Skill - 检查系统各组件状态
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import base_config
from account.account_pool import AccountPool


class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {}
        }

    async def check_database(self) -> Dict[str, Any]:
        """检查数据库连接"""
        try:
            save_option = base_config.SAVE_DATA_OPTION

            # 检查数据库配置
            if save_option in ["csv", "json"]:
                return {
                    "status": "healthy",
                    "type": save_option,
                    "message": f"使用文件存储模式: {save_option}"
                }
            elif save_option in ["db", "mysql"]:
                # 检查 MySQL 配置
                if hasattr(base_config, 'RELATION_DB_PWD') and base_config.RELATION_DB_PWD:
                    return {
                        "status": "healthy",
                        "type": "mysql",
                        "message": "MySQL 配置正常"
                    }
                else:
                    return {
                        "status": "warning",
                        "message": "MySQL 未配置密码"
                    }
            elif save_option == "sqlite":
                db_path = Path(project_root) / "data" / "media_crawler.db"
                if db_path.exists():
                    return {
                        "status": "healthy",
                        "type": "sqlite",
                        "message": f"SQLite 数据库存在: {db_path}"
                    }
                else:
                    return {
                        "status": "warning",
                        "message": "SQLite 数据库文件不存在，需要初始化"
                    }
            else:
                return {
                    "status": "healthy",
                    "type": save_option,
                    "message": f"存储模式: {save_option}"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"数据库检查异常: {str(e)}"
            }

    async def check_proxy_pool(self) -> Dict[str, Any]:
        """检查代理池状态"""
        if not base_config.ENABLE_IP_PROXY:
            return {
                "status": "disabled",
                "message": "代理池未启用"
            }

        try:
            # 检查代理配置文件
            proxy_config_path = project_root / "config" / "proxy_config.yaml"
            if not proxy_config_path.exists():
                return {
                    "status": "warning",
                    "message": "代理配置文件不存在"
                }

            # 检查代理数据文件
            proxy_data_path = project_root / "data" / "proxies.json"
            if proxy_data_path.exists():
                import json
                with open(proxy_data_path, 'r') as f:
                    proxies = json.load(f)
                    total = len(proxies)
                    return {
                        "status": "healthy",
                        "total_proxies": total,
                        "message": f"代理池配置正常，已保存 {total} 个代理"
                    }
            else:
                return {
                    "status": "warning",
                    "message": "代理池已启用但无代理数据"
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"代理池检查异常: {str(e)}"
            }

    async def check_account_pool(self) -> Dict[str, Any]:
        """检查账号池状态"""
        try:
            account_pool = AccountPool(base_config.PLATFORM)
            await account_pool.load_accounts()

            total = len(account_pool.accounts)
            available = sum(1 for acc in account_pool.accounts if acc.get("status") != "banned")

            status = "healthy" if available > 0 else "critical"

            return {
                "status": status,
                "platform": base_config.PLATFORM,
                "total_accounts": total,
                "available_accounts": available,
                "message": f"账号池正常，可用账号: {available}/{total}"
            }
        except Exception as e:
            return {
                "status": "warning",
                "message": f"账号池检查异常: {str(e)}"
            }

    async def check_storage_space(self) -> Dict[str, Any]:
        """检查存储空间"""
        try:
            import shutil

            data_dir = project_root / "data"
            if not data_dir.exists():
                data_dir.mkdir(parents=True)

            total, used, free = shutil.disk_usage(data_dir)

            free_gb = free / (1024**3)
            total_gb = total / (1024**3)
            usage_percent = (used / total) * 100

            status = "healthy" if free_gb > 1 else "warning"

            return {
                "status": status,
                "free_space_gb": f"{free_gb:.2f}",
                "total_space_gb": f"{total_gb:.2f}",
                "usage_percent": f"{usage_percent:.1f}%",
                "message": f"存储空间充足，剩余 {free_gb:.2f}GB"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"存储空间检查异常: {str(e)}"
            }

    async def check_browser_data(self) -> Dict[str, Any]:
        """检查浏览器数据目录"""
        try:
            browser_dir = project_root / "browser_data"

            if not browser_dir.exists():
                return {
                    "status": "warning",
                    "message": "浏览器数据目录不存在"
                }

            platforms = [d.name for d in browser_dir.iterdir() if d.is_dir()]

            return {
                "status": "healthy",
                "cached_platforms": platforms,
                "count": len(platforms),
                "message": f"已缓存 {len(platforms)} 个平台的登录态"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"浏览器数据检查异常: {str(e)}"
            }

    async def check_config(self) -> Dict[str, Any]:
        """检查配置文件"""
        try:
            issues = []

            # 检查必要配置
            if not base_config.PLATFORM:
                issues.append("未设置目标平台")

            if base_config.ENABLE_IP_PROXY and not hasattr(base_config, 'IP_PROXY_POOL_COUNT'):
                issues.append("启用了代理但未配置代理池")

            if base_config.CRAWLER_MAX_NOTES_COUNT <= 0:
                issues.append("爬取数量配置异常")

            status = "healthy" if not issues else "warning"

            return {
                "status": status,
                "platform": base_config.PLATFORM,
                "crawler_type": base_config.CRAWLER_TYPE,
                "issues": issues,
                "message": "配置正常" if not issues else f"发现 {len(issues)} 个配置问题"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"配置检查异常: {str(e)}"
            }

    async def run_all_checks(self) -> Dict[str, Any]:
        """运行所有健康检查"""
        print("🏥 开始系统健康检查...\n")

        checks = {
            "配置文件": self.check_config(),
            "数据库": self.check_database(),
            "代理池": self.check_proxy_pool(),
            "账号池": self.check_account_pool(),
            "存储空间": self.check_storage_space(),
            "浏览器缓存": self.check_browser_data(),
        }

        # 并发执行所有检查
        results = await asyncio.gather(*checks.values(), return_exceptions=True)

        # 整理结果
        for name, result in zip(checks.keys(), results):
            if isinstance(result, Exception):
                self.results["checks"][name] = {
                    "status": "error",
                    "message": str(result)
                }
            else:
                self.results["checks"][name] = result

        # 计算总体状态
        statuses = [check["status"] for check in self.results["checks"].values()]
        if "critical" in statuses or "error" in statuses:
            self.results["overall_status"] = "unhealthy"
        elif "warning" in statuses:
            self.results["overall_status"] = "warning"

        return self.results

    def print_results(self):
        """打印检查结果"""
        status_emoji = {
            "healthy": "✅",
            "warning": "⚠️",
            "unhealthy": "❌",
            "critical": "🔴",
            "error": "💥",
            "disabled": "⏸️"
        }

        print(f"\n{'='*60}")
        print(f"  系统健康检查报告")
        print(f"  时间: {self.results['timestamp']}")
        print(f"  总体状态: {status_emoji.get(self.results['overall_status'], '❓')} {self.results['overall_status'].upper()}")
        print(f"{'='*60}\n")

        for name, check in self.results["checks"].items():
            status = check.get("status", "unknown")
            emoji = status_emoji.get(status, "❓")
            print(f"{emoji} {name}: {status.upper()}")
            print(f"   {check.get('message', '无详细信息')}")

            # 打印额外信息
            for key, value in check.items():
                if key not in ["status", "message"]:
                    print(f"   - {key}: {value}")
            print()

        print(f"{'='*60}\n")

    def save_report(self, output_path: str = None):
        """保存检查报告"""
        if output_path is None:
            output_path = project_root / "data" / f"health_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"📄 报告已保存至: {output_path}")


async def main():
    """主函数"""
    checker = HealthChecker()
    await checker.run_all_checks()
    checker.print_results()
    checker.save_report()


if __name__ == "__main__":
    asyncio.run(main())
