"""Tests for VectorStore search method"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from vector_store import SearchResults, VectorStore


class TestVectorStore:
    """Test VectorStore core functionality"""

    @pytest.fixture
    def mock_chroma_client(self):
        """Mock ChromaDB client"""
        client = Mock()

        # Mock collections
        catalog_collection = Mock()
        content_collection = Mock()

        client.get_or_create_collection = Mock(
            side_effect=lambda name, **kwargs: (
                catalog_collection if name == "course_catalog" else content_collection
            )
        )

        return client, catalog_collection, content_collection

    @pytest.fixture
    def vector_store(self, mock_chroma_client):
        """Create VectorStore instance"""
        client, catalog, content = mock_chroma_client

        with (
            patch("vector_store.chromadb.PersistentClient", return_value=client),
            patch(
                "vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ),
        ):

            store = VectorStore(
                chroma_path="./test_db", embedding_model="test-model", max_results=5
            )
            store.client = client
            store.course_catalog = catalog
            store.course_content = content

            return store

    def test_search_without_filters(self, vector_store):
        """Test: Search without filters"""
        # Mock query results
        vector_store.course_content.query.return_value = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"course_title": "Course1"}, {"course_title": "Course2"}]],
            "distances": [[0.1, 0.2]],
        }

        results = vector_store.search(query="test query")

        # Verify return format
        assert isinstance(results, SearchResults)
        assert len(results.documents) == 2
        assert results.documents[0] == "doc1"
        assert not results.is_empty()
        assert results.error is None

        # Verify query was called
        vector_store.course_content.query.assert_called_once_with(
            query_texts=["test query"], n_results=5, where=None
        )

    def test_search_with_course_filter(self, vector_store):
        """Test: Search with course name filter"""
        vector_store.course_catalog.query.return_value = {
            "documents": [["Full Course Name"]],
            "metadatas": [[{"title": "Full Course Name"}]],
        }

        vector_store.course_content.query.return_value = {
            "documents": [["filtered doc"]],
            "metadatas": [[{"course_title": "Full Course Name"}]],
            "distances": [[0.1]],
        }

        results = vector_store.search(query="test", course_name="Partial Course")

        # Verify course name resolution
        vector_store.course_catalog.query.assert_called_once()

        # Verify content search uses correct filter
        vector_store.course_content.query.assert_called_once()
        call_args = vector_store.course_content.query.call_args
        assert call_args.kwargs["where"] == {"course_title": "Full Course Name"}

    def test_search_course_not_found(self, vector_store):
        """Test: Course name not found"""
        # Mock catalog query returns empty
        vector_store.course_catalog.query.return_value = {"documents": [[]], "metadatas": [[]]}

        results = vector_store.search(query="test", course_name="Nonexistent")

        # Verify empty results with error
        assert results.is_empty()
        assert "No course found" in results.error
        assert "Nonexistent" in results.error

    def test_search_with_lesson_filter(self, vector_store):
        """Test: Search with lesson number filter"""
        vector_store.course_content.query.return_value = {
            "documents": [["lesson content"]],
            "metadatas": [[{"lesson_number": 2}]],
            "distances": [[0.1]],
        }

        results = vector_store.search(query="test", lesson_number=2)

        # Verify lesson filter is used
        call_args = vector_store.course_content.query.call_args
        assert call_args.kwargs["where"] == {"lesson_number": 2}

    def test_search_with_combined_filters(self, vector_store):
        """Test: Combined course + lesson filter"""
        vector_store.course_catalog.query.return_value = {
            "documents": [["Course Name"]],
            "metadatas": [[{"title": "Course Name"}]],
        }

        vector_store.course_content.query.return_value = {
            "documents": [["content"]],
            "metadatas": [[{"course_title": "Course Name", "lesson_number": 3}]],
            "distances": [[0.1]],
        }

        results = vector_store.search(query="test", course_name="Course", lesson_number=3)

        # Verify AND filter is used
        call_args = vector_store.course_content.query.call_args
        assert call_args.kwargs["where"] == {
            "$and": [{"course_title": "Course Name"}, {"lesson_number": 3}]
        }

    def test_search_exception_handling(self, vector_store):
        """Test: Search exception handling"""
        vector_store.course_content.query.side_effect = Exception("DB Error")

        results = vector_store.search(query="test")

        # Verify error is caught and returned
        assert results.is_empty()
        assert "Search error" in results.error
        assert "DB Error" in results.error

    def test_search_with_limit_override(self, vector_store):
        """Test: Search with custom limit"""
        vector_store.course_content.query.return_value = {
            "documents": [["doc1"]],
            "metadatas": [[{"course_title": "Course1"}]],
            "distances": [[0.1]],
        }

        results = vector_store.search(query="test", limit=3)

        # Verify custom limit is used
        call_args = vector_store.course_content.query.call_args
        assert call_args.kwargs["n_results"] == 3
