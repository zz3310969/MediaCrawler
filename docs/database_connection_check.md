# 数据库连接验证功能

## 功能说明

为了提前发现数据库配置问题，项目在启动时会自动验证数据库连接是否正常。这样可以避免爬取到一半才发现数据库无法连接的情况。

## 功能特性

### 1. 命令行模式启动验证

当使用数据库存储模式（`db`、`sqlite`、`mysql`、`postgres`）时，在 `main.py` 启动时会自动验证数据库连接：

```bash
python main.py --platform xhs --lt qrcode --type search
```

**成功时的输出：**
```
[Main] 正在验证数据库连接...
[verify_connection] 正在验证 sqlite 数据库连接...
[verify_connection] 连接地址: sqlite:///Users/xxx/MediaCrawler/database/sqlite_tables.db
[verify_connection] sqlite 数据库连接验证成功 ✓
[Main] ✓ 数据库连接验证成功
```

**失败时的输出：**
```
[Main] 正在验证数据库连接...
[verify_connection] 正在验证 mysql 数据库连接...
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
[verify_connection] mysql 数据库连接验证失败: Can't connect to MySQL server on 'localhost'
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
[Main] ❌ 数据库连接失败，请检查数据库配置和连接状态
[Main] 当前数据库类型: db
```

> 注意：连接地址中的密码会被替换为 `****` 以保护敏感信息。

失败时程序会提前终止，不会开始爬取任务。

### 2. API 服务启动验证

当启动 WebUI API 服务时，也会验证数据库连接。

**使用配置文件的数据库设置：**
```bash
python -m api.main
# 或
uvicorn api.main:app --port 8080
```

**使用命令行参数指定数据库类型：**
```bash
python -m api.main --save_data_option db
# 或指定其他数据库
python -m api.main --save_data_option sqlite
python -m api.main --save_data_option postgres
```

**成功时的输出：**
```
[API] MediaCrawler WebUI API 正在启动...
[API] 已应用命令行参数
[API] 正在验证数据库连接...
[verify_connection] 正在验证 sqlite 数据库连接...
[verify_connection] 连接地址: sqlite:///Users/xxx/MediaCrawler/database/sqlite_tables.db
[verify_connection] sqlite 数据库连接验证成功 ✓
[API] ✓ 数据库连接验证成功
[API] ✓ API 服务启动完成
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**失败时的输出：**
```
[API] MediaCrawler WebUI API 正在启动...
[API] 已应用命令行参数
[API] 正在验证数据库连接...
[verify_connection] 正在验证 mysql 数据库连接...
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
[verify_connection] mysql 数据库连接验证失败: Connection refused
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
[API] ⚠️  数据库连接失败，请检查数据库配置和连接状态
[API] 当前数据库类型: db
[API] API 服务将继续启动，但数据存储功能可能不可用
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

> 注意：API 服务在数据库连接失败时会继续启动，但数据存储功能可能不可用。

### 3. 手动测试数据库连接

可以使用提供的测试脚本来手动测试数据库连接：

```bash
python test_db_connection.py
```

**输出示例（成功）：**
```
============================================================
数据库连接测试
============================================================

当前配置的存储方式: sqlite

正在测试 sqlite 数据库连接...
[verify_connection] 正在验证 sqlite 数据库连接...
[verify_connection] 连接地址: sqlite:///Users/xxx/MediaCrawler/database/sqlite_tables.db
[verify_connection] sqlite 数据库连接验证成功 ✓
✓ 数据库连接成功!
✓ 可以正常使用 sqlite 数据库存储数据

============================================================
测试通过 ✓
============================================================
```

**输出示例（失败）：**
```
============================================================
数据库连接测试
============================================================

当前配置的存储方式: db

正在测试 db 数据库连接...
[verify_connection] 正在验证 db 数据库连接...
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
[verify_connection] db 数据库连接验证失败: (2003, "Can't connect to MySQL server...")
[verify_connection] 连接地址: mysql://root:****@localhost:3306/media_crawler
✗ 数据库连接失败!
✗ 请检查以下配置:
  - 主机: localhost:3306
  - 用户: root
  - 数据库: media_crawler

============================================================
测试失败 ✗
============================================================
```

### 4. API 端点检查

API 服务提供了一个端点用于检查数据库连接状态：

```bash
curl http://localhost:8080/api/db/check
```

**响应示例（连接成功）：**
```json
{
  "success": true,
  "db_type": "sqlite",
  "message": "sqlite 数据库连接正常",
  "need_db": true
}
```

**响应示例（连接失败）：**
```json
{
  "success": false,
  "db_type": "mysql",
  "message": "mysql 数据库连接失败，请检查配置",
  "need_db": true
}
```

**响应示例（文件存储模式）：**
```json
{
  "success": true,
  "db_type": "json",
  "message": "当前使用文件存储模式 (json)，无需数据库连接",
  "need_db": false
}
```

## 适用的存储模式

验证功能会在以下存储模式下启用：
- `db` (MySQL)
- `mysql` (MySQL)
- `sqlite` (SQLite)
- `postgres` (PostgreSQL)

以下模式无需验证（使用文件存储）：
- `json`
- `csv`
- `excel`
- `mongodb` (暂不支持自动验证)

## 配置检查清单

如果数据库连接失败，请检查以下配置：

### SQLite
- 检查文件路径是否正确
- 检查目录是否有写入权限

### MySQL
在 `config/db_config.py` 或环境变量中检查：
- `MYSQL_DB_HOST`: 数据库主机地址
- `MYSQL_DB_PORT`: 数据库端口（默认 3306）
- `MYSQL_DB_USER`: 数据库用户名
- `MYSQL_DB_PWD`: 数据库密码
- `MYSQL_DB_NAME`: 数据库名称

确保 MySQL 服务已启动：
```bash
# macOS
brew services start mysql

# Linux
sudo systemctl start mysql

# Windows
net start mysql
```

### PostgreSQL
在 `config/db_config.py` 或环境变量中检查：
- `POSTGRES_DB_HOST`: 数据库主机地址
- `POSTGRES_DB_PORT`: 数据库端口（默认 5432）
- `POSTGRES_DB_USER`: 数据库用户名
- `POSTGRES_DB_PWD`: 数据库密码
- `POSTGRES_DB_NAME`: 数据库名称

确保 PostgreSQL 服务已启动：
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql

# Windows
net start postgresql
```

## 技术实现

数据库连接验证通过 `database/db.py` 中的 `verify_connection()` 函数实现：

```python
async def verify_connection(db_type: str = None) -> bool:
    """
    验证数据库连接是否正常
    Args:
        db_type: 数据库类型，如果为 None 则使用配置中的类型
    Returns:
        bool: 连接成功返回 True，否则返回 False
    """
    # 实现细节...
```

该函数会：
1. 获取数据库配置信息
2. 打印数据库连接地址（密码已隐藏为 `****`）
3. 获取数据库引擎
4. 执行简单的 `SELECT 1` 查询
5. 根据结果返回连接状态

### 连接地址格式

不同数据库类型的连接地址格式：

- **SQLite**: `sqlite:///path/to/database.db`
- **MySQL**: `mysql://user:****@host:port/database`
- **PostgreSQL**: `postgresql://user:****@host:port/database`

密码部分始终显示为 `****`，保护敏感信息不被泄露到日志中。

## 常见问题

### Q: 为什么 API 服务连接失败还会继续启动？
A: API 服务需要保持可用性，即使数据库连接失败，用户仍然可以使用 WebUI 修改配置或查看其他信息。只是数据存储功能可能不可用。

### Q: API 服务如何指定数据库类型？
A: 有两种方式：
1. **在配置文件中设置**：修改 `config/base_config.py` 中的 `SAVE_DATA_OPTION` 参数
2. **使用命令行参数**：启动时添加 `--save_data_option` 参数
   ```bash
   python -m api.main --save_data_option db
   ```

### Q: 为什么我设置了 `--save_data_option db` 但没有验证数据库？
A: 请确保：
1. 使用的是新版本的代码（已修复此问题）
2. 启动命令包含参数，例如：`python -m api.main --save_data_option db`
3. 查看启动日志中是否有 `[API] 已应用命令行参数` 的提示

### Q: 可以跳过数据库验证吗？
A: 目前不支持跳过验证。这是为了确保数据不会因为连接问题而丢失。如果不需要数据库，可以改用文件存储模式（json/csv/excel）。

### Q: 验证失败但我确定配置是对的，怎么办？
A: 请检查：
1. 数据库服务是否已启动
2. 网络连接是否正常
3. 防火墙设置是否正确
4. 数据库用户权限是否足够
5. 查看详细的错误日志信息

### Q: 看到 DeprecationWarning about `on_event` 怎么办？
A: 这个警告已经在新版本中修复，现在使用了 FastAPI 推荐的 `lifespan` 事件处理器。更新到最新版本即可消除此警告。

## 相关文件

- `database/db.py`: 数据库验证核心实现
- `main.py`: 命令行模式启动验证
- `api/main.py`: API 服务启动验证
- `test_db_connection.py`: 独立测试脚本
- `config/db_config.py`: 数据库配置

