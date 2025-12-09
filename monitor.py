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
    python monitor.py metrics    - Show live metrics dashboard
    python monitor.py adaptive   - Show adaptive difficulty stats
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

def cmd_metrics():
    """Show live metrics dashboard from monitoring.json"""
    monitoring_file = "outputs/monitoring.json"
    
    if not os.path.exists(monitoring_file):
        print("❌ No monitoring data yet. Run autonomous_loop.py first.")
        return
    
    with open(monitoring_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    scores = data.get('metrics', {}).get('scores', [])
    durations = data.get('metrics', {}).get('durations', [])
    events = data.get('events', [])
    
    # Calculate stats
    avg_score = sum(scores) / len(scores) if scores else 0
    avg_duration = sum(durations) / len(durations) if durations else 0
    min_score = min(scores) if scores else 0
    max_score = max(scores) if scores else 0
    
    # Get session info
    session_start = data.get('session_start', 'Unknown')
    last_updated = data.get('last_updated', 'Unknown')
    
    print("\n" + "="*55)
    print("📊 LIVE METRICS DASHBOARD")
    print("="*55)
    print(f"Session started: {session_start}")
    print(f"Last updated:    {last_updated}")
    print("-"*55)
    print(f"Total tasks completed: {len(scores)}")
    print(f"Average score:         {avg_score:.1f}/25")
    print(f"Score range:           {min_score} - {max_score}")
    print(f"Average duration:      {avg_duration:.1f}s")
    print("-"*55)
    
    # Show last 5 tasks
    print("\n📝 Recent Tasks:")
    task_events = [e for e in events if e.get('type') == 'task_complete']
    for i, evt in enumerate(task_events[-5:], 1):
        details = evt.get('details', {})
        print(f"  {i}. Score: {details.get('score', '?')}/25 | "
              f"Duration: {details.get('duration', 0):.1f}s | "
              f"Verified: {'✓' if details.get('verified') else '✗'}")
    
    # Trend indicator
    if len(scores) >= 3:
        recent_avg = sum(scores[-3:]) / 3
        early_avg = sum(scores[:3]) / 3 if len(scores) >= 3 else recent_avg
        trend = "📈 Improving" if recent_avg > early_avg else "📉 Declining" if recent_avg < early_avg else "➡️ Stable"
        print(f"\nTrend: {trend} (early avg: {early_avg:.1f}, recent avg: {recent_avg:.1f})")
    
    print("="*55)

def cmd_adaptive():
    """Show adaptive difficulty stats"""
    adaptive_file = "data/adaptive_learning.json"
    
    if not os.path.exists(adaptive_file):
        print("❌ No adaptive learning data yet.")
        return
    
    with open(adaptive_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    current_level = data.get('current_difficulty', 2)
    level_names = {1: "Basic", 2: "Easy", 3: "Medium", 4: "Hard", 5: "Expert"}
    
    print("\n" + "="*55)
    print("🎯 ADAPTIVE DIFFICULTY STATS")
    print("="*55)
    print(f"Current Level: {current_level}/5 ({level_names.get(current_level, '?')})")
    print(f"Last Updated:  {data.get('last_updated', 'Unknown')}")
    print("-"*55)
    
    # Performance by category
    print("\n📊 Performance by Category:")
    performance = data.get('performance', {})
    for cat, levels in performance.items():
        total = sum(l.get('total', 0) for l in levels.values())
        success = sum(l.get('success', 0) for l in levels.values())
        rate = success / total * 100 if total > 0 else 0
        scores = []
        for l in levels.values():
            scores.extend(l.get('scores', []))
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {cat.upper():12} | {success}/{total} ({rate:.0f}%) | Avg: {avg:.1f}")
    
    # Weaknesses
    weaknesses = data.get('weakness_categories', [])
    if weaknesses:
        print(f"\n⚠️ Weakness Categories:")
        for w in weaknesses:
            print(f"  - {w['category']}: {w['success_rate']:.0%} success rate")
    else:
        print("\n✅ No weaknesses detected!")
    
    # Recent history
    history = data.get('history', [])
    if history:
        print(f"\n📝 Last 5 Tasks:")
        for h in history[-5:]:
            status = "✓" if h.get('success') else "✗"
            print(f"  {status} {h.get('category', '?'):10} | Score: {h.get('score', '?')} | Verified: {'✓' if h.get('verified') else '✗'}")
    
    print("="*55)

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
    elif cmd == 'metrics':
        cmd_metrics()
    elif cmd == 'adaptive':
        cmd_adaptive()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()

