"""
Utilities for extracting Playwright code blocks and todo information from conversation markdown files.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


class ToolCall(NamedTuple):
    """Represents a tool call with both input and output."""
    tool_name: str
    input_data: Dict
    playwright_code: str
    description: str = ""  # Optional description text before the tool call


class PlaywrightCodeExtractor:
    """
    Extracts and persists Playwright code snippets and todo information from conversation markdown logs.
    """

    _PATTERN = re.compile(r"### Ran Playwright code\s*```js\s*(.*?)\s*```", re.DOTALL)
    _TODO_PATTERN = re.compile(r"#### Tool: TodoWrite.*?```json\s*(.*?)\s*```", re.DOTALL | re.MULTILINE)
    # Pattern to find tool calls with both Input and Output
    # This pattern handles cases where there might be multiple outputs (like TodoWrite + Playwright)
    _TOOL_CALL_PATTERN = re.compile(
        r"#### Tool: ([^\n]+)\n\n\*\*Input:\*\*\n\n```json\n(.*?)\n```\n\n(?:\*\*Output.*?:\*\*\n\n```json\n.*?\n```\n\n)?\*\*Output.*?:\*\*\n\n```\n### Ran Playwright code\n```js\n(.*?)\n```",
        re.DOTALL
    )

    def __init__(self, conversation_path: Path):
        self.conversation_path = conversation_path

    def extract(self) -> List[str]:
        """
        Extract Playwright code snippets (legacy method for backward compatibility).
        This method extracts only the code snippets without input context.
        """
        if not self.conversation_path.exists():
            raise FileNotFoundError(
                f"Conversation file not found: {self.conversation_path}"
            )

        text = self.conversation_path.read_text(encoding="utf-8")
        matches = self._PATTERN.findall(text)
        return [match.strip() for match in matches if match.strip()]

    def extract_tool_calls(self) -> List[ToolCall]:
        """
        Extract tool calls that have both input and Playwright output.
        Only returns tool calls where both input JSON and Playwright code are present.
        Also extracts the description text that appears before each tool call.
        """
        if not self.conversation_path.exists():
            raise FileNotFoundError(
                f"Conversation file not found: {self.conversation_path}"
            )

        text = self.conversation_path.read_text(encoding="utf-8")

        # Split by "#### Tool:" to get sections
        # First, find all positions of "#### Tool:"
        tool_positions = []
        for match in re.finditer(r"#### Tool:", text):
            tool_positions.append(match.start())

        tool_calls = []
        
        for i, pos in enumerate(tool_positions):
            # Determine the end position of this section
            if i + 1 < len(tool_positions):
                section_end = tool_positions[i + 1]
            else:
                section_end = len(text)
            
            section = text[pos:section_end]
            
            # Extract tool name
            tool_name_match = re.search(r"#### Tool: ([^\n]+)", section)
            if not tool_name_match:
                continue

            tool_name = tool_name_match.group(1).strip()

            # Extract input JSON
            input_match = re.search(r"\*\*Input:\*\*\n\n```json\n(.*?)\n```", section, re.DOTALL)
            if not input_match:
                continue

            input_json = input_match.group(1).strip()

            # Extract Playwright code (must be present)
            playwright_match = re.search(r"### Ran Playwright code\n```js\n(.*?)\n```", section, re.DOTALL)
            if not playwright_match:
                continue

            playwright_code = playwright_match.group(1).strip()

            # Extract description: text before "#### Tool:" but after the previous section
            description = ""
            if i > 0:
                # Get text between previous section's end and current tool call
                prev_section_end = tool_positions[i - 1]
                # Find the last "```" before current position (end of previous output)
                text_before = text[prev_section_end:pos]
                
                # Find the last occurrence of "```" which marks the end of previous output
                last_code_block = text_before.rfind("```")
                if last_code_block != -1:
                    # Get text after the last code block and before current tool
                    potential_desc = text_before[last_code_block + 3:].strip()
                    # Clean up the description (remove extra newlines)
                    description = potential_desc.strip()
            else:
                # For the first tool call, look for text after "### Claude's Response"
                response_match = re.search(r"### Claude's Response\n\n(.*?)\n#### Tool:", text[:pos], re.DOTALL)
                if response_match:
                    description = response_match.group(1).strip()

            # Parse input JSON
            try:
                input_data = json.loads(input_json)
                tool_calls.append(ToolCall(
                    tool_name=tool_name,
                    input_data=input_data,
                    playwright_code=playwright_code,
                    description=description
                ))
            except json.JSONDecodeError as e:
                print(f"Error parsing input JSON for tool {tool_name}: {e}")
                continue

        return tool_calls

    def extract_last_todo(self) -> Optional[Dict]:
        """
        Extract the last todo item from the conversation.

        Returns:
            Dict containing the last todo item information, or None if no todos found.
        """
        # Use the new method to get the full todo list, then return the last item
        full_todo_list = self.extract_last_todo_list()
        if full_todo_list and full_todo_list.get("todos"):
            return full_todo_list["todos"][-1]
        return None

    def extract_last_todo_list(self) -> Optional[Dict]:
        """
        Extract the last complete todo list from the conversation.

        Returns:
            Dict containing the complete todo list with all todos, or None if no todos found.
        """
        if not self.conversation_path.exists():
            raise FileNotFoundError(
                f"Conversation file not found: {self.conversation_path}"
            )

        text = self.conversation_path.read_text(encoding="utf-8")

        # Find the position of the last TodoWrite
        last_todo_pos = text.rfind("#### Tool: TodoWrite")

        if last_todo_pos == -1:
            return None

        # Extract the section from the last TodoWrite to the next tool or end of file
        section_start = last_todo_pos
        next_tool_pos = text.find("#### Tool:", section_start + 20)
        if next_tool_pos == -1:
            section_text = text[section_start:]
        else:
            section_text = text[section_start:next_tool_pos]

        # Extract JSON content from the section
        json_start = section_text.find("```json")
        json_end = section_text.find("```", json_start + 1)

        if json_start == -1 or json_end == -1:
            return None

        # Extract the JSON content between the markers
        json_content = section_text[json_start:json_end + 3]
        json_lines = json_content.split("\n")
        json_data = "\n".join(json_lines[1:-1])  # Remove ```json and ```
        json_data = json_data.strip()

        try:
            todo_data = json.loads(json_data)
            return todo_data

        except json.JSONDecodeError as e:
            print(f"Error parsing todo JSON: {e}")
            return None

    @staticmethod
    def save(blocks: List[str], output_path: Path) -> None:
        if not blocks:
            output_path.write_text(
                "// No Playwright code blocks found.\n", encoding="utf-8"
            )
            return

        header_lines = [
            "// Extracted Playwright code blocks",
            f"// Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        body_lines = []
        for idx, block in enumerate(blocks, 1):
            body_lines.append(f"// ---- Block {idx} ----")
            body_lines.append(block)
            body_lines.append("")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "\n".join(header_lines + body_lines).rstrip() + "\n", encoding="utf-8"
        )

    @staticmethod
    def print_blocks(blocks: List[str]) -> None:
        print("\n--- Extracted Playwright Code Blocks ---")
        if not blocks:
            print("No Playwright code blocks were found in the conversation file.")
            return

        for idx, block in enumerate(blocks, 1):
            print(f"\n// Block {idx}\n{block}\n")

    @staticmethod
    def print_last_todo(todo: Optional[Dict]) -> None:
        """
        Print the last todo item in a readable format.
        """
        print("\n--- Last Todo Item ---")
        if not todo:
            print("No todo items were found in the conversation file.")
            return

        print("Content:", todo.get("content", "N/A"))
        print("Status:", todo.get("status", "N/A"))
        print("Active Form:", todo.get("activeForm", "N/A"))

    @staticmethod
    def print_last_todo_list(todo_list: Optional[Dict]) -> None:
        """
        Print the last complete todo list in a readable format.
        """
        print("\n--- Last Todo List ---")
        if not todo_list:
            print("No todo list was found in the conversation file.")
            return

        todos = todo_list.get("todos", [])
        print(f"Total todos: {len(todos)}")

        for i, todo in enumerate(todos, 1):
            print(f"\n{i}. Content: {todo.get('content', 'N/A')}")
            print(f"   Status: {todo.get('status', 'N/A')}")
            print(f"   Active Form: {todo.get('activeForm', 'N/A')}")

    @staticmethod
    def print_tool_calls(tool_calls: List[ToolCall]) -> None:
        """
        Print tool calls in a readable format.
        """
        print(f"\n--- Extracted Tool Calls ({len(tool_calls)}) ---")
        if not tool_calls:
            print("No tool calls with both input and output were found in the conversation file.")
            return

        for idx, tool_call in enumerate(tool_calls, 1):
            print(f"\n## Tool Call {idx}: {tool_call.tool_name}")
            if tool_call.description:
                print("**Description:**")
                print(tool_call.description)
            print("**Input:**")
            print(json.dumps(tool_call.input_data, indent=2))
            print("**Playwright Code:**")
            print(f"```javascript\n{tool_call.playwright_code}\n```")

