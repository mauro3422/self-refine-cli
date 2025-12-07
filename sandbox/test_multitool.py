# Test script for multi-tool agentic loop
import sys
sys.path.insert(0, '.')

from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
register_file_tools()
register_command_tools()

from core.poetiq import run_poetiq

print("=" * 70)
print("🧪 TESTING MULTI-TOOL AGENTIC LOOP")
print("=" * 70)
print()
print("Task: Lista los archivos en sandbox, lee README.md y dime cuántas líneas tiene")
print()
print("=" * 70)

result = run_poetiq("lista los archivos en sandbox, lee README.md y dime cuántas líneas tiene")

print("\n" + "=" * 70)
print("📊 RESULT:")
print(f"  Score: {result.get('score', 'N/A')}/25")
print(f"  Tools used: {result.get('tools_used', [])}")
print("=" * 70)
