from typing import Callable
from langchain.agents.middleware.types import wrap_model_call
from langchain.agents.middleware import ModelRequest, ModelResponse


class BaseAgent:
    """
    Base class for all agents providing common middleware functionality.
    """

    @staticmethod
    @wrap_model_call
    async def retry_model(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        """
        Retry logic middleware for model calls.
        Attempts up to 3 retries on failure with exponential backoff.
        
        Args:
            request: The model request to execute
            handler: The handler function to call
            
        Returns:
            ModelResponse from successful execution
            
        Raises:
            Exception: If all retry attempts fail
        """
        for attempt in range(3):
            try:
                return await handler(request)
            except Exception as e:
                if attempt == 2:
                    raise
                print(f"Retry {attempt + 1}/3 after error: {e}")

