# Self-Healing Test Automation System

AI-powered test maintenance and self-healing capabilities for automated test suites using Claude Agent SDK and Playwright MCP tools.

---

## Overview

This system automatically fixes failing Cypress tests by:
1. Executing tests with Playwright MCP tools to capture real browser interactions
2. Analyzing failures and identifying incorrect selectors
3. Auto-fixing test code based on actual page structure
4. Currently supports **Cypress** framework

---

## Installation

### 1. Clone this repository into your automation testing repo

```bash
cd your-automation-testing-repo
git clone <this-repo-url> self_healing
```

Or add as a git subtree:
```bash
git subtree add --prefix=self_healing <repo-url> main --squash
```

### 2. Install uv (Python Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Install Dependencies

Navigate to the self_healing directory and install Python dependencies:

```bash
cd self_healing
uv sync
```

### 4. Configure API Keys

Create a `.env` file in the **root directory** of your automation testing repo (not in self_healing):

```bash
# In your-automation-testing-repo/.env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here  # Optional, for additional features
```

---

## Usage

Run the self-healing system with your test script path:

```bash
PYTHONPATH=. self_healing/main.py --test-script-path=<path-to-your-test>
```

**Example:**
```bash
PYTHONPATH=. self_healing/main.py --test-script-path=cypress/e2e/login.cy.js
```

The system will:
1. Execute your test using Playwright MCP tools
2. Capture any failures and page snapshots
3. Automatically fix selector issues in your test code
4. Generate a detailed conversation log in `self_healing/results/`

---

## Customization for Different Test Frameworks

### For Non-Cypress Frameworks

#### 1. Modify Test Execution Command

Edit `self_healing/src/utils/subprocess_executor.py` to change the subprocess execution command:

```python
# Example: Change from Cypress to Playwright
cmd = [
    "npx",
    "playwright",
    "test",
    test_file_path,
]
```

#### 2. Update Prompts

Adjust prompts in `self_healing/src/prompts/` to match your framework:

- `claude_agent.yaml` - Main agent prompts
- `coding_agent.yaml` - Code fixing prompts

Replace "Cypress" references with your target framework (e.g., "Playwright", "Selenium", etc.)

---

## How It Works

### Architecture

The system uses **Claude Agent SDK** combined with **Playwright MCP (Model Context Protocol) tools**:

1. **Web Agent** (`WebAgentApp`)
   - Uses Playwright MCP tools to interact with the browser
   - Captures page snapshots and element information
   - Identifies actual selectors from the DOM

2. **Coding Agent** (`CodingAgentApp`)
   - Analyzes test failures from conversation logs
   - Fixes incorrect selectors in test code
   - Retries tests up to 3 times with continuous learning

3. **MCP Integration**
   - Playwright MCP server provides browser automation tools
   - Real-time page inspection and interaction
   - Accurate selector identification from live page state

### Workflow

```
Test File → Web Agent (Browser Execution) → Conversation Log
                                                ↓
                                        Coding Agent (Fix Code)
                                                ↓
                                        Execute Fixed Test
                                                ↓
                                        Success or Retry (max 3 times)
```

---

## Project Structure

```
self_healing/
├── src/
│   ├── agents/          # Agent implementations
│   │   ├── web_agent.py       # Browser automation agent
│   │   └── coding_agent.py    # Code fixing agent
│   ├── lib/             # Core runner implementations
│   │   ├── web_agent_runner.py
│   │   └── coding_agent_runner.py
│   ├── utils/           # Utility modules
│   │   ├── subprocess_executor.py  # Test execution
│   │   ├── conversation_extractor.py
│   │   └── prompt_loader.py
│   └── prompts/         # Agent prompts
│       ├── claude_agent.yaml
│       └── coding_agent.yaml
├── playwright/          # Playwright MCP server (subtree)
├── results/            # Generated logs and reports
└── main.py            # Entry point
```

---

## Requirements

- **Python**: 3.10+
- **Node.js**: 22+ (for Playwright MCP server)
- **API Keys**: Anthropic API key (Claude)

---

## Support

For issues or questions, contact: **hank.tsai@appier.com**
