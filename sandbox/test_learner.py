# Debug test for MemoryLearner
import sys
sys.path.insert(0, '.')

from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
register_file_tools()
register_command_tools()

from memory.learner import MemoryLearner

learner = MemoryLearner()

print("=" * 60)
print("Testing MemoryLearner directly...")
print("=" * 60)

result = learner.learn_from_session(
    task="crear un archivo test.py",
    initial_score=10,
    final_score=20,
    iterations=2,
    tool_results={"write_file": "success"},
    errors=[]
)

print(f"\nResult: {result}")
print("=" * 60)

# Check memory file
import json
with open("outputs/agent_memory.json", "r") as f:
    data = json.load(f)
    print(f"Memories in file: {len(data.get('memories', []))}")
    for m in data.get('memories', [])[-3:]:
        print(f"  - {m.get('lesson', '')[:50]}...")
