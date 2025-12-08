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
    
    def aggregate(self, responses: List[WorkerResponse], task: str) -> WorkerResponse:
        """Aggregate responses - PRIORITIZE verified (code-tested) responses"""
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
            
        # No verified responses - fall back to LLM synthesis
        print(f"    ⚠️ No verified responses, synthesizing from {len(responses)} candidates")
            
        # Prepare context for aggregation
        candidates_text = ""
        for i, r in enumerate(responses):
            tool_status = f"(Tool: {r.tool_call.get('tool')})" if r.tool_call else "(No tool)"
            candidates_text += f"\n--- CANDIDATE {i+1} {tool_status} ---\n{r.raw_response[:800]}\n"
        
        # Get list of VALID tools
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
        synthesized_text = self.llm.generate(prompt, temp=0.3)
        duration = time.time() - agg_start
        
        # Extract new tool call
        tool_call = extract_tool_call(synthesized_text)
        
        # SMART VALIDATION: If hallucinated tool, extract real code from workers
        if tool_call:
            self._validate_and_fix_tool(tool_call, responses, synthesized_text)
        
        # Return as a specialized WorkerResponse
        return WorkerResponse(
            worker_id=999,  # ID for aggregator
            raw_response=synthesized_text,
            tool_call=tool_call,
            duration=duration,
            temperature=0.0
        )
    
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
