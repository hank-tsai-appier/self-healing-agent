# Lazy imports to avoid circular dependency issues
def __getattr__(name):
    if name == "JsonFormatter":
        from .conversation_formatter import JsonFormatter

        return JsonFormatter
    elif name == "PromptLoader":
        from .prompt_loader import PromptLoader

        return PromptLoader
    elif name == "load_prompts":
        from .prompt_loader import load_prompts

        return load_prompts
    else:
        raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "JsonFormatter",
    "PromptLoader",
    "load_prompts",
]
