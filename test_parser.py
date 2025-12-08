"""Test the improved parser with malformed JSON examples"""
from core.parsers import extract_tool_call

# Test cases from real LLM outputs
test_cases = [
    # Case 1: Python raw string
    '{"tool": "re", "params": {"pattern": r"^test$"}}',
    
    # Case 2: Python booleans
    '{"tool": "test", "params": {"valid": True, "debug": False}}',
    
    # Case 3: With comments
    '''{"tool": "python_exec", "params": {"code": "print(1)"}}  # This is a test''',
    
    # Case 4: Trailing comma
    '{"tool": "test", "params": {"a": 1,}}',
    
    # Case 5: Complex pattern with r'' 
    '''{"tool": "re", "params": {"pattern": r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+$'}}''',
    
    # Case 6: Just extract tool name as fallback
    'Some text {"tool": "unittest", garbage that breaks json',
]

print("=" * 60)
print("Testing Parser Improvements")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    result = extract_tool_call(test)
    status = "✅" if result else "❌"
    tool = result.get("tool", "N/A") if result else "FAILED"
    print(f"\nCase {i}: {status}")
    print(f"  Input: {test[:60]}...")
    print(f"  Tool: {tool}")
