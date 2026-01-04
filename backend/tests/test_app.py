"""
Tests for FastAPI endpoints using the test app fixture.

This module has been updated to use the test_app fixture from conftest.py
to avoid issues with static file mounting in test environments.
"""

from fastapi.testclient import TestClient
import pytest


pytestmark = pytest.mark.api


class TestQueryEndpoint:
    """Test /api/query endpoint"""

    def test_query_endpoint_success(self, test_client: TestClient, test_app):
        """Test: Successful query request"""
        # Configure mock to return specific values
        test_app.state.mock_rag.query.return_value = ("Answer text", ["Source 1"])

        response = test_client.post(
            "/api/query",
            json={"query": "What is RAG?"}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Answer text"
        assert data["sources"] == ["Source 1"]
        assert data["session_id"] == "test_session"

        # Verify RAG system was called
        test_app.state.mock_rag.query.assert_called_once_with(
            "What is RAG?",
            "test_session"
        )

    def test_query_endpoint_with_existing_session(self, test_client: TestClient, test_app):
        """Test: Query with existing session_id"""
        test_app.state.mock_rag.query.return_value = ("Answer", ["Source"])

        response = test_client.post(
            "/api/query",
            json={
                "query": "Follow up question",
                "session_id": "existing_session"
            }
        )

        # Verify new session is NOT created
        assert not test_app.state.mock_rag.session_manager.create_session.called

        # Verify existing session is used
        test_app.state.mock_rag.query.assert_called_once_with(
            "Follow up question",
            "existing_session"
        )

        assert response.status_code == 200

    def test_query_endpoint_rag_exception(self, test_client: TestClient, test_app):
        """Test: RAG system exception"""
        # Mock RAG system exception
        test_app.state.mock_rag.query.side_effect = Exception("ChromaDB connection failed")

        response = test_client.post(
            "/api/query",
            json={"query": "test"}
        )

        # Verify 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "ChromaDB connection failed" in data["detail"]

    def test_query_endpoint_missing_query(self, test_client: TestClient):
        """Test: Missing query parameter"""
        response = test_client.post(
            "/api/query",
            json={"session_id": "session_1"}
        )

        # FastAPI auto-validation returns 422
        assert response.status_code == 422

    def test_query_endpoint_empty_query(self, test_client: TestClient):
        """Test: Empty query string"""
        response = test_client.post(
            "/api/query",
            json={"query": ""}
        )

        # Should still be 422 (validation error)
        # or 200 if empty strings are allowed
        assert response.status_code in [200, 422]

    def test_query_endpoint_special_characters(self, test_client: TestClient, test_app):
        """Test: Query with special characters"""
        test_app.state.mock_rag.query.return_value = ("Special answer", ["Source"])

        response = test_client.post(
            "/api/query",
            json={"query": "What about RAG & AI? Test <tag>"}
        )

        # Should handle special characters
        assert response.status_code == 200
        assert response.json()["answer"] == "Special answer"


class TestCoursesEndpoint:
    """Test /api/courses endpoint"""

    def test_courses_endpoint_success(self, test_client: TestClient, test_app):
        """Test: Successful course stats request"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["Course 1", "Course 2", "Course 3"]
        }

        response = test_client.get("/api/courses")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert data["course_titles"] == ["Course 1", "Course 2", "Course 3"]
        assert len(data["course_titles"]) == 3

    def test_courses_endpoint_empty(self, test_client: TestClient, test_app):
        """Test: No courses available"""
        test_app.state.mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_exception(self, test_client: TestClient, test_app):
        """Test: Exception handling"""
        test_app.state.mock_rag.get_course_analytics.side_effect = Exception("Database error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]


class TestRootEndpoint:
    """Test root endpoint"""

    def test_root_endpoint(self, test_client: TestClient):
        """Test: Root endpoint returns API info"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
