import json
from pathlib import Path
from langchain.agents.middleware.types import before_agent, after_agent
from langchain_core.messages import HumanMessage, RemoveMessage
from langgraph.runtime import Runtime

from self_healing.src.agents.base import BaseAgent
from self_healing.src.types.models import AgentState, Todo
from self_healing.src.utils.json_fommatter import JsonFormatter
from self_healing.src.utils.prompt_loader import load_prompts


class PlanningAgent(BaseAgent):
    """
    Planning Agent responsible for analyzing test scripts and creating todo lists.
    """

    @staticmethod
    @before_agent(state_schema=AgentState)
    def process_message(state: AgentState, run_time: Runtime):
        """
        Processes incoming messages and prepares prompts for planning.
        
        This middleware:
        1. Finds related test scripts based on the input test script
        2. Arranges test steps into a structured todos list
        
        Args:
            state: Current agent state containing messages and context
            run_time: Runtime context providing access to long-term memory and streaming
            
        Returns:
            Dictionary with updated messages containing formatted prompts
        """
        prompt_loader = load_prompts()
        
        # Load prompt from YAML
        test_script_path = state['messages'][0].content
        plan_prompt = prompt_loader.format_prompt("plan_agent", test_script_path=test_script_path)

        # Prepare user prompts
        user_prompt = [
            HumanMessage(content=plan_prompt),
            HumanMessage(content=f"target file: {test_script_path}")
        ]

        return {"messages": user_prompt}

    @staticmethod
    @after_agent(state_schema=AgentState)
    def process_response(state: AgentState, runtime: Runtime):
        """
        Processes the agent's response and saves the generated todo list.
        
        This middleware:
        1. Extracts JSON response containing todos
        2. Validates and parses todo items
        3. Saves todos to a markdown file
        4. Updates related script paths
        5. Cleans up messages for the next stage
        
        Args:
            state: Current agent state with response messages
            runtime: Runtime context
            
        Returns:
            Dictionary with messages to remove for cleanup
        """
        todo_dir = Path("self_healing/todo")
        todo_file = todo_dir / f"todo_{state['task_id']}.md"
        
        # Find final JSON response
        response = state['messages'][-1]

        if not response.tool_calls:
            try:
                # Use JsonFormatter to remove markdown markers
                content = JsonFormatter.remove_markdown_markers(response.content[0]["text"])
                
                # Parse Content JSON
                content_data = json.loads(content)

                # Parse todos and save to file
                todos = [Todo(**todo) for todo in content_data.get("todos", [])]
                with open(todo_file, "w", encoding="utf-8") as f:
                    for todo in todos:
                        f.write(f"[{todo.status}] [{todo.id}] ({todo.type}) {todo.description}\n")

                print(f"Created {len(todos)} todos and saved to {todo_file}")

                # Update related test script
                related_script_pathes = content_data.get("related_script_pathes", [])

            except Exception as e:
                print(f"Failed to parse todos: {e}")
        
            # Clean messages for the next stage
            return {"messages": [RemoveMessage(id=m.id) for m in state['messages']]}
        
        return None
