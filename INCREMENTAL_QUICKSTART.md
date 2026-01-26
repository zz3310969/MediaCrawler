# 🚀 增量爬取 - 2分钟快速开始

> **📢 重要提示**: V2 版本无需数据库迁移即可使用！

## 第一步：启用增量爬取

编辑 `config/base_config.py`，找到增量爬取配置部分：

```python
# ==================== 增量爬取配置 ====================
# 将 False 改为 True
ENABLE_INCREMENTAL_CRAWL = True  # ← 这里改成 True

# 早停阈值（可选，默认3即可）
CREATOR_EARLY_STOP_THRESHOLD = 3
```

保存文件。

---

## 第二步：开始爬取

正常运行爬虫：

```bash
python main.py
```

---

## 第三步：查看效果

### 首次运行

会看到类似日志：
```
[XiaoHongShuCrawler] 增量爬取已启用 - 创作者早停模式 (阈值: 3)
[CreatorIncremental] 创作者 XXX 首次爬取，将处理所有笔记
[CreatorIncremental] 创作者 XXX 统计: 总计=1000, 新增=1000, 已跳过=0
[CreatorIncremental] 📝 创建元数据: 创作者=XXX, 最新笔记=note_999, 本次新增=1000
```

### 第二次运行（看到效果！）

```
[XiaoHongShuCrawler] 增量爬取已启用 - 创作者早停模式 (阈值: 3)
[CreatorIncremental] 创作者 XXX 上次最新笔记: note_999 标题: ... 
[CreatorIncremental] ✨ 发现新笔记: note_1001 (新标题...)
[CreatorIncremental] ✨ 发现新笔记: note_1000 (新标题...)
[CreatorIncremental] 🛑 停止爬取创作者 XXX (连续 3 条笔记已存在，剩余 997 条已跳过)
[CreatorIncremental] 创作者 XXX 统计: 总计=1000, 新增=2, 已跳过=998
[CreatorIncremental] 📊 更新元数据: 创作者=XXX, 最新笔记=note_1001, 本次新增=2
```

**效率提升：1000条 → 2条 = 500倍！** ⚡

---

## ⭐ V2 新特性

### 无需数据库迁移！

V2 版本已经**不再强制要求**创建 `incremental_metadata` 表：

- ✅ **DB 模式**：直接查询 `xhs_note` 表
- ✅ **JSON 模式**：扫描 JSON 文件
- ✅ **CSV 模式**：读取 CSV 文件

**开箱即用，无需额外配置！**

### 可选的性能优化

如果你是大规模爬取（创作者 > 1000），可以执行迁移以获得更好性能：

```bash
python database/migrations/migrate_incremental.py
```

这会创建一个带索引的元数据表，加速查询。**但这是完全可选的！**

---

## 常见问题

### Q: 我已经爬取过数据了，现在启用增量会怎样？

A: 完全没问题！系统会自动从数据库查询已有的最新笔记作为基准，后续只爬取新内容。

### Q: 如何重新全量爬取某个创作者？

A: 删除该创作者的增量记录即可：

```sql
DELETE FROM incremental_metadata 
WHERE platform='xhs' 
  AND crawler_type='creator' 
  AND target_key='创作者ID';
```

### Q: 如何临时禁用增量？

A: 两种方法：
1. 配置文件改回 `ENABLE_INCREMENTAL_CRAWL = False`
2. 在 `main.py` 开头添加：
   ```python
   import config
   config.ENABLE_INCREMENTAL_CRAWL = False
   ```

### Q: JSON 存储可以用增量吗？

A: **当然可以！** V2 版本完美支持 JSON 存储的增量爬取：

```python
# config/base_config.py
SAVE_DATA_OPTION = "json"
ENABLE_INCREMENTAL_CRAWL = True
```

系统会自动扫描 `data/xhs/json/` 目录，找出最新笔记，然后增量爬取。

### Q: CSV 存储可以用增量吗？

A: **可以！** V2 版本也支持 CSV 存储：

```python
# config/base_config.py
SAVE_DATA_OPTION = "csv"
ENABLE_INCREMENTAL_CRAWL = True
```

---

## 更多帮助

- 🎉 **V2 重大更新**: `INCREMENTAL_UPDATE_V2.md` ← 必读！
- 📘 **详细使用指南**: `docs/incremental_crawl_guide.md`
- 📗 **V1 功能说明**: `INCREMENTAL_CRAWL_CHANGELOG.md`
- 💬 **遇到问题**: 查看日志中的 `[CreatorIncremental]` 相关信息

---

**就是这么简单！享受高效爬取** 🎉

