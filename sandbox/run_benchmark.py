# Benchmark Suite - Training and Testing the Poetiq Agent
# Runs multiple tasks, collects detailed metrics, generates report

import sys
sys.path.insert(0, '.')

import time
import json
from datetime import datetime

# Register tools first
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
register_file_tools()
register_command_tools()

from core.poetiq import run_poetiq
from utils.metrics import get_metrics

# Test tasks - varying complexity
TASKS = [
    # Simple tasks
    ("read", "lee el archivo sandbox/README.md y dame un resumen"),
    ("list", "lista los archivos en el directorio sandbox"),
    
    # Medium tasks
    ("write", "crea un archivo llamado sandbox/hello.py que imprima 'Hola Mundo'"),
    ("execute", "ejecuta python y muestra 2+2"),
    
    # Complex tasks
    ("analyze", "lee sandbox/test_agent.py y dime qué hace"),
]

def run_benchmark():
    print("=" * 70)
    print("🧪 POETIQ BENCHMARK SUITE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tasks: {len(TASKS)}")
    print("=" * 70)
    
    results = []
    metrics = get_metrics()
    
    for i, (task_type, task) in enumerate(TASKS, 1):
        print(f"\n{'='*70}")
        print(f"[{i}/{len(TASKS)}] Task Type: {task_type.upper()}")
        print(f"Task: {task[:60]}...")
        print("=" * 70)
        
        # Start timing
        start = time.time()
        metrics.start_session(task)
        
        try:
            result = run_poetiq(task)
            success = result.get('score', 0) >= 15
            
            duration = time.time() - start
            metrics.end_session(success=success, score=result.get('score', 0))
            
            results.append({
                "task_type": task_type,
                "task": task[:50],
                "score": result.get('score', 0),
                "success": success,
                "duration": round(duration, 1),
                "tools_used": result.get('tools_used', []),
                "iterations": result.get('iterations', 0)
            })
            
            print(f"\n✅ Completed: Score {result.get('score', 0)}/25 in {duration:.1f}s")
            
        except Exception as e:
            duration = time.time() - start
            metrics.end_session(success=False, score=0)
            
            results.append({
                "task_type": task_type,
                "task": task[:50],
                "score": 0,
                "success": False,
                "duration": round(duration, 1),
                "error": str(e)[:100]
            })
            
            print(f"\n❌ Failed: {e}")
        
        # Small delay between tasks
        time.sleep(2)
    
    # Generate report
    print("\n" + "=" * 70)
    print("📊 BENCHMARK REPORT")
    print("=" * 70)
    
    total_time = sum(r['duration'] for r in results)
    successes = sum(1 for r in results if r['success'])
    avg_score = sum(r['score'] for r in results) / len(results)
    
    print(f"\nSummary:")
    print(f"  Total tasks: {len(results)}")
    print(f"  Successful: {successes}/{len(results)} ({successes/len(results)*100:.0f}%)")
    print(f"  Average score: {avg_score:.1f}/25")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Avg time per task: {total_time/len(results):.1f}s")
    
    print(f"\nBy Task Type:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} [{r['task_type']:8}] Score: {r['score']:2}/25  Time: {r['duration']:5.1f}s  Tools: {r.get('tools_used', [])}")
    
    # Get metrics summary
    summary = metrics.get_summary(len(results))
    print(f"\nPhase Timing (avg):")
    for phase, avg_time in summary.get('phase_avg_times', {}).items():
        print(f"  {phase}: {avg_time:.1f}s")
    
    # Save results
    report_path = f"outputs/benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": results,
            "summary": {
                "total_tasks": len(results),
                "success_rate": successes/len(results),
                "avg_score": avg_score,
                "total_time": total_time
            }
        }, f, indent=2)
    
    print(f"\n📁 Report saved: {report_path}")
    print("=" * 70)

if __name__ == "__main__":
    run_benchmark()
