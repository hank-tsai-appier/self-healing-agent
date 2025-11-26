from json_repair import repair_json


class JsonFormatter:
    @staticmethod
    def remove_markdown_markers(content: str) -> str:
        """
        Repairs and cleans JSON content using json-repair library.
        
        This method:
        - Removes markdown code block markers (```json, ```)
        - Fixes missing quotes and commas
        - Handles trailing commas
        - Removes comments
        - Repairs other common JSON formatting issues
        
        Args:
            content: Raw content that may contain JSON with markdown markers or formatting issues
            
        Returns:
            Cleaned and repaired JSON string
        """
        return repair_json(content)