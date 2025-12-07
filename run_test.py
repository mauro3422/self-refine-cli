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
    """Run single agent"""
    from core.agent import Agent, init_tools
    
    print(f"\n{'='*60}")
    print(f"🤖 SINGLE AGENT: {task[:50]}...")
    print(f"{'='*60}")
    
    init_tools()
    agent = Agent(debug=True)
    
    start = time.time()
    response = agent.run(task)
    duration = time.time() - start
    
    print(f"\n📝 Response:\n{response[:500]}...")
    print(f"\n✅ Score: {agent.last_score}/25 | Time: {duration:.1f}s")
    print(f"🔧 Tools: {agent.tools_used}")
    
    return agent.last_score


def run_parallel(task: str, num_workers: int = 3):
    """Run multiple agents in parallel (true parallel - 1 call each, then vote)"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from core.agent import Agent, init_tools
    
    print(f"\n{'='*60}")
    print(f"🔀 PARALLEL ({num_workers} workers): {task[:50]}...")
    print(f"{'='*60}")
    
    init_tools()
    
    def worker(worker_id: int):
        # single_shot=True means NO self-refine (just 1 LLM call)
        agent = Agent(debug=False, single_shot=True)
        start = time.time()
        response = agent.run(task)
        return {
            "id": worker_id,
            "score": agent.last_score,
            "tools": agent.tools_used,
            "duration": time.time() - start,
            "response": response
        }
    
    results = []
    start = time.time()
    
    print(f"  🚀 Launching {num_workers} workers (single-shot mode)...")
    
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker, i) for i in range(num_workers)]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"  ✓ Worker-{result['id']}: {result['score']}/25 ({result['duration']:.1f}s)")
    
    parallel_time = time.time() - start
    
    # Find best
    best = max(results, key=lambda r: r["score"])
    print(f"\n🏆 Best: Worker-{best['id']} with {best['score']}/25")
    print(f"⏱️ Parallel phase: {parallel_time:.1f}s")
    
    # Now refine only the winning response
    if best["score"] < 22:
        print(f"\n🔄 Refining winner (score < 22)...")
        agent = Agent(debug=False)
        # Manually set the response and run self-refine
        final_response = agent._self_refine(best["response"], task)
        print(f"  📊 Final score: {agent.last_score}/25")
        best["score"] = agent.last_score
        best["response"] = final_response
    
    total_time = time.time() - start
    print(f"⏱️ Total time: {total_time:.1f}s")
    
    return best["score"]


def run_poetiq(task: str, num_workers: int = 3):
    """Run full Poetiq system with true single-call workers"""
    from core.poetiq import run_poetiq as poetiq_run
    from tools.file_tools import register_file_tools
    from tools.command_tools import register_command_tools
    
    # Init tools
    print("\n🔧 Initializing tools...")
    register_file_tools()
    register_command_tools()
    
    result = poetiq_run(task, num_workers)
    
    print(f"\n📝 Response:\n{result['response'][:500]}...")
    print(f"\n✨ Winner: Worker-{result['winner_id']}")
    print(f"🔧 Tools: {result['tools_used']}")
    print(f"⏱️ Parallel phase: {result['parallel_time']:.1f}s")
    
    return 25 if result['tools_used'] else 0  # Simplified score


def run_stress(num_agents: int = 6):
    """Run stress test with many agents"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from core.agent import Agent, init_tools
    from config.settings import AGENT_WORKSPACE
    
    os.makedirs(AGENT_WORKSPACE, exist_ok=True)
    
    print(f"\n{'='*60}")
    print(f"🔥 STRESS TEST: {num_agents} agents")
    print(f"{'='*60}")
    
    init_tools()
    
    def agent_task(agent_id: int):
        agent = Agent(debug=False)
        task = f"Crea archivo agent_{agent_id}.txt con el numero {agent_id} y un saludo."
        start = time.time()
        response = agent.run(task)
        return {
            "id": agent_id,
            "score": agent.last_score,
            "duration": time.time() - start,
            "success": agent.last_score >= 18
        }
    
    results = []
    start = time.time()
    
    with ThreadPoolExecutor(max_workers=num_agents) as executor:
        futures = [executor.submit(agent_task, i) for i in range(1, num_agents + 1)]
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✅" if result["success"] else "❌"
            print(f"  {status} Agent-{result['id']}: {result['score']}/25 ({result['duration']:.1f}s)")
    
    total_time = time.time() - start
    success_count = sum(1 for r in results if r["success"])
    
    print(f"\n{'='*60}")
    print(f"📊 RESULTS: {success_count}/{num_agents} successful")
    print(f"⏱️ Total time: {total_time:.1f}s")
    print(f"📁 Check sandbox/ for created files")
    
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
