import os
from pathlib import Path
from langchain.agents.middleware.types import before_agent, before_model
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from langgraph.runtime import Runtime

from self_healing.src.agents.base import BaseAgent
from self_healing.src.types.models import AgentState
from self_healing.src.utils.prompt_loader import load_prompts


class WebAgent(BaseAgent):
    """
    Web Agent responsible for executing test automation tasks using browser tools.
    """

    @staticmethod
    @before_agent(state_schema=AgentState)
    def init_message(state: AgentState, run_time: Runtime):
        """
        Initializes the web agent with system prompts and context.
        
        This middleware:
        1. Loads the appropriate web agent prompt template
        2. Reads the todo file for the current task
        3. Includes agent.md documentation if available
        
        Args:
            state: Current agent state
            run_time: Runtime context
            
        Returns:
            Dictionary with initialized system messages
        """
        prompt_loader = load_prompts()
        todo_dir = Path("self_healing/todo")
        todo_file = todo_dir / f"todo_{state['task_id']}.md"

        # Load prompt from YAML
        system_prompt_text = prompt_loader.format_prompt(
            "web_agent",
            todo_file=str(todo_file)
        )

        # Get agent.md file if it exists
        agent_md_content = None
        if os.path.isfile("agent.md"):
            with open("agent.md", mode="r", encoding="utf-8") as f:
                agent_md_content = f.read()

        # Prepare system prompts
        system_prompts = [SystemMessage(content=system_prompt_text)]
        if agent_md_content:
            system_prompts.append(SystemMessage(content=agent_md_content))

        return {"messages": system_prompts}

    @staticmethod
    @before_model
    def refresh_messages(state: AgentState, run_time: Runtime):
        """
        Refreshes messages before each model call with current todo status.
        
        This middleware:
        1. Removes old todo list messages
        2. Reads the current todo file
        3. Identifies the current pending task
        4. Provides guidance for completing the current step
        
        Args:
            state: Current agent state
            run_time: Runtime context
            
        Returns:
            Dictionary with refreshed messages including current task instructions
        """
        todo_dir = Path("self_healing/todo")
        todo_file = todo_dir / f"todo_{state['task_id']}.md"

        # Remove old todo messages
        todo_message = [m for m in state["messages"] if isinstance(m, SystemMessage) and "Todo List" in m.content]
        messages_to_remove = [RemoveMessage(id=m.id) for m in todo_message] if todo_message else []

        # Get todo list
        with open(todo_file, "r", encoding="utf-8") as f:
            todo_file_content = f.read()

        # Find current pending step
        lines = todo_file_content.splitlines()
        current_todo_step = None
        for i, line in enumerate(lines):
            if i > 0 and lines[i-1].strip().startswith('[done]') and line.strip().startswith('[pending]'):
                current_todo_step = line
                break
        
        # If not found, get the first pending task
        if not current_todo_step:
            current_todo_step = next((line for line in lines if '[pending]' in line), "No pending tasks")

        refreshed_messages = [
            SystemMessage(content=f"Todo List:\n{todo_file_content}"),
            HumanMessage(content=f"""Current task: {current_todo_step}

Steps to complete:
1. Use browser_snapshot to check current page state
2. Execute appropriate tools for this todo step
3. Verify the result
4. Mark this step as [done] in the todo file when completed

Repeat until the step is finished.""")
        ]

        return {"messages": messages_to_remove + refreshed_messages}

