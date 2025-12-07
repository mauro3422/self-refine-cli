import sys
import os
import time
from core.poetiq import run_poetiq
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools

# Setup
sys.path.append(os.getcwd())
register_file_tools()
register_command_tools()

def run_task(task_name, prompt):
    print(f"\n\n{'='*60}")
    print(f"🎓 EDUCATION TASK: {task_name}")
    print(f"📝 Prompt: {prompt}")
    print(f"{'='*60}")
    
    start = time.time()
    result = run_poetiq(prompt)
    duration = time.time() - start
    
    print(f"\n✅ Finished in {duration:.1f}s")
    print(f"📊 Score: {result['score']}")
    print(f"🛠️ Tools: {result['tools_used']}")
    
    return result

# Iteration 1: Creation
task1 = "Create a python file named 'sandbox/utils.py' that contains a function 'get_system_info()' which returns the current OS name."
res1 = run_task("Code Generation", task1)

# Wait a bit for memory to potentially index (although indexing is blocking in current implementation usually)
time.sleep(2)

# Iteration 2: Execution / Usage
# This tests if it can use 'python_exec' or if it tries to invent a tool, and if it knows where the file is.
task2 = "Execute the 'get_system_info' function from 'sandbox/utils.py' and tell me the operating system."
res2 = run_task("Code Execution", task2)

print("\n\n🎓 Education Session Complete.")
