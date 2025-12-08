# Unified Test Script - Supports single agent, parallel, and Poetiq modes
# Use: python run_test.py "task"                  → Single agent
#      python run_test.py "task" --parallel 3     → 3 agents parallel
#      python run_test.py "task" --poetiq         → Full Poetiq system
#      python run_test.py --stress 6              → Stress test with 6 agents

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_single(task: str):
    """Run single agent (using Poetiq with 1 worker)"""
    from core.poetiq import run_poetiq
    
    print(f"\n{'='*60}")
    print(f"🤖 SINGLE AGENT (Poetiq-1): {task[:50]}...")
    print(f"{'='*60}")
    
    result = run_poetiq(task, num_workers=1)
    
    print(f"\n📝 Response:\n{result['response'][:500]}...")
    print(f"\n✅ Score: {result['score']}/25 | Time: {result['total_time']:.1f}s")
    
    return result['score']


def run_parallel(task: str, num_workers: int = 3):
    """Run multiple agents (Poetiq mode)"""
    from core.poetiq import run_poetiq
    return run_poetiq(task, num_workers)['score']


def run_poetiq(task: str, num_workers: int = 3):
    """Run full Poetiq system"""
    from core.poetiq import run_poetiq
    result = run_poetiq(task, num_workers)
    return result['score']


def run_stress(num_agents: int = 6):
    """Run stress test using Poetiq instances"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from core.poetiq import run_poetiq
    
    print(f"\n{'='*60}")
    print(f"🔥 STRESS TEST: {num_agents} Poetiq instances")
    print(f"{'='*60}")
    
    def agent_task(agent_id: int):
        task = f"Crea archivo agent_{agent_id}.txt con el numero {agent_id}"
        # Run with 1 worker per instance to save resources
        result = run_poetiq(task, num_workers=1)
        return {
            "id": agent_id,
            "score": result['score'],
            "success": result['score'] >= 18
        }
    
    results = []
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=num_agents) as executor:
        futures = [executor.submit(agent_task, i) for i in range(1, num_agents + 1)]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✅" if result["success"] else "❌"
            print(f"  {status} Instance-{result['id']}: {result['score']}/25")
    
    success_count = sum(1 for r in results if r["success"])
    print(f"\n📊 RESULTS: {success_count}/{num_agents} successful")
    
    return success_count


def main():
    parser = argparse.ArgumentParser(description="Self-Refine Agent Test Runner")
    parser.add_argument("task", nargs="?", default=None, help="Task to run")
    parser.add_argument("--parallel", "-p", type=int, help="Run N agents in parallel")
    parser.add_argument("--poetiq", "-q", action="store_true", help="Use Poetiq system")
    parser.add_argument("--stress", "-s", type=int, help="Stress test with N agents")
    
    args = parser.parse_args()
    
    if args.stress:
        run_stress(args.stress)
    elif args.task:
        if args.poetiq:
            run_poetiq(args.task, num_workers=args.parallel or 3)
        elif args.parallel:
            run_parallel(args.task, args.parallel)
        else:
            run_single(args.task)
    else:
        print("""
🧪 Self-Refine Agent Test Runner

Usage:
  python run_test.py "task"                  → Single agent
  python run_test.py "task" --parallel 3     → 3 agents parallel
  python run_test.py "task" --poetiq         → Full Poetiq system
  python run_test.py --stress 6              → Stress test with 6 agents

Examples:
  python run_test.py "list files in sandbox/"
  python run_test.py "create hello.py with print hello" --parallel 3
  python run_test.py "analyze core folder" --poetiq
  python run_test.py --stress 6
        """)


if __name__ == "__main__":
    main()
