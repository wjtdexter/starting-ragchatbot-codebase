#!/bin/bash
# 代码格式化脚本 - 使用 Black 和 isort 自动格式化代码

set -e  # 遇到错误立即退出

echo "🎨 开始格式化代码..."

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 切换到 backend 目录
cd backend

echo -e "${BLUE}步骤 1: 使用 isort 排序 imports...${NC}"
uv run isort .

echo -e "${BLUE}步骤 2: 使用 Black 格式化代码...${NC}"
uv run black .

echo -e "${GREEN}✅ 代码格式化完成!${NC}"
echo ""
echo "格式化内容:"
echo "  • 已按 PEP8 标准排序所有 import 语句"
echo "  • 已统一代码风格 (缩进、空格、引号等)"
echo ""
echo "💡 提示: 如果您想查看格式化前后的差异,可以运行:"
echo "   ./format.sh  # 先格式化"
echo "   git diff      # 查看变更"
