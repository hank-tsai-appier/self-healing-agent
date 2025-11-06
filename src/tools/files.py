from langchain_core.tools import tool
from pydantic import BaseModel, Field

class UpdateFileInput(BaseModel):
    path: str = Field(..., description="The path to the file to update.")
    content: str = Field(..., description="The new content to write to the file.")

class UpdateFileOutput(BaseModel):
    success: bool = Field(..., description="Whether the file was successfully updated.")
    message: str = Field(..., description="A message describing the result.")

@tool
def update_file(path: str, content: str) -> UpdateFileOutput:
    """
    Update the content of a file at the given path.
    Args:
        path: The path to the file to update.
        content: The new content to write to the file.
    Returns:
        UpdateFileOutput: A message describing the result.
    """
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return UpdateFileOutput(success=True, message="✅ File updated successfully.")
    except Exception as e:
        return UpdateFileOutput(success=False, message=f"❌ Error updating file: {e}")
