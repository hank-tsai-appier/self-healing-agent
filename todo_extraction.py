"""
Test script for PlaywrightCodeExtractor

This script demonstrates and tests the functionality of PlaywrightCodeExtractor
by extracting todos and tool calls from a conversation file.

Usage:
    python self_healing/tests/test_playwright_extractor.py --conversation-path self_healing/results/conversation_70f0c5af8e1c455ebf52eb3a86c9bae0.md
"""

import argparse
from pathlib import Path
import sys

# Add parent directory to path to import utils
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from self_healing.src.utils.playwright_extractor import PlaywrightCodeExtractor


def print_section_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def test_extract_last_todo(extractor: PlaywrightCodeExtractor):
    """Test extracting the last todo item."""
    print_section_header("Testing: Extract Last Todo")
    
    last_todo = extractor.extract_last_todo()
    
    if last_todo:
        print(f"\n✅ Found last todo:")
        PlaywrightCodeExtractor.print_last_todo(last_todo)
    else:
        print("\n⚠️  No todo item found in conversation")
    
    return last_todo


def test_extract_last_todo_list(extractor: PlaywrightCodeExtractor):
    """Test extracting the last complete todo list."""
    print_section_header("Testing: Extract Last Todo List")
    
    last_todo_list = extractor.extract_last_todo_list()
    
    if last_todo_list:
        print(f"\n✅ Found todo list with {len(last_todo_list.get('todos', []))} items:")
        PlaywrightCodeExtractor.print_last_todo_list(last_todo_list)
    else:
        print("\n⚠️  No todo list found in conversation")
        print("This is normal if the conversation doesn't contain Markdown todo lists")
    
    return last_todo_list


def test_extract_tool_calls(extractor: PlaywrightCodeExtractor):
    """Test extracting tool calls with input/output pairs."""
    print_section_header("Testing: Extract Tool Calls")
    
    tool_calls = extractor.extract_tool_calls()
    
    if tool_calls:
        print(f"\n✅ Found {len(tool_calls)} tool calls:")
        PlaywrightCodeExtractor.print_tool_calls(tool_calls)
    else:
        print("\n⚠️  No tool calls found in conversation")
    
    return tool_calls


def save_extraction_results(
    output_path: Path,
    last_todo_list,
    tool_calls: list
):
    """Save extraction results to a file."""
    print_section_header("Saving Results")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Write todos section
        todos = last_todo_list.get('todos', []) if last_todo_list else []
        f.write(f"Todos ({len(todos)}):\n")
        f.write("=" * 60 + "\n")
        
        if todos:
            for todo in todos:
                f.write(f"{todo}\n")
        else:
            f.write("No todo list found in conversation.\n")
        
        # Write tool calls section
        f.write(f"\n\nTool Calls ({len(tool_calls)}):\n")
        f.write("=" * 60 + "\n")
        
        if tool_calls:
            for i, call in enumerate(tool_calls, 1):
                # ToolCall is a NamedTuple, use attribute access instead of .get()
                f.write(f"\n[{i}] Tool: {call.tool_name}\n")
                if call.description:
                    f.write(f"Description: {call.description}\n")
                f.write(f"Input: {call.input_data}\n")
                f.write(f"Playwright Code:\n{call.playwright_code}\n")
                f.write("-" * 60 + "\n")
        else:
            f.write("No tool calls found.\n")
    
    print(f"\n✅ Results saved to: {output_path}")
    print(f"   - Todos: {len(todos)}")
    print(f"   - Tool calls: {len(tool_calls)}")


def main():
    parser = argparse.ArgumentParser(
        description="Test PlaywrightCodeExtractor functionality",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--conversation-path",
        type=str,
        required=True,
        help="Path to the conversation markdown file",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="Path to save extraction results (default: same dir as conversation with _extracted.txt suffix)",
    )
    
    args = parser.parse_args()
    
    # Validate conversation path
    conversation_path = Path(args.conversation_path)
    if not conversation_path.exists():
        print(f"❌ Error: Conversation file not found: {conversation_path}")
        sys.exit(1)
    
    # Set output path
    if args.output_path:
        output_path = Path(args.output_path)
    else:
        output_path = conversation_path.parent / f"{conversation_path.stem}_extracted.txt"
    
    # Print header
    print("=" * 80)
    print("PlaywrightCodeExtractor Test Suite")
    print("=" * 80)
    print(f"Conversation file: {conversation_path}")
    print(f"Output file: {output_path}")
    
    # Initialize extractor
    extractor = PlaywrightCodeExtractor(conversation_path)
    
    # Run tests
    last_todo = test_extract_last_todo(extractor)
    last_todo_list = test_extract_last_todo_list(extractor)
    tool_calls = test_extract_tool_calls(extractor)
    
    # Save results
    save_extraction_results(output_path, last_todo_list, tool_calls)
    
    # Print summary
    print_section_header("Test Summary")
    print(f"✅ Last todo found: {'Yes' if last_todo else 'No'}")
    print(f"✅ Todo list found: {'Yes' if last_todo_list else 'No'}")
    print(f"✅ Tool calls found: {len(tool_calls)}")
    print("\n" + "=" * 80)
    print("All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during testing: {e}")
        raise