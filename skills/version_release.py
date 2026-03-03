#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
版本发布 Skill - 自动化版本发布流程
"""
import sys
import re
import subprocess
from pathlib import Path
from typing import Optional, List
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class VersionReleaser:
    """版本发布管理器"""

    def __init__(self):
        self.project_root = project_root
        self.pyproject_path = self.project_root / "pyproject.toml"
        self.changelog_path = self.project_root / "CHANGELOG.md"
        self.current_version = self._get_current_version()

    def _get_current_version(self) -> str:
        """获取当前版本号"""
        try:
            with open(self.pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
                match = re.search(r'version\s*=\s*"([^"]+)"', content)
                if match:
                    return match.group(1)
        except Exception as e:
            print(f"❌ 读取版本号失败: {e}")
        return "0.0.0"

    def _bump_version(self, bump_type: str = "patch") -> str:
        """递增版本号"""
        parts = self.current_version.split('.')
        major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"不支持的版本类型: {bump_type}")

        return f"{major}.{minor}.{patch}"

    def _update_pyproject_version(self, new_version: str) -> bool:
        """更新 pyproject.toml 中的版本号"""
        try:
            with open(self.pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = re.sub(
                r'version\s*=\s*"[^"]+"',
                f'version = "{new_version}"',
                content
            )

            with open(self.pyproject_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"✅ 已更新 pyproject.toml: {self.current_version} → {new_version}")
            return True

        except Exception as e:
            print(f"❌ 更新版本号失败: {e}")
            return False

    def _get_recent_commits(self, count: int = 10) -> List[str]:
        """获取最近的提交记录"""
        try:
            result = subprocess.run(
                ["git", "log", f"-{count}", "--pretty=format:%s"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return result.stdout.strip().split('\n')
        except Exception as e:
            print(f"⚠️ 获取提交记录失败: {e}")
        return []

    def _categorize_commits(self, commits: List[str]) -> dict:
        """分类提交记录"""
        categories = {
            "features": [],
            "fixes": [],
            "docs": [],
            "refactor": [],
            "others": []
        }

        for commit in commits:
            commit = commit.strip()
            if not commit:
                continue

            if re.match(r'^feat(\(.+\))?:', commit, re.IGNORECASE):
                categories["features"].append(commit)
            elif re.match(r'^fix(\(.+\))?:', commit, re.IGNORECASE):
                categories["fixes"].append(commit)
            elif re.match(r'^docs?(\(.+\))?:', commit, re.IGNORECASE):
                categories["docs"].append(commit)
            elif re.match(r'^refactor(\(.+\))?:', commit, re.IGNORECASE):
                categories["refactor"].append(commit)
            else:
                categories["others"].append(commit)

        return categories

    def _generate_changelog_entry(self, version: str, commits: List[str]) -> str:
        """生成 CHANGELOG 条目"""
        date = datetime.now().strftime('%Y-%m-%d')
        lines = [
            f"\n## [{version}] - {date}\n"
        ]

        categories = self._categorize_commits(commits)

        if categories["features"]:
            lines.append("\n### ✨ 新功能\n")
            for commit in categories["features"]:
                lines.append(f"- {commit}\n")

        if categories["fixes"]:
            lines.append("\n### 🐛 Bug 修复\n")
            for commit in categories["fixes"]:
                lines.append(f"- {commit}\n")

        if categories["refactor"]:
            lines.append("\n### ♻️ 重构\n")
            for commit in categories["refactor"]:
                lines.append(f"- {commit}\n")

        if categories["docs"]:
            lines.append("\n### 📝 文档\n")
            for commit in categories["docs"]:
                lines.append(f"- {commit}\n")

        if categories["others"]:
            lines.append("\n### 🔧 其他变更\n")
            for commit in categories["others"]:
                lines.append(f"- {commit}\n")

        return "".join(lines)

    def _update_changelog(self, new_version: str, commits: List[str]) -> bool:
        """更新 CHANGELOG.md"""
        try:
            # 生成新条目
            new_entry = self._generate_changelog_entry(new_version, commits)

            # 读取现有内容
            if self.changelog_path.exists():
                with open(self.changelog_path, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            else:
                existing_content = "# 更新日志\n\n所有重要的项目变更都会记录在此文件中。\n"

            # 插入新条目（在标题后）
            parts = existing_content.split('\n', 3)
            if len(parts) >= 3:
                new_content = '\n'.join(parts[:3]) + new_entry + '\n' + (parts[3] if len(parts) > 3 else '')
            else:
                new_content = existing_content + new_entry

            # 写入文件
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"✅ 已更新 CHANGELOG.md")
            return True

        except Exception as e:
            print(f"❌ 更新 CHANGELOG 失败: {e}")
            return False

    def _create_git_tag(self, version: str, message: str = None) -> bool:
        """创建 Git 标签"""
        try:
            tag_name = f"v{version}"
            tag_message = message or f"Release version {version}"

            # 创建标签
            result = subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ 已创建 Git 标签: {tag_name}")
                return True
            else:
                print(f"❌ 创建标签失败: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ 创建标签异常: {e}")
            return False

    def _git_commit(self, message: str) -> bool:
        """提交 Git 更改"""
        try:
            # 添加文件
            subprocess.run(
                ["git", "add", str(self.pyproject_path), str(self.changelog_path)],
                cwd=self.project_root,
                check=True
            )

            # 提交
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                print(f"✅ 已提交更改: {message}")
                return True
            else:
                print(f"⚠️ 提交失败或无更改: {result.stderr}")
                return False

        except Exception as e:
            print(f"❌ Git 提交异常: {e}")
            return False

    def release(self, bump_type: str = "patch", dry_run: bool = False, push: bool = False) -> bool:
        """执行版本发布"""
        print(f"\n🚀 开始版本发布流程...\n")
        print(f"当前版本: {self.current_version}")

        # 计算新版本号
        new_version = self._bump_version(bump_type)
        print(f"新版本: {new_version}")
        print(f"发布类型: {bump_type}")
        print(f"模式: {'演习模式 (不会实际修改)' if dry_run else '正式发布'}\n")

        if dry_run:
            print("📋 演习模式 - 将执行以下操作:")
            print(f"  1. 更新 pyproject.toml: {self.current_version} → {new_version}")
            print(f"  2. 更新 CHANGELOG.md")
            print(f"  3. 提交更改: chore: release v{new_version}")
            print(f"  4. 创建标签: v{new_version}")
            if push:
                print(f"  5. 推送到远程仓库")
            print("\n✅ 演习完成，未实际修改任何文件")
            return True

        # 获取最近的提交
        commits = self._get_recent_commits(20)

        # 1. 更新版本号
        if not self._update_pyproject_version(new_version):
            return False

        # 2. 更新 CHANGELOG
        if not self._update_changelog(new_version, commits):
            return False

        # 3. 提交更改
        commit_message = f"chore: release v{new_version}"
        if not self._git_commit(commit_message):
            print("⚠️ 提交失败，但版本文件已更新")

        # 4. 创建标签
        if not self._create_git_tag(new_version):
            print("⚠️ 标签创建失败")

        # 5. 推送（可选）
        if push:
            try:
                print("\n📤 推送到远程仓库...")
                subprocess.run(["git", "push"], cwd=self.project_root, check=True)
                subprocess.run(["git", "push", "--tags"], cwd=self.project_root, check=True)
                print("✅ 已推送到远程仓库")
            except Exception as e:
                print(f"❌ 推送失败: {e}")
                print("💡 请手动执行: git push && git push --tags")

        print(f"\n🎉 版本发布完成！")
        print(f"\n📦 发布信息:")
        print(f"  版本: v{new_version}")
        print(f"  标签: v{new_version}")
        print(f"  提交: {commit_message}")

        if not push:
            print(f"\n💡 提示: 使用 --push 参数可自动推送到远程仓库")

        return True


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="自动化版本发布")
    parser.add_argument(
        "bump_type",
        nargs='?',
        default="patch",
        choices=["major", "minor", "patch"],
        help="版本递增类型 (major: 1.0.0, minor: 0.1.0, patch: 0.0.1)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="演习模式，不实际修改文件"
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="自动推送到远程仓库"
    )

    args = parser.parse_args()

    releaser = VersionReleaser()
    releaser.release(
        bump_type=args.bump_type,
        dry_run=args.dry_run,
        push=args.push
    )


if __name__ == "__main__":
    main()
