"""
Claude Agent Test Pipeline

This module demonstrates how to use Claude Agent SDK with existing MCP tools
(Playwright and Filesystem) to automate test analysis and execution.

The difference from agent.py:
- agent.py uses LangChain with custom MCP loader
- test_pipeline.py uses Claude Agent SDK with native MCP server configuration

Usage:
    python test_pipeline.py --test-file-path cypress/e2e/login.cy.js
"""

import os
import asyncio
import argparse
import dotenv
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from claude_agent_sdk import (
    AssistantMessage,
    SystemMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    AgentDefinition,
)

from self_healing.src.utils.prompt_loader import PromptLoader
from self_healing.src.utils.playwright_extractor import PlaywrightCodeExtractor
from self_healing.src.utils.conversation_formatter import ConversationFormatter

# Load environment variables
dotenv.load_dotenv()

class WebAgentTestRunner:
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


class WebAgentApp:
    """
    High-level orchestrator for running the agent pipeline and extracting Playwright code.
    """

    @staticmethod
    def parse_args(args=None):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Claude Agent test pipeline with MCP tools",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--test-file-path",
            type=str,
            required=True,
            help="Path to the test file to analyze",
        )
        return parser.parse_args(args)

    def __init__(
        self,
        test_file_path: str,
        prompt_loader: PromptLoader = None,
        workspace_path: str = None,
        run_uuid: str = None,
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace_path = workspace_path or os.getcwd()
        self.test_file_path = test_file_path
        self.run_uuid = run_uuid or uuid.uuid4().hex
        self.results_dir = Path("self_healing/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_path = self.results_dir / f"conversation_{self.run_uuid}.md"
        self.code_blocks_path = self.results_dir / f"code_blocks_{self.run_uuid}.txt"

    async def run(self):
        await self._run_full_pipeline()

    async def _run_full_pipeline(self):
        runner = WebAgentTestRunner(
            test_file_path=self.test_file_path,
            workspace_path=self.workspace_path,
            conversation_path=self.conversation_path,
            prompt_loader=self.prompt_loader,
        )
        await runner.run()
        self._extract_code_blocks()

    def _extract_code_blocks(self):
        """Extract todos and tool calls from the conversation file."""
        extractor = PlaywrightCodeExtractor(self.conversation_path)
        
        print("\n" + "=" * 60)
        print("Extracting Todos")
        print("=" * 60)
        
        # Extract the last todo item
        last_todo = extractor.extract_last_todo()
        PlaywrightCodeExtractor.print_last_todo(last_todo)
        
        # Extract the last complete todo list
        last_todo_list = extractor.extract_last_todo_list()
        PlaywrightCodeExtractor.print_last_todo_list(last_todo_list)
        
        print("\n" + "=" * 60)
        print("Extracting Tool Calls (Input + Output pairs)")
        print("=" * 60)
        
        # Extract tool calls with both input and output
        tool_calls = extractor.extract_tool_calls()
        PlaywrightCodeExtractor.print_tool_calls(tool_calls)
        
        # Save results to file
        with open(self.code_blocks_path, 'w', encoding='utf-8') as f:
            # Handle None case for last_todo_list
            todos = last_todo_list.get('todos', []) if last_todo_list else []
            f.write(f"Todos ({len(todos)}):\n")
            f.write("=" * 60 + "\n")
            
            if todos:
                for todo in todos:
                    f.write(f"{todo}\n")
            else:
                f.write("No todo list found in conversation.\n")
            
            f.write(f"\n\nTool Calls ({len(tool_calls)}):\n")
            f.write("=" * 60 + "\n")
            
            if tool_calls:
                for call in tool_calls:
                    # ToolCall is a NamedTuple, use attribute access instead of .get()
                    if call.description:
                        f.write(f"\n--- Description ---\n{call.description}\n")
                    f.write(f"\nTool: {call.tool_name}\n")
                    f.write(f"Input: {call.input_data}\n")
                    f.write(f"Playwright Code:\n{call.playwright_code}\n")
                    f.write("-" * 60 + "\n")
            else:
                f.write("No tool calls found.\n")
        
        print(f"\n✅ Extraction completed successfully!")
        print(f"   - Extracted {len(todos)} todos from last list")
        print(f"   - Found {len(tool_calls)} tool calls with Input + Output pairs")
        print(f"   - Results saved to: {self.code_blocks_path}")


async def main():
    args = WebAgentApp.parse_args()
    app = WebAgentApp(
        test_file_path=args.test_file_path,
        prompt_loader= PromptLoader(),
    )
    await app.run()
    return app.run_uuid


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise

