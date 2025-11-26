"""
Shared helpers for formatting conversation histories and tool outputs.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


class ConversationFormatter:
    """
    Formats Claude conversation history markdown and tool outputs.
    """

    def __init__(
        self,
        log_title: str,
        test_file_path: str,
        include_test_results: bool = False,
    ):
        self.log_title = log_title
        self.test_file_path = test_file_path
        self.include_test_results = include_test_results

    @staticmethod
    def format_tool_output(content: Any) -> str:
        if isinstance(content, (dict, list)):
            try:
                import json

                return json.dumps(content, indent=2, ensure_ascii=False)
            except (TypeError, ValueError):
                return str(content)
        if isinstance(content, str):
            return content
        return str(content)

    def format_conversation(
        self,
        conversation_history: List[Dict[str, Any]],
        show_tool_summary: bool = False,
    ) -> str:
        lines: List[str] = []
        lines.append(f"# {self.log_title}")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**Test File:** {self.test_file_path}")
        lines.append("")
        lines.append("---")
        lines.append("")

        for idx, entry in enumerate(conversation_history, 1):
            step_name = entry.get("step", f"Step {idx}")
            user_prompt = entry.get("user_prompt", "")
            messages = entry.get("messages", [])
            tool_outputs = entry.get("tool_outputs", {})
            test_result = entry.get("test_result")

            lines.append(f"## {step_name}")
            lines.append("")

            if user_prompt:
                lines.append("### User Prompt")
                lines.append("")
                lines.append("```")
                lines.append(user_prompt)
                lines.append("```")
                lines.append("")

            if self.include_test_results and test_result is not None:
                success, output = test_result
                status = "✅ Success" if success else "❌ Failed"
                lines.append(f"### Test Execution Result: {status}")
                lines.append("")
                lines.append("```")
                if len(output) > 5000:
                    lines.append(output[:5000])
                    lines.append("\n... (truncated)")
                else:
                    lines.append(output)
                lines.append("```")
                lines.append("")

            lines.append("### Claude's Response")
            lines.append("")

            tool_use_map: Dict[str, Any] = {}
            for message in messages:
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            lines.append(block.text)
                            lines.append("")
                        elif isinstance(block, ToolUseBlock):
                            tool_use_map[block.id] = block
                            lines.append(f"#### Tool: {block.name}")
                            lines.append("")
                            lines.append("**Input:**")
                            lines.append("")
                            lines.append("```json")
                            lines.append(
                                ConversationFormatter.format_tool_output(block.input)
                            )
                            lines.append("```")
                            lines.append("")
                elif isinstance(message, UserMessage):
                    for block in message.content:
                        if isinstance(block, ToolResultBlock):
                            tool_name = "Unknown"
                            if block.tool_use_id in tool_use_map:
                                tool_name = tool_use_map[block.tool_use_id].name
                            lines.append(f"**Output ({tool_name}):**")
                            lines.append("")
                            output_content = block.content
                            if isinstance(output_content, list) and len(output_content) > 0:
                                first_item = output_content[0]
                                if isinstance(first_item, dict) and 'text' in first_item:
                                    lines.append("```")
                                    lines.append(first_item['text'])
                                    lines.append("```")
                                else:
                                    lines.append("```json")
                                    lines.append(
                                        ConversationFormatter.format_tool_output(
                                            output_content
                                        )
                                    )
                                    lines.append("```")
                            else:
                                lines.append("```json")
                                lines.append(
                                    ConversationFormatter.format_tool_output(
                                        output_content
                                    )
                                )
                                lines.append("```")
                            lines.append("")

            if show_tool_summary and tool_outputs:
                lines.append("### Tool Outputs Summary")
                lines.append("")
                for tool_id, output in tool_outputs.items():
                    tool_info = tool_use_map.get(tool_id)
                    tool_name = tool_info.name if tool_info else "Unknown"
                    lines.append(f"**{tool_name} ({tool_id}):**")
                    lines.append("")
                    lines.append("```json")
                    lines.append(
                        ConversationFormatter.format_tool_output(output)
                    )
                    lines.append("```")
                    lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def save(
        self,
        conversation_history: List[Dict[str, Any]],
        output_path: Path,
        show_tool_summary: bool = False,
    ):
        markdown = self.format_conversation(
            conversation_history, show_tool_summary=show_tool_summary
        )
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"\nConversation saved to: {output_path.absolute()}")

