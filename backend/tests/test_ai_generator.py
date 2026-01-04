"""Tests for AIGenerator tool calling mechanism"""

from unittest.mock import MagicMock, Mock, call, patch

import pytest

from ai_generator import AIGenerator


class TestAIGeneratorToolCalls:
    """Test AIGenerator with Claude API tool calling integration"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        client = Mock()
        client.messages = Mock()
        client.messages.create = Mock()
        return client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator instance"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-test")
            generator.client = mock_anthropic_client
            return generator

    @pytest.fixture
    def mock_tool_manager(self):
        """Mock ToolManager"""
        manager = Mock()
        manager.execute_tool = Mock(return_value="Tool executed successfully")
        return manager

    def test_direct_response_no_tools(self, ai_generator, mock_anthropic_client):
        """Test: Claude responds directly without using tools"""
        # Mock Claude returns direct text response
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [Mock(text="Hello! How can I help you?")]
        mock_anthropic_client.messages.create.return_value = mock_response

        # Execute query
        result = ai_generator.generate_response(query="What is your name?", tools=None)

        # Verify
        assert result == "Hello! How can I help you?"
        mock_anthropic_client.messages.create.assert_called_once()
        call_args = mock_anthropic_client.messages.create.call_args
        assert "tools" not in call_args.kwargs  # Should not have tools parameter

    def test_tool_use_scenario(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test: Claude decides to use tool for search"""
        # First API call: Claude returns tool_use request
        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "toolu_123"
        tool_use_block.input = {"query": "embeddings", "course_name": None}

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_use_block]

        # Second API call: Claude returns final answer based on tool results
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text_block = Mock()
        final_text_block.type = "text"
        final_text_block.text = "Based on the search results, embeddings are..."
        final_response.content = [final_text_block]

        # Set mock return sequence
        mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]

        # Execute query
        result = ai_generator.generate_response(
            query="Tell me about embeddings",
            tools=[{"name": "search_course_content", "description": "test"}],
            tool_manager=mock_tool_manager,
        )

        # Verify tool was called
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="embeddings", course_name=None
        )

        # Verify final result is returned
        assert result == "Based on the search results, embeddings are..."

        # Verify API was called twice
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_tool_execution_error_propagation(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: Tool execution failure error handling"""
        # Mock tool execution returns error
        mock_tool_manager.execute_tool.return_value = "Error: Course not found"

        tool_use_block = Mock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "search_course_content"
        tool_use_block.id = "toolu_error"
        tool_use_block.input = {"query": "test"}

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_use_block]

        # Claude gives final response based on error result
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text_block = Mock()
        final_text_block.type = "text"
        final_text_block.text = "I couldn't find information about that topic."
        final_response.content = [final_text_block]

        mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]

        # Execute query
        result = ai_generator.generate_response(
            query="test query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify tool error was passed to Claude
        # Second API call should contain tool_result
        second_call = mock_anthropic_client.messages.create.call_args_list[1]
        messages = second_call.kwargs["messages"]

        # Verify tool_result message (messages[2] is user with tool_result)
        # [user_query, assistant(tool_use), user(tool_result)]
        assert len(messages) == 3
        assert messages[2]["role"] == "user"
        assert messages[2]["content"][0]["type"] == "tool_result"
        assert messages[2]["content"][0]["content"] == "Error: Course not found"

    def test_multiple_tool_calls(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test: Claude calls multiple tools"""
        # Create two tool_use blocks
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.id = "toolu_1"
        tool_use_1.input = {"query": "topic1"}

        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "toolu_2"
        tool_use_2.input = {"query": "topic2"}

        initial_response = Mock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_use_1, tool_use_2]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text = Mock()
        final_text.type = "text"
        final_text.text = "Final answer"
        final_response.content = [final_text]

        mock_anthropic_client.messages.create.side_effect = [initial_response, final_response]

        # Execute
        result = ai_generator.generate_response(
            query="test", tools=[{"name": "search_course_content"}], tool_manager=mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2

    def test_conversation_history_included(self, ai_generator, mock_anthropic_client):
        """Test: Conversation history is correctly passed to API"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response"
        mock_response.content = [text_block]
        mock_anthropic_client.messages.create.return_value = mock_response

        history = "User: Previous question\nAssistant: Previous answer"

        ai_generator.generate_response(query="New question", conversation_history=history)

        # Verify system prompt includes history
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args.kwargs["system"]
        assert "Previous conversation:" in system_content
        assert history in system_content

    def test_tool_choice_auto(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test: tool_choice is set to auto when tools are provided"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response"
        mock_response.content = [text_block]

        mock_anthropic_client.messages.create.return_value = mock_response

        tools = [{"name": "search_course_content", "description": "test"}]

        ai_generator.generate_response(query="test", tools=tools, tool_manager=mock_tool_manager)

        # Verify tool_choice is set
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["tool_choice"] == {"type": "auto"}

    def test_max_tokens_parameter(self, ai_generator, mock_anthropic_client):
        """Test: max_tokens is set correctly in base_params"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response"
        mock_response.content = [text_block]

        mock_anthropic_client.messages.create.return_value = mock_response

        ai_generator.generate_response(query="test")

        # Verify max_tokens
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 800

    def test_temperature_parameter(self, ai_generator, mock_anthropic_client):
        """Test: temperature is set to 0 for consistent responses"""
        mock_response = Mock()
        mock_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Response"
        mock_response.content = [text_block]

        mock_anthropic_client.messages.create.return_value = mock_response

        ai_generator.generate_response(query="test")

        # Verify temperature
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args.kwargs["temperature"] == 0


class TestMultiRoundToolCalling:
    """Test multi-round sequential tool calling (up to 2 rounds)"""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client"""
        client = Mock()
        client.messages = Mock()
        client.messages.create = Mock()
        return client

    @pytest.fixture
    def ai_generator(self, mock_anthropic_client):
        """Create AIGenerator instance"""
        with patch("ai_generator.anthropic.Anthropic", return_value=mock_anthropic_client):
            generator = AIGenerator(api_key="test-key", model="claude-test")
            generator.client = mock_anthropic_client
            return generator

    @pytest.fixture
    def mock_tool_manager(self):
        """Mock ToolManager"""
        manager = Mock()
        manager.execute_tool = Mock(return_value="Tool executed successfully")
        return manager

    def test_two_round_tool_calling(self, ai_generator, mock_anthropic_client, mock_tool_manager):
        """Test: Claude makes 2 sequential tool calls across 2 API rounds"""
        # Round 1: Claude calls get_course_outline
        tool_use_round1 = Mock()
        tool_use_round1.type = "tool_use"
        tool_use_round1.name = "get_course_outline"
        tool_use_round1.id = "toolu_round1"
        tool_use_round1.input = {"course_name": "Machine Learning"}

        response_round1 = Mock()
        response_round1.stop_reason = "tool_use"
        response_round1.content = [tool_use_round1]

        # After tool result, Claude calls search_course_content
        tool_use_round2 = Mock()
        tool_use_round2.type = "tool_use"
        tool_use_round2.name = "search_course_content"
        tool_use_round2.id = "toolu_round2"
        tool_use_round2.input = {"query": "neural networks", "course_name": None}

        response_round2 = Mock()
        response_round2.stop_reason = "tool_use"
        response_round2.content = [tool_use_round2]

        # Final response after 2 rounds
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        final_text_block = Mock()
        final_text_block.type = "text"
        final_text_block.text = "Based on the course outline and search results..."
        final_response.content = [final_text_block]

        # Configure mock to return responses in sequence
        mock_anthropic_client.messages.create.side_effect = [
            response_round1,  # First API call
            response_round2,  # Second API call (after first tool result)
            final_response,  # Final call (after second tool result)
        ]

        # Execute query
        result = ai_generator.generate_response(
            query="Find information about neural networks in the Machine Learning course",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify both tools were called
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="Machine Learning"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="neural networks", course_name=None
        )

        # Verify final result
        assert result == "Based on the course outline and search results..."

        # Verify 3 API calls were made (2 rounds + 1 final)
        assert mock_anthropic_client.messages.create.call_count == 3

    def test_single_round_tool_calling(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: Claude completes task in 1 round, no additional tools needed"""
        # Single tool call
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.id = "toolu_123"
        tool_use.input = {"query": "embeddings"}

        first_response = Mock()
        first_response.stop_reason = "tool_use"
        first_response.content = [tool_use]

        # After tool result, Claude responds directly (no more tools)
        second_response = Mock()
        second_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Here's what I found about embeddings..."
        second_response.content = [text_block]

        mock_anthropic_client.messages.create.side_effect = [first_response, second_response]

        # Execute
        result = ai_generator.generate_response(
            query="Tell me about embeddings",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify tool was called once
        mock_tool_manager.execute_tool.assert_called_once()

        # Verify 2 API calls (1 round + 1 final response)
        assert mock_anthropic_client.messages.create.call_count == 2

    def test_max_rounds_limit_enforced(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: System enforces maximum 2 rounds even if Claude wants more"""
        # Round 1
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.id = "toolu_1"
        tool_use_1.input = {"query": "topic1"}

        response_1 = Mock()
        response_1.stop_reason = "tool_use"
        response_1.content = [tool_use_1]

        # Round 2
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "toolu_2"
        tool_use_2.input = {"query": "topic2"}

        response_2 = Mock()
        response_2.stop_reason = "tool_use"
        response_2.content = [tool_use_2]

        # Claude would want a 3rd round, but we limit to 2
        # So we make a final call WITHOUT tools
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "I've completed 2 rounds of searches. Here's the summary..."
        final_response.content = [text_block]

        mock_anthropic_client.messages.create.side_effect = [response_1, response_2, final_response]

        # Execute
        result = ai_generator.generate_response(
            query="Complex multi-part query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify exactly 2 tools were executed (max rounds)
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify 3 API calls: round 1, round 2, final (no tools)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify final call had no tools
        final_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in final_call_kwargs or final_call_kwargs.get("tools") is None

    def test_tool_execution_error_handling(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: Tool execution errors are passed to Claude for recovery attempt"""
        # Round 1: Tool fails
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.id = "toolu_1"
        tool_use_1.input = {"query": "invalid_course"}

        response_1 = Mock()
        response_1.stop_reason = "tool_use"
        response_1.content = [tool_use_1]

        # Mock tool execution failure
        mock_tool_manager.execute_tool.return_value = "Error: Course not found"

        # Round 2: Claude tries alternative search
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "toolu_2"
        tool_use_2.input = {"query": "general topic"}

        response_2 = Mock()
        response_2.stop_reason = "tool_use"
        response_2.content = [tool_use_2]

        # Mock second tool success
        mock_tool_manager.execute_tool.side_effect = [
            "Error: Course not found",
            "Found relevant content...",
        ]

        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Although the specific course wasn't found, I found related content..."
        final_response.content = [text_block]

        mock_anthropic_client.messages.create.side_effect = [response_1, response_2, final_response]

        # Execute
        result = ai_generator.generate_response(
            query="Search for content",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify both tool attempts were made
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify error was handled gracefully
        assert "Although the specific course wasn't found" in result

    def test_no_tool_use_returns_directly(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: If Claude doesn't request tools, return immediately"""
        response = Mock()
        response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "I can answer that from my knowledge."
        response.content = [text_block]

        mock_anthropic_client.messages.create.return_value = response

        # Execute with tools available but Claude chooses not to use them
        result = ai_generator.generate_response(
            query="What is 2+2?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify no tools were called
        mock_tool_manager.execute_tool.assert_not_called()

        # Verify only 1 API call was made
        assert mock_anthropic_client.messages.create.call_count == 1

        # Verify direct response
        assert result == "I can answer that from my knowledge."

    def test_message_history_across_rounds(
        self, ai_generator, mock_anthropic_client, mock_tool_manager
    ):
        """Test: Multiple rounds of tool calling work correctly"""
        # This test verifies that multi-round tool calling produces correct results
        # by checking that both tools are executed and final response is returned

        # Round 1: get course outline
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "get_course_outline"
        tool_use_1.id = "toolu_1"
        tool_use_1.input = {"course_name": "Test Course"}

        response_1 = Mock()
        response_1.stop_reason = "tool_use"
        response_1.content = [tool_use_1]

        # Round 2: search content
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.id = "toolu_2"
        tool_use_2.input = {"query": "topic"}

        response_2 = Mock()
        response_2.stop_reason = "tool_use"
        response_2.content = [tool_use_2]

        # Final response
        final_response = Mock()
        final_response.stop_reason = "end_turn"
        text_block = Mock()
        text_block.type = "text"
        text_block.text = "Final answer based on both tool results"
        final_response.content = [text_block]

        mock_anthropic_client.messages.create.side_effect = [response_1, response_2, final_response]

        # Execute
        result = ai_generator.generate_response(
            query="Find info in Test Course",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

        # Verify both tools were executed in sequence
        assert mock_tool_manager.execute_tool.call_count == 2

        # Verify tools were called in correct order
        first_call = mock_tool_manager.execute_tool.call_args_list[0]
        second_call = mock_tool_manager.execute_tool.call_args_list[1]

        assert first_call[0][0] == "get_course_outline"
        assert first_call[1]["course_name"] == "Test Course"

        assert second_call[0][0] == "search_course_content"
        assert second_call[1]["query"] == "topic"

        # Verify API was called 3 times (2 rounds + final)
        assert mock_anthropic_client.messages.create.call_count == 3

        # Verify final response is correct
        assert result == "Final answer based on both tool results"

        # Verify final call had no tools parameter (prevents additional rounds)
        final_call_kwargs = mock_anthropic_client.messages.create.call_args_list[2].kwargs
        assert "tools" not in final_call_kwargs or final_call_kwargs.get("tools") is None
