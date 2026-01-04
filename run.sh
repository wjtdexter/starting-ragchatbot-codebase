#!/bin/bash

# 解析命令行参数
DEV_MODE=false
SKIP_LINT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dev)
            DEV_MODE=true
            shift
            ;;
        --skip-lint)
            SKIP_LINT=true
            shift
            ;;
        *)
            echo "未知选项: $1"
            echo "用法: ./run.sh [--dev] [--skip-lint]"
            exit 1
            ;;
    esac
done

# 开发模式:先运行质量检查
if [ "$DEV_MODE" = true ] && [ "$SKIP_LINT" = false ]; then
    echo "🔧 开发模式:运行快速质量检查..."
    if ! ./lint.sh; then
        echo "⚠️  质量检查未通过,但继续启动服务器..."
        echo "   如需跳过检查,使用: ./run.sh --dev --skip-lint"
    fi
fi

# Create necessary directories
mkdir -p docs

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo "Error: backend directory not found"
    exit 1
fi

echo "Starting Course Materials RAG System..."
echo "Make sure you have set your ANTHROPIC_API_KEY in .env"

# Change to backend directory and start the server
cd backend && uv run uvicorn app:app --reload --port 8000