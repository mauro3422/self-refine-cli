# core/poetiq/aggregator.py
# Synthesizes multiple worker responses into one optimal response

from typing import List, Dict
import time
import re

from core.llm_client import LLMClient
from core.parsers import extract_tool_call
from tools.registry import get_registry
from .worker import WorkerResponse


class Aggregator:
    """
    Synthesizes multiple worker responses into one optimal response.
    PRIORITIZES verified responses from True Poetiq workers.
    """
    
    def __init__(self):
        self.llm = LLMClient()
    
    def select_best_response(self, responses: List[WorkerResponse], task: str) -> WorkerResponse:
        """
        Selects the best response from the candidates.
        PRIORITIZE verified, PRUNE weak candidates (ToT), FALLBACK if all fail.
        
        Note: Currently selects the best single response. 
        TODO: Implement true synthesis using `synthesize()` for combining multiple high-quality responses.
        """
        if not responses:
            raise ValueError("No responses to aggregate")
            
        # If only 1 response, just return it
        if len(responses) == 1:
            return responses[0]
        
        # TRUE POETIQ: Prioritize verified responses (code already tested)
        verified = [r for r in responses if r.verified]
        if verified:
            # Return the verified response with fewest attempts (cleanest solution)
            best = min(verified, key=lambda r: r.attempts)
            print(f"    ✅ Using verified response from Worker-{best.worker_id} ({len(verified)}/{len(responses)} verified)")
            return best
        
        # TREE OF THOUGHTS: Evaluate and PRUNE weak candidates
        print(f"    🌳 ToT Pruning: Evaluating {len(responses)} candidates...")
        scored = self._evaluate_and_prune(responses, task)
        
        if len(scored) == 1:
            # Only one candidate after pruning - use it directly
            best = scored[0]
            print(f"    ✅ Selected Worker-{best['response'].worker_id} (score: {best['score']})")
            return best['response']
        
        # Still multiple candidates - use best one (no synthesis needed)
        best = max(scored, key=lambda x: x['score'])
        best_response = best['response']
        
        # FALLBACK: If best score is very low, log warning
        if best['score'] < 5:
            print(f"    ⚠️ FALLBACK: All workers produced low-quality responses (best score: {best['score']})")
            print(f"    ⚠️ Using Worker-{best_response.worker_id} as fallback - refiner will handle")
            # Mark as fallback (checked by runner)
            best_response.fallback_used = True
        else:
            print(f"    ✅ Best candidate: Worker-{best_response.worker_id} (score: {best['score']})")
        
        return best_response

    def synthesize(self, responses: List[WorkerResponse], task: str) -> WorkerResponse:
        """
        Combine multiple high-quality responses into a single 'Super Response'.
        
        Currently a placeholder for future implementation.
        Strategy: Use LLM to merge Code A and Code B if both have unique strengths.
        """
        # Placeholder for future advanced synthesis
        # For now, we rely on select_best_response
        return self.select_best_response(responses, task)
    
    def _evaluate_and_prune(self, responses: List[WorkerResponse], task: str) -> List[Dict]:
        """
        TREE OF THOUGHTS: Quick-evaluate each candidate and prune weak ones.
        Returns list of {response, score} for survivors.
        """
        scored = []
        
        for r in responses:
            score = self._quick_score(r, task)
            scored.append({'response': r, 'score': score})
            print(f"      Worker-{r.worker_id}: score={score}")
        
        # Sort by score descending
        scored.sort(key=lambda x: x['score'], reverse=True)
        
        # PRUNE: Keep only top candidate(s)
        # If best score is significantly higher, keep only it
        if len(scored) >= 2:
            best_score = scored[0]['score']
            second_score = scored[1]['score']
            
            # If clear winner (>3 points difference), prune others
            if best_score - second_score > 3:
                print(f"    ✂️ Pruned {len(scored)-1} weak candidates")
                return [scored[0]]
        
        # Return top 2 if close scores (for potential synthesis)
        return scored[:2]
    
    def _quick_score(self, response: WorkerResponse, task: str) -> int:
        """
        Quick heuristic scoring without LLM call.
        Used for ToT pruning - fast but approximate.
        """
        score = 5  # Base score
        
        # +5 if has valid tool call
        if response.tool_call:
            score += 5
            tool = response.tool_call.get('tool', '')
            
            # +3 if tool matches task type
            task_lower = task.lower()
            if 'python' in tool and ('implement' in task_lower or 'code' in task_lower or 'function' in task_lower):
                score += 3
            if 'file' in tool and ('create' in task_lower or 'write' in task_lower):
                score += 3
        
        # +3 if has code block
        if '```python' in response.raw_response:
            score += 3
        
        # +2 if reasonable length (not too short, not too long)
        length = len(response.raw_response)
        if 200 < length < 2000:
            score += 2
        
        # +2 if fewer attempts (cleaner first try)
        if response.attempts == 1:
            score += 2
        
        # -3 if mentions error or failure
        if 'error' in response.raw_response.lower() or 'failed' in response.raw_response.lower():
            score -= 3
        
        return max(0, min(25, score))  # Clamp to 0-25
    
    def _validate_and_fix_tool(self, tool_call: Dict, responses: List[WorkerResponse], 
                                synthesized_text: str) -> None:
        """Validate tool exists, extract code from workers if hallucinated"""
        from utils.logger import get_logger
        
        registry = get_registry()
        logger = get_logger()
        tool_name = tool_call.get("tool", "")
        
        if not registry.get(tool_name):
            # Tool doesn't exist - extract code from worker responses
            print(f"    ⚠️ Hallucinated tool '{tool_name}' → extracting code from workers")
            
            # Try to extract Python code from all worker responses
            best_code = None
            best_length = 0
            
            for r in responses:
                code_match = re.search(r'```python\s*\n(.+?)\n```', r.raw_response, re.DOTALL)
                if code_match:
                    code = code_match.group(1).strip()
                    if len(code) > best_length:
                        best_code = code
                        best_length = len(code)
            
            if best_code:
                print(f"    ✅ Extracted {best_length} chars of code from workers")
                tool_call["tool"] = "python_exec"
                tool_call["params"] = {"code": best_code}
                logger.log_extraction(tool_name, best_length, "worker")
            else:
                # Fallback: try to extract from synthesized text
                code_match = re.search(r'```python\s*\n(.+?)\n```', synthesized_text, re.DOTALL)
                if code_match:
                    extracted = code_match.group(1).strip()
                    print(f"    ✅ Extracted {len(extracted)} chars from synthesized response")
                    tool_call["tool"] = "python_exec"
                    tool_call["params"] = {"code": extracted}
                    logger.log_extraction(tool_name, len(extracted), "synthesized")
                else:
                    print(f"    ⚠️ No code found, using placeholder")
                    tool_call["tool"] = "python_exec"
                    tool_call["params"] = {"code": f"# Tool '{tool_name}' was hallucinated\nprint('Manual implementation needed')"}
                    logger.log_extraction(tool_name, 0, "placeholder")
