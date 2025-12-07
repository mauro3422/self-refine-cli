# Quick test script - no args needed
# Run: python sandbox/test_agent.py

import sys
sys.path.insert(0, '.')

# Register tools first
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
print("🔧 Registering tools...")
register_file_tools()
register_command_tools()

from core.poetiq import run_poetiq

print("=" * 60)
print("🧪 Testing Poetiq Agent - Tool Name Fix")
print("=" * 60)

result = run_poetiq("crear un archivo llamado test_fix.py que imprima 'Fix exitoso!'")

print("\n" + "=" * 60)
print("📊 RESULT:")
print(f"  Score: {result.get('score', 'N/A')}/25")
print(f"  Tools used: {result.get('tools_used', [])}")
print(f"  Tool result: {result.get('tool_result', 'N/A')[:100]}")
print("=" * 60)

# Verify file was created
import os
if os.path.exists("sandbox/test_fix.py"):
    print("✅ File created successfully!")
    with open("sandbox/test_fix.py", "r") as f:
        print(f"   Content: {f.read()}")
else:
    print("❌ File NOT created - bug still exists")
