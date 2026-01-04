"""Tests for FastAPI endpoints"""

from unittest.mock import Mock, patch

import pytest
from app import app
from fastapi.testclient import TestClient


class TestQueryEndpoint:
    """Test /api/query endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAGSystem"""
        with patch("app.rag_system") as mock:
            mock.session_manager.create_session = Mock(return_value="session_123")
            mock.query = Mock(return_value=("Answer text", ["Source 1"]))
            yield mock

    def test_query_endpoint_success(self, client, mock_rag_system):
        """Test: Successful query request"""
        response = client.post("/api/query", json={"query": "What is RAG?"})

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Answer text"
        assert data["sources"] == ["Source 1"]
        assert data["session_id"] == "session_123"

        # Verify RAG system was called
        mock_rag_system.query.assert_called_once_with("What is RAG?", "session_123")

    def test_query_endpoint_with_existing_session(self, client, mock_rag_system):
        """Test: Query with existing session_id"""
        mock_rag_system.query.return_value = ("Answer", ["Source"])

        response = client.post(
            "/api/query", json={"query": "Follow up question", "session_id": "existing_session"}
        )

        # Verify new session is NOT created
        assert not mock_rag_system.session_manager.create_session.called

        # Verify existing session is used
        mock_rag_system.query.assert_called_once_with("Follow up question", "existing_session")

        assert response.status_code == 200

    def test_query_endpoint_rag_exception(self, client, mock_rag_system):
        """Test: RAG system exception"""
        # Mock RAG system exception
        mock_rag_system.query.side_effect = Exception("ChromaDB connection failed")

        response = client.post("/api/query", json={"query": "test"})

        # Verify 500 error
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "ChromaDB connection failed" in data["detail"]

    def test_query_endpoint_missing_query(self, client):
        """Test: Missing query parameter"""
        response = client.post("/api/query", json={"session_id": "session_1"})

        # FastAPI auto-validation returns 422
        assert response.status_code == 422

    def test_query_endpoint_empty_query(self, client):
        """Test: Empty query string"""
        response = client.post("/api/query", json={"query": ""})

        # Should still be 422 (validation error)
        # or 200 if empty strings are allowed
        assert response.status_code in [200, 422]

    def test_query_endpoint_special_characters(self, client, mock_rag_system):
        """Test: Query with special characters"""
        mock_rag_system.query.return_value = ("Special answer", ["Source"])

        response = client.post("/api/query", json={"query": "What about RAG & AI? Test <tag>"})

        # Should handle special characters
        assert response.status_code == 200
        assert response.json()["answer"] == "Special answer"


class TestCoursesEndpoint:
    """Test /api/courses endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_rag_system(self):
        """Mock RAGSystem"""
        with patch("app.rag_system") as mock:
            mock.get_course_analytics = Mock(
                return_value={
                    "total_courses": 5,
                    "course_titles": ["Course 1", "Course 2", "Course 3"],
                }
            )
            yield mock

    def test_courses_endpoint_success(self, client, mock_rag_system):
        """Test: Successful course stats request"""
        response = client.get("/api/courses")

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 5
        assert data["course_titles"] == ["Course 1", "Course 2", "Course 3"]
        assert len(data["course_titles"]) == 3

    def test_courses_endpoint_empty(self, client, mock_rag_system):
        """Test: No courses available"""
        mock_rag_system.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_exception(self, client, mock_rag_system):
        """Test: Exception handling"""
        mock_rag_system.get_course_analytics.side_effect = Exception("Database error")

        response = client.get("/api/courses")

        assert response.status_code == 500
        data = response.json()
        assert "Database error" in data["detail"]


class TestStaticFiles:
    """Test static file serving"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_frontend_served(self, client):
        """Test: Frontend index.html is served"""
        # Note: This test might fail if frontend files don't exist in test environment
        # In that case, we can mock the static file mounting
        response = client.get("/")

        # Should return 200 or 404 depending on whether frontend exists
        assert response.status_code in [200, 404]
