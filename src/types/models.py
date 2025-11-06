from typing import List, TypedDict
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage


class Todo(BaseModel):
    """
    Todo model for the todos list
    """
    id: int = Field(description="The id of the todo")
    type: str = Field(description="api or ui")
    description: str = Field(description="The description of the todo")
    status: str = Field(description="pending or done")


class AgentState(TypedDict, total=False):
    """
    AgentState defines the mutable state shared across the agent's workflow.
    """
    messages: List[BaseMessage]
    related_script_pathes: List[str]
    task_id: str

