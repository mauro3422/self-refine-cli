# core/poetiq/worker.py
# True Poetiq Worker: Generates code, EXECUTES it, and refines based on results

from dataclasses import dataclass
from typing import Dict, Optional
import time
import re

from core.llm_client import LLMClient
from core.prompts import AGENT_SYSTEM_PROMPT
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
    
    def __init__(self, worker_id: int, temperature: float = 0.7, memory_context: str = ""):
        self.worker_id = worker_id
        self.temperature = temperature
        self.llm = LLMClient()
        self.registry = get_registry()
        self.memory_context = memory_context
    
    def generate(self, task: str) -> WorkerResponse:
        """Original simple generation (kept for compatibility)"""
        return self.generate_and_verify(task, max_retries=0)
    
    def generate_and_verify(self, task: str, max_retries: int = 2) -> WorkerResponse:
        """
        TRUE POETIQ: Generate code, execute it, refine on error.
        Returns a WorkerResponse with verified=True if code runs successfully.
        """
        start = time.time()
        attempts = 0
        last_error = ""
        
        # First generation
        response = self._generate_llm(task)
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
            result = self._execute_code(code)
            
            if result.get("success"):
                # Code works! Return verified response
                print(f"    Worker-{self.worker_id}: ✅ Code verified (attempt {attempts})")
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
        """Single LLM generation call"""
        tools_schema = self.registry.get_tools_prompt()
        
        # Inject harvested skills if available
        from memory.skill_harvester import get_harvester
        skills_context = get_harvester().get_skills_for_prompt(task)
        
        system_prompt = AGENT_SYSTEM_PROMPT.format(
            tools_schema=tools_schema,
            workspace="sandbox",
            memory_context=self.memory_context
        )
        
        # Append skills to system prompt if available
        if skills_context:
            system_prompt += skills_context
        
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
    
    def _execute_code(self, code: str) -> Dict:
        """Execute Python code and return result"""
        return self.registry.execute_tool("python_exec", code=code)
    
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
