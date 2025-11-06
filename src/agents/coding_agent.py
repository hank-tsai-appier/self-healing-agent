from langchain_google_genai import ChatGoogleGenerativeAI

from self_healing.src.types.models import AgentState
from self_healing.src.utils.prompt_loader import load_prompts


class CodingAgent:
    """
    Coding Agent responsible for converting playwright code to target test framework code.
    
    This agent takes playwright automation code and related context, then generates
    code in the target language/framework (e.g., Cypress, JS Playwright, Python Playwright).
    """

    def __init__(self, coding_model: ChatGoogleGenerativeAI):
        """
        Initialize the coding agent with a language model.
        
        Args:
            coding_model: Pre-configured ChatGoogleGenerativeAI model with tools bound
        """
        self.coding_model = coding_model
        self.prompt_loader = load_prompts()

    async def coding_agent(self, state: AgentState):
        """
        Main execution method for the coding agent.
        
        Args:
            state: Current agent state containing messages and context
            
        Returns:
            Dictionary with updated messages containing the generated code
        """
        response = await self.coding_model.ainvoke(state.messages)
        print(f"response: {response}")

        return {"messages": [response]}

    def get_template_name(self, goal_language: str) -> str:
        """
        Maps goal language to template name.
        
        Args:
            goal_language: Target language identifier
            
        Returns:
            Template name for the specified language
            
        Raises:
            ValueError: If the goal language is not supported
        """
        language_template_map = {
            "js-playwright": "js_playwright_template",
            "python-playwright": "python_playwright_template",
            "cypress": "cypress_template"
        }
        
        if goal_language not in language_template_map:
            raise ValueError(f"Invalid goal language: {goal_language}")
        
        return language_template_map[goal_language]

    def get_template(self, goal_language: str) -> str:
        """
        Loads the appropriate code template for the target language.
        
        Args:
            goal_language: Target language identifier
            
        Returns:
            Template string for code generation
        """
        template_name = self.get_template_name(goal_language)

        # Load prompt from coding_agent.yaml
        prompt_data = self.prompt_loader.load_prompt("coding_agent")
        return prompt_data.get(template_name, "")

    def should_continue(self, state: AgentState) -> str:
        """
        Determines if the agent should continue processing or end.
        
        Args:
            state: Current agent state
            
        Returns:
            "end" if extras are found in the last message, "continue" otherwise
        """
        messages = state.messages
        last_message = messages[-1]

        if "extras" in str(last_message.content):
            return "end"
        else:
            return "continue"

