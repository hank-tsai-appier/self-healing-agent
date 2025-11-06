# Self-Healing Test Automation - Architecture

## Overview

This document describes the refactored architecture of the self-healing test automation system, following Python best practices for modularity, maintainability, and scalability.

## Project Structure

```
self_healing/
├── agent.py                    # Main entry point
├── src/
│   ├── __init__.py            # Package exports
│   ├── types/                 # Type definitions and models
│   │   ├── __init__.py
│   │   └── models.py          # Todo, AgentState
│   ├── agents/                # Agent implementations
│   │   ├── __init__.py
│   │   ├── base.py           # BaseAgent with retry middleware
│   │   ├── planning_agent.py # Test analysis and todo generation
│   │   ├── web_agent.py      # Browser automation execution
│   │   └── coding_agent.py   # Code generation and transformation
│   ├── utils/                 # Utility functions
│   │   ├── __init__.py
│   │   ├── json_fommatter.py # JSON parsing helpers
│   │   ├── prompt_loader.py  # YAML prompt management
│   │   └── mcp_loader.py     # MCP server initialization
│   ├── prompts/               # YAML prompt templates
│   │   ├── plan_agent.yaml
│   │   ├── web_agent.yaml
│   │   └── coding_agent.yaml
│   └── tools/                 # Custom tool implementations
│       └── files.py
├── todo/                      # Generated todo lists
└── results/                   # Test execution results
```

## Module Responsibilities

### 1. Types (`src/types/`)

Contains all type definitions and data models used throughout the system.

**models.py**
- `Todo`: Pydantic model for todo items with validation
- `AgentState`: TypedDict defining shared state across agents

### 2. Agents (`src/agents/`)

Implements the three main agents in the system.

**base.py**
- `BaseAgent`: Base class providing common middleware functionality
  - Retry logic with exponential backoff
  - Error handling patterns

**planning_agent.py**
- `PlanningAgent`: Analyzes test scripts and creates structured todo lists
  - `process_message`: Prepares prompts for test analysis
  - `process_response`: Parses AI responses and saves todos

**web_agent.py**
- `WebAgent`: Executes browser automation tasks
  - `init_message`: Initializes agent with context
  - `refresh_messages`: Updates messages with current todo status

**coding_agent.py**
- `CodingAgent`: Converts playwright code to target framework
  - `coding_agent`: Main execution method
  - `get_template`: Loads appropriate code template
  - `should_continue`: Controls agent loop

### 3. Utils (`src/utils/`)

Utility functions and helpers.

**json_fommatter.py**
- `JsonFormatter`: Handles JSON parsing and markdown removal

**prompt_loader.py**
- `PromptLoader`: Manages YAML prompt templates
- `load_prompts`: Factory function for creating loader instances

**mcp_loader.py**
- `load_mcp_server_tools`: Initializes MCP servers and loads tools
  - Manages persistent sessions
  - Handles multiple server configurations
  - Returns combined tool list

### 4. Entry Point (`agent.py`)

Main execution script that:
1. Parses command line arguments
2. Initializes MCP servers
3. Creates agent pipeline
4. Executes workflow using LangGraph

## Design Patterns

### Separation of Concerns
Each module has a single, well-defined responsibility:
- Types: Data structures
- Agents: Business logic
- Utils: Reusable helpers
- Entry point: Orchestration

### Middleware Pattern
Agents use middleware for cross-cutting concerns:
- Retry logic
- Message preprocessing
- Response post-processing
- Error handling

### Factory Pattern
- `load_prompts()`: Creates PromptLoader instances
- `load_mcp_server_tools()`: Initializes MCP servers

### Dependency Injection
Agents receive dependencies through constructor injection:
```python
coding_agent = CodingAgent(coding_model=model)
```

## Best Practices Applied

1. **Clear Module Structure**: Organized by functionality (types, agents, utils)
2. **Type Hints**: All functions have proper type annotations
3. **Documentation**: Comprehensive docstrings for all classes and methods
4. **Single Responsibility**: Each class/function has one clear purpose
5. **DRY Principle**: Common functionality in BaseAgent
6. **Package Exports**: Controlled exports via `__init__.py`
7. **Configuration Management**: Centralized in main entry point
8. **Error Handling**: Consistent error handling patterns
9. **Async/Await**: Proper async context management
10. **Logging**: Clear console output for debugging

## Usage

### Basic Execution
```bash
python agent.py --goal-language cypress --test-file-path path/to/test.cy.js
```

### Importing Modules
```python
from self_healing.src.types import AgentState, Todo
from self_healing.src.agents import PlanningAgent, WebAgent
from self_healing.src.utils import load_mcp_server_tools
```

## Future Enhancements

1. **Configuration File**: Move hardcoded configs to YAML/JSON
2. **Plugin System**: Allow custom agent implementations
3. **Testing**: Add unit tests for each module
4. **Logging**: Replace print statements with proper logging
5. **Metrics**: Add performance monitoring
6. **CLI**: Enhanced CLI with more options
7. **Documentation**: API reference generation

## Migration Notes

The refactoring maintains backward compatibility with existing:
- Prompt templates (no changes needed)
- Tool configurations
- Agent behavior and logic

All functionality from the original `agent.py` has been preserved and organized into logical modules.

