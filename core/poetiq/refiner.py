# core/poetiq/refiner.py
# Self-Refine loop with Memory Orchestrator integration + Poetiq Code Verification

from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import median
from typing import List, Dict, Any, Optional
import time
import re
import json

from core.llm_client import LLMClient
from core.prompts import EVAL_PROMPT, REFINE_PROMPT
from core.parsers import extract_tool_call
from tools.registry import get_registry
from config.settings import (
    WORKER_TEMPS, 
    LIMIT_RESPONSE_PREVIEW, 
    LIMIT_FEEDBACK_PREVIEW,
    LIMIT_CODE_PREVIEW,
    EVALUATOR_SLOT  # Auto-assign slot for evaluator (avoid overloading MEMORY_SLOT)
)
from .worker import WorkerResponse
from memory.reflection_buffer import get_buffer as get_reflection_buffer
from memory.curator import get_curator  # Get error patterns for context


class SelfRefiner:
    """
    Self-Refine loop with Memory Orchestrator integration + Poetiq Code Verification:
    1. FEEDBACK: Evaluate response
    2. VERIFY: If code involved, test against examples (Poetiq-style)
    3. CHECK: If score >= threshold AND code passes, stop
    4. MEMORY: If low score, get more context from orchestrator
    5. ITERATE: Refine with enhanced context (including verification errors)
    """
    
    def __init__(self, max_iterations: int = 2, score_threshold: int = 15, orchestrator=None):
        self.llm = LLMClient()
        self.max_iterations = max_iterations
        self.score_threshold = score_threshold
        self.orchestrator = orchestrator
        self.registry = get_registry()
        
        # Poetiq-style code verification
        from core.code_verifier import get_verifier
        self.verifier = get_verifier()
        
        # Reflexion buffer for intra-session learning
        self.reflection_buffer = get_reflection_buffer()
    
    def refine(self, response: str, task: str, tools_used: List[str], 
                errors: List[str] = None, test_cases: List[Dict] = None) -> Dict[str, Any]:
        """
        Run self-refine loop with memory-enhanced refinement.
        Tracks best response across all iterations and returns the highest-scoring one.
        """
        current_response = response
        total_eval_time = 0
        total_refine_time = 0
        verification_passed = False
        
        # Track best response across iterations
        best_response = response
        best_score = 0
        best_iteration = 0
        best_verification_passed = False
        
        for i in range(self.max_iterations):
            # Step 1: FEEDBACK (evaluate response quality) - SINGLE WORKER
            eval_start = time.time()
            # print(f"    📊 Parallel evaluation (3 workers)...") -> Disabled to save resources
            print(f"    📊 Evaluation (single supervisor)...")
            
            # Use single evaluation instead of parallel to save 2 LLM calls per iter
            score, feedback = self._evaluate(current_response, task, tools_used)
            
            eval_time = time.time() - eval_start
            total_eval_time += eval_time
            print(f"    Iter {i+1}: score={score}/25 (eval: {eval_time:.1f}s)")
            
            # Step 2: VERIFY (Poetiq-style)
            verify_feedback = ""
            if test_cases and 'python_exec' in tools_used:
                code = self._extract_code_from_response(current_response)
                if code:
                    verify_result = self.verifier.verify_and_learn(code, test_cases, task_hint=task)
                    verification_passed = verify_result.passed
                    print(f"    🧪 Verification: {verify_result.passed_tests}/{verify_result.total_tests} passed")
                    if not verify_result.passed:
                        verify_feedback = f"\n\nCODE VERIFICATION FAILED:\n{verify_result.to_feedback()}"
            
            # Track best response
            is_better = score > best_score or (score == best_score and verification_passed and not best_verification_passed)
            if is_better:
                best_response = current_response
                best_score = score
                best_iteration = i + 1
                best_verification_passed = verification_passed
                print(f"    📈 New best: score={best_score}/25 at iter {best_iteration}")
            
            # Step 3: CHECK stopping criteria
            should_stop = score >= self.score_threshold
            if test_cases and 'python_exec' in tools_used:
                should_stop = should_stop and verification_passed
            
            if should_stop:
                print(f"    ✓ Score >= {self.score_threshold} and verification passed, stopping")
                return {
                    "response": current_response,
                    "score": score,
                    "iterations": i + 1,
                    "eval_time": total_eval_time,
                    "refine_time": total_refine_time,
                    "verification_passed": verification_passed
                }
            
            if i == self.max_iterations - 1:
                print(f"    ⚠ Max iterations reached")
                break
            
            # Step 4: Get additional memory context if score is low
            extra_context = ""
            if self.orchestrator and score < 12:
                print(f"    🧠 Fetching memory for refinement...")
                refine_ctx = self.orchestrator.get_refine_context(
                    task, current_response, errors, tools_used
                )
                extra_context = refine_ctx.to_prompt()
            
            # Step 5: ITERATE (refine with memory + verification feedback) - PARALLEL
            refine_start = time.time()
            combined_feedback = feedback + verify_feedback
            
            # Add reflection from this iteration's failure
            if not should_stop:
                self.reflection_buffer.add_from_error(i + 1, combined_feedback)
            
            # Get reflection context to inject
            reflection_context = self.reflection_buffer.get_context()
            if reflection_context:
                extra_context = f"{extra_context}\n\n{reflection_context}" if extra_context else reflection_context
            
            # OPTIMIZATION 2: Single-worker refine instead of parallel (saves 2 LLM calls/iter)
            print(f"    🔄 Single-worker refine...")
            current_response = self._refine_response(
                current_response, task, combined_feedback, tools_used, extra_context
            )
            refine_time = time.time() - refine_start
            total_refine_time += refine_time
            print(f"    → Refined ({refine_time:.1f}s)")
        
        # Return BEST response, not last response
        print(f"    🏆 Returning best response from iter {best_iteration} (score={best_score}/25)")
        return {
            "response": best_response,
            "score": best_score,
            "iterations": self.max_iterations,
            "eval_time": total_eval_time,
            "refine_time": total_refine_time,
            "verification_passed": best_verification_passed,
            "best_iteration": best_iteration
        }

    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract Python code from response for verification"""
        patterns = [
            r'"code"\s*:\s*"([^"]+)"',  # JSON format
            r'```python\s*\n?(.*?)\n?```',  # Markdown code block
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                code = match.group(1)
                code = code.replace('\\n', '\n').replace('\\"', '"')
                return code
        return None
    
    def _evaluate(self, response: str, task: str, tools_used: List[str]) -> tuple:
        """FEEDBACK phase: single worker with memory context.
        Uses MEMORY_SLOT for KV cache efficiency.
        """
        tools_str = ", ".join(tools_used) if tools_used else "None"
        
        # Get memory context from curator (error patterns)
        memory_context = ""
        try:
            curator = get_curator()
            error_summary = curator.get_error_summary_for_prompt()
            if error_summary:
                memory_context = f"\nKNOWN ERROR PATTERNS:\n{error_summary}\n"
        except:
            pass  # Memory context is optional
        
        eval_prompt = EVAL_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            response=response[:LIMIT_RESPONSE_PREVIEW],
            memory_context=memory_context
        )
        
        # Use MEMORY_SLOT for evaluator (shares context with memory system)
        feedback = self.llm.chat(
            [{"role": "user", "content": eval_prompt}], 
            temp=0.3, 
            slot_id=EVALUATOR_SLOT
        )
        score = self._extract_score(feedback)
        
        return score, feedback
    
    def _parallel_evaluate(self, response: str, task: str, tools_used: List[str], 
                           num_workers: int = 3) -> tuple:
        """PARALLEL FEEDBACK: Use multiple evaluators with memory context."""
        tools_str = ", ".join(tools_used) if tools_used else "None"
        
        # Get memory context from curator (error patterns)
        memory_context = ""
        try:
            curator = get_curator()
            error_summary = curator.get_error_summary_for_prompt()
            if error_summary:
                memory_context = f"\nKNOWN ERROR PATTERNS:\n{error_summary}\n"
        except:
            pass
        
        eval_prompt = EVAL_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            response=response[:LIMIT_RESPONSE_PREVIEW],
            memory_context=memory_context
        )
        
        temps = [0.2, 0.3, 0.4][:num_workers]
        
        def eval_worker(worker_id: int, temp: float) -> tuple:
            llm = LLMClient()
            # Use MEMORY_SLOT for evaluators
            feedback = llm.chat(
                [{"role": "user", "content": eval_prompt}], 
                temp=temp, 
                slot_id=EVALUATOR_SLOT
            )
            score = self._extract_score(feedback)
            return worker_id, score, feedback
        
        results = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(eval_worker, i, temps[i]): i 
                for i in range(num_workers)
            }
            for future in as_completed(futures):
                try:
                    worker_id, score, feedback = future.result(timeout=60)
                    results.append((worker_id, score, feedback))
                    print(f"      Eval-{worker_id}: {score}/25 (temp={temps[worker_id]})")
                except Exception as e:
                    print(f"      ⚠️ Eval worker failed: {e}")
        
        if not results:
            return self._evaluate(response, task, tools_used)
        
        scores = [r[1] for r in results]
        final_score = int(median(scores))
        
        best_result = min(results, key=lambda r: abs(r[1] - final_score))
        best_feedback = best_result[2]
        
        print(f"      → Median score: {final_score}/25 (from {len(results)} evals)")
        
        return final_score, best_feedback
    
    def _refine_response(self, response: str, task: str, feedback: str, 
                          tools_used: List[str], extra_context: str = "") -> str:
        """ITERATE phase: single worker with memory context"""
        tools_str = ", ".join(tools_used) if tools_used else "None"
        tools_schema = self.registry.get_tools_prompt()
        
        # Get memory context from curator
        memory_context = ""
        try:
            curator = get_curator()
            error_summary = curator.get_error_summary_for_prompt()
            if error_summary:
                memory_context = f"Previous errors to avoid:\n{error_summary}"
        except:
            pass
        
        refine_prompt = REFINE_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            tools_schema=tools_schema,
            feedback=feedback[:LIMIT_FEEDBACK_PREVIEW],
            memory_context=memory_context
        )
        
        if extra_context:
            refine_prompt = f"{extra_context}\n\n{refine_prompt}"
        
        refined = self.llm.chat([{"role": "user", "content": refine_prompt}], temp=0.7)
        return refined
    
    def _parallel_refine(self, response: str, task: str, feedback: str,
                         tools_used: List[str], extra_context: str = "", num_workers: int = 3) -> str:
        """PARALLEL ITERATE: Launch multiple workers to refine in parallel."""
        tools_str = ", ".join(tools_used) if tools_used else "None"
        tools_schema = self.registry.get_tools_prompt()
        
        # Get memory context from curator
        memory_context = ""
        try:
            curator = get_curator()
            error_summary = curator.get_error_summary_for_prompt()
            if error_summary:
                memory_context = f"Previous errors to avoid:\n{error_summary}"
        except:
            pass
        
        refine_prompt = REFINE_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            tools_schema=tools_schema,
            feedback=feedback[:LIMIT_FEEDBACK_PREVIEW],
            memory_context=memory_context
        )
        
        if extra_context:
            refine_prompt = f"{extra_context}\n\n{refine_prompt}"
        
        temps = WORKER_TEMPS[:num_workers] if len(WORKER_TEMPS) >= num_workers else [0.5, 0.7, 0.9][:num_workers]
        
        def refine_worker(worker_id: int, temp: float) -> WorkerResponse:
            start = time.time()
            llm = LLMClient()
            refined = llm.chat([{"role": "user", "content": refine_prompt}], temp=temp)
            tool_call = extract_tool_call(refined)
            return WorkerResponse(
                worker_id=worker_id,
                raw_response=refined,
                tool_call=tool_call,
                duration=time.time() - start,
                temperature=temp
            )
        
        responses = []
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            futures = {
                executor.submit(refine_worker, i, temps[i]): i 
                for i in range(num_workers)
            }
            for future in as_completed(futures):
                try:
                    resp = future.result(timeout=120)
                    responses.append(resp)
                except Exception as e:
                    print(f"      ⚠️ Refine worker failed: {e}")
        
        if not responses:
            return self._refine_response(response, task, feedback, tools_used, extra_context)
        
        for r in responses:
            print(f"      Worker-{r.worker_id}: {r.duration:.1f}s (temp={r.temperature})")
        
        if len(responses) == 1:
            return responses[0].raw_response
        
        best = max(responses, key=lambda r: (
            1 if r.tool_call else 0,
            len(r.raw_response)
        ))
        
        print(f"      → Selected Worker-{best.worker_id}")
        return best.raw_response
    
    def _extract_score(self, text: str) -> int:
        """Extract score from evaluation text"""
        patterns = [
            r'TOTAL_SCORE:\s*(\d+)/25',
            r'(\d+)/25',
            r'score[:\s]+(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return min(25, int(match.group(1)))
        return 0
        
    def generate_test_cases(self, task: str, response: str) -> List[Dict]:
        """Generate test cases for code verification"""
        if "```python" not in response and '"code":' not in response:
            return []
            
        prompt = f"""Generate 3 test cases to verify the python code for this task.
        
TASK: {task}
RESPONSE: {response[:LIMIT_CODE_PREVIEW]}

Return a JSON list of test cases.
FORMAT:
```json
[
  {{"input": "input_value", "expected": "expected_output"}},
  ...
]
```
If the task is about side effects (files, printing) or unclear, return `[]`.
"""
        try:
            txt = self.llm.generate(prompt, temp=0.3)
            match = re.search(r'\[.*\]', txt, re.DOTALL)
            if match:
                cases = json.loads(match.group(0))
                if isinstance(cases, list):
                    return cases[:3]
        except:
            pass
        return []
