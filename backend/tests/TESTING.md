# 测试框架文档

## 概述

本项目的测试框架已经过增强,提供了全面的 API 端点测试、共享的测试 fixtures 和 pytest 配置。

## 测试统计

- **总测试数**: 86 个
- **API 测试**: 43 个(全部通过 ✅)
- **单元测试**: 覆盖所有核心组件
- **集成测试**: 包含真实系统测试

## 测试结构

```
backend/tests/
├── conftest.py                      # 共享 fixtures 和测试配置
├── test_api_endpoints.py            # 全面的 API 端点测试 (新)
├── test_app.py                      # FastAPI 应用测试 (已更新)
├── test_ai_generator.py             # AI 生成器测试
├── test_rag_system.py               # RAG 系统测试
├── test_search_tools.py             # 搜索工具测试
├── test_vector_store.py             # 向量存储测试
└── test_real_system_integration.py  # 真实系统集成测试
```

## 运行测试

### 运行所有测试
```bash
uv run pytest backend/tests/ -v
```

### 仅运行 API 测试
```bash
uv run pytest backend/tests/ -k "api" -v
```

### 运行特定测试文件
```bash
uv run pytest backend/tests/test_api_endpoints.py -v
```

### 运行带覆盖率报告的测试
```bash
uv run pytest backend/tests/ --cov=backend --cov-report=html
```

### 按标记运行测试
```bash
# 仅运行单元测试
uv run pytest backend/tests/ -m unit

# 仅运行 API 测试
uv run pytest backend/tests/ -m api

# 仅运行集成测试
uv run pytest backend/tests/ -m integration
```

## Pytest 配置

`pyproject.toml` 中的 pytest 配置:

```toml
[tool.pytest.ini_options]
minversion = "9.0"
addopts = [
    "-ra",                           # 显示测试摘要
    "-q",                            # 简化输出
    "--strict-markers",              # 严格标记检查
    "--cov=backend",                 # 覆盖率报告
    "--cov-report=term-missing",     # 终端显示缺失行
    "--cov-report=html",             # HTML 覆盖率报告
    "--asyncio-mode=auto"            # 自动异步模式
]
testpaths = ["backend/tests"]
pythonpath = ["backend"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "api: API endpoint tests",
    "slow: Slow running tests"
]
```

## 共享 Fixtures (conftest.py)

### 核心 Fixtures

#### `test_app`
创建测试专用的 FastAPI 应用,避免静态文件挂载问题。
```python
def test_example(test_client, test_app):
    # 使用 test_client 发送请求
    response = test_client.post("/api/query", json={"query": "test"})
```

#### `test_client`
从 test_app 创建的 TestClient 实例。

#### `mock_rag_system`
Mock 的 RAGSystem 实例。
```python
def test_with_mock(mock_rag_system):
    mock_rag_system.query.return_value = ("Answer", ["Source"])
```

#### `mock_anthropic_client`
Mock 的 Anthropic API 客户端。

#### `mock_vector_store`
Mock 的 VectorStore 实例。

#### `mock_session_manager`
Mock 的 SessionManager 实例。

### 示例 Fixtures

#### `sample_query`
示例查询字符串。

#### `sample_course_metadata`
示例课程元数据。

#### `sample_search_results`
示例搜索结果。

#### `sample_query_requests`
多种示例查询请求列表。

#### `sample_course_documents`
示例课程文档内容。

## API 端点测试

### 测试覆盖

#### `/api/query` 端点
- ✅ 基本成功请求
- ✅ 带现有 session_id 的请求
- ✅ 新 session 创建
- ✅ 缺失查询字段验证
- ✅ 空查询处理
- ✅ 特殊字符处理
- ✅ 超长字符串处理
- ✅ Unicode 字符处理
- ✅ 响应结构验证
- ✅ 服务器错误处理

#### `/api/courses` 端点
- ✅ 基本成功请求
- ✅ 响应结构验证
- ✅ 包含实际数据
- ✅ 空响应处理
- ✅ 错误处理
- ✅ 方法不允许验证
- ✅ 大数据集处理

#### `/` 根端点
- ✅ 基本信息
- ✅ 方法不允许验证

#### 其他测试
- ✅ 不存在的端点 (404)
- ✅ 无效的 HTTP 方法 (405)
- ✅ 格式错误的 JSON
- ✅ 自定义请求头
- ✅ 并发请求处理
- ✅ Session 隔离
- ✅ 参数化测试场景

### 使用示例

```python
import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.api

def test_query_endpoint(test_client: TestClient, test_app):
    """测试查询端点"""
    response = test_client.post(
        "/api/query",
        json={"query": "What is RAG?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "session_id" in data
```

## 测试标记

使用 pytest 标记来组织和运行特定类型的测试:

```python
@pytest.mark.unit
def test_something():
    """单元测试"""
    pass

@pytest.mark.api
def test_api_endpoint():
    """API 测试"""
    pass

@pytest.mark.integration
def test_integration():
    """集成测试"""
    pass

@pytest.mark.slow
def test_slow_operation():
    """慢速测试"""
    pass
```

## 最佳实践

1. **使用共享 fixtures**: 在 `conftest.py` 中定义共享的测试数据和 mock 对象
2. **标记测试**: 使用适当的标记 (unit, api, integration)
3. **使用 test_app fixture**: 避免静态文件挂载问题
4. **Mock 外部依赖**: 使用 mock_rag_system, mock_anthropic_client 等
5. **测试边界情况**: 包括空输入、特殊字符、错误处理等
6. **验证响应结构**: 确保响应符合预期的 schema

## 故障排除

### 导入错误
如果遇到导入错误,确保在测试目录中运行或使用 `pythonpath` 配置:
```bash
uv run pytest backend/tests/ --pythonpath=backend
```

### 静态文件错误
使用 `test_app` fixture 而不是直接导入 `app.py` 以避免静态文件挂载问题。

### API Key 问题
某些集成测试需要 `ANTHROPIC_API_KEY` 环境变量。这些测试在密钥缺失时会跳过。

## 覆盖率报告

生成 HTML 覆盖率报告:
```bash
uv run pytest backend/tests/ --cov=backend --cov-report=html
open htmlcov/index.html
```

查看终端覆盖率报告:
```bash
uv run pytest backend/tests/ --cov=backend --cov-report=term-missing
```

## 持续集成

这些测试配置为与 CI/CD 管道兼容:

```yaml
# GitHub Actions 示例
- name: Run tests
  run: |
    uv sync
    uv run pytest backend/tests/ -v --cov=backend --cov-report=xml
```

## 贡献指南

添加新测试时:
1. 在适当的测试文件中添加测试
2. 使用共享 fixtures (如 `test_client`, `mock_rag_system`)
3. 添加适当的标记 (`@pytest.mark.api`, `@pytest.mark.unit`)
4. 确保测试独立且可重复运行
5. 运行所有测试确保没有破坏现有功能
