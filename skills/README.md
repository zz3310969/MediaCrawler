# MediaCrawler Skills

项目自动化工具集，提供健康检查、数据统计和版本发布等功能。

## 📋 可用 Skills

### 1. 🏥 健康检查 (health_check.py)

检查系统各组件的运行状态，包括数据库、代理池、账号池、存储空间等。

**使用方法:**
```bash
# 运行健康检查
uv run python skills/health_check.py
```

**检查项目:**
- ✅ 配置文件验证
- ✅ 数据库连接状态
- ✅ 代理池状态（可用代理数量）
- ✅ 账号池状态（可用账号数量）
- ✅ 存储空间检查
- ✅ 浏览器缓存状态

**输出:**
- 终端彩色报告
- JSON 格式报告文件（保存在 `data/` 目录）

---

### 2. 📊 数据统计报告 (data_statistics.py)

生成爬取数据的统计分析报告，包括内容统计、评论分析、创作者排行等。

**使用方法:**
```bash
# 生成默认平台的统计报告（最近7天）
uv run python skills/data_statistics.py

# 指定平台和时间范围
uv run python skills/data_statistics.py --platform xhs --days 30

# 指定输出格式
uv run python skills/data_statistics.py --platform dy --format txt
```

**参数说明:**
- `--platform`: 平台名称 (xhs/dy/ks/bili/wb/tieba/zhihu)
- `--days`: 统计天数（默认7天）
- `--format`: 输出格式 (json/txt)

**统计内容:**
- 📝 内容统计（总数、新增、平均互动）
- 💬 评论统计（数量、长度、情感分析）
- 👥 创作者统计（排行榜、分类）
- 📈 互动数据（点赞、评论、分享趋势）
- ⚡ 爬取性能（成功率、��度）
- 🔮 趋势分析和建议

**输出:**
- 终端格式化报告
- JSON/TXT 报告文件（保存在 `data/reports/` 目录）

---

### 3. 🚀 版本发布 (version_release.py)

自动化版本发布流程，包括版本号递增、CHANGELOG 生成、Git 标签创建等。

**使用方法:**
```bash
# 演习模式（不实际修改文件）
uv run python skills/version_release.py patch --dry-run

# 发布 patch 版本（0.0.1）
uv run python skills/version_release.py patch

# 发布 minor 版本（0.1.0）
uv run python skills/version_release.py minor

# 发布 major 版本（1.0.0）
uv run python skills/version_release.py major

# 发布并自动推送到远程仓库
uv run python skills/version_release.py patch --push
```

**版本类型:**
- `major`: 主版本号 (1.0.0 → 2.0.0)
- `minor`: 次版本号 (1.0.0 → 1.1.0)
- `patch`: 修订号 (1.0.0 → 1.0.1)

**执行流程:**
1. 📝 更新 `pyproject.toml` 中的版本号
2. 📋 自动生成 CHANGELOG 条目（基于 Git 提交记录）
3. 💾 提交更改到 Git
4. 🏷️ 创建 Git 标签
5. 📤 推送到远程仓库（可选）

**CHANGELOG 自动分类:**
- ✨ 新功能 (feat:)
- 🐛 Bug 修复 (fix:)
- ♻️ 重构 (refactor:)
- 📝 文档 (docs:)
- 🔧 其他变更

---

## 🎯 使用场景

### 日常开发
```bash
# 每天开始工作前检查系统状态
uv run python skills/health_check.py

# 开发完成后生成数据报告
uv run python skills/data_statistics.py --platform xhs
```

### 版本发布
```bash
# 1. 先演习一遍
uv run python skills/version_release.py patch --dry-run

# 2. 确认无误后正式发布
uv run python skills/version_release.py patch

# 3. 推送到远程
git push && git push --tags
# 或者直接使用 --push 参数自动推送
```

### CI/CD 集成
```yaml
# GitHub Actions 示例
- name: Health Check
  run: uv run python skills/health_check.py

- name: Generate Stats
  run: uv run python skills/data_statistics.py --format json
```

---

## 📦 依赖

所有 skills 使用项目现有依赖，无需额外安装。

---

## 🔧 自定义

每个 skill 都可以根据项目需求进行定制：

- **health_check.py**: 添加更多检查项（如 API 健康、第三方服务状态）
- **data_statistics.py**: 扩展统计维度（如地域分析、时段分析）
- **version_release.py**: 自定义发布流程（如自动构建 Docker 镜像）

---

## 💡 提示

1. 建议在 `.gitignore` 中添加 `data/health_check_*.json` 和 `data/reports/`
2. 可以将 skills 集成到 WebUI 中，提供可视化界面
3. 使用 cron 定时执行健康检查和数据统计

---

## 📝 TODO

- [ ] 添加邮件/钉钉通知功能
- [ ] 集成到 WebUI Dashboard
- [ ] 支持更多数据可视化图表
- [ ] 添加性能基准测试 skill
- [ ] 支持自动化测试 skill
