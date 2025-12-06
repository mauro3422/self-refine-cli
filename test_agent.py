# Unified Test Script - Runs agent and saves complete debug logs
# Use: python test_agent.py "your question"
#      python test_agent.py --batch  (runs predefined tests)
#      python test_agent.py --view   (view last debug log)

import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import Agent, init_tools
from utils.debug_logger import get_debug_logger


def run_single_test(query: str, show_summary: bool = True):
    """Run a single test"""
    print("\n" + "="*60)
    print(f"🧪 TEST: {query[:50]}...")
    print("="*60)
    
    init_tools()
    agent = Agent(debug=True)
    
    response = agent.run(query)
    
    print("\n" + "="*60)
    print("🤖 RESPONSE:")
    print("="*60)
    print(response)
    
    if show_summary:
        print("\n" + agent.get_debug_summary())
    
    print(f"\n📝 Full debug log: {agent.logger.get_log_path()}")
    
    return response


def run_batch_tests():
    """Run predefined tests"""
    tests = [
        # Spanish tests
        ("lee README.md y dame un resumen corto", "Spanish - read file"),
        ("lista los archivos en tools/", "Spanish - list dir"),
        ("qué archivos hay en config/", "Spanish - list config"),
        
        # English tests  
        ("read main.py and explain what it does", "English - read file"),
        ("list files in the core folder", "English - list dir"),
    ]
    
    print("\n" + "="*60)
    print("🧪 BATCH TESTS")
    print("="*60)
    
    results = []
    
    for query, description in tests:
        print(f"\n\n{'='*60}")
        print(f"TEST: {description}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        try:
            init_tools()
            agent = Agent(debug=True)
            response = agent.run(query)
            
            results.append({
                "description": description,
                "query": query,
                "tools_used": agent.tools_used,
                "score": agent.last_score,
                "success": agent.last_score >= 18,
                "response_preview": response[:200]
            })
            
            print(f"\n✅ Score: {agent.last_score}/25")
            print(f"   Tools: {agent.tools_used}")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            results.append({
                "description": description,
                "query": query,
                "error": str(e),
                "success": False
            })
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 BATCH TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for r in results if r.get("success"))
    print(f"\nPassed: {passed}/{len(results)}")
    
    for r in results:
        status = "✅" if r.get("success") else "❌"
        score = r.get("score", "N/A")
        print(f"  {status} {r['description']}: {score}/25")
    
    # Save results
    results_file = os.path.join("outputs", "debug_logs", f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n📝 Results saved: {results_file}")


def view_latest_log():
    """View the latest debug log"""
    log_dir = os.path.join("outputs", "debug_logs")
    
    if not os.path.exists(log_dir):
        print("No debug logs found")
        return
    
    logs = sorted([f for f in os.listdir(log_dir) if f.startswith("session_")])
    
    if not logs:
        print("No session logs found")
        return
    
    latest = logs[-1]
    log_path = os.path.join(log_dir, latest)
    
    print(f"\n📝 Latest log: {log_path}")
    print("="*60)
    
    with open(log_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Session start: {data.get('session_start')}")
    print(f"Interactions: {len(data.get('interactions', []))}")
    
    for i, interaction in enumerate(data.get("interactions", []), 1):
        print(f"\n--- Interaction {i} ---")
        print(f"Input: {interaction.get('user_input', '')[:80]}...")
        print(f"Language: {interaction.get('detected_language')}")
        print(f"Required tools: {interaction.get('required_tools')}")
        print(f"Tools used: {interaction.get('tools_used')}")
        print(f"LLM calls: {len(interaction.get('llm_calls', []))}")
        print(f"Refinements: {len(interaction.get('refinement_iterations', []))}")
        print(f"Final score: {interaction.get('final_score')}/25")
        
        # Show refinement details
        for ref in interaction.get("refinement_iterations", []):
            print(f"  - Iter {ref['iteration']}: {ref['score']}/25")


def main():
    if len(sys.argv) < 2:
        print("""
🧪 Self-Refine Agent Test Script

Usage:
  python test_agent.py "your question"     - Run single test
  python test_agent.py --batch             - Run batch tests  
  python test_agent.py --view              - View latest debug log

Examples:
  python test_agent.py "lee README.md y resúmelo"
  python test_agent.py "list files in tools/"
  python test_agent.py --batch
        """)
        return
    
    arg = sys.argv[1]
    
    if arg == "--batch":
        run_batch_tests()
    elif arg == "--view":
        view_latest_log()
    else:
        query = " ".join(sys.argv[1:])
        run_single_test(query)


if __name__ == "__main__":
    main()
