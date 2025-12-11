# core/poetiq/worker.py
# True Poetiq Worker: Generates code, EXECUTES it, and refines based on results

from dataclasses import dataclass
from typing import Dict, Optional, List
import time
import re

from core.llm_client import LLMClient
from core.prompts import AGENT_SYSTEM_PROMPT, build_tools_section
from core.parsers import extract_tool_call
from tools.registry import get_registry
from utils.error_translator import format_for_llm


@dataclass
class WorkerResponse:
    """Response from a single worker with verification status"""
    worker_id: int
    raw_response: str
    tool_call: Optional[Dict]
    duration: float
    temperature: float
    verified: bool = False  # True if code executed successfully
    execution_result: str = ""  # Result of execution (success or error)
    attempts: int = 1  # How many generation attempts


class LightWorker:
    """
    True Poetiq Worker: Generates code, EXECUTES it, and refines based on results.
    Each worker is a mini self-refine loop that verifies its own code.
    """
    
    MAX_RETRIES = 2  # Max refinement attempts per worker
    
    def __init__(self, worker_id: int, temperature: float = 0.7, 
                 memory_context: str = "", suggested_tools: List[str] = None):
        self.worker_id = worker_id
        self.temperature = temperature
        self.llm = LLMClient()
        self.registry = get_registry()
        self.memory_context = memory_context
        self.suggested_tools = suggested_tools or ["python_exec"]  # Default fallback
    
    def generate(self, task: str) -> WorkerResponse:
        """Original simple generation (kept for compatibility)"""
        return self.generate_and_verify(task, test_cases=None, max_retries=0)
    
    def generate_and_verify(self, task: str, test_cases: list = None, max_retries: int = 2) -> WorkerResponse:
        """
        TRUE POETIQ: Generate code, execute it, refine on error.
        Returns a WorkerResponse with verified=True if code runs successfully.
        """
        start = time.time()
        attempts = 0
        last_error = ""
        
        # First generation
        response = self._generate_llm(task)
        
        # Check for invalid/empty response
        if self._is_invalid_response(response):
            print(f"    Worker-{self.worker_id}: ❌ Empty/invalid response detected")
            return WorkerResponse(
                worker_id=self.worker_id,
                raw_response=response,
                tool_call=None,
                duration=time.time() - start,
                temperature=self.temperature,
                verified=False,
                execution_result="Invalid response: empty or truncated",
                attempts=1
            )
        
        code = self._extract_code(response)
        
        if not code:
            # No code generated, return as-is (might be explanation only)
            return WorkerResponse(
                worker_id=self.worker_id,
                raw_response=response,
                tool_call=extract_tool_call(response),
                duration=time.time() - start,
                temperature=self.temperature,
                verified=False,
                execution_result="No code block found",
                attempts=1
            )
        
        # Execute and verify loop
        for attempt in range(max_retries + 1):
            attempts = attempt + 1
            result = self._execute_code(code, test_cases)
            
            if result.get("success"):
                # Code works! Return verified response
                msg = f"✅ Code verified with {len(test_cases) if test_cases else 0} tests"
                print(f"    Worker-{self.worker_id}: {msg} (attempt {attempts})")
                return WorkerResponse(
                    worker_id=self.worker_id,
                    raw_response=response,
                    tool_call={"tool": "python_exec", "params": {"code": code}},
                    duration=time.time() - start,
                    temperature=self.temperature,
                    verified=True,
                    execution_result=result.get("result", "")[:200],
                    attempts=attempts
                )
            
            # Code failed - save error
            last_error = result.get("error", "Unknown error")
            
            # Refine if we have retries left
            if attempt < max_retries:
                print(f"    Worker-{self.worker_id}: ⚠️ Error (attempt {attempts}), refining...")
                response = self._refine_with_error(task, code, last_error)
                code = self._extract_code(response)
                if not code:
                    break  # Couldn't extract code from refinement
        
        # Max retries reached or refinement failed
        print(f"    Worker-{self.worker_id}: ❌ Failed after {attempts} attempts")
        return WorkerResponse(
            worker_id=self.worker_id,
            raw_response=response,
            tool_call={"tool": "python_exec", "params": {"code": code}} if code else None,
            duration=time.time() - start,
            temperature=self.temperature,
            verified=False,
            execution_result=f"Error: {last_error[:150]}",
            attempts=attempts
        )
    
    def _generate_llm(self, task: str) -> str:
        """Single LLM generation call with two-phase tool selection"""
        # Get skill names for lightweight list
        from memory.skill_harvester import get_harvester
        harvester = get_harvester()
        skill_names = harvester.list_skills() if harvester else []
        
        # Build tools section with two-phase approach:
        # - Full schema for suggested tools (from ContextVectors)
        # - Lightweight list for other tools
        # - Lightweight list for skills
        tools_section = build_tools_section(
            suggested_tools=self.suggested_tools,
            registry=self.registry,
            skills=skill_names
        )
        
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            tools_schema=tools_section,
            workspace="sandbox",
            memory_context=self.memory_context
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task}
        ]
        
        # Use worker_id as slot_id for slot affinity (prevents context thrashing)
        return self.llm.chat(messages, temp=self.temperature, slot_id=self.worker_id)
    
    def _extract_code(self, response: str) -> Optional[str]:
        """Extract Python code from ```python blocks"""
        match = re.search(r'```python\s*\n(.+?)\n```', response, re.DOTALL)
        return match.group(1).strip() if match else None
    
    def _is_invalid_response(self, response: str) -> bool:
        """Detect empty, truncated, or invalid LLM responses"""
        if not response:
            return True
        
        # Clean whitespace
        cleaned = response.strip()
        
        # Too short to be useful
        if len(cleaned) < 20:
            return True
        
        # Common invalid patterns (truncated responses)
        invalid_patterns = [
            r'^\[/?SYS\]$',           # Just [/SYS] or [SYS]
            r'^\[/?INST\]$',          # Just [/INST]
            r'^```\s*$',              # Empty code block
            r'^\s*$',                 # Whitespace only
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, cleaned, re.IGNORECASE):
                return True
        
        # Check if response is mostly just system tags
        system_tags = len(re.findall(r'\[/?(?:SYS|INST|RESP)\]', cleaned))
        if system_tags > 0 and len(cleaned) - (system_tags * 6) < 50:
            return True
        
        return False
    
    def _execute_code(self, code: str, test_cases: list = None) -> Dict:
        """Execute Python code and return result, optionally verifying with test cases"""
        import ast

        execution_code = code
        
        # Detect function name dynamically
        func_name = "solve" # fallback
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    break # Use the first function found
        except:
            pass # Use fallback if parse fails
        
        if test_cases:
            print(f"    Worker-{self.worker_id}: 🧪 Injecting {len(test_cases)} tests for function '{func_name}'...")
            # Append test case verification block
            test_block = "\n\n# --- Auto-Generated Verification ---\n"
            test_block += "try:\n"
            for i, tc in enumerate(test_cases):
                # Using repr() to correctly format strings, lists, etc.
                call_str = f"{func_name}({repr(tc['input'])})"
                test_block += f"    assert {call_str} == {repr(tc['expected'])}, f'Test {i+1} failed: input={repr(tc['input'])} expected={repr(tc['expected'])} got={{{call_str}}}'\n"
            test_block += "    print('ALL_TESTS_PASSED')\n"
            test_block += "except Exception as e:\n"
            # Raise so that exit code is non-zero (if runner respects it) or just output error
            test_block += "    print(f'VERIFICATION_FAILED: {e}')\n"
            test_block += "    raise\n" 
            
            execution_code += test_block
        else:
            print(f"    Worker-{self.worker_id}: ⚠️ No test cases provided for verification")
            
        return self.registry.execute_tool("python_exec", code=execution_code)
    
    def _refine_with_error(self, task: str, code: str, error: str) -> str:
        """Ask LLM to fix code based on execution error - with semantic translation"""
        # Translate technical error to semantic instruction
        semantic_error = format_for_llm(error)
        
        prompt = f"""The following Python code failed. Fix it based on the error analysis.

ORIGINAL TASK: {task[:200]}

CODE THAT FAILED:
```python
{code}
```

{semantic_error}

Provide the CORRECTED code in a ```python block. Only fix the error, keep the logic."""
        
        # Use same slot as the worker for cache affinity
        return self.llm.generate(prompt, temp=self.temperature, slot_id=self.worker_id)
