"""
Coding Agent Runner

Handles interactions with Claude Agent to fix the Cypress test.
"""

from typing import Any, Dict, List

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)
from self_healing.src.utils.conversation_formatter import ConversationFormatter
from self_healing.src.utils.prompt_loader import PromptLoader
from self_healing.src.utils.subprocess_executor import SubprocessExecutor


class CodingAgentRunner:
    """
    Handles interactions with Claude Agent to fix the Cypress test.
    """

    def __init__(
        self,
        test_file_path: str,
        workspace_path: str,
        conversation_content: str,
        prompt_loader: PromptLoader,
        model: str = "haiku",
    ):
        self.test_file_path = test_file_path
        self.workspace_path = workspace_path
        self.prompt_loader = prompt_loader
        self.model = model
        self.conversation_snippet = (
            conversation_content[-15000:] if len(conversation_content) > 15000 else conversation_content
        )
        self.options = self._build_agent_options()
        self.conversation_formatter = ConversationFormatter(
            log_title="Coding Agent Conversation Log",
            test_file_path=self.test_file_path,
            include_test_results=True,
        )

    def _build_agent_options(self) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            model=self.model,
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

    async def run_all_attempts(self, max_retries: int, cypress_executor: SubprocessExecutor) -> List[Dict[str, Any]]:
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
                                is_error = block.is_error if block.is_error is not None else False
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

        # Save conversation log
        from pathlib import Path

        output_path = Path(self.workspace_path) / "self_healing" / "results" / "coding_agent_conversation.md"
        self.conversation_formatter.save(conversation_history, output_path)
        print("\n" + "=" * 80)
        print("Coding Agent execution completed!")
        print("=" * 80)

        return conversation_history

    def _build_retry_prompt(self, attempt: int, previous_test_output: str) -> str:
        """Build a follow-up prompt for retry attempts."""
        snippet = previous_test_output[-10000:] if len(previous_test_output) > 10000 else previous_test_output
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
