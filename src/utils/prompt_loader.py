from pathlib import Path
from typing import Any, Dict

import yaml


class PromptLoader:
    """
    PromptLoader is responsible for loading prompts from YAML files.
    It provides a simple interface to load and format prompts with variables.
    """

    def __init__(self, prompts_dir: str = "self_healing/src/prompts"):
        """
        Initialize the PromptLoader with the directory containing prompt YAML files.

        Args:
            prompts_dir: Path to the directory containing prompt YAML files
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompts_cache: Dict[str, Dict[str, Any]] = {}

    def load_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Load a single prompt from a YAML file.

        Args:
            prompt_name: Name of the prompt file (without .yaml extension)

        Returns:
            Dictionary containing the prompt data
        """
        if prompt_name in self.prompts_cache:
            return self.prompts_cache[prompt_name]

        prompt_file = self.prompts_dir / f"{prompt_name}.yaml"

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_data = yaml.safe_load(f)

        self.prompts_cache[prompt_name] = prompt_data
        return prompt_data

    def format_prompt(self, prompt_name: str, prompt_key: str = "template", **kwargs) -> str:
        """
        Load and format a prompt with the provided variables.

        Args:
            prompt_name: Name of the prompt file (without .yaml extension)
            prompt_key: Key within the YAML file to access (default: "template")
                       For files with multiple prompts, specify the key like "system_prompt", "analysis_prompt"
            **kwargs: Variables to format the prompt template with

        Returns:
            Formatted prompt string

        Examples:
            # Single template format (legacy)
            loader.format_prompt("web_agent", todo_file="/path/to/file")

            # Multiple prompts format (new)
            loader.format_prompt("claude_agent", prompt_key="system_prompt")
            loader.format_prompt("claude_agent", prompt_key="analysis_prompt", test_file_path="/path")
        """
        prompt_data = self.load_prompt(prompt_name)

        # Check if prompt_key exists in the data
        if prompt_key in prompt_data:
            # New format: nested prompts with template inside
            if isinstance(prompt_data[prompt_key], dict) and "template" in prompt_data[prompt_key]:
                template = prompt_data[prompt_key]["template"]
            # Old format or direct string
            else:
                template = prompt_data[prompt_key]
        else:
            # Fallback to legacy "template" key
            template = prompt_data.get("template", "")

        return template.format(**kwargs)

    def load_all_prompts(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all prompt files from the prompts directory.

        Returns:
            Dictionary mapping prompt names to their data
        """
        all_prompts = {}

        for prompt_file in self.prompts_dir.glob("*.yaml"):
            prompt_name = prompt_file.stem
            all_prompts[prompt_name] = self.load_prompt(prompt_name)

        return all_prompts


def load_prompts(prompts_dir: str = "self_healing/src/prompts") -> PromptLoader:
    """
    Factory function to create and return a PromptLoader instance.

    Args:
        prompts_dir: Path to the directory containing prompt YAML files

    Returns:
        PromptLoader instance
    """
    return PromptLoader(prompts_dir)
