# Training Mission 1: Search and List TODOs
# Run: python sandbox/test_agent.py

import sys
import os
sys.path.insert(0, '.')

# 1. Register tools (including new search tool)
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
from tools.search_tools import register_search_tools

print("🔧 Registering tools...")
register_file_tools()
register_command_tools()
register_search_tools() 

# 2. Run Poetiq on a training task
from core.poetiq import run_poetiq

print("\n" + "="*70)
print("🎓 TRAINING MISSION 1: CODE SEARCH")
print("="*70)

task = """
Misión: Encuentra todos los comentarios "TODO" (todo en mayúsculas) dentro de la carpeta 'core/' y 'memory/'.
Usa la herramienta 'search_files' para esto.
Luego, crea un archivo llamado 'sandbox/todo_list.md' con una lista limpia de lo que encuentres.
"""

print(f"Task: {task.strip()}")

result = run_poetiq(task)

print("\n" + "="*70)
print("📊 TRAINING RESULT:")
print(f"  Score: {result.get('score', 'N/A')}/25")
print(f"  Tools used: {result.get('tools_used', [])}")
print("="*70)

# 3. Check if we learned how to search
from memory.orchestrator import get_orchestrator
orch = get_orchestrator()
orch.memory.reload()

print("\n📚 NEW MEMORIES:")
for mem in orch.memory.memories[-3:]:  # Last 3
    print(f"  - {mem.get('lesson', 'N/A')[:100]}...")
