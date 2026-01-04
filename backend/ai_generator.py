import logging
from typing import Any, Dict, List, Optional, Tuple

import anthropic

logger = logging.getLogger(__name__)


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content**: Search course materials by semantic similarity
   - Use for specific content questions (topics, concepts, explanations)
   - Supports filtering by course and lesson
   - One search per query maximum

2. **get_course_outline**: Get course structure and lesson list
   - Use for outline queries (e.g., "what's the outline", "what lessons", "course structure")
   - Returns: course title, link, instructor, and complete lesson list with numbers and titles
   - One query per request maximum

Multi-Round Tool Usage:
- You can make up to 2 rounds of tool calls to complete complex queries
- Round 1: Make initial tool calls based on the user's request
- Round 2: Use results from round 1 to inform additional searches or provide final answer
- Example: "Compare lesson 4 of course X with similar content" → Round 1: get outline → Round 2: search for similar topics
- If a tool execution fails, you can attempt alternative approaches in the next round

Tool Usage Guidelines:
- Choose the right tool based on the query type
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives
- Prioritize completing tasks within 2 rounds when possible

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course content questions**: Use search_course_content
- **Course structure/outline questions**: Use get_course_outline
- **No meta-commentary**: Provide direct answers only — no reasoning process, tool explanations, or question-type analysis

All responses must be:
1. **Brief and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

        # Maximum rounds of tool calling
        self.max_tool_rounds = 2

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """
        # Build system content
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Build initial messages
        messages = self._build_initial_messages(query)

        # If tools are available, execute multi-round tool calling
        if tools and tool_manager:
            return self._execute_tool_rounds(messages, system_content, tools, tool_manager)

        # No tools: direct API call
        api_params = {**self.base_params, "messages": messages, "system": system_content}
        response = self.client.messages.create(**api_params)
        return response.content[0].text

    def _execute_tool_rounds(
        self, messages: List[Dict], system_content: str, tools: List, tool_manager
    ) -> str:
        """
        Execute multiple rounds of tool calling (max 2 rounds).

        Args:
            messages: Current message history
            system_content: System prompt content
            tools: Available tools
            tool_manager: Tool execution manager

        Returns:
            Final response text
        """
        for round_num in range(1, self.max_tool_rounds + 1):
            logger.info(f"工具调用轮次 {round_num}/{self.max_tool_rounds}")

            # A. Call Claude API
            response_text, tool_blocks = self._call_claude_api(messages, system_content, tools)

            # B. Check if Claude wants to use tools
            if not tool_blocks:
                logger.info("无工具调用，终止流程")
                return response_text

            # C. Add assistant message with tool_use blocks to history
            assistant_msg = self._create_assistant_message(response_text, tool_blocks)
            messages.append(assistant_msg)

            # D. Execute tools
            tool_results, execution_success = self._execute_tool_calls(tool_blocks, tool_manager)

            # E. Add tool results to history
            tool_result_msg = self._create_tool_result_message(tool_results)
            messages.append(tool_result_msg)

            # F. Check if should continue to next round
            if not self._should_continue_to_next_round(round_num, execution_success):
                logger.info(f"在轮次 {round_num} 后终止")
                break

        # If we've completed max rounds and still have tools, make one final call
        # to get Claude's final response based on all tool results
        logger.info("达到最大轮次，获取最终响应")
        final_response_text, _ = self._call_claude_api(
            messages, system_content, tools=None  # No tools in final call
        )
        return final_response_text

    def _call_claude_api(
        self, messages: List[Dict], system_content: str, tools: Optional[List]
    ) -> Tuple[str, List]:
        """
        Make a single API call to Claude.

        Args:
            messages: Message history
            system_content: System prompt
            tools: Available tools (or None for no tools)

        Returns:
            Tuple of (response_text, tool_blocks)
        """
        api_params = {**self.base_params, "messages": messages, "system": system_content}

        # Add tools if provided
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response
        response = self.client.messages.create(**api_params)

        # Extract response text and tool_use blocks
        response_text = ""
        tool_blocks = []

        for content_block in response.content:
            if content_block.type == "text":
                response_text = content_block.text
            elif content_block.type == "tool_use":
                tool_blocks.append(content_block)

        return response_text, tool_blocks

    def _execute_tool_calls(self, tool_blocks: List, tool_manager) -> Tuple[List[Dict], bool]:
        """
        Execute all tool calls and collect results.

        Args:
            tool_blocks: List of tool_use content blocks
            tool_manager: Tool execution manager

        Returns:
            Tuple of (tool_results, all_success)
        """
        results = []
        all_success = True

        for block in tool_blocks:
            try:
                logger.info(f"执行工具: {block.name}")
                result = tool_manager.execute_tool(block.name, **block.input)

                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                        "is_error": False,
                    }
                )

            except Exception as e:
                logger.error(f"工具 {block.name} 执行失败: {e}")
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": f"错误: {str(e)}",
                        "is_error": True,
                    }
                )
                all_success = False

        return results, all_success

    def _should_continue_to_next_round(self, round_num: int, execution_success: bool) -> bool:
        """
        Determine if we should continue to the next round of tool calling.

        Args:
            round_num: Current round number
            execution_success: Whether all tools executed successfully

        Returns:
            True if should continue, False otherwise
        """
        # Condition A: Reached max rounds
        if round_num >= self.max_tool_rounds:
            logger.info("达到最大工具调用轮次")
            return False

        # Condition B: Tool execution failed
        # We still continue to let Claude see the error and decide what to do
        # This allows for graceful error handling

        return True

    def _build_initial_messages(self, query: str) -> List[Dict]:
        """Build initial message list with user query."""
        return [{"role": "user", "content": query}]

    def _create_assistant_message(self, response_text: str, tool_blocks: List) -> Dict:
        """
        Create an assistant message containing tool_use blocks.

        Args:
            response_text: Text response from Claude
            tool_blocks: List of tool_use content blocks

        Returns:
            Message dict for assistant role
        """
        # Build content list: text (if any) + tool_use blocks
        content = []

        # Add text if present
        if response_text:
            # Create a mock text block
            text_block = type("obj", (object,), {"type": "text", "text": response_text})
            content.append(text_block)

        # Add tool_use blocks
        content.extend(tool_blocks)

        return {"role": "assistant", "content": content}

    def _create_tool_result_message(self, tool_results: List[Dict]) -> Dict:
        """
        Create a user message containing tool results.

        Args:
            tool_results: List of tool result dicts

        Returns:
            Message dict for user role
        """
        return {"role": "user", "content": tool_results}
