"""
Self-Healing Test Automation Framework

This package provides AI-powered test maintenance and self-healing capabilities
for automated test suites. It includes agents for planning, web automation,
and code generation, along with utilities for MCP server management and prompt handling.
"""

# Lazy imports to avoid circular dependency issues
def __getattr__(name):
    if name == "load_prompts":
        from .utils.prompt_loader import load_prompts
        return load_prompts
    elif name == "PromptLoader":
        from .utils.prompt_loader import PromptLoader
        return PromptLoader
    elif name == "JsonFormatter":
        from .utils.json_fommatter import JsonFormatter
        return JsonFormatter
    elif name == "TextFileLoader":
        from .utils.file_loader import TextFileLoader
        return TextFileLoader
    elif name == "PlaywrightCodeExtractor":
        from .utils.playwright_extractor import PlaywrightCodeExtractor
        return PlaywrightCodeExtractor
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "load_prompts",
    "PromptLoader",
    "JsonFormatter",
    "TextFileLoader",
    "PlaywrightCodeExtractor",
]

