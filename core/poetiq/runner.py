# core/poetiq/runner.py
# Full Poetiq pipeline with True Poetiq workers and Self-Refine

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any
import time
import re
import json
import threading

from core.llm_client import LLMClient
from core.parsers import extract_tool_call
from tools.registry import get_registry
from utils.logger import new_session
from memory.orchestrator import get_orchestrator
from memory.learner import MemoryLearner
from config.settings import MAX_ITERATIONS, SCORE_THRESHOLD, WORKER_TEMPS

from .worker import LightWorker, WorkerResponse
from .aggregator import Aggregator
from .executor import ToolExecutor
from .refiner import SelfRefiner


class PoetiqRunner:
    """
    Full Poetiq pipeline with True Poetiq Workers:
    1. Parallel workers generate AND VERIFY code (True Poetiq)
    2. AGGREGATOR: Prioritize verified responses
    3. Self-refine the best response
    4. Execute tools
    5. Generate final response
    """
    
    def __init__(self, num_workers: int = 3, refine_threshold: int = SCORE_THRESHOLD):
        self.num_workers = num_workers
        
        # Ensure tools are registered
        self._ensure_tools_registered()
        
        self.orchestrator = get_orchestrator()
        self.aggregator = Aggregator()
        self.executor = ToolExecutor(working_memory=self.orchestrator.working_memory)
        self.refiner = SelfRefiner(
            max_iterations=MAX_ITERATIONS,
            score_threshold=refine_threshold,
            orchestrator=self.orchestrator
        )
        self.llm = LLMClient()
        
        # Initialize Working Memory
        try:
            self.orchestrator.working_memory.index_workspace("sandbox")
        except:
            pass
    
    def _ensure_tools_registered(self):
        """Register all tools (idempotent)"""
        registry = get_registry()
        
        if registry.list_tools():
            return
        
        from tools.file_tools import register_file_tools
        from tools.command_tools import register_command_tools
        from tools.search_tools import register_search_tools
        from tools.code_tools import register_code_tools
        from tools.edit_tools import register_edit_tools
        from tools.verify_tools import register_verify_tools
        
        register_file_tools()
        register_command_tools()
        register_search_tools()
        register_code_tools()
        register_edit_tools()
        register_verify_tools()
        print("✅ All tools registered")
    
    def run(self, task: str, test_cases: list = None) -> Dict[str, Any]:
        """Run full Poetiq + Self-Refine pipeline
        
        Args:
            task: The task description
            test_cases: Optional list of {input, expected} dicts for verification
        """
        start_time = time.time()
        logger = new_session()
        logger.set_task(task)
        logger.log_info(f"Starting task: {task[:60]}...")
        
        print(f"\n{'='*60}")
        print(f"🎯 POETIQ ({self.num_workers} workers): {task[:50]}...")
        print(f"{'='*60}")
        
        # Reset reflection buffer for new session (prevents leakage)
        from memory.reflection_buffer import get_buffer as get_reflection_buffer
        get_reflection_buffer().start_session(logger.session_id)
        
        # Phase 1: Parallel generation (True Poetiq - workers verify code)
        print(f"\n📡 Phase 1: Parallel generation...")
        responses, memory_ids_used = self._generate_parallel(task)
        
        logger.log_parallel(responses)
        
        parallel_time = max(r.duration for r in responses) if responses else 0
        print(f"  ⏱️ {parallel_time:.1f}s")
        
        # Phase 2: Aggregation (prioritizes verified responses)
        print(f"\n🧠 Phase 2: Aggregating candidates...")
        winner = self.aggregator.aggregate(responses, task)
        
        logger.log_aggregation(winner.raw_response, winner.duration)
        
        print(f"  ✨ Synthesized optimal response ({winner.duration:.1f}s)")
        
        # Phase 3: Self-Refine winner
        print(f"\n🔄 Phase 3: Self-Refine loop...")
        
        # Count verified workers for tracking
        verified_count = sum(1 for r in responses if getattr(r, 'verified', False))
        winner_verified = getattr(winner, 'verified', False)
        print(f"  📊 Pre-refine: {verified_count}/{len(responses)} workers verified code")
        
        tool_name = winner.tool_call.get("tool") if winner.tool_call else None
        
        # Get pre-refine score to decide if we need refinement
        from core.prompts import EVAL_PROMPT
        tools_str = tool_name if tool_name else "None"
        pre_eval_prompt = EVAL_PROMPT.format(
            user_input=task[:200],
            tools_used=tools_str,
            response=winner.raw_response[:600]
        )
        pre_feedback = self.llm.chat([{"role": "user", "content": pre_eval_prompt}], temp=0.2)
        pre_score = self.refiner._extract_score(pre_feedback)
        print(f"  📈 Pre-refine score: {pre_score}/25")
        
        # OPTIMIZATION: Skip SelfRefiner if workers already verified code AND score is good
        skip_refiner = winner_verified and pre_score >= 15
        
        if skip_refiner:
            # Use winner response directly - code is already verified!
            print(f"  ⚡ SKIP: Worker verified + score {pre_score}/25 >= 15 → Using directly")
            refined = {
                "response": winner.raw_response,
                "score": pre_score,
                "iterations": 0,  # No refinement needed
                "eval_time": 0,
                "refine_time": 0,
                "verification_passed": True
            }
            score_delta = 0
            delta_icon = "⚡"  # Lightning = skipped
            
            logger.log_refine(
                0,  # 0 iterations = skipped
                pre_score, 
                "SKIPPED - verified code",
                pre_score=pre_score,
                verified_workers=verified_count,
                total_workers=len(responses)
            )
        else:
            # Run SelfRefiner for non-verified or low-score responses
            # Use external test_cases if provided, otherwise generate
            refine_test_cases = test_cases if test_cases else []
            if not refine_test_cases and (tool_name == "python_exec" or "```python" in winner.raw_response):
                refine_test_cases = self.refiner.generate_test_cases(task, winner.raw_response)
            if refine_test_cases:
                print(f"  🧪 Using {len(refine_test_cases)} test cases for verification")
            
            refined = self.refiner.refine(
                winner.raw_response, 
                task, 
                [tool_name] if tool_name else [],
                test_cases=refine_test_cases
            )
            
            # Calculate score delta
            score_delta = refined['score'] - pre_score
            delta_icon = "↑" if score_delta > 0 else ("↓" if score_delta < 0 else "→")
            
            logger.log_refine(
                refined['iterations'], 
                refined['score'], 
                f"Refined in {refined['refine_time']:.1f}s",
                pre_score=pre_score,
                verified_workers=verified_count,
                total_workers=len(responses)
            )
        
        print(f"  📊 Final score: {refined['score']}/25 ({refined['iterations']} iter) | Delta: {delta_icon}{abs(score_delta) if isinstance(score_delta, int) else 'skip'}")
        
        # Phase 4: Execute tools
        result_text = ""
        tool_call = extract_tool_call(refined["response"])
        
        # Validate tool exists
        if tool_call:
            registry = get_registry()
            tool_name = tool_call.get("tool", "")
            if not registry.get(tool_name):
                print(f"    ⚠️ Hallucinated tool '{tool_name}' → remapping to 'python_exec'")
                tool_call["tool"] = "python_exec"
                
                # Extract code from response
                extracted_code = None
                response_text = refined.get("response", "")
                code_match = re.search(r'```python\s*\n(.+?)\n```', response_text, re.DOTALL)
                if code_match:
                    extracted_code = code_match.group(1).strip()
                    print(f"    ✅ Extracted {len(extracted_code)} chars of code from response")
                
                if extracted_code:
                    tool_call["params"] = {"code": extracted_code}
                elif "code" not in tool_call.get("params", {}):
                    tool_call["params"] = {"code": f"# LLM tried to use '{tool_name}' which doesn't exist\nprint('Manual implementation needed')"}
                
                refined["response"] = f"```json\n{json.dumps(tool_call, indent=2)}\n```"
        
        if tool_call:
            print(f"\n🔧 Phase 4: Executing tools...")
            
            tool_name = tool_call.get("tool", "")
            params = tool_call.get("params", {})
            
            # Direct execution for python_exec with code
            if tool_name == "python_exec" and params.get("code"):
                print(f"  🔧 [1] Executing: python_exec (direct)")
                result = self.executor.execute(tool_call)
                if "[OK]" in result:
                    print(f"      → {result[:80]}...")
                else:
                    print(f"      ⚠️ Error: {result[:80]}...")
                result_text = result
                print(f"  ✅ Executed 1 tool(s)")
            else:
                # Use agentic loop for multi-tool tasks
                from core.agentic_loop import AgenticLoop
                agentic = AgenticLoop(self.executor, orchestrator=self.orchestrator)
                loop_result = agentic.run(task, refined["response"])
                
                if loop_result["all_results"]:
                    result_text = "\n".join(loop_result["all_results"])
                    print(f"  ✅ Executed {loop_result['iterations']} tool(s)")
        
        # Phase 5: Final response
        final_response = refined["response"]
        if result_text:
            print(f"\n📝 Phase 5: Final response...")
            final_response = self._generate_final(task, refined["response"], result_text)
        
        # Phase 6: Learn from session (async)
        total_time = time.time() - start_time
        logger.log_final(final_response, refined['score'], total_time)
        
        def learn_async():
            try:
                learner = MemoryLearner()
                workers_data = [
                    {
                        "id": r.worker_id,
                        "tool": r.tool_call.get("tool") if r.tool_call else None,
                        "response": r.raw_response[:300] if r.raw_response else "",
                        "verified": getattr(r, 'verified', False),  # True Poetiq success
                        "attempts": getattr(r, 'attempts', 1)       # How many retries
                    }
                    for r in responses
                ]
                result = learner.learn_from_session(
                    task=task,
                    initial_score=10,
                    final_score=refined["score"],
                    iterations=refined["iterations"],
                    workers_data=workers_data
                )
                patterns = result.get('success_patterns', 0)
                evolved = result.get('lessons_evolved', 0)
                added = result.get('lessons_added', 0)
                print(f"\n💡 Learning: {added} new, {evolved} evolved, {patterns} patterns")
            except Exception as e:
                print(f"\n⚠️ Learning error: {e}")
        
        learn_thread = threading.Thread(target=learn_async, daemon=False)
        learn_thread.start()
        print(f"\n💡 Phase 6: Learning in background...")
        
        # Phase 7: Memory Maintenance
        try:
            decay_stats = self.orchestrator.run_maintenance()
            print(f"  🧹 Maintenance: {decay_stats.get('decayed_by', 0):.2f} decay applied")
        except Exception as e:
            print(f"  ⚠️ Maintenance warning: {e}")
        
        print(f"\n⏱️ Total time: {total_time:.1f}s")
        
        # Memory Feedback
        if memory_ids_used:
            score_ok = refined["score"] >= 15
            tools_ok = not self.executor.had_any_failure() if self.executor.tool_results else True
            task_success = score_ok and tools_ok
            self.orchestrator.mark_memories_feedback(memory_ids_used, task_success)
            
            if not task_success:
                print(f"    ⚠️ Memory feedback: FAIL (score_ok={score_ok}, tools_ok={tools_ok})")
        
        return {
            "response": final_response,
            "winner_id": "Aggregator",
            "score": refined["score"],
            "iterations": refined["iterations"],
            "tool_result": result_text,
            "tools_used": self.executor.tools_used,
            "parallel_time": parallel_time,
            "total_time": total_time
        }
    
    def _generate_parallel(self, task: str) -> tuple:
        """TRUE POETIQ: Workers execute and verify their own code"""
        temps = WORKER_TEMPS
        responses = []
        
        context = self.orchestrator.get_context(task, use_llm=False)
        memory_context = context.to_prompt()
        memory_ids = context.memory_ids or []
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {}
            for i in range(self.num_workers):
                worker = LightWorker(i, temps[i % len(temps)], memory_context)
                # TRUE POETIQ: Workers execute and verify their own code
                futures[executor.submit(worker.generate_and_verify, task, 2)] = i
            
            for future in as_completed(futures):
                wid = futures[future]
                try:
                    r = future.result(timeout=180)
                    responses.append(r)
                    verified_icon = "✓" if r.verified else "✗"
                    attempts_str = f" ({r.attempts} att)" if r.attempts > 1 else ""
                    print(f"  Worker-{wid}: {r.duration:.1f}s [verified:{verified_icon}]{attempts_str}")
                except Exception as e:
                    print(f"  Worker-{wid}: ERROR - {e}")
        
        return responses, memory_ids
    
    def _generate_final(self, task: str, response: str, tool_result: str) -> str:
        prompt = f"""Task: {task}

Tool Result: {tool_result}

Provide a complete, helpful final answer based on the tool result."""
        
        return self.llm.chat([{"role": "user", "content": prompt}])


def run_poetiq(task: str, num_workers: int = 3) -> Dict[str, Any]:
    """Convenience function to run Poetiq pipeline"""
    runner = PoetiqRunner(num_workers)
    return runner.run(task)
