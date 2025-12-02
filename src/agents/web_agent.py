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

import argparse
import asyncio
import os
import uuid
from pathlib import Path

import dotenv
from self_healing.src.agents.support_models import SUPPORT_MODELS
from self_healing.src.lib.web_agent_runner import WebAgentRunner
from self_healing.src.utils.conversation_extractor import ConversationExtractor
from self_healing.src.utils.prompt_loader import PromptLoader

# Load environment variables
dotenv.load_dotenv()


class WebAgent:
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
        parser.add_argument(
            "--web-agent-model",
            type=str,
            help=f"Model you want to use. Supported models: {', '.join(SUPPORT_MODELS)}",
        )
        return parser.parse_args(args)

    def __init__(
        self,
        test_file_path: str,
        prompt_loader: PromptLoader = None,
        workspace_path: str = None,
        run_uuid: str = None,
        model: str = "sonnet",
    ):
        self.prompt_loader = prompt_loader or PromptLoader()
        self.workspace_path = workspace_path or os.getcwd()
        self.test_file_path = test_file_path
        self.run_uuid = run_uuid or uuid.uuid4().hex
        self.model = model
        self.results_dir = Path("self_healing/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_path = self.results_dir / f"conversation_{self.run_uuid}.md"
        self.code_blocks_path = self.results_dir / f"code_blocks_{self.run_uuid}.txt"

    async def run(self):
        await self._run_full_pipeline()

    async def _run_full_pipeline(self):
        runner = WebAgentRunner(
            test_file_path=self.test_file_path,
            workspace_path=self.workspace_path,
            conversation_path=self.conversation_path,
            prompt_loader=self.prompt_loader,
            model=self.model,
        )
        await runner.run()
        self._extract_code_blocks()

    def _extract_code_blocks(self):
        """Extract todos and tool calls from the conversation file."""
        extractor = ConversationExtractor(self.conversation_path)

        print("\n" + "=" * 60)
        print("Extracting Todos")
        print("=" * 60)

        # Extract the last todo item
        last_todo = extractor.extract_last_todo()
        ConversationExtractor.print_last_todo(last_todo)

        # Extract the last complete todo list
        last_todo_list = extractor.extract_last_todo_list()
        ConversationExtractor.print_last_todo_list(last_todo_list)

        print("\n" + "=" * 60)
        print("Extracting Tool Calls (Input + Output pairs)")
        print("=" * 60)

        # Extract tool calls with both input and output
        tool_calls = extractor.extract_tool_calls()
        ConversationExtractor.print_tool_calls(tool_calls)

        # Save results to file
        with open(self.code_blocks_path, "w", encoding="utf-8") as f:
            # Handle None case for last_todo_list
            todos = last_todo_list.get("todos", []) if last_todo_list else []
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

        print("\n✅ Extraction completed successfully!")
        print(f"   - Extracted {len(todos)} todos from last list")
        print(f"   - Found {len(tool_calls)} tool calls with Input + Output pairs")
        print(f"   - Results saved to: {self.code_blocks_path}")


async def main():
    args = WebAgent.parse_args()

    app = WebAgent(
        test_file_path=args.test_file_path,
        prompt_loader=PromptLoader(),
        model=args.web_agent_model if args.web_agent_model else "sonnet",
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
