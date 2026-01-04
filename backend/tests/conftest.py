"""Pytest configuration and shared fixtures for RAG system tests"""

import sys
from pathlib import Path

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
    from unittest.mock import Mock

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
    from unittest.mock import Mock

    response = Mock()
    response.stop_reason = "end_turn"

    text_block = Mock()
    text_block.text = "Based on the course materials, embeddings are numerical representations..."

    response.content = [text_block]
    return response
