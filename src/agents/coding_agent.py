"""
Coding Agent - Test Fixing Pipeline

This module uses Claude Agent SDK to fix test files based on conversation logs.
It reads conversation.md, analyzes the issues, fixes the test file and related files,
then executes the test with retry logic (up to 3 attempts).

Usage:
    python test_coding_agent.py --test-file-path cypress/e2e/login.cy.js
"""

import argparse
import asyncio
import os
from pathlib import Path

import dotenv
from self_healing.src.agents.support_models import SUPPORT_MODELS
from self_healing.src.lib.coding_agent_runner import CodingAgentRunner
from self_healing.src.utils.file_loader import TextFileLoader
from self_healing.src.utils.prompt_loader import PromptLoader
from self_healing.src.utils.subprocess_executor import SubprocessExecutor

# Load environment variables
dotenv.load_dotenv()

# Initialize prompt loader
prompt_loader = PromptLoader()

# Configuration
MAX_RETRIES = 3


class CodingAgent:
    """
    High-level orchestrator managing fix attempts, test execution, and logging.
    """

    @staticmethod
    def parse_args(args=None):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(
            description="Coding Agent - Fix tests based on conversation logs",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        parser.add_argument(
            "--test-file-path",
            type=str,
            required=True,
            help="Path to the test file to fix",
        )
        parser.add_argument(
            "--task-id",
            type=str,
            required=True,
            help="Optional identifier for the current fix task (for logging/metadata only).",
        )
        parser.add_argument(
            "--coding-agent-model",
            type=str,
            help=f"Model you want to use. Supported models: {', '.join(SUPPORT_MODELS)}",
        )
        return parser.parse_args(args)

    def __init__(
        self,
        test_file_path: str,
        task_id: str,
        prompt_loader: PromptLoader = None,
        workspace_path: str = None,
        max_retries: int = MAX_RETRIES,
        model: str = "haiku",
    ):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path or os.getcwd()
        self.task_id = task_id
        self.max_retries = max_retries
        self.model = model
        code_blocks_path = Path(self.workspace_path) / "self_healing" / "results" / f"code_blocks_{task_id}.txt"
        self.file_loader = TextFileLoader(
            code_blocks_path,
            hint="Please run test_web_agent.py first to generate code_blocks.txt",
        )
        self.cypress_executor = SubprocessExecutor(self.workspace_path)
        self.prompt_loader = prompt_loader or PromptLoader()

    async def run(self):
        conversation_content = self.file_loader.read()
        fix_runner = CodingAgentRunner(
            test_file_path=self.test_file_path,
            workspace_path=self.workspace_path,
            conversation_content=conversation_content,
            prompt_loader=self.prompt_loader,
            model=self.model,
        )

        # Run all attempts in a single Claude session
        await fix_runner.run_all_attempts(
            max_retries=self.max_retries,
            cypress_executor=self.cypress_executor,
        )


async def main():
    args = CodingAgent.parse_args()

    app = CodingAgent(
        test_file_path=args.test_file_path,
        task_id=args.task_id,
        prompt_loader=prompt_loader,
        model=args.coding_agent_model if args.coding_agent_model else "haiku",
    )
    await app.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        raise
