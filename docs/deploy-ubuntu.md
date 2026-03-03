# MediaCrawler Ubuntu 22.04 云服务器部署指南

## 目录

- [环境要求](#环境要求)
- [第一步：系统基础配置](#第一步系统基础配置)
- [第二步：安装 Python 环境](#第二步安装-python-环境)
- [第三步：安装 Node.js](#第三步安装-nodejs)
- [第四步：部署项目](#第四步部署项目)
- [第五步：安装 Playwright 浏览器](#第五步安装-playwright-浏览器)
- [第六步：配置数据库](#第六步配置数据库)
- [第七步：构建 WebUI 前端](#第七步构建-webui-前端)
- [第八步：修改配置文件](#第八步修改配置文件)
- [第九步：启动服务](#第九步启动服务)
- [第十步：配置 systemd 守护进程](#第十步配置-systemd-守护进程)
- [第十一步：配置 Nginx 反向代理（可选）](#第十一步配置-nginx-反向代理可选)
- [常见问题排查](#常见问题排查)
- [Docker 部署方案（替代方案）](#docker-部署方案替代方案)

---

## 环境要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Ubuntu 22.04 LTS |
| 内存 | >= 2GB（推荐 4GB，Chromium 比较吃内存） |
| 磁盘 | >= 10GB |
| Python | >= 3.11 |
| Node.js | >= 16（仅构建前端和签名需要） |
| 网络 | 需要访问目标社媒平台 |

---

## 第一步：系统基础配置

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y \
    curl \
    wget \
    git \
    build-essential \
    software-properties-common \
    unzip \
    ca-certificates \
    gnupg

# 安装 Chromium 运行所需的系统库（关键！）
# 这些是 Playwright Chromium 在无桌面 Linux 上运行的必要依赖
sudo apt install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2

# 安装中文字体支持（词云和页面渲染需要）
sudo apt install -y fonts-noto-cjk fonts-wqy-zenhei
```

---

## 第二步：安装 Python 环境

项目要求 Python >= 3.11，Ubuntu 22.04 默认是 Python 3.10，需要手动安装。

```bash
# 添加 deadsnakes PPA
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# 安装 Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev

# 验证
python3.11 --version

# 安装 uv（推荐的 Python 包管理器）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 让 uv 命令立即可用
source $HOME/.local/bin/env  # 或重新登录 shell

# 验证
uv --version
```

---

## 第三步：安装 Node.js

```bash
# 安装 Node.js 20 LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 验证
node --version
npm --version
```

---

## 第四步：部署项目

```bash
# 创建部署目录
sudo mkdir -p /opt/mediacrawler
sudo chown $USER:$USER /opt/mediacrawler

# 方式一：从 Git 克隆（推荐）
cd /opt
git clone <你的仓库地址> mediacrawler
cd mediacrawler

# 方式二：从本地上传（如果是私有项目）
# 在本地执行：
# rsync -avz --exclude='node_modules' --exclude='.venv' --exclude='__pycache__' \
#   ./ user@server:/opt/mediacrawler/

# 安装 Python 依赖
cd /opt/mediacrawler
uv sync

# 验证安装
uv run python -c "import fastapi; print('FastAPI OK')"
uv run python -c "import playwright; print('Playwright OK')"
```

---

## 第五步：安装 Playwright 浏览器

这是云服务器部署最关键的一步。Playwright 需要下载自带的 Chromium 浏览器。

```bash
cd /opt/mediacrawler

# 安装 Chromium 浏览器（会下载约 150MB）
uv run playwright install chromium

# 安装 Chromium 的系统依赖（需要 root）
# 这个命令会自动检测并安装所有缺失的系统库
sudo $(uv run which playwright) install-deps chromium

# 验证浏览器可用
uv run python -c "
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.baidu.com')
        title = await page.title()
        print(f'Browser OK! Page title: {title}')
        await browser.close()

asyncio.run(test())
"
```

如果验证脚本输出 `Browser OK!`，说明浏览器环境正常。

---

## 第六步：配置数据库

### 方案 A：使用 SQLite（最简单，适合单机）

```bash
cd /opt/mediacrawler
uv run python main.py --init_db sqlite
```

无需额外安装，数据文件保存在 `database/sqlite_tables.db`。

### 方案 B：使用 MySQL（推荐生产环境）

```bash
# 安装 MySQL
sudo apt install -y mysql-server
sudo systemctl start mysql
sudo systemctl enable mysql

# 安全初始化
sudo mysql_secure_installation

# 创建数据库和用户
sudo mysql -e "
CREATE DATABASE media_crawler CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'mediacrawler'@'%' IDENTIFIED BY 'maxmaxmax';
GRANT ALL PRIVILEGES ON media_crawler.* TO 'mediacrawler'@'%';
FLUSH PRIVILEGES;
"

# 设置环境变量（后面会写入 .env 文件）
export MYSQL_DB_HOST=localhost
export MYSQL_DB_PORT=3306
export MYSQL_DB_NAME=media_crawler
export MYSQL_DB_USER=mediacrawler
export MYSQL_DB_PWD='maxmaxmax'

# 初始化表结构
cd /opt/mediacrawler
uv run python main.py --init_db mysql
```

### 方案 C：使用 PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

sudo -u postgres psql -c "
CREATE USER mediacrawler WITH PASSWORD '你的密码';
CREATE DATABASE media_crawler OWNER mediacrawler;
"

export POSTGRES_DB_HOST=localhost
export POSTGRES_DB_PORT=5432
export POSTGRES_DB_NAME=media_crawler
export POSTGRES_DB_USER=mediacrawler
export POSTGRES_DB_PWD='你的密码'

cd /opt/mediacrawler
uv run python main.py --init_db postgres
```

---

## 第七步：构建 WebUI 前端

```bash
cd /opt/mediacrawler/webui-src

# 安装前端依赖
npm install

# 构建（输出到 ../api/webui/）
npm run build

# 验证
ls -la ../api/webui/
# 应该能看到 index.html 和 assets/ 目录
```

> 如果项目中已经包含预构建的 `api/webui/` 目录，可以跳过此步。

---

## 第八步：修改配置文件

### 8.1 创建环境变量文件

```bash
cat > /opt/mediacrawler/.env << 'EOF'
# ==================== 数据库配置 ====================
# SQLite 无需配置，如使用 MySQL/PostgreSQL 请取消注释并填写

# MySQL
# MYSQL_DB_HOST=localhost
# MYSQL_DB_PORT=3306
# MYSQL_DB_NAME=media_crawler
# MYSQL_DB_USER=mediacrawler
# MYSQL_DB_PWD=你的密码

# PostgreSQL
# POSTGRES_DB_HOST=localhost
# POSTGRES_DB_PORT=5432
# POSTGRES_DB_NAME=media_crawler
# POSTGRES_DB_USER=mediacrawler
# POSTGRES_DB_PWD=你的密码

# ==================== 运行模式 ====================
# 使用真实爬虫（非 mock 模式）
USE_REAL_CRAWLER=1
EOF

# 保护敏感文件
chmod 600 /opt/mediacrawler/.env
```

### 8.2 修改爬虫配置

编辑 `config/base_config.py`，需要修改以下关键项：

```python
# 云服务器必须开启无头模式
HEADLESS = True

# 关闭 CDP 模式（云服务器没有 Chrome/Edge）
ENABLE_CDP_MODE = False

# 数据保存方式（根据你选的数据库）
SAVE_DATA_OPTION = "sqlite"  # 或 "db"(MySQL) 或 "postgres"

# 登录方式推荐 cookie（避免扫码问题）
# 也可以保持 qrcode，通过 WebUI 远程扫码
LOGIN_TYPE = "qrcode"

# 关闭词云（除非你确认字体文件存在）
ENABLE_GET_WORDCLOUD = False
```

> **注意**：WebUI 的任务执行已经自动处理了 `ENABLE_CDP_MODE = False` 和 `HEADLESS = True`，所以通过 WebUI 创建任务时不需要担心这两项。但如果你直接命令行运行 `main.py`，务必手动修改。

---

## 第九步：启动服务

### 快速测试启动

```bash
cd /opt/mediacrawler

# 启动 API 服务器（前台运行，用于测试）
uv run python -m api.main

# 服务默认监听 0.0.0.0:8080
# 浏览器访问 http://你的服务器IP:8080 查看 WebUI
```

### 后台运行（使用 nohup）

```bash
cd /opt/mediacrawler
nohup uv run python -m api.main > /var/log/mediacrawler.log 2>&1 &

# 查看日志
tail -f /var/log/mediacrawler.log
```

---

## 第十步：配置 systemd 守护进程

创建 systemd 服务文件，让应用自动启动和崩溃重启。

```bash
sudo tee /etc/systemd/system/mediacrawler.service << 'EOF'
[Unit]
Description=MediaCrawler WebUI API Server
After=network.target
# 如果使用 MySQL，取消下一行注释
# After=network.target mysql.service

[Service]
Type=simple
User=你的用户名
Group=你的用户名
WorkingDirectory=/opt/mediacrawler
EnvironmentFile=/opt/mediacrawler/.env
ExecStart=/home/你的用户名/.local/bin/uv run python -m api.main
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# 安全限制
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/mediacrawler

# 资源限制
LimitNOFILE=65535
MemoryMax=4G

[Install]
WantedBy=multi-user.target
EOF
```

> 请将 `你的用户名` 替换为实际的 Linux 用户名。uv 的路径可通过 `which uv` 确认。

```bash
# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start mediacrawler

# 设置开机自启
sudo systemctl enable mediacrawler

# 查看状态
sudo systemctl status mediacrawler

# 查看日志
sudo journalctl -u mediacrawler -f
```

---

## 第十一步：配置 Nginx 反向代理（可选）

如果你需要域名访问、HTTPS 或者想把端口从 8080 改为 80/443：

```bash
sudo apt install -y nginx

sudo tee /etc/nginx/sites-available/mediacrawler << 'EOF'
server {
    listen 80;
    server_name 你的域名或IP;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持（任务实时日志需要）
    location /ws/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/mediacrawler /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 配置 HTTPS（Let's Encrypt）

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d 你的域名
# 按提示完成，证书会自动续期
```

---

## 常见问题排查

### 1. Chromium 启动失败

```
Error: Browser closed unexpectedly
```

**原因**：缺少系统库。

**解决**：

```bash
# 方法一：使用 Playwright 官方命令
sudo $(uv run which playwright) install-deps chromium

# 方法二：手动检查缺失的库
ldd $(find ~/.cache/ms-playwright -name chrome -type f) | grep "not found"
# 然后 apt install 缺失的库
```

### 2. 内存不足导致 Chromium 崩溃

```
Page crashed! / Browser process was killed
```

**解决**：

```bash
# 检查内存
free -h

# 添加 swap（如果内存 < 2GB）
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. 二维码扫码登录无法显示

**原因**：云服务器没有图形界面。

**解决**：通过 WebUI (`http://IP:8080`) 访问，在账号管理页面进行扫码登录，二维码会显示在网页上。

### 4. uv 命令找不到

```bash
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```

### 5. 端口被占用

```bash
# 检查 8080 端口
sudo lsof -i :8080
# 或者改用其他端口启动
uv run uvicorn api.main:app --port 9090 --host 0.0.0.0
```

### 6. 防火墙未放行

```bash
# UFW 防火墙
sudo ufw allow 8080/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 云服务商安全组
# 需要在云服务商控制台（阿里云/腾讯云/AWS等）放行对应端口
```

### 7. Playwright 下载超时

国内服务器下载 Chromium 可能很慢，可以设置镜像：

```bash
# 使用国内镜像加速 Playwright 下载
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/

uv run playwright install chromium
```

---

## Docker 部署方案（替代方案）

如果你更喜欢 Docker，可以使用以下方案，省去手动安装浏览器和系统依赖的麻烦。

### Dockerfile

```dockerfile
FROM mcr.microsoft.com/playwright:v1.45.0-jammy

WORKDIR /app

# 安装 uv
RUN pip install uv

# 复制项目文件
COPY . .

# 安装 Python 依赖
RUN uv sync

# 安装前端依赖并构建 WebUI
RUN cd webui-src && npm install && npm run build

# 初始化 SQLite 数据库
RUN uv run python main.py --init_db sqlite

EXPOSE 8080

ENV USE_REAL_CRAWLER=1

CMD ["uv", "run", "python", "-m", "api.main"]
```

### docker-compose.yml

```yaml
version: '3.8'
services:
  mediacrawler:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./database:/app/database        # 持久化数据库
      - ./browser_data:/app/browser_data # 持久化登录态
      - ./crawl_progress:/app/crawl_progress
    environment:
      - USE_REAL_CRAWLER=1
    ipc: host        # Chromium 需要足够的共享内存
    init: true       # 防止僵尸进程
    restart: unless-stopped
```

### 启动

```bash
docker compose up -d

# 查看日志
docker compose logs -f
```

---

## 一键部署脚本

将以下脚本保存为 `setup.sh`，在 Ubuntu 22.04 服务器上以普通用户执行：

```bash
#!/bin/bash
set -e

echo "=========================================="
echo " MediaCrawler 一键部署脚本 (Ubuntu 22.04)"
echo "=========================================="

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

PROJECT_DIR=$(cd "$(dirname "$0")" && pwd)

# 1. 系统依赖
info "安装系统依赖..."
sudo apt update
sudo apt install -y \
    curl wget git build-essential software-properties-common \
    unzip ca-certificates gnupg \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libdbus-1-3 libxkbcommon0 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
    libcairo2 libasound2 fonts-noto-cjk fonts-wqy-zenhei

# 2. Python 3.11
if ! command -v python3.11 &> /dev/null; then
    info "安装 Python 3.11..."
    sudo add-apt-repository ppa:deadsnakes/ppa -y
    sudo apt update
    sudo apt install -y python3.11 python3.11-venv python3.11-dev
fi
info "Python 版本: $(python3.11 --version)"

# 3. uv
if ! command -v uv &> /dev/null; then
    info "安装 uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi
info "uv 版本: $(uv --version)"

# 4. Node.js
if ! command -v node &> /dev/null; then
    info "安装 Node.js 20..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi
info "Node.js 版本: $(node --version)"

# 5. Python 依赖
info "安装 Python 依赖..."
cd "$PROJECT_DIR"
uv sync

# 6. Playwright 浏览器
info "安装 Playwright Chromium..."
export PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright/
uv run playwright install chromium
sudo "$(uv run which playwright)" install-deps chromium 2>/dev/null || true

# 7. 构建 WebUI
if [ -d "$PROJECT_DIR/webui-src" ]; then
    info "构建 WebUI 前端..."
    cd "$PROJECT_DIR/webui-src"
    npm install
    npm run build
    cd "$PROJECT_DIR"
fi

# 8. 初始化数据库
if [ ! -f "$PROJECT_DIR/database/sqlite_tables.db" ]; then
    info "初始化 SQLite 数据库..."
    uv run python main.py --init_db sqlite
fi

# 9. 创建 .env
if [ ! -f "$PROJECT_DIR/.env" ]; then
    info "创建 .env 文件..."
    cat > "$PROJECT_DIR/.env" << 'ENVEOF'
USE_REAL_CRAWLER=1
ENVEOF
    chmod 600 "$PROJECT_DIR/.env"
fi

# 10. 验证浏览器
info "验证 Chromium 浏览器..."
uv run python -c "
import asyncio
from playwright.async_api import async_playwright
async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.baidu.com')
        title = await page.title()
        print(f'浏览器验证通过! 页面标题: {title}')
        await browser.close()
asyncio.run(test())
"

echo ""
echo "=========================================="
info "部署完成！"
echo "=========================================="
echo ""
echo "启动命令:"
echo "  cd $PROJECT_DIR"
echo "  uv run python -m api.main"
echo ""
echo "访问地址: http://服务器IP:8080"
echo ""
warn "请确认已修改 config/base_config.py:"
warn "  HEADLESS = True"
warn "  ENABLE_CDP_MODE = False"
echo ""
```

使用方式：

```bash
# 将脚本放到项目根目录
chmod +x setup.sh
./setup.sh
```
