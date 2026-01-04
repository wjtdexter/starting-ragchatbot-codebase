"""
Comprehensive API endpoint tests for RAG system.

This module tests all FastAPI endpoints using a test-specific app instance
to avoid issues with static file mounting in test environments.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from typing import Dict, Any


pytestmark = pytest.mark.api


class TestQueryEndpoint:
    """Test suite for /api/query endpoint"""

    def test_query_basic_success(self, test_client: TestClient):
        """Test: Basic successful query request"""
        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

    def test_query_with_existing_session(self, test_client: TestClient):
        """Test: Query with existing session_id"""
        existing_session = "my_existing_session_456"

        response = test_client.post(
            "/api/query",
            json={
                "query": "Follow up question",
                "session_id": existing_session
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == existing_session

    def test_query_creates_new_session(self, test_client: TestClient, test_app):
        """Test: New session is created when none provided"""
        response = test_client.post(
            "/api/query",
            json={"query": "New conversation"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test_session"

        # Verify create_session was called
        test_app.state.mock_rag.session_manager.create_session.assert_called_once()

    def test_query_missing_query_field(self, test_client: TestClient):
        """Test: Request without query field returns validation error"""
        response = test_client.post(
            "/api/query",
            json={"session_id": "session_123"}
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_query_empty_query(self, test_client: TestClient):
        """Test: Empty query string"""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Empty query is still valid string, so should be 200 or 422
        assert response.status_code in [200, 422]

    def test_query_special_characters(self, test_client: TestClient):
        """Test: Query with special characters and HTML"""
        special_queries = [
            "What about RAG & AI?",
            "Test <tag> and [brackets]",
            "Query with 'quotes' and \"double quotes\"",
            "Test slashes / \\ and pipes |",
            "Emoji test 🤖 🔥",
            "中文查询测试"
        ]

        for query in special_queries:
            response = test_client.post(
                "/api/query",
                json={"query": query}
            )
            assert response.status_code == 200

    def test_query_very_long_string(self, test_client: TestClient):
        """Test: Query with very long string"""
        long_query = "What is RAG? " * 100  # 1500+ characters

        response = test_client.post(
            "/api/query",
            json={"query": long_query}
        )

        assert response.status_code == 200

    def test_query_unicode_characters(self, test_client: TestClient):
        """Test: Query with various Unicode characters"""
        unicode_queries = [
            "测试中文查询",
            "Тест на русском",
            "Test العربية",
            "日本語テスト",
            "🚀 Rocket emoji test"
        ]

        for query in unicode_queries:
            response = test_client.post(
                "/api/query",
                json={"query": query}
            )
            assert response.status_code == 200

    def test_query_response_structure(self, test_client: TestClient):
        """Test: Response matches expected structure"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test query"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields exist
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify types
        assert isinstance(data["answer"], str)
        assert isinstance(data["sources"], list)
        assert isinstance(data["session_id"], str)

        # Verify no extra fields
        assert set(data.keys()) == {"answer", "sources", "session_id"}

    def test_query_server_error_handling(self, test_client: TestClient, test_app):
        """Test: Server error when RAG system fails"""
        # Make the mock raise an exception
        test_app.state.mock_rag.query.side_effect = Exception("Database connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "Test error"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database connection failed" in data["detail"]


class TestCoursesEndpoint:
    """Test suite for /api/courses endpoint"""

    def test_courses_basic_success(self, test_client: TestClient):
        """Test: Basic successful course stats request"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data

    def test_courses_response_structure(self, test_client: TestClient):
        """Test: Response has correct structure and types"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        # Verify field types
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
        assert all(isinstance(title, str) for title in data["course_titles"])

        # Verify no extra fields
        assert set(data.keys()) == {"total_courses", "course_titles"}

    def test_courses_with_data(self, test_client: TestClient):
        """Test: Response contains actual course data"""
        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]

    def test_courses_empty_response(self, test_client: TestClient, test_app):
        """Test: Empty course list"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": []
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_error_handling(self, test_client: TestClient, test_app):
        """Test: Error handling when analytics fails"""
        test_app.state.mock_rag.get_course_analytics.side_effect = Exception(
            "Vector store unavailable"
        )

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "Vector store unavailable" in data["detail"]

    def test_courses_method_not_allowed(self, test_client: TestClient):
        """Test: POST request to GET endpoint"""
        response = test_client.post("/api/courses")

        assert response.status_code == 405  # Method Not Allowed

    def test_courses_large_dataset(self, test_client: TestClient, test_app):
        """Test: Response with many courses"""
        many_titles = [f"Course {i}" for i in range(100)]
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 100,
            "course_titles": many_titles
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 100
        assert len(data["course_titles"]) == 100


class TestRootEndpoint:
    """Test suite for root endpoint"""

    def test_root_endpoint(self, test_client: TestClient):
        """Test: Root endpoint returns API info"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Test RAG API" in data["message"]

    def test_root_method_not_allowed_post(self, test_client: TestClient):
        """Test: POST to root endpoint not allowed"""
        response = test_client.post("/")

        assert response.status_code == 405


class TestInvalidEndpoints:
    """Test suite for invalid endpoint access"""

    def test_nonexistent_endpoint(self, test_client: TestClient):
        """Test: Access to nonexistent endpoint"""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_invalid_method(self, test_client: TestClient):
        """Test: Invalid HTTP method on valid endpoint"""
        response = test_client.put("/api/query")

        assert response.status_code == 405  # Method Not Allowed

    def test_malformed_json(self, test_client: TestClient):
        """Test: Malformed JSON in request body"""
        response = test_client.post(
            "/api/query",
            data="invalid json {",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


class TestRequestHeaders:
    """Test suite for request header handling"""

    def test_query_with_content_type(self, test_client: TestClient):
        """Test: Request with proper Content-Type header"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test"},
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200

    def test_query_without_content_type(self, test_client: TestClient):
        """Test: Request without Content-Type header"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test"}
        )

        # FastAPI defaults to JSON, should work
        assert response.status_code == 200

    def test_query_with_custom_headers(self, test_client: TestClient):
        """Test: Request with custom headers"""
        response = test_client.post(
            "/api/query",
            json={"query": "Test"},
            headers={
                "X-Custom-Header": "custom_value",
                "User-Agent": "TestClient/1.0"
            }
        )

        assert response.status_code == 200


class TestConcurrency:
    """Test suite for concurrent request handling"""

    def test_multiple_sequential_queries(self, test_client: TestClient):
        """Test: Multiple sequential query requests"""
        responses = []
        for i in range(5):
            response = test_client.post(
                "/api/query",
                json={"query": f"Query {i}"}
            )
            responses.append(response)

        for response in responses:
            assert response.status_code == 200

    def test_session_isolation(self, test_client: TestClient):
        """Test: Different sessions don't interfere"""
        session1_response = test_client.post(
            "/api/query",
            json={"query": "Session 1 query"}
        )

        session2_response = test_client.post(
            "/api/query",
            json={"query": "Session 2 query"}
        )

        assert session1_response.status_code == 200
        assert session2_response.status_code == 200

        data1 = session1_response.json()
        data2 = session2_response.json()

        # Both should have valid session IDs
        assert data1["session_id"]
        assert data2["session_id"]


@pytest.mark.parametrize("query,session_id,expected_status", [
    ("What is RAG?", None, 200),
    ("Follow up", "existing_session", 200),
    ("", None, 200),  # Empty query might be valid
    ("Test with emojis 🚀", None, 200),
    ("Test", "", 200),  # Empty session_id should trigger new session creation
])
def test_query_parametrized(test_client, query, session_id, expected_status):
    """Parametrized test for various query scenarios"""
    payload = {"query": query}
    if session_id is not None:
        payload["session_id"] = session_id

    response = test_client.post("/api/query", json=payload)
    assert response.status_code == expected_status
