# Poetiq System with Self-Refine Loop + Memory Orchestrator
# Architecture: Parallel Workers → Aggregate → Self-Refine → Execute Tools

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import time
import re

from core.llm_client import LLMClient
from core.prompts import AGENT_SYSTEM_PROMPT, EVAL_PROMPT, REFINE_PROMPT
from core.parsers import extract_tool_call
from tools.registry import get_registry
from utils.logger import new_session
from utils.metrics import get_metrics
from memory.orchestrator import get_orchestrator, get_memory_context
from memory.learner import MemoryLearner
from config.settings import MAX_ITERATIONS, SCORE_THRESHOLD, WORKER_TEMPS, TEMPERATURE, TEMPERATURE_FEEDBACK


@dataclass
class WorkerResponse:
    """Response from a single worker (1 LLM call)"""
    worker_id: int
    raw_response: str
    tool_call: Optional[Dict]
    duration: float
    temperature: float


class LightWorker:
    """Single LLM call worker using shared MemoryContext"""
    
    def __init__(self, worker_id: int, temperature: float = 0.7, memory_context: str = ""):
        self.worker_id = worker_id
        self.temperature = temperature
        self.llm = LLMClient()
        self.registry = get_registry()
        self.memory_context = memory_context  # Pre-built from Orchestrator
    
    def generate(self, task: str) -> WorkerResponse:
        start = time.time()
        
        tools_schema = self.registry.get_tools_prompt()
        
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            tools_schema=tools_schema,
            workspace="sandbox",
            memory_context=self.memory_context
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        response = self.llm.chat(messages, temp=self.temperature)
        tool_call = extract_tool_call(response)
        
        return WorkerResponse(
            worker_id=self.worker_id,
            raw_response=response,
            tool_call=tool_call,
            duration=time.time() - start,
            temperature=self.temperature
        )


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
        self.orchestrator = orchestrator  # For memory during refinement
        self.registry = get_registry()  # Access tools
        
        # Poetiq-style code verification
        from core.code_verifier import get_verifier
        self.verifier = get_verifier()
    
    def refine(self, response: str, task: str, tools_used: List[str], 
                errors: List[str] = None, test_cases: List[Dict] = None) -> Dict[str, Any]:
        """
        Run self-refine loop with memory-enhanced refinement.
        If test_cases provided, also runs Poetiq-style code verification.
        
        NEW: Tracks best response across all iterations and returns the highest-scoring one,
        not just the last iteration. This prevents regression where iter5 scores 0 but iter3 had 18.
        """
        current_response = response
        total_eval_time = 0
        total_refine_time = 0
        verification_passed = False
        
        # NEW: Track best response across iterations
        best_response = response
        best_score = 0
        best_iteration = 0
        best_verification_passed = False
        
        for i in range(self.max_iterations):
            # Step 1: FEEDBACK (evaluate response quality) - NOW PARALLEL!
            eval_start = time.time()
            print(f"    📊 Parallel evaluation (3 workers)...")
            score, feedback = self._parallel_evaluate(current_response, task, tools_used)
            eval_time = time.time() - eval_start
            total_eval_time += eval_time
            print(f"    Iter {i+1}: score={score}/25 (eval: {eval_time:.1f}s)")
            
            # Step 2: VERIFY (Poetiq-style) - if test cases provided and code present
            verify_feedback = ""
            if test_cases and 'python_exec' in tools_used:
                code = self._extract_code_from_response(current_response)
                if code:
                    # Use verify_and_learn to persist lessons found during verification
                    verify_result = self.verifier.verify_and_learn(code, test_cases, task_hint=task)
                    verification_passed = verify_result.passed
                    print(f"    🧪 Verification: {verify_result.passed_tests}/{verify_result.total_tests} passed")
                    if not verify_result.passed:
                        verify_feedback = f"\n\nCODE VERIFICATION FAILED:\n{verify_result.to_feedback()}"
            
            # NEW: Track best response (prioritize score, then verification)
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
            
            # Step 5: ITERATE (refine with memory + verification feedback) - NOW PARALLEL!
            refine_start = time.time()
            combined_feedback = feedback + verify_feedback
            print(f"    🔄 Parallel refine (3 workers)...")
            current_response = self._parallel_refine(
                current_response, task, combined_feedback, tools_used, extra_context
            )
            refine_time = time.time() - refine_start
            total_refine_time += refine_time
            print(f"    → Parallel refined ({refine_time:.1f}s)")
        
        # NEW: Return BEST response, not last response
        print(f"    🏆 Returning best response from iter {best_iteration} (score={best_score}/25)")
        return {
            "response": best_response,  # Changed from current_response
            "score": best_score,         # Changed from score
            "iterations": self.max_iterations,
            "eval_time": total_eval_time,
            "refine_time": total_refine_time,
            "verification_passed": best_verification_passed,  # Changed
            "best_iteration": best_iteration  # NEW: Track which iter was best
        }

    
    def _extract_code_from_response(self, response: str) -> Optional[str]:
        """Extract Python code from response for verification"""
        import re
        # Look for code in python_exec params or code blocks
        patterns = [
            r'"code"\s*:\s*"([^"]+)"',  # JSON format
            r'```python\s*\n?(.*?)\n?```',  # Markdown code block
        ]
        for pattern in patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                code = match.group(1)
                # Unescape if from JSON
                code = code.replace('\\n', '\n').replace('\\"', '"')
                return code
        return None
    
    def _evaluate(self, response: str, task: str, tools_used: List[str]) -> tuple:
        """FEEDBACK phase: evaluate with multi-dimensional scoring (single worker - fallback)"""
        tools_str = ", ".join(tools_used) if tools_used else "None"
        
        eval_prompt = EVAL_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            response=response[:1000]
        )
        
        feedback = self.llm.chat([{"role": "user", "content": eval_prompt}], temp=0.3)
        score = self._extract_score(feedback)
        
        return score, feedback
    
    def _parallel_evaluate(self, response: str, task: str, tools_used: List[str], 
                           num_workers: int = 3) -> tuple:
        """
        PARALLEL FEEDBACK: Use multiple evaluators for more robust scoring.
        Returns median score and combined feedback for diversity.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from statistics import median
        
        tools_str = ", ".join(tools_used) if tools_used else "None"
        
        eval_prompt = EVAL_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            response=response[:1000]
        )
        
        # Different temps for diversity in evaluation
        temps = [0.2, 0.3, 0.4][:num_workers]
        
        def eval_worker(worker_id: int, temp: float) -> tuple:
            """Single evaluation worker"""
            llm = LLMClient()
            feedback = llm.chat([{"role": "user", "content": eval_prompt}], temp=temp)
            score = self._extract_score(feedback)
            return worker_id, score, feedback
        
        # Launch evaluators in parallel
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
            # Fallback to single evaluator
            return self._evaluate(response, task, tools_used)
        
        # Calculate median score (robust against outliers)
        scores = [r[1] for r in results]
        final_score = int(median(scores))
        
        # Use feedback from worker with score closest to median
        best_result = min(results, key=lambda r: abs(r[1] - final_score))
        best_feedback = best_result[2]
        
        print(f"      → Median score: {final_score}/25 (from {len(results)} evals)")
        
        return final_score, best_feedback
    
    def _refine_response(self, response: str, task: str, feedback: str, 
                          tools_used: List[str], extra_context: str = "") -> str:
        """ITERATE phase: refine based on feedback + memory context (single worker)"""
        tools_str = ", ".join(tools_used) if tools_used else "None"
        tools_schema = self.registry.get_tools_prompt()
        
        refine_prompt = REFINE_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            tools_schema=tools_schema,
            feedback=feedback[:800]
        )
        
        # Add memory context if available and not empty
        if extra_context:
            refine_prompt = f"{extra_context}\n\n{refine_prompt}"
        
        refined = self.llm.chat([{"role": "user", "content": refine_prompt}], temp=0.7)
        return refined
    
    def _parallel_refine(self, response: str, task: str, feedback: str,
                         tools_used: List[str], extra_context: str = "", num_workers: int = 3) -> str:
        """
        PARALLEL ITERATE: Launch multiple workers to refine in parallel,
        then aggregate the best response. More diverse refinement.
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        tools_str = ", ".join(tools_used) if tools_used else "None"
        tools_schema = self.registry.get_tools_prompt()
        
        # Build the refine prompt (same for all workers)
        refine_prompt = REFINE_PROMPT.format(
            user_input=task,
            tools_used=tools_str,
            tools_schema=tools_schema,
            feedback=feedback[:800]
        )
        
        if extra_context:
            refine_prompt = f"{extra_context}\n\n{refine_prompt}"
        
        # Workers with different temperatures for diversity
        temps = WORKER_TEMPS[:num_workers] if len(WORKER_TEMPS) >= num_workers else [0.5, 0.7, 0.9][:num_workers]
        
        def refine_worker(worker_id: int, temp: float) -> WorkerResponse:
            """Single refine worker"""
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
        
        # Launch workers in parallel
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
            # Fallback to single refine if all workers failed
            return self._refine_response(response, task, feedback, tools_used, extra_context)
        
        # Print worker stats
        for r in responses:
            print(f"      Worker-{r.worker_id}: {r.duration:.1f}s (temp={r.temperature})")
        
        if len(responses) == 1:
            return responses[0].raw_response
        
        # Aggregate: Pick the best response (simple scoring by tool presence + length)
        best = max(responses, key=lambda r: (
            1 if r.tool_call else 0,  # Prefer responses with valid tool calls
            len(r.raw_response)       # Tiebreaker: longer = more detail
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
        # Only verify if code is detected
        if "```python" not in response and '"code":' not in response:
            return []
            
        prompt = f"""Generate 3 test cases to verify the python code for this task.
        
TASK: {task}
RESPONSE: {response[:800]}

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
            # Simple extraction
            import json
            match = re.search(r'\[.*\]', txt, re.DOTALL)
            if match:
                cases = json.loads(match.group(0))
                if isinstance(cases, list):
                    return cases[:3]
        except:
            pass
        return []



class Aggregator:
    """
    Synthesizes multiple worker responses into one optimal response.
    Instead of just voting, it combines the best parts of each.
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    def aggregate(self, responses: List[WorkerResponse], task: str) -> WorkerResponse:
        """Aggregate responses into a single best response"""
        if not responses:
            raise ValueError("No responses to aggregate")
            
        # If only 1 response, just return it
        if len(responses) == 1:
            return responses[0]
            
        # Prepare context for aggregation
        candidates_text = ""
        for i, r in enumerate(responses):
            tool_status = f"(Tool: {r.tool_call.get('tool')})" if r.tool_call else "(No tool)"
            candidates_text += f"\n--- CANDIDATE {i+1} {tool_status} ---\n{r.raw_response[:800]}\n"
        
        # Get list of VALID tools
        from tools.registry import get_registry
        registry = get_registry()
        valid_tools = list(registry._tools.keys())
        tools_list = ", ".join(valid_tools)
            
        prompt = f"""Select or synthesize the best tool call from these candidates.

TASK: {task}

VALID TOOLS (use ONLY these exact names):
{tools_list}

CANDIDATES:
{candidates_text}

CRITICAL RULES:
1. The "tool" field MUST be one of: {tools_list}
2. Do NOT use module names like 're', 'ast', 'json' as tools - these are NOT valid.
3. If candidates show Python code, use "python_exec" with the code.
4. If candidates show file creation, use "write_file" with path and content.
5. Output ONLY the JSON, no explanations.

Output EXACTLY this format:
```json
{{"tool": "valid_tool_name", "params": {{...}}}}
```"""

        # Generate synthesized response
        print(f"    → Synthesizing {len(responses)} candidates...")
        agg_start = time.time()
        synthesized_text = self.llm.generate(prompt, temp=0.3)  # Lower temp for consistency
        duration = time.time() - agg_start
        
        # Extract new tool call
        tool_call = extract_tool_call(synthesized_text)
        
        # NEW: Validate tool exists, remap if hallucinated
        if tool_call:
            from tools.registry import get_registry
            registry = get_registry()
            tool_name = tool_call.get("tool", "")
            if not registry.get(tool_name):
                # Tool doesn't exist - likely hallucination like 'ast.parse' or 'unittest'
                print(f"    ⚠️ Hallucinated tool '{tool_name}' → remapping to 'python_exec'")
                tool_call["tool"] = "python_exec"
                # Try to preserve any code in params
                if "code" not in tool_call.get("params", {}):
                    tool_call["params"] = {"code": f"# Original tool was '{tool_name}'\nprint('Task requires manual implementation')"}
        
        # Return as a specialized WorkerResponse
        return WorkerResponse(
            worker_id=999,  # ID for aggregator
            raw_response=synthesized_text,
            tool_call=tool_call,
            duration=duration,
            temperature=0.0
        )


class ToolExecutor:
    """Executes tools from winning response with granular tracking"""
    
    def __init__(self, working_memory=None):
        self.registry = get_registry()
        self.tools_used = []
        self.tool_results = []  # NEW: Track individual results
        self.working_memory = working_memory
    
    def execute(self, tool_call: Dict) -> str:
        if not tool_call:
            return ""
        
        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {})
        
        self.tools_used.append(tool_name)
        result = self.registry.execute_tool(tool_name, **params)
        
        # Track granular result
        self.tool_results.append({
            "tool": tool_name,
            "success": result.get("success", False),
            "error": result.get("error") if not result.get("success") else None
        })
        
        # Re-index if we created/modified files
        if result.get("success") and tool_name == "write_file" and self.working_memory:
            file_path = params.get("path", "")
            if file_path:
                try:
                    self.working_memory._index_file(file_path, file_path)
                    print(f"    📂 Indexed: {file_path}")
                except Exception as e:
                    pass  # Non-critical
        
        if result.get("success"):
            return f"[OK] {tool_name}: {result.get('result', '')}"
        else:
            return f"[ERROR] {tool_name}: {result.get('error', 'Unknown')}"
    
    def get_success_rate(self) -> float:
        """Calculate overall tool success rate"""
        if not self.tool_results:
            return 0.0
        successes = sum(1 for r in self.tool_results if r["success"])
        return successes / len(self.tool_results)
    
    def had_any_failure(self) -> bool:
        """Check if any tool failed"""
        return any(not r["success"] for r in self.tool_results)


class PoetiqRunner:
    """
    Full Poetiq pipeline with Self-Refine:
    1. Parallel workers generate candidates
    2. AGGREGATOR: Synthesize best response
    3. Self-refine the synthesized response
    4. Execute tools
    5. Generate final response
    """
    
    def __init__(self, num_workers: int = 3, refine_threshold: int = SCORE_THRESHOLD):
        self.num_workers = num_workers
        
        # Ensure tools are registered (only runs once due to singleton registry)
        self._ensure_tools_registered()
        
        self.orchestrator = get_orchestrator()  # Unified memory system
        self.aggregator = Aggregator()
        self.executor = ToolExecutor(working_memory=self.orchestrator.working_memory)
        self.refiner = SelfRefiner(
            max_iterations=MAX_ITERATIONS,  # From settings.py
            score_threshold=refine_threshold,
            orchestrator=self.orchestrator  # Pass for memory-enhanced refinement
        )
        self.llm = LLMClient()
        
        # Initialize Working Memory (index project files)
        try:
            self.orchestrator.working_memory.index_workspace("sandbox")
        except:
            pass
    
    def _ensure_tools_registered(self):
        """Register all tools (idempotent - only registers if not already present)"""
        from tools.registry import get_registry
        registry = get_registry()
        
        # Skip if already registered
        if registry.list_tools():
            return
        
        # Register all tool categories
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
    
    def run(self, task: str) -> Dict[str, Any]:
        """Run full Poetiq + Self-Refine pipeline"""
        start_time = time.time()
        logger = new_session()
        logger.set_task(task)
        logger.log_info(f"Starting task: {task[:60]}...")
        
        print(f"\n{'='*60}")
        print(f"🎯 POETIQ ({self.num_workers} workers): {task[:50]}...")
        print(f"{'='*60}")
        
        # Phase 1: Parallel generation
        print(f"\n📡 Phase 1: Parallel generation...")
        responses, memory_ids_used = self._generate_parallel(task)  # Unpack tuple
        
        # Log parallel
        logger.log_parallel(responses)
        
        parallel_time = max(r.duration for r in responses) if responses else 0
        print(f"  ⏱️ {parallel_time:.1f}s")
        
        # Phase 2: Aggregation (Synthesis)
        print(f"\n🧠 Phase 2: Aggregating candidates...")
        winner = self.aggregator.aggregate(responses, task)
        
        # Log aggregation
        logger.log_aggregation(winner.raw_response, winner.duration)
        
        print(f"  ✨ Synthesized optimal response ({winner.duration:.1f}s)")
        
        # Phase 3: Self-Refine winner (synthesized)
        print(f"\n🔄 Phase 3: Self-Refine loop...")
        
        # NEW: Generate test cases if possible
        tool_name = winner.tool_call.get("tool") if winner.tool_call else None
        test_cases = []
        if tool_name == "python_exec" or "```python" in winner.raw_response:
             test_cases = self.refiner.generate_test_cases(task, winner.raw_response)
             if test_cases:
                 print(f"  🧪 Generated {len(test_cases)} test cases for verification")
        
        refined = self.refiner.refine(
            winner.raw_response, 
            task, 
            [tool_name] if tool_name else [],
            test_cases=test_cases
        )
        
        # Log refine result
        logger.log_refine(refined['iterations'], refined['score'], f"Refined in {refined['refine_time']:.1f}s")
        
        print(f"  📊 Final score: {refined['score']}/25 ({refined['iterations']} iterations)")
        
        # Phase 4: Execute tools (with agentic loop for multi-tool tasks)
        result_text = ""
        tool_call = extract_tool_call(refined["response"])
        
        # CRITICAL: Validate tool exists before execution (catches hallucinations from refiner)
        if tool_call:
            from tools.registry import get_registry
            registry = get_registry()
            tool_name = tool_call.get("tool", "")
            if not registry.get(tool_name):
                print(f"    ⚠️ Hallucinated tool '{tool_name}' → remapping to 'python_exec'")
                tool_call["tool"] = "python_exec"
                
                # SMART CODE EXTRACTION: Try to find Python code in the response
                extracted_code = None
                response_text = refined.get("response", "")
                
                # Try to extract code from ```python blocks
                import re
                code_match = re.search(r'```python\s*\n(.+?)\n```', response_text, re.DOTALL)
                if code_match:
                    extracted_code = code_match.group(1).strip()
                    print(f"    ✅ Extracted {len(extracted_code)} chars of code from response")
                
                # Use extracted code or placeholder
                if extracted_code:
                    tool_call["params"] = {"code": extracted_code}
                elif "code" not in tool_call.get("params", {}):
                    tool_call["params"] = {"code": f"# LLM tried to use '{tool_name}' which doesn't exist\nprint('Manual implementation needed')"}
                
                # CRITICAL FIX: Update the response string so AgenticLoop sees the change!
                import json
                refined["response"] = f"```json\n{json.dumps(tool_call, indent=2)}\n```"
        
        if tool_call:
            print(f"\n🔧 Phase 4: Executing tools...")
            
            # Import here to avoid circular
            from core.agentic_loop import AgenticLoop
            
            # Use agentic loop for multi-tool execution with memory access
            agentic = AgenticLoop(self.executor, orchestrator=self.orchestrator)
            loop_result = agentic.run(task, refined["response"])
            
            # Combine all results
            if loop_result["all_results"]:
                result_text = "\n".join(loop_result["all_results"])
                print(f"  ✅ Executed {loop_result['iterations']} tool(s)")
        
        # Phase 5: Final response
        final_response = refined["response"]
        if result_text:
            print(f"\n📝 Phase 5: Final response...")
            final_response = self._generate_final(task, refined["response"], result_text)
        
        # Phase 6: Learn from session (async - runs in background)
        total_time = time.time() - start_time
        
        # Log final
        logger.log_final(final_response, refined['score'], total_time)
        
        # ALWAYS learn from every session - run in background thread
        import threading
        
        def learn_async():
            try:
                learner = MemoryLearner()
                
                # Prepare workers data for richer learning
                workers_data = [
                    {
                        "id": r.worker_id,
                        "tool": r.tool_call.get("tool") if r.tool_call else None,
                        "response": r.raw_response[:200] if r.raw_response else ""
                    }
                    for r in responses
                ]
                
                result = learner.learn_from_session(
                    task=task,
                    initial_score=10,  # Approximate
                    final_score=refined["score"],
                    iterations=refined["iterations"],
                    workers_data=workers_data
                )
                print(f"\n💡 Learning complete: {result.get('lessons_added', 0)} new, {result.get('lessons_evolved', 0)} evolved")
            except Exception as e:
                print(f"\n⚠️ Learning error: {e}")
        
        # Start learning in background (non-daemon so it completes before exit)
        learn_thread = threading.Thread(target=learn_async, daemon=False)
        learn_thread.start()
        print(f"\n💡 Phase 6: Learning in background...")
        
        # Phase 7: Run Memory Maintenance (Decay) - also in background or main thread?
        # Main thread is safer for DB locks, but quick.
        try:
            decay_stats = self.orchestrator.run_maintenance()
            print(f"  🧹 Maintenance: {decay_stats.get('decayed_by', 0):.2f} decay applied")
        except Exception as e:
            print(f"  ⚠️ Maintenance warning: {e}")
        
        print(f"\n⏱️ Total time: {total_time:.1f}s")
        
        # Phase 7: Memory Feedback Loop (IMPROVED - uses tool success)
        # Mark used memories as success/failure based on BOTH score AND tool results
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
        """Returns (responses, memory_ids) tuple"""
        temps = WORKER_TEMPS  # From config.settings [0.2, 0.3, 0.4]
        responses = []
        
        # Get unified context from orchestrator ONCE
        context = self.orchestrator.get_context(task, use_llm=False)  # Fast mode
        memory_context = context.to_prompt()
        memory_ids = context.memory_ids or []  # Track which memories we used
        
        with ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = {}
            for i in range(self.num_workers):
                # All workers share the same pre-built context
                worker = LightWorker(i, temps[i % len(temps)], memory_context)
                futures[executor.submit(worker.generate, task)] = i
            
            for future in as_completed(futures):
                wid = futures[future]
                try:
                    r = future.result(timeout=60)
                    responses.append(r)
                    has_tool = "✓" if r.tool_call else "✗"
                    print(f"  Worker-{wid}: {r.duration:.1f}s [tool:{has_tool}]")
                except Exception as e:
                    print(f"  Worker-{wid}: ERROR - {e}")
        
        return responses, memory_ids  # Return both
    
    def _generate_final(self, task: str, response: str, tool_result: str) -> str:
        prompt = f"""Task: {task}

Tool Result: {tool_result}

Provide a complete, helpful final answer based on the tool result."""
        
        return self.llm.chat([{"role": "user", "content": prompt}])


def run_poetiq(task: str, num_workers: int = 3) -> Dict[str, Any]:
    runner = PoetiqRunner(num_workers)
    return runner.run(task)
