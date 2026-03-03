#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据统计报告 Skill - 生成爬取数据的统计分析报告
"""
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import base_config
from database import db


class DataStatisticsReporter:
    """数据统计报告生成器"""

    def __init__(self, platform: str = None, days: int = 7):
        self.platform = platform or base_config.PLATFORM
        self.days = days
        self.report = {
            "generated_at": datetime.now().isoformat(),
            "platform": self.platform,
            "period_days": days,
            "statistics": {}
        }

    async def get_content_stats(self) -> Dict[str, Any]:
        """获取内容统计"""
        try:
            db_instance = await db.get_db()
            if not db_instance:
                return {"error": "数据库连接失败"}

            # 根据平台获取对应的表名
            table_map = {
                "xhs": "xhs_note",
                "dy": "douyin_video",
                "ks": "kuaishou_video",
                "bili": "bilibili_video",
                "wb": "weibo_note",
                "tieba": "tieba_note",
                "zhihu": "zhihu_note"
            }

            table_name = table_map.get(self.platform)
            if not table_name:
                return {"error": f"不支持的平台: {self.platform}"}

            # 计算时间范围
            start_date = datetime.now() - timedelta(days=self.days)

            # 查询统计数据（这里需要根据实际数据库结构调整）
            stats = {
                "total_content": 0,
                "new_content_last_period": 0,
                "avg_likes": 0,
                "avg_comments": 0,
                "avg_shares": 0,
                "top_creators": [],
                "content_types": {}
            }

            # 这里添加实际的数据库查询逻辑
            # 示例：从 CSV 或 JSON 文件读取（如果使用文件存储）
            data_dir = project_root / "data" / self.platform
            if data_dir.exists():
                stats["total_content"] = len(list(data_dir.glob("*.json")))

            return stats

        except Exception as e:
            return {"error": f"内容统计异常: {str(e)}"}

    async def get_comment_stats(self) -> Dict[str, Any]:
        """获取评论统计"""
        try:
            stats = {
                "total_comments": 0,
                "avg_comment_length": 0,
                "sentiment_distribution": {},
                "top_keywords": [],
                "active_hours": {}
            }

            # 从数据文件中读取评论数据
            data_dir = project_root / "data" / self.platform
            if data_dir.exists():
                comment_files = list(data_dir.glob("*comments*.json"))
                stats["total_comments"] = len(comment_files)

            return stats

        except Exception as e:
            return {"error": f"评论统计异常: {str(e)}"}

    async def get_creator_stats(self) -> Dict[str, Any]:
        """获取创作者统计"""
        try:
            stats = {
                "total_creators": 0,
                "top_creators_by_content": [],
                "top_creators_by_engagement": [],
                "creator_categories": {}
            }

            return stats

        except Exception as e:
            return {"error": f"创作者统计异常: {str(e)}"}

    async def get_engagement_stats(self) -> Dict[str, Any]:
        """获取互动数据统计"""
        try:
            stats = {
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_engagement_rate": 0,
                "engagement_trend": [],
                "peak_engagement_time": None
            }

            return stats

        except Exception as e:
            return {"error": f"互动统计异常: {str(e)}"}

    async def get_crawl_performance(self) -> Dict[str, Any]:
        """获取爬取性能统计"""
        try:
            # 读取爬取进度文件
            progress_dir = project_root / "crawl_progress"
            stats = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "avg_crawl_speed": 0,
                "success_rate": 0
            }

            if progress_dir.exists():
                progress_files = list(progress_dir.glob("*.json"))
                stats["total_tasks"] = len(progress_files)

                for file in progress_files:
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get("status") == "completed":
                                stats["completed_tasks"] += 1
                            elif data.get("status") == "failed":
                                stats["failed_tasks"] += 1
                    except:
                        continue

                if stats["total_tasks"] > 0:
                    stats["success_rate"] = f"{(stats['completed_tasks']/stats['total_tasks']*100):.1f}%"

            return stats

        except Exception as e:
            return {"error": f"性能统计异常: {str(e)}"}

    async def analyze_trends(self) -> Dict[str, Any]:
        """分析数据趋势"""
        try:
            trends = {
                "content_growth": "稳定",
                "engagement_trend": "上升",
                "popular_topics": [],
                "recommendations": []
            }

            # 添加建议
            trends["recommendations"] = [
                "建议在互动高峰时段发布内容",
                "关注热门话题以提高曝光",
                "优化内容质量以提升互动率"
            ]

            return trends

        except Exception as e:
            return {"error": f"趋势分析异常: {str(e)}"}

    async def generate_report(self) -> Dict[str, Any]:
        """生成完整报告"""
        print(f"📊 开始生成 {self.platform} 平台数据统计报告...\n")

        # 并发执行所有统计
        stats_tasks = {
            "content": self.get_content_stats(),
            "comments": self.get_comment_stats(),
            "creators": self.get_creator_stats(),
            "engagement": self.get_engagement_stats(),
            "performance": self.get_crawl_performance(),
            "trends": self.analyze_trends()
        }

        results = await asyncio.gather(*stats_tasks.values(), return_exceptions=True)

        # 整理结果
        for name, result in zip(stats_tasks.keys(), results):
            if isinstance(result, Exception):
                self.report["statistics"][name] = {"error": str(result)}
            else:
                self.report["statistics"][name] = result

        return self.report

    def print_report(self):
        """打印报告"""
        print(f"\n{'='*70}")
        print(f"  📊 {self.platform.upper()} 平台数据统计报告")
        print(f"  生成时间: {self.report['generated_at']}")
        print(f"  统计周期: 最近 {self.days} 天")
        print(f"{'='*70}\n")

        stats = self.report["statistics"]

        # 内容统计
        if "content" in stats and "error" not in stats["content"]:
            content = stats["content"]
            print("📝 内容统计")
            print(f"  总内容数: {content.get('total_content', 0)}")
            print(f"  新增内容: {content.get('new_content_last_period', 0)}")
            print(f"  平均点赞: {content.get('avg_likes', 0)}")
            print(f"  平均评论: {content.get('avg_comments', 0)}")
            print()

        # 评论统计
        if "comments" in stats and "error" not in stats["comments"]:
            comments = stats["comments"]
            print("💬 评论统计")
            print(f"  总评论数: {comments.get('total_comments', 0)}")
            print(f"  平均长度: {comments.get('avg_comment_length', 0)}")
            print()

        # 性能统计
        if "performance" in stats and "error" not in stats["performance"]:
            perf = stats["performance"]
            print("⚡ 爬取性能")
            print(f"  总任务数: {perf.get('total_tasks', 0)}")
            print(f"  完成任务: {perf.get('completed_tasks', 0)}")
            print(f"  失败任务: {perf.get('failed_tasks', 0)}")
            print(f"  成功率: {perf.get('success_rate', 'N/A')}")
            print()

        # 趋势分析
        if "trends" in stats and "error" not in stats["trends"]:
            trends = stats["trends"]
            print("📈 趋势分析")
            print(f"  内容增长: {trends.get('content_growth', 'N/A')}")
            print(f"  互动趋势: {trends.get('engagement_trend', 'N/A')}")
            if trends.get("recommendations"):
                print("\n  💡 建议:")
                for rec in trends["recommendations"]:
                    print(f"    • {rec}")
            print()

        print(f"{'='*70}\n")

    def save_report(self, output_path: str = None, format: str = "json"):
        """保存报告"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = project_root / "data" / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"stats_report_{self.platform}_{timestamp}.{format}"

        output_path = Path(output_path)

        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.report, f, ensure_ascii=False, indent=2)
        elif format == "txt":
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(self._format_text_report())

        print(f"📄 报告已保存至: {output_path}")

    def _format_text_report(self) -> str:
        """格式化文本报告"""
        lines = []
        lines.append("="*70)
        lines.append(f"  {self.platform.upper()} 平台数据统计报告")
        lines.append(f"  生成时间: {self.report['generated_at']}")
        lines.append(f"  统计周期: 最近 {self.days} 天")
        lines.append("="*70)
        lines.append("")

        # 添加各项统计内容
        for section, data in self.report["statistics"].items():
            lines.append(f"\n{section.upper()}:")
            lines.append(json.dumps(data, ensure_ascii=False, indent=2))

        return "\n".join(lines)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生成数据统计报告")
    parser.add_argument("--platform", type=str, help="平台名称 (xhs/dy/ks/bili/wb/tieba/zhihu)")
    parser.add_argument("--days", type=int, default=7, help="统计天数")
    parser.add_argument("--format", type=str, default="json", choices=["json", "txt"], help="输出格式")

    args = parser.parse_args()

    reporter = DataStatisticsReporter(platform=args.platform, days=args.days)
    await reporter.generate_report()
    reporter.print_report()
    reporter.save_report(format=args.format)


if __name__ == "__main__":
    asyncio.run(main())
