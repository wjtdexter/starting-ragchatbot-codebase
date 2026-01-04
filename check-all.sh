#!/bin/bash
# 综合质量检查脚本 - 格式化 + Lint + 测试

set -e

echo "🚀 运行完整的代码质量检查流程..."

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步骤 1/4: 代码格式化"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ./format.sh; then
    echo -e "${GREEN}✅ 格式化完成${NC}"
else
    echo -e "${RED}❌ 格式化失败${NC}"
    FAILED=1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步骤 2/4: 代码质量检查"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if ./lint.sh; then
    echo -e "${GREEN}✅ Lint 检查通过${NC}"
else
    echo -e "${RED}❌ Lint 检查失败${NC}"
    FAILED=1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步骤 3/4: 运行测试"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
cd backend
if uv run pytest -v; then
    echo -e "${GREEN}✅ 测试通过${NC}"
else
    echo -e "${RED}❌ 测试失败${NC}"
    FAILED=1
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 步骤 4/4: 生成测试覆盖率报告"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if uv run pytest --cov=. --cov-report=term-missing; then
    echo -e "${GREEN}✅ 覆盖率报告生成成功${NC}"
else
    echo -e "${YELLOW}⚠️  覆盖率报告生成失败 (非致命)${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 所有检查通过!代码质量良好!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
else
    echo -e "${RED}⚠️  部分检查失败,请修复后重试${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
fi
