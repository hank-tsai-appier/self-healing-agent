class JsonFormatter:
    @staticmethod
    def remove_markdown_markers(content: str) -> str:
        if content.startswith("```json"):
            content = content[len("```json"):].strip()
        if content.startswith("```"):
            content = content[len("```"):].strip()
        if content.endswith("```"):
            content = content[:-3].strip()
        return content