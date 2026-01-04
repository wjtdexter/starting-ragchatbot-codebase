"""Tests for RAGSystem query end-to-end flow"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rag_system import RAGSystem


class TestRAGSystemQuery:
    """Test RAGSystem.query() end-to-end flow"""

    @pytest.fixture
    def mock_config(self):
        """Mock config object"""
        config = Mock()
        config.CHUNK_SIZE = 800
        config.CHUNK_OVERLAP = 100
        config.CHROMA_PATH = "./test_chroma_db"
        config.EMBEDDING_MODEL = "test-model"
        config.MAX_RESULTS = 5
        config.MAX_HISTORY = 2
        config.ANTHROPIC_API_KEY = "test-key"
        config.ANTHROPIC_MODEL = "claude-test"
        return config

    @pytest.fixture
    def rag_system(self, mock_config):
        """Create RAGSystem instance with Mock components"""
        with patch('rag_system.DocumentProcessor'), \
             patch('rag_system.VectorStore') as mock_vs, \
             patch('rag_system.AIGenerator') as mock_ai, \
             patch('rag_system.SessionManager'):

            system = RAGSystem(mock_config)

            # Configure mocks
            system.ai_generator.generate_response = Mock(return_value="Test response")
            system.tool_manager.get_last_sources = Mock(return_value=["Source 1"])
            system.tool_manager.reset_sources = Mock()  # Mock the reset method

            return system

    def test_query_successful_flow(self, rag_system):
        """Test: Complete successful query flow"""
        # Execute query
        answer, sources = rag_system.query("What is RAG?", session_id="session_1")

        # Verify AI generator is called
        rag_system.ai_generator.generate_response.assert_called_once()
        call_args = rag_system.ai_generator.generate_response.call_args

        # Verify tools are passed
        assert "tools" in call_args.kwargs
        assert "tool_manager" in call_args.kwargs

        # Verify return values
        assert answer == "Test response"
        assert sources == ["Source 1"]

        # Verify session history is recorded
        rag_system.session_manager.add_exchange.assert_called_once_with(
            "session_1",
            "What is RAG?",
            "Test response"
        )

    def test_query_without_session(self, rag_system):
        """Test: Query without session_id"""
        answer, sources = rag_system.query("Test query")

        # Should still call AI generator
        assert rag_system.ai_generator.generate_response.called

        # Should return results
        assert answer == "Test response"
        assert sources == ["Source 1"]

    def test_query_with_history(self, rag_system):
        """Test: Query with conversation history"""
        # Mock session manager returns history
        rag_system.session_manager.get_conversation_history = Mock(
            return_value="User: Previous\nAssistant: Answer"
        )

        rag_system.query("New question", session_id="session_1")

        # Verify history is passed to AI generator
        call_args = rag_system.ai_generator.generate_response.call_args
        assert "conversation_history" in call_args.kwargs
        assert call_args.kwargs["conversation_history"] == "User: Previous\nAssistant: Answer"

    def test_query_propagates_ai_exception(self, rag_system):
        """Test: AI generator exception propagation"""
        # Mock AI generator throws exception
        rag_system.ai_generator.generate_response.side_effect = Exception("API Error")

        # Query should raise exception
        with pytest.raises(Exception, match="API Error"):
            rag_system.query("Test query")

    def test_query_tools_and_sources_integration(self, rag_system):
        """Test: Tool calls and sources integration complete flow"""
        # Mock AI uses tools and returns results
        rag_system.ai_generator.generate_response.return_value = "Based on the search..."
        rag_system.tool_manager.get_last_sources.return_value = [
            '<a href="http://example.com">Course - Lesson 1</a>',
            '<a href="http://example.com">Course - Lesson 2</a>'
        ]

        answer, sources = rag_system.query("Tell me about embeddings")

        # Verify sources are correctly retrieved
        assert len(sources) == 2
        assert sources[0] == '<a href="http://example.com">Course - Lesson 1</a>'

        # Verify sources are reset after retrieval
        rag_system.tool_manager.reset_sources.assert_called_once()

    def test_query_with_empty_tool_results(self, rag_system):
        """Test: Query with empty tool results"""
        rag_system.ai_generator.generate_response.return_value = "No information found."
        rag_system.tool_manager.get_last_sources.return_value = []

        answer, sources = rag_system.query("obscure topic")

        # Should still return answer but with empty sources
        assert answer == "No information found."
        assert sources == []

    def test_query_prompt_formatting(self, rag_system):
        """Test: Query is properly formatted in prompt"""
        rag_system.query("test query")

        # Verify the prompt includes the query
        call_args = rag_system.ai_generator.generate_response.call_args
        assert "test query" in call_args.kwargs["query"]
        assert "course materials" in call_args.kwargs["query"].lower()

    def test_get_course_analytics(self, rag_system):
        """Test: Get course analytics"""
        # Mock vector store analytics
        rag_system.vector_store.get_course_count = Mock(return_value=5)
        rag_system.vector_store.get_existing_course_titles = Mock(
            return_value=["Course 1", "Course 2"]
        )

        analytics = rag_system.get_course_analytics()

        assert analytics["total_courses"] == 5
        assert analytics["course_titles"] == ["Course 1", "Course 2"]

    def test_add_course_document(self, rag_system):
        """Test: Add single course document"""
        # Mock document processor
        mock_course = Mock()
        mock_course.title = "Test Course"
        mock_chunks = [Mock(), Mock(), Mock()]

        rag_system.document_processor.process_course_document = Mock(
            return_value=(mock_course, mock_chunks)
        )

        course, chunk_count = rag_system.add_course_document("test.txt")

        assert course == mock_course
        assert chunk_count == 3
        rag_system.vector_store.add_course_metadata.assert_called_once_with(mock_course)
        rag_system.vector_store.add_course_content.assert_called_once_with(mock_chunks)

    def test_add_course_document_error_handling(self, rag_system):
        """Test: Error handling when adding document"""
        rag_system.document_processor.process_course_document = Mock(
            side_effect=Exception("Parse error")
        )

        course, chunk_count = rag_system.add_course_document("bad.txt")

        # Should return None and 0 on error
        assert course is None
        assert chunk_count == 0
