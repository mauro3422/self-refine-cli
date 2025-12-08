"""
Unified monitoring utility for Poetiq autonomous worker.
Usage:
    python monitor.py status     - Check if worker is running
    python monitor.py kill       - Kill the worker
    python monitor.py log [N]    - Show last N lines of log (default 50)
    python monitor.py tasks [N]  - Show last N tasks (default 5)
    python monitor.py learnings  - Show all learnings from log
    python monitor.py memory     - Show memory summary
    python monitor.py recent     - Show recently modified files
    python monitor.py health     - Run health check on all systems
"""
import sys
import os
import json
import psutil
from datetime import datetime, timedelta

LOG_FILE = "autonomous.log"
MEMORY_FILE = "data/agent_memory.json"

def cmd_status():
    """Check if autonomous_loop.py is running"""
    print("Checking for autonomous_loop.py...")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('autonomous_loop.py' in arg for arg in cmdline):
                print(f"✅ ALIVE: PID {proc.info['pid']}")
                return
        except:
            pass
    print("❌ NOT RUNNING")

def cmd_kill():
    """Kill the autonomous_loop.py process"""
    print("Searching for autonomous_loop.py processes...")
    killed = 0
    for proc in psutil.process_iter(['pid', 'cmdline']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any('autonomous_loop.py' in arg for arg in cmdline):
                print(f"Killing PID {proc.info['pid']}...")
                proc.kill()
                killed += 1
        except:
            pass
    print(f"Terminated {killed} process(es).")

def cmd_log(lines=50):
    """Show last N lines of autonomous.log"""
    if not os.path.exists(LOG_FILE):
        print(f"❌ Log file not found: {LOG_FILE}")
        return
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        all_lines = f.readlines()
    
    for line in all_lines[-lines:]:
        print(line.rstrip())

def cmd_tasks(count=5):
    """Show last N generated tasks"""
    if not os.path.exists(LOG_FILE):
        print(f"❌ Log file not found: {LOG_FILE}")
        return
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    tasks = []
    for line in content.split('\n'):
        if 'Generated Task:' in line:
            task = line.split('Generated Task:')[-1].strip()
            tasks.append(task)
    
    print(f"=== Last {count} Tasks ===")
    for i, task in enumerate(tasks[-count:], 1):
        print(f"{i}. {task[:100]}...")

def cmd_learnings():
    """Extract all learnings from the log"""
    if not os.path.exists(LOG_FILE):
        print(f"❌ Log file not found: {LOG_FILE}")
        return
    
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    learnings = []
    for line in content.split('\n'):
        if 'Learned:' in line:
            learning = line.split('Learned:')[-1].strip()
            learnings.append(learning)
    
    print(f"=== {len(learnings)} Learnings ===")
    for l in learnings:
        print(f"  • {l}")

def cmd_memory():
    """Show memory summary"""
    if not os.path.exists(MEMORY_FILE):
        print(f"❌ Memory file not found: {MEMORY_FILE}")
        return
    
    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    memories = data.get('memories', data) if isinstance(data, dict) else data
    if isinstance(memories, dict):
        memories = list(memories.values())
    
    today = datetime.now().date().isoformat()
    today_count = sum(1 for m in memories if isinstance(m, dict) and m.get('created', '').startswith(today))
    
    print(f"=== Memory Summary ===")
    print(f"Total memories: {len(memories)}")
    print(f"Created today: {today_count}")
    print(f"\nLast 5 memories:")
    for m in memories[-5:]:
        if isinstance(m, dict):
            print(f"  • {m.get('content', str(m))[:80]}...")

def cmd_recent():
    """Show recently modified files (last 10 min)"""
    cutoff = datetime.now() - timedelta(minutes=10)
    recent = []
    
    exclude = {'__pycache__', '.git', 'node_modules', '.gemini', 'outputs'}
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude]
        for f in files:
            if f.endswith(('.py', '.md', '.json', '.txt')):
                path = os.path.join(root, f)
                try:
                    mtime = datetime.fromtimestamp(os.path.getmtime(path))
                    if mtime > cutoff:
                        recent.append((path, mtime))
                except:
                    pass
    
    recent.sort(key=lambda x: x[1], reverse=True)
    
    print(f"=== Files Modified in Last 10 Min ===")
    for path, mtime in recent[:20]:
        print(f"  {mtime.strftime('%H:%M:%S')} - {path}")

def cmd_health():
    """Check health of all systems"""
    print("=== System Health Check ===\n")
    
    # Check worker
    print("1. Autonomous Worker:")
    cmd_status()
    
    # Check LLM server
    print("\n2. LLM Server (port 8000):")
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5)
        print("   ✅ LLM Server responding")
    except:
        print("   ❌ LLM Server not responding")
    
    # Check Chroma
    print("\n3. ChromaDB (port 8100):")
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8100/api/v1/heartbeat", timeout=5)
        print("   ✅ ChromaDB responding")
    except:
        print("   ❌ ChromaDB not responding")
    
    # Check log
    print("\n4. Log File:")
    if os.path.exists(LOG_FILE):
        size = os.path.getsize(LOG_FILE)
        print(f"   ✅ {LOG_FILE} exists ({size:,} bytes)")
    else:
        print(f"   ⚠️ No log file yet")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'status':
        cmd_status()
    elif cmd == 'kill':
        cmd_kill()
    elif cmd == 'log':
        lines = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        cmd_log(lines)
    elif cmd == 'tasks':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        cmd_tasks(count)
    elif cmd == 'learnings':
        cmd_learnings()
    elif cmd == 'memory':
        cmd_memory()
    elif cmd == 'recent':
        cmd_recent()
    elif cmd == 'health':
        cmd_health()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
