"""
Web Agent Runner

Encapsulates the logic to run the Claude test pipeline and persist conversation logs.
"""

import os
from pathlib import Path
from typing import Dict, Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    AgentDefinition,
)

from self_healing.src.utils.prompt_loader import PromptLoader
from self_healing.src.utils.conversation_formatter import ConversationFormatter


class WebAgentRunner:
    """
    Encapsulates the logic to run the Claude test pipeline and persist conversation logs.
    """

    def __init__(
        self,
        test_file_path: str,
        workspace_path: str,
        conversation_path: Path,
        prompt_loader: PromptLoader,
    ):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path
        self.conversation_path = conversation_path
        self.prompt_loader = prompt_loader
        self.local_playwright_cli = os.path.join(
            workspace_path, "self_healing/playwright/packages/playwright/cli.js"
        )
        self.conversation_formatter = ConversationFormatter(
            log_title="Claude Agent Conversation Log",
            test_file_path=self.test_file_path,
            include_test_results=False,
        )

    async def run(self):
        self._print_header()
        options = self._build_agent_options()

        conversation_history = []
        user_prompt = self.prompt_loader.format_prompt(
            "claude_agent",
            prompt_key="user_prompt",
            test_file_path=self.test_file_path,
        )

        async with ClaudeSDKClient(options=options) as client:
            print("\n" + "=" * 80)
            print("Executing test with Web UI Agent")
            print("=" * 80)

            await client.query(user_prompt)
            history_entry = await self._collect_messages(client)
            history_entry["user_prompt"] = user_prompt
            conversation_history.append(history_entry)

        self.conversation_path.parent.mkdir(parents=True, exist_ok=True)
        self.conversation_formatter.save(
            conversation_history,
            self.conversation_path,
            show_tool_summary=True,
        )

    def _print_header(self):
        print("=" * 80)
        print("Claude Agent Test Pipeline")
        print("=" * 80)
        print(f"Test File: {self.test_file_path}")
        print(f"Workspace: {self.workspace_path}")
        print("=" * 80)

    def _build_agent_options(self) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            model="sonnet",
            mcp_servers={
            "playwright": {
            "command": "node",
            "args": [self.local_playwright_cli, "run-mcp-server", "--isolated"],
            }
            },
            allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "mcp__playwright__browser_navigate",
            "mcp__playwright__browser_snapshot",
            "mcp__playwright__browser_click",
            "mcp__playwright__browser_type",
            "mcp__playwright__browser_wait_for",
            "mcp__playwright__browser_take_screenshot",
            "mcp__playwright__browser_press_key",
            "mcp__playwright__browser_evaluate",
            ],
            permission_mode="acceptEdits",
            cwd=self.workspace_path,
            agents={
            "web-agent": AgentDefinition(
            description="Agent specialized in browser operations for web navigation, clicking, and screenshots",
            prompt="""
                You are a web usage expert who uses playwright mcp tools to execute test content. The file content may contain errors. If you cannot find the element with the corresponding selector, please help me find the element with the closest semantic meaning to interact with.
                If you need base_url or config information, you can find it in the cypress.config.js file.
            """,
            tools=[
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "mcp__playwright__browser_navigate",
                "mcp__playwright__browser_snapshot",
                "mcp__playwright__browser_click",
                "mcp__playwright__browser_type",
                "mcp__playwright__browser_wait_for",
                "mcp__playwright__browser_take_screenshot",
                "mcp__playwright__browser_press_key",
                "mcp__playwright__browser_evaluate",
            ],
            model="haiku"
            ),
            "coding-agent": AgentDefinition(
            description="Agent specialized in QA and have strong cypress and playwright coding skill",
            prompt="""
                You are a QA expert proficient in cypress and playwright. Please help me modify my target test file and related files based on the page snapshot.
                **IMPORTANT: Please focus on fixing the code and do not write any .md files.**
                
                Please note:
                1. Cypress does not have pseudo-syntax like :has-text. Please use cy.contains() syntax to achieve equivalent functionality.
                2. Do not use 'generic' as a selector. In Playwright, use role-based selectors directly; in Cypress, use cy.contains directly.
                3. If there is an input field, please pay attention to whether it's an input or textarea element.
            """,
            tools=["Read", "Write", "Edit", "Glob", "Grep"],
            model="haiku"
            )
            }
        )

    async def _collect_messages(self, client) -> Dict[str, Any]:
        messages = []
        tool_outputs: Dict[str, Any] = {}
        tool_use_map: Dict[str, ToolUseBlock] = {}

        async for message in client.receive_response():
            messages.append(message)
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_use_map[block.id] = block
                        print(f"\n[Tool Used: {block.name}]")
                        print(
                            f"  Input: {ConversationFormatter.format_tool_output(block.input)}"
                        )
            elif isinstance(message, UserMessage):
                for block in message.content:
                    if isinstance(block, ToolResultBlock):
                        tool_outputs[block.tool_use_id] = block.content
                        tool_name = "Unknown"
                        if block.tool_use_id in tool_use_map:
                            tool_name = tool_use_map[block.tool_use_id].name

                        is_error = block.is_error if block.is_error is not None else False
                        error_marker = " ⚠️ ERROR" if is_error else ""
                        print(f"\n[Tool Result: {tool_name} (ID: {block.tool_use_id}){error_marker}]")

                        output_str = ConversationFormatter.format_tool_output(
                            block.content
                        )
                        if len(output_str) > 1000:
                            print(f"  Output (truncated):\n{output_str[:1000]}...")
                            print("  ... (Full output saved to conversation.md)")
                        else:
                            print(f"  Output:\n{output_str}")

        print("\n" + "=" * 80)
        print("Claude Agent execution completed!")
        print("=" * 80)

        return {
            "step": "Test Execution",
            "messages": messages,
            "tool_outputs": tool_outputs,
        }
