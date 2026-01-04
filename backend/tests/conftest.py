"""Pytest configuration and shared fixtures for RAG system tests"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

import pytest

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def sample_query():
    """Example query"""
    return "What is retrieval-augmented generation?"


@pytest.fixture
def sample_course_metadata():
    """Example course metadata"""
    return {
        "title": "Introduction to RAG",
        "instructor": "AI Expert",
        "course_link": "https://example.com/rag-course",
        "lesson_count": 5,
    }


@pytest.fixture
def sample_search_results():
    """Example search results"""
    from vector_store import SearchResults

    return SearchResults(
        documents=[
            "RAG combines retrieval systems with generative AI models.",
            "The retrieval component finds relevant documents from a knowledge base.",
        ],
        metadata=[
            {"course_title": "Introduction to RAG", "lesson_number": 1, "chunk_index": 0},
            {"course_title": "Advanced RAG Techniques", "lesson_number": 3, "chunk_index": 2},
        ],
        distances=[0.23, 0.45],
        error=None,
    )


@pytest.fixture
def mock_claude_tool_use_response():
    """Mock Claude API tool_use response"""
    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "search_course_content"
    tool_use_block.id = "toolu_test123"
    tool_use_block.input = {"query": "embeddings", "course_name": None, "lesson_number": None}

    initial_response = Mock()
    initial_response.stop_reason = "tool_use"
    initial_response.content = [tool_use_block]

    return initial_response


@pytest.fixture
def mock_claude_final_response():
    """Mock Claude API final text response"""
    response = Mock()
    response.stop_reason = "end_turn"

    text_block = Mock()
    text_block.text = "Based on the course materials, embeddings are numerical representations..."

    response.content = [text_block]
    return response


@pytest.fixture
def mock_rag_system():
    """Mock RAGSystem instance for API testing"""
    mock = MagicMock()
    mock.session_manager.create_session.return_value = "test_session_123"
    mock.query.return_value = ("Test answer", ["Source 1", "Source 2"])
    mock.get_course_analytics.return_value = {
        "total_courses": 3,
        "course_titles": ["Course 1", "Course 2", "Course 3"]
    }
    return mock


@pytest.fixture
def test_app():
    """
    Create a test FastAPI app without static files mounting.
    This avoids issues with missing frontend files in test environment.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional

    app = FastAPI(title="Test RAG System")

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[str]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # Mock RAG system
    mock_rag = MagicMock()
    mock_rag.session_manager.create_session.return_value = "test_session"
    mock_rag.query.return_value = ("Mock answer", ["Source 1"])
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Test Course 1", "Test Course 2"]
    }

    # Store mock in app state for access in tests
    app.state.mock_rag = mock_rag

    # Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag.session_manager.create_session()

            answer, sources = mock_rag.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        return {"message": "Test RAG API"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create test client from test app"""
    return TestClient(test_app)


@pytest.fixture
def sample_query_requests():
    """Various sample query requests for testing"""
    return [
        {"query": "What is RAG?"},
        {"query": "Explain embeddings", "session_id": "existing_session"},
        {"query": "How does vector search work?"},
        {"query": "Test with special chars: <tag> & symbols"},
        {"query": "长中文查询测试"}
    ]


@pytest.fixture
def sample_course_documents():
    """Sample course document content for testing"""
    return """
Course Title: Advanced RAG Techniques
Course Link: https://example.com/advanced-rag
Course Instructor: Dr. AI Specialist

Lesson 1: Vector Embeddings
Lesson Link: https://example.com/lesson-1
Vector embeddings are numerical representations of text that capture semantic meaning. They allow machines to understand the similarity between different pieces of text.

Lesson 2: Semantic Search
Lesson Link: https://example.com/lesson-2
Semantic search uses vector embeddings to find relevant documents based on meaning rather than keyword matching.
"""


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for AI generator testing"""
    mock_client = MagicMock()

    # Mock messages.create response
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"

    text_block = MagicMock()
    text_block.text = "This is a test response from the AI."
    mock_response.content = [text_block]

    mock_client.messages.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_vector_store():
    """Mock VectorStore for testing"""
    mock_store = MagicMock()

    # Mock search results
    from vector_store import SearchResults
    mock_store.search.return_value = SearchResults(
        documents=["Test document content"],
        metadata=[{"course_title": "Test Course", "lesson_number": 1}],
        distances=[0.1],
        error=None
    )

    mock_store.get_all_courses.return_value = [
        {
            "title": "Test Course",
            "instructor": "Test Instructor",
            "course_link": "https://example.com"
        }
    ]

    return mock_store


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager for testing"""
    mock_manager = MagicMock()
    mock_manager.create_session.return_value = "test_session_123"
    mock_manager.get_session.return_value = []
    mock_manager.add_exchange.return_value = None
    mock_manager.get_history.return_value = []
    mock_manager.clear_session.return_value = None
    return mock_manager
