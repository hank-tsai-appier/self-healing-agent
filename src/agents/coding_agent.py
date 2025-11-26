"""
Coding Agent - Test Fixing Pipeline

This module uses Claude Agent SDK to fix test files based on conversation logs.
It reads conversation.md, analyzes the issues, fixes the test file and related files,
then executes the test with retry logic (up to 3 attempts).

Usage:
    python test_coding_agent.py --test-file-path cypress/e2e/login.cy.js
"""

import os
import asyncio
import argparse
import dotenv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

from self_healing.src.utils.prompt_loader import PromptLoader
from self_healing.src.utils.conversation_formatter import ConversationFormatter
from self_healing.src.utils.file_loader import TextFileLoader
from self_healing.src.utils.cypress_executor import SubprocessExecutor

# Load environment variables
dotenv.load_dotenv()

# Initialize prompt loader
prompt_loader = PromptLoader()

# Configuration
MAX_RETRIES = 3


class CodingAgentFixRunner:
    """
    Handles interactions with Claude Agent to fix the Cypress test.
    """

    def __init__(
        self,
        test_file_path: str,
        workspace_path: str,
        conversation_content: str,
        prompt_loader: PromptLoader,
    ):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path
        self.prompt_loader = prompt_loader
        self.conversation_snippet = (
            conversation_content[-15000:]
            if len(conversation_content) > 15000
            else conversation_content
        )
        self.options = self._build_agent_options()

    def _build_agent_options(self) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            model="claude-haiku-4-5",
            allowed_tools=[
                "Read",
                "Write",
                "Edit",
                "Glob",
                "Grep",
                "Bash",
            ],
            permission_mode="acceptEdits",
            cwd=self.workspace_path,
        )

    async def run_all_attempts(
        self, max_retries: int, cypress_executor: SubprocessExecutor
    ) -> List[Dict[str, Any]]:
        """
        Run all fix attempts in a single Claude client session.
        This allows Claude to remember previous attempts and learn from them.
        """
        conversation_history: List[Dict[str, Any]] = []
        
        print("\n" + "=" * 80)
        print("Starting Claude Agent Fix Session (Continuous Conversation)")
        print("=" * 80)

        async with ClaudeSDKClient(options=self.options) as client:
            # Initial prompt with conversation context
            initial_prompt = self.prompt_loader.format_prompt(
                "coding_agent",
                prompt_key="user_prompt",
                test_file_path=self.test_file_path,
                conversation_content=self.conversation_snippet,
            )

            for attempt in range(1, max_retries + 1):
                print(f"\n{'#' * 80}")
                print(f"# Attempt {attempt} of {max_retries}")
                print(f"{'#' * 80}\n")

                # First attempt uses initial prompt, subsequent attempts use follow-up prompts
                if attempt == 1:
                    user_prompt = initial_prompt
                else:
                    # Get previous test result
                    prev_success, prev_output = conversation_history[-1]["test_result"]
                    user_prompt = self._build_retry_prompt(attempt, prev_output)

                print("=" * 80)
                print(f"Fixing test with Claude Agent (Attempt {attempt})")
                print("=" * 80)

                # Send query to Claude (in the same session)
                await client.query(user_prompt)

                print("\nClaude's Fixing Process:")
                print("-" * 80)

                # Collect messages for this attempt
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
                                if block.name in ["Read", "Write", "Edit"]:
                                    file_path = block.input.get("file_path", "unknown")
                                    print(f"  File: {file_path}")
                    elif isinstance(message, UserMessage):
                        for block in message.content:
                            if isinstance(block, ToolResultBlock):
                                tool_outputs[block.tool_use_id] = block.content
                                tool_name = (
                                    tool_use_map[block.tool_use_id].name
                                    if block.tool_use_id in tool_use_map
                                    else "Unknown"
                                )
                                is_error = (
                                    block.is_error if block.is_error is not None else False
                                )
                                icon = "⚠️" if is_error else "✅"
                                print(f"\n{icon} [Tool Result: {tool_name}]")

                print("\n" + "=" * 80)
                print("Code fixing completed!")
                print("=" * 80)

                # Save this attempt's conversation
                entry = {
                    "step": f"Fix Attempt {attempt}",
                    "user_prompt": user_prompt,
                    "messages": messages,
                    "tool_outputs": tool_outputs,
                }
                conversation_history.append(entry)

                # Execute test
                print(f"\n{'=' * 80}")
                print(f"Executing test: {self.test_file_path}")
                print(f"{'=' * 80}")
                test_success, test_output = cypress_executor.run(self.test_file_path)
                conversation_history[-1]["test_result"] = (test_success, test_output)

                if test_success:
                    print(f"\n🎉 Test passed on attempt {attempt}!")
                    break

                if attempt < max_retries:
                    print(f"\n⚠️ Test failed on attempt {attempt}. Retrying in same session...")
                    print(f"Error output (first 1000 chars):\n{test_output[:1000]}...")
                    print("\n📋 Claude will remember this context for the next attempt")
                else:
                    print(f"\n❌ Test failed after {max_retries} attempts")

        print("\n" + "=" * 80)
        print("Claude Agent Fix Session Completed")
        print("=" * 80)

        return conversation_history

    def _build_retry_prompt(self, attempt: int, previous_test_output: str) -> str:
        """Build a follow-up prompt for retry attempts."""
        snippet = (
            previous_test_output[-10000:]
            if len(previous_test_output) > 10000
            else previous_test_output
        )
        return f"""
上一次的修復沒有成功，測試仍然失敗了。

**測試執行輸出 (Attempt {attempt - 1}):**

```
{snippet}
```

請分析這個錯誤輸出，找出問題所在並繼續修復代碼。
請特別注意：
1. 錯誤訊息中的具體問題
2. 失敗的步驟和行號
3. 找不到的元素或選擇器問題
4. 時序或非同步問題

請基於你之前的修復嘗試和這次的錯誤輸出，調整你的修復策略。
"""


class CodingAgentApp:
    """
    High-level orchestrator managing fix attempts, test execution, and logging.
    """
    def __init__(
        self,
        test_file_path: str,
        task_id: str,
        prompt_loader: PromptLoader = None,
        workspace_path: str = None,
        max_retries: int = MAX_RETRIES,
    ):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path or os.getcwd()
        self.task_id = task_id
        self.max_retries = max_retries
        code_blocks_path = Path(self.workspace_path) / "self_healing" / "results" / f"code_blocks_{task_id}.txt"
        self.file_loader = TextFileLoader(
            code_blocks_path,
            hint="Please run test_web_agent.py first to generate code_blocks.txt",
        )
        self.cypress_executor = SubprocessExecutor(self.workspace_path)
        self.prompt_loader = prompt_loader or PromptLoader()
        self.conversation_formatter = ConversationFormatter(
            log_title="Coding Agent Conversation Log",
            test_file_path=self.test_file_path,
            include_test_results=True,
        )

    async def run(self):
        conversation_content = self.file_loader.read()
        fix_runner = CodingAgentFixRunner(
            test_file_path=self.test_file_path,
            workspace_path=self.workspace_path,
            conversation_content=conversation_content,
            prompt_loader=self.prompt_loader,
        )

        # Run all attempts in a single Claude session
        conversation_history = await fix_runner.run_all_attempts(
            max_retries=self.max_retries,
            cypress_executor=self.cypress_executor,
        )

        # Save conversation log
        output_path = (
            Path(self.workspace_path)
            / "self_healing"
            / "results"
            / "coding_agent_conversation.md"
        )
        self.conversation_formatter.save(conversation_history, output_path)
        print("\n" + "=" * 80)
        print("Coding Agent execution completed!")
        print("=" * 80)


async def main():
    parser = argparse.ArgumentParser(
        description="Coding Agent - Fix tests based on conversation logs",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--test-file-path",
        type=str,
        required=True,
        help="Path to the test file to fix"
    )
    parser.add_argument(
        "--task-id",
        type=str,
        required=True,
        help="Optional identifier for the current fix task (for logging/metadata only)."
    )

    args = parser.parse_args()

    app = CodingAgentApp(
        test_file_path=args.test_file_path,
        task_id=args.task_id,
        prompt_loader=prompt_loader,
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

