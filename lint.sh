#!/bin/bash
# 代码质量检查脚本 - 使用 flake8 检查代码质量

set -e

echo "🔍 开始代码质量检查..."

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 检查结果变量
HAS_ERRORS=0

echo -e "${BLUE}步骤 1: 检查代码风格 (flake8)...${NC}"
cd backend

if uv run flake8 .; then
    echo -e "${GREEN}✅ flake8 检查通过!${NC}"
else
    echo -e "${RED}❌ flake8 发现问题!${NC}"
    echo -e "${YELLOW}💡 提示: 运行 './format.sh' 可以自动修复大部分问题${NC}"
    HAS_ERRORS=1
fi

echo ""
echo -e "${BLUE}步骤 2: 检查 import 排序 (isort --check-only)...${NC}"
if uv run isort --check-only .; then
    echo -e "${GREEN}✅ import 排序检查通过!${NC}"
else
    echo -e "${RED}❌ import 排序存在问题!${NC}"
    echo -e "${YELLOW}💡 提示: 运行 './format.sh' 可以自动修复${NC}"
    HAS_ERRORS=1
fi

echo ""
echo -e "${BLUE}步骤 3: 检查代码格式 (Black --check)...${NC}"
if uv run black --check .; then
    echo -e "${GREEN}✅ 代码格式检查通过!${NC}"
else
    echo -e "${RED}❌ 代码格式存在问题!${NC}"
    echo -e "${YELLOW}💡 提示: 运行 './format.sh' 可以自动修复${NC}"
    HAS_ERRORS=1
fi

echo ""
if [ $HAS_ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有代码质量检查通过!${NC}"
    exit 0
else
    echo -e "${RED}⚠️  代码质量检查失败,请修复上述问题后重试${NC}"
    exit 1
fi
