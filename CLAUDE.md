# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MediaCrawler is a multi-platform social media data collection tool supporting XiaoHongShu (小红书), Douyin (抖音), Kuaishou (快手), Bilibili, Weibo (微博), Tieba (贴吧), Zhihu (知乎), and WeChat (微信). It uses Playwright browser automation to maintain login sessions and extract data without requiring JavaScript reverse engineering.

**Important**: This project is for educational and research purposes only. Never use for commercial purposes or large-scale scraping that could disrupt platform operations.

## Development Setup

### Prerequisites
- Python >= 3.11
- Node.js >= 16.0.0
- uv (recommended Python package manager)

### Installation
```bash
# Install dependencies
uv sync

# Install Playwright browsers
uv run playwright install
```

### Running the Crawler
```bash
# Basic usage - search mode with QR code login
uv run main.py --platform xhs --lt qrcode --type search

# Detail mode - crawl specific posts by ID
uv run main.py --platform xhs --lt qrcode --type detail

# Creator mode - crawl creator's homepage
uv run main.py --platform xhs --lt qrcode --type creator

# View all options
uv run main.py --help
```

### WebUI Development
```bash
# Start API server (default port 8080)
uv run uvicorn api.main:app --port 8080 --reload

# Or using module mode
uv run python -m api.main

# Frontend development (in webui-src/)
cd webui-src
npm install
npm run dev      # Development server
npm run build    # Production build
```

### Database Initialization
```bash
# Initialize SQLite (default)
uv run main.py --init_db sqlite

# Initialize MySQL
uv run main.py --init_db mysql

# Initialize PostgreSQL
uv run main.py --init_db postgres
```

### Testing
```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest test/test_specific.py
```

## Architecture

### Core Components

**main.py**: Entry point that orchestrates the crawling process. Uses `CrawlerFactory` to instantiate platform-specific crawlers. Handles initialization of sign server, database verification, and cleanup.

**base/base_crawler.py**: Abstract base class (`AbstractCrawler`) that all platform crawlers inherit from. Provides common functionality for:
- Resume crawling (断点续爬) via `ProgressManager`
- Multi-account management via `AccountPool`
- Incremental crawling to avoid re-crawling existing content

**media_platform/**: Platform-specific crawler implementations (xhs/, douyin/, bilibili/, weibo/, etc.). Each platform has its own module with login, search, and data extraction logic.

**config/**: Configuration system with `base_config.py` as the main config and platform-specific configs (xhs_config.py, dy_config.py, etc.). All crawler behavior is controlled through these configs.

**database/**: Database abstraction layer supporting SQLite, MySQL, PostgreSQL, and MongoDB. `db.py` provides connection management and `models.py` defines ORM models.

**store/**: Data persistence layer with platform-specific stores. Supports multiple output formats: CSV, JSON, Excel, and database storage. `excel_store_base.py` provides base class for Excel exports.

**proxy/**: IP proxy pool system with:
- `proxy_manager.py`: Main proxy management
- `providers/`: Different proxy provider integrations (kuaidaili, wandouhttp)
- `quality/`: Proxy quality assessment
- `failover/`: Automatic failover when proxies fail
- `binding/`: Account-proxy binding for multi-account scenarios

**api/**: FastAPI-based WebUI backend with:
- `routers/`: REST API endpoints for tasks, data, proxies, accounts, etc.
- `services/`: Business logic including task execution, crawler adapters
- `schemas/`: Pydantic models for request/response validation
- `middleware/`: Session management and CORS

**webui-src/**: React + TypeScript frontend using Vite, TailwindCSS, and Radix UI components.

### Key Design Patterns

**Factory Pattern**: `CrawlerFactory` creates platform-specific crawler instances based on platform string.

**Abstract Base Class**: `AbstractCrawler` defines the interface all platform crawlers must implement (start, search, get_creators, etc.).

**CDP Mode**: Chrome DevTools Protocol mode (`ENABLE_CDP_MODE`) allows using user's existing Chrome/Edge browser for better anti-detection. Controlled via `tools/cdp_manager.py`.

**Sign Server**: Remote signing service support (`SIGN_SERVER_ENABLED`) to offload JS signature generation. Falls back to local Playwright signing if unavailable.

**Progress Management**: Resume crawling from where it left off using `crawler/progress.py`. Saves progress periodically to handle interruptions.

**Multi-Account Pool**: `account/account_pool.py` manages multiple accounts with automatic rotation and failure handling.

## Configuration

All configuration is in `config/base_config.py` with extensive Chinese comments. Key settings:

- `PLATFORM`: Target platform (xhs, dy, ks, bili, wb, tieba, zhihu, wechat)
- `CRAWLER_TYPE`: search, detail, creator, creator_vip, album
- `LOGIN_TYPE`: qrcode, phone, cookie, mp_qrcode
- `ENABLE_CDP_MODE`: Use Chrome DevTools Protocol for better anti-detection
- `SAVE_DATA_OPTION`: csv, db, json, sqlite, excel, postgres, mongodb
- `ENABLE_GET_COMMENTS`: Whether to crawl comments
- `ENABLE_IP_PROXY`: Enable IP proxy pool
- `ENABLE_RESUME_CRAWL`: Enable resume crawling (断点续爬)
- `ENABLE_INCREMENTAL_CRAWL`: Only crawl new content

Platform-specific configs override base config (e.g., `config/xhs_config.py` for XiaoHongShu).

## Data Storage

The project supports multiple storage backends controlled by `SAVE_DATA_OPTION`:

- **csv**: Simple CSV files per platform
- **json**: JSON files with structured data
- **excel**: Excel workbooks with multiple sheets
- **db/mysql**: MySQL database with full schema
- **sqlite**: Local SQLite database
- **postgres**: PostgreSQL database
- **mongodb**: MongoDB for document storage

Database models are in `database/models.py` and `database/webui_models.py` (for WebUI-specific tables).

## Important Notes

### Large File Operations
When reading or writing large files, always use segmented operations:
- **Reading**: Use `offset`/`limit` parameters to read in chunks
- **Writing**: Split into multiple small edits, max 5000 characters per operation

### Browser Automation
- **Playwright Mode**: Default mode, launches isolated browser instances
- **CDP Mode**: Connects to user's existing Chrome/Edge browser via DevTools Protocol for better anti-detection
- Browser data is cached in `browser_data/` directory per platform

### Login State
Login state is saved in `account/` directory. Set `SAVE_LOGIN_STATE = True` to persist cookies/tokens across runs.

### Proxy System
When `ENABLE_IP_PROXY = True`, the proxy pool system automatically:
- Fetches proxies from configured provider
- Tests proxy quality and speed
- Rotates proxies on failure
- Binds specific proxies to accounts for consistency

### WebUI Task System
The WebUI uses an event-driven task system:
- Tasks are created via REST API and executed by `TaskExecutor`
- Real-time progress updates via WebSocket (`api/routers/ws_tasks.py`)
- Task state managed by `EventBus` for pub/sub communication
- Supports both mock mode (testing) and real crawler mode (`USE_REAL_CRAWLER=1`)

## Common Workflows

### Adding a New Platform
1. Create new directory in `media_platform/`
2. Implement crawler class inheriting from `AbstractCrawler`
3. Add platform config in `config/`
4. Add platform enum to `cmd_arg/arg.py`
5. Register in `CrawlerFactory.CRAWLERS` dict in `main.py`
6. Create store implementation in `store/`
7. Add database models if using DB storage

### Debugging Login Issues
- Set `HEADLESS = False` to see browser window
- Check `browser_data/` for cached login state
- For XiaoHongShu: manually pass slider CAPTCHA if QR code fails
- For Douyin: check for phone verification after QR scan

### Extending Data Storage
- Inherit from platform-specific store base class in `store/`
- Implement required methods: `store_content`, `store_comment`, etc.
- Register new storage option in `SaveDataOptionEnum`

## Environment Variables

- `INTEGRATED_WORKER=1`: Run crawler in same process as API (for development)
- `USE_REAL_CRAWLER=1`: Use real crawler instead of mock in WebUI
- `SIGN_SERVER_ENABLED=1`: Enable remote signing service
- `SIGN_SERVER_URL`: URL of signing service

## File Naming Conventions

- Platform modules use short codes: xhs, dy, ks, bili, wb
- Config files: `{platform}_config.py`
- Store implementations: `store/{platform}/`
- Models: `{platform}_store_impl.py` for platform-specific storage

## Documentation

All developer documentation lives in `docs/`:
- `docs/architecture.md` - System architecture, module design, directory structure
- `docs/development.md` - Environment setup, WebUI development, debugging
- `docs/README.md` - Documentation index with full navigation
