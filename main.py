"""
Self-Healing Test Pipeline Main Entry Point

This module orchestrates the two-stage self-healing test pipeline:
1. Web Agent - Executes test with Playwright MCP tools to generate conversation logs
2. Coding Agent - Fixes the test based on conversation logs with retry logic

Usage:
    python self_healing/main.py --test-file-path cypress/e2e/login.cy.js
"""

import os
import sys
import asyncio
import argparse
import uuid
import dotenv
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from self_healing.src.agents.web_agent import WebAgentApp
from self_healing.src.agents.coding_agent import CodingAgentApp
from self_healing.src.utils.prompt_loader import PromptLoader

# Load environment variables
dotenv.load_dotenv()


class SelfHealingPipeline:
    """
    Main orchestrator for the self-healing test pipeline.
    Coordinates Web Agent and Coding Agent execution.
    """

    def __init__(self, test_file_path: str, workspace_path: str = None):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path or os.getcwd()
        self.prompt_loader = PromptLoader()
        self.run_uuid = uuid.uuid4()

    async def run(self):
        """Execute the complete self-healing pipeline."""
        print("=" * 80)
        print("Self-Healing Test Pipeline")
        print("=" * 80)
        print(f"Test File: {self.test_file_path}")
        print(f"Workspace: {self.workspace_path}")
        print("=" * 80 + "\n")

        # Stage 1: Run Web Agent to generate conversation logs
        print("STAGE 1: Web Agent - Executing test with Playwright\n")

        web_agent = WebAgentApp(
            test_file_path=self.test_file_path,
            prompt_loader=self.prompt_loader,
            workspace_path=self.workspace_path,
            run_uuid=self.run_uuid
        )

        await web_agent.run()

        print("\n" + "✅ " * 20)
        print(f"STAGE 1 COMPLETED: Task ID = {self.run_uuid}")
        print("✅ " * 20 + "\n")

        # Stage 2: Run Coding Agent to fix the test
        print("STAGE 2: Coding Agent - Fixing test based on conversation logs")

        coding_agent = CodingAgentApp(
            test_file_path=self.test_file_path,
            task_id=self.run_uuid,
            prompt_loader=self.prompt_loader,
            workspace_path=self.workspace_path,
        )
        await coding_agent.run()

        print("\n" + "🎉 " * 20)
        print("PIPELINE COMPLETED SUCCESSFULLY!")
        print("🎉 " * 20 + "\n")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Self-Healing Test Pipeline - Automated test analysis and fixing",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--test-file-path",
        type=str,
        required=True,
        help="Path to the test file to analyze and fix",
    )
    return parser.parse_args()


async def main():
    """Main entry point for the self-healing pipeline."""
    args = parse_args()
    pipeline = SelfHealingPipeline(
        test_file_path=args.test_file_path,
    )
    await pipeline.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExecution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        raise
