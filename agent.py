"""
Self-Healing Test Automation Agent

This module provides an automated test maintenance system that analyzes failing tests,
understands their intent, and attempts to fix them using AI-powered agents.

The system consists of three main agents:
1. Planning Agent: Analyzes test scripts and creates structured todo lists
2. Web Agent: Executes browser automation tasks to understand test behavior
3. Coding Agent: Generates or modifies test code in the target framework

Usage:
    python agent.py --goal-language cypress --test-file-path path/to/test.cy.js
"""

import os
import asyncio
import uuid
import argparse
import dotenv
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END

from self_healing.src.types import AgentState
from self_healing.src.agents import PlanningAgent, WebAgent, CodingAgent
from self_healing.src.utils.mcp_loader import load_mcp_server_tools


# Load environment variables
dotenv.load_dotenv()

# Parse command line arguments
parser = argparse.ArgumentParser(
    description="Self-healing test automation agent",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  python agent.py --goal-language cypress --test-file-path cypress/e2e/login.cy.js
  python agent.py --goal-language js-playwright --test-file-path tests/login.spec.js
    """
)
parser.add_argument(
    "--goal-language",
    choices=["js-playwright", "python-playwright", "cypress"],
    default="cypress",
    help="Target test framework for code generation"
)
parser.add_argument(
    "--test-file-path",
    type=str,
    required=True,
    help="Path to the test file to analyze and fix"
)

args, _ = parser.parse_known_args()

# Configuration
GOAL_LANGUAGE = args.goal_language
TEST_FILE_PATH = args.test_file_path
TODO_DIR = Path("self_healing/todo")

# Model configuration
PLANNING_MODEL = "google_genai:gemini-2.5-flash"
WEB_MODEL = "google_genai:gemini-2.5-flash"
CODING_MODEL = "gemini-2.5-flash"


async def main():
    """
    Main execution flow for the self-healing test automation system.
    
    Workflow:
    1. Initialize MCP servers (Playwright, Filesystem)
    2. Create Planning Agent to analyze test and generate todos
    3. Create Web Agent to execute browser automation tasks
    4. (Optional) Create Coding Agent to generate fixed test code
    5. Execute agent pipeline using LangGraph
    """
    
    print("="*80)
    print("Self-Healing Test Automation Agent")
    print("="*80)
    print(f"Target Language: {GOAL_LANGUAGE}")
    print(f"Test File: {TEST_FILE_PATH}")
    print("="*80)
    
    # MCP Server Configurations
    mcp_configs = {
        "playwright": {
            "command": "npx",
            "args": ["-y", "@playwright/mcp@latest", "--isolated"],
        },
        "filesystem": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", os.getcwd()],
        }
    }
    
    # Load MCP tools with stateful sessions
    print("\nInitializing MCP servers...")
    stack, sessions, all_tools = await load_mcp_server_tools(mcp_configs)
    
    # Keep the stack alive throughout the execution
    async with stack:
        # Extract tools by server
        playwright_tools = sessions["playwright"]["tools"]
        file_system_tools = sessions["filesystem"]["tools"]
        
        print(f"Total tools loaded: {len(all_tools)}")
        print(f"Playwright tools: {len(playwright_tools)}")
        print(f"Filesystem tools: {len(file_system_tools)}")
        
        # Initialize coding model (for future use)
        coding_model = ChatGoogleGenerativeAI(
            model=CODING_MODEL,
            api_key=os.getenv("GOOGLE_API_KEY")
        ).bind_tools(file_system_tools)

        # Create Planning Agent
        print("\nCreating Planning Agent...")
        planning_agent = create_agent(
            model=PLANNING_MODEL,
            tools=file_system_tools,
            middleware=[
                PlanningAgent.process_message,
                PlanningAgent.process_response,
                PlanningAgent.retry_model,
                ToolRetryMiddleware(
                    max_retries=3,
                    backoff_factor=0,
                    initial_delay=1.0,
                )    
            ]
        )

        # Create Web Agent
        print("Creating Web Agent...")
        web_agent = create_agent(
            model=WEB_MODEL,
            tools=file_system_tools + playwright_tools,
            middleware=[
                WebAgent.init_message,
                WebAgent.refresh_messages,
                WebAgent.retry_model,
                ToolRetryMiddleware(
                    max_retries=3,
                    backoff_factor=0,
                    initial_delay=1.0,
                )
            ]
        )

        # Build agent graph
        print("Building agent workflow graph...")
        graph = StateGraph(AgentState)
        graph.add_node("planning_agent", planning_agent)
        graph.add_node("web_agent", web_agent)

        # Set the entry point
        graph.set_entry_point("planning_agent")

        # Add edges
        graph.add_edge("planning_agent", "web_agent")
        graph.add_edge("web_agent", END)

        # Compile the graph
        app = graph.compile()

        # Prepare initial state
        task_id = str(uuid.uuid4())
        input_state = AgentState({
            "messages": [HumanMessage(content=[TEST_FILE_PATH])],
            "related_script_pathes": [],
            "task_id": task_id
        })

        print(f"\nStarting agent execution (Task ID: {task_id})...")
        print("="*80)

        # Execute the agent pipeline
        conversation = []
        async for chunk in app.astream(
            input_state,
            stream_mode="updates",
            config={"recursion_limit": 200}
        ):
            conversation.append(chunk)

        print("\n" + "="*80)
        print("Agent execution completed!")
        print(f"Results saved to: {TODO_DIR}/todo_{task_id}.md")
        print("="*80)

        # Future: Coding Agent Integration
        # Uncomment below to enable code generation from playwright actions
        
        # # Parse playwright code from conversation
        # playwright_code = []
        # for item in conversation:
        #     content = item[list(item.keys())[0]]['messages'][0].content
        #     if isinstance(content, str):
        #         js_code_blocks = re.findall(r"```js\s*([\s\S]*?)```", content)
        #         if js_code_blocks:
        #             playwright_code.append(js_code_blocks[0])
        #
        # # Initialize coding agent
        # coding_agent_instance = CodingAgent(coding_model=coding_model)
        # coding_prompt = coding_agent_instance.get_template(GOAL_LANGUAGE)
        # 
        # # Build coding graph and execute
        # ...


if __name__ == "__main__":
    asyncio.run(main())
