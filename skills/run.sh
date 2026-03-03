#!/bin/bash
# MediaCrawler Skills 快速启动脚本

set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   MediaCrawler Skills 工具集          ║${NC}"
echo -e "${BLUE}╚═════════════════════���══════════════════╝${NC}"
echo ""

# 显示菜单
echo -e "${GREEN}请选择要执行的操作:${NC}"
echo ""
echo "  1) 🏥 健康检查 - 检查系统状态"
echo "  2) 📊 数据统计 - 生成统计报告"
echo "  3) 🚀 版本发布 - 自动化发布流程"
echo "  4) 📚 查看帮助文档"
echo "  0) 退出"
echo ""

read -p "请输入选项 [0-4]: " choice

case $choice in
    1)
        echo -e "\n${YELLOW}执行健康检查...${NC}\n"
        uv run python skills/health_check.py
        ;;
    2)
        echo -e "\n${YELLOW}生成数据统计报告...${NC}\n"
        read -p "请输入平台 (xhs/dy/ks/bili/wb/tieba/zhihu) [默认: xhs]: " platform
        platform=${platform:-xhs}
        read -p "请输入统计天数 [默认: 7]: " days
        days=${days:-7}
        uv run python skills/data_statistics.py --platform $platform --days $days
        ;;
    3)
        echo -e "\n${YELLOW}版本发布流程...${NC}\n"
        echo "版本类型:"
        echo "  1) patch (0.0.1)"
        echo "  2) minor (0.1.0)"
        echo "  3) major (1.0.0)"
        read -p "请选择版本类型 [1-3]: " version_type

        case $version_type in
            1) bump_type="patch" ;;
            2) bump_type="minor" ;;
            3) bump_type="major" ;;
            *) echo "无效选项"; exit 1 ;;
        esac

        read -p "是否演习模式? (y/n) [默认: y]: " dry_run
        dry_run=${dry_run:-y}

        if [ "$dry_run" = "y" ]; then
            uv run python skills/version_release.py $bump_type --dry-run
        else
            read -p "是否自动推送到远程? (y/n) [默认: n]: " push
            if [ "$push" = "y" ]; then
                uv run python skills/version_release.py $bump_type --push
            else
                uv run python skills/version_release.py $bump_type
            fi
        fi
        ;;
    4)
        echo -e "\n${YELLOW}打开帮助文档...${NC}\n"
        cat skills/README.md
        ;;
    0)
        echo -e "\n${GREEN}再见！${NC}\n"
        exit 0
        ;;
    *)
        echo -e "\n${YELLOW}无效选项${NC}\n"
        exit 1
        ;;
esac

echo -e "\n${GREEN}✅ 操作完成！${NC}\n"
