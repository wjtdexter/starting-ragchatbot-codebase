"""Tests for CourseSearchTool execute method"""

from unittest.mock import MagicMock, Mock

import pytest

from search_tools import CourseSearchTool
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test CourseSearchTool core functionality"""

    @pytest.fixture
    def mock_vector_store(self):
        """Mock VectorStore instance"""
        store = Mock()
        store.search = Mock()
        store.get_lesson_link = Mock(return_value="http://example.com/lesson1")
        store.get_course_link = Mock(return_value="http://example.com/course")
        return store

    @pytest.fixture
    def search_tool(self, mock_vector_store):
        """Create CourseSearchTool instance"""
        return CourseSearchTool(mock_vector_store)

    def test_execute_with_valid_results(self, search_tool, mock_vector_store):
        """Test: Normal search query with results"""
        # Prepare mock search results
        mock_results = SearchResults(
            documents=["Content about embeddings"],
            metadata=[{"course_title": "Introduction to RAG", "lesson_number": 1}],
            distances=[0.23],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        # Execute search
        result = search_tool.execute(query="embeddings")

        # Verify
        assert "Introduction to RAG" in result
        assert "Content about embeddings" in result
        assert search_tool.last_sources  # Should track sources
        mock_vector_store.search.assert_called_once_with(
            query="embeddings", course_name=None, lesson_number=None
        )

    def test_execute_with_no_results(self, search_tool, mock_vector_store):
        """Test: Empty results scenario"""
        # Mock empty results
        mock_results = SearchResults(documents=[], metadata=[], distances=[], error=None)
        mock_vector_store.search.return_value = mock_results

        # Execute search
        result = search_tool.execute(query="nonexistent topic")

        # Verify
        assert result == "No relevant content found."
        assert search_tool.last_sources == []  # No sources

    def test_execute_with_course_filter(self, search_tool, mock_vector_store):
        """Test: Search with course name filter"""
        mock_results = SearchResults(
            documents=["RAG content"],
            metadata=[{"course_title": "RAG Course", "lesson_number": 1}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        # Execute search with course filter
        result = search_tool.execute(query="embeddings", course_name="RAG")

        # Verify parameters passed correctly
        mock_vector_store.search.assert_called_once_with(
            query="embeddings", course_name="RAG", lesson_number=None
        )
        assert "RAG Course" in result

    def test_execute_with_lesson_filter(self, search_tool, mock_vector_store):
        """Test: Search with lesson number filter"""
        mock_results = SearchResults(
            documents=["Lesson 2 content"],
            metadata=[{"course_title": "Course", "lesson_number": 2}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="topic", lesson_number=2)

        mock_vector_store.search.assert_called_once_with(
            query="topic", course_name=None, lesson_number=2
        )

    def test_execute_with_search_error(self, search_tool, mock_vector_store):
        """Test: Search error scenario"""
        # Mock search returns error
        mock_results = SearchResults.empty("Database connection failed")
        mock_vector_store.search.return_value = mock_results

        # Execute search
        result = search_tool.execute(query="test")

        # Verify error is returned
        assert result == "Database connection failed"

    def test_execute_with_combined_filters(self, search_tool, mock_vector_store):
        """Test: Search with both course and lesson filters"""
        mock_results = SearchResults(
            documents=["Filtered content"],
            metadata=[{"course_title": "Course", "lesson_number": 3}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.search.return_value = mock_results

        result = search_tool.execute(query="test", course_name="Course", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="test", course_name="Course", lesson_number=3
        )

    def test_get_tool_definition(self, search_tool):
        """Test: Tool definition format is correct"""
        definition = search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert "query" in definition["input_schema"]["required"]
