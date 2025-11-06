import yaml
from pathlib import Path
from typing import Dict, Any


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
    
    def format_prompt(self, prompt_name: str, **kwargs) -> str:
        """
        Load and format a prompt with the provided variables.
        
        Args:
            prompt_name: Name of the prompt file (without .yaml extension)
            **kwargs: Variables to format the prompt template with
            
        Returns:
            Formatted prompt string
        """
        prompt_data = self.load_prompt(prompt_name)
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

