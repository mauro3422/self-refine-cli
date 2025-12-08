# core/agentic_loop.py - Multi-tool execution loop
# Allows the agent to execute multiple tools in sequence until task is complete

from typing import Dict, Any, List, Optional
import time

from core.llm_client import LLMClient
from core.parsers import extract_tool_call
from tools.registry import get_registry


class AgenticLoop:
    """
    Executes tools in a loop until the task is complete.
    
    The LLM decides:
    1. Which tool to execute next
    2. When the task is complete (returns "DONE")
    """
    
    MAX_ITERATIONS = 5  # Safety limit
    
    def __init__(self, executor, workspace: str = "sandbox", orchestrator=None):
        self.executor = executor
        self.workspace = workspace
        self.orchestrator = orchestrator  # NEW: Access to memory
        self.llm = LLMClient()
        self.registry = get_registry()
        self.tools_executed: List[Dict] = []
    
    def run(self, task: str, initial_response: str) -> Dict[str, Any]:
        """
        Execute tools in a loop until task is complete.
        
        Args:
            task: The original user task
            initial_response: The first LLM response with tool call
            
        Returns:
            Dict with final result, tools executed, etc.
        """
        iteration = 0
        current_response = initial_response
        all_results = []
        
        while iteration < self.MAX_ITERATIONS:
            iteration += 1
            
            # Extract tool call from current response
            tool_call = extract_tool_call(current_response)
            
            if not tool_call:
                # No tool call found - check if task is complete
                if self._is_task_complete(current_response):
                    break
                else:
                    # No tool and not complete - something's wrong
                    break
            
            # Execute the tool
            tool_name = tool_call.get('tool')
            print(f"  🔧 [{iteration}] Executing: {tool_name}")
            
            result = self.executor.execute(tool_call)
            
            # Check if tool execution had an error
            is_error = "[ERROR]" in result or "not found" in result.lower()
            
            self.tools_executed.append({
                "iteration": iteration,
                "tool": tool_name,
                "params": tool_call.get('params', {}),
                "result": result[:200],
                "success": not is_error
            })
            
            all_results.append(f"[{tool_name}]: {result}")
            
            if is_error:
                print(f"      ⚠️ Error: {result[:60]}...")
                # Ask LLM to try a different approach
                current_response = self._handle_error(task, tool_name, result)
                print(f"      🔄 Retrying with: {current_response[:60]}...")
            else:
                print(f"      → {result[:60]}...")
                # Ask LLM: what's next?
                current_response = self._get_next_action(
                    task=task,
                    history=self.tools_executed,
                    last_result=result
                )
            
            # Debug: show what LLM decided
            print(f"      🤔 LLM next action: {current_response[:80]}...")
            
            # Check if LLM says DONE
            if self._is_task_complete(current_response):
                print(f"  ✅ Task complete after {iteration} tools")
                break
        
        return {
            "iterations": iteration,
            "tools_executed": self.tools_executed,
            "all_results": all_results,
            "final_response": current_response
        }
    
    def _get_next_action(self, task: str, history: List[Dict], last_result: str) -> str:
        """Ask LLM what to do next based on history"""
        
        history_text = "\n".join([
            f"- {h['tool']}({h['params']}) → {h['result'][:100]}"
            for h in history
        ])
        
        tools_schema = self.registry.get_tools_prompt()
        
        prompt = f"""You just executed a tool. Now analyze if more tools are needed.

ORIGINAL TASK: {task}

WHAT YOU HAVE DONE:
{history_text}

LAST TOOL RESULT:
{last_result[:500]}

AVAILABLE TOOLS:
{tools_schema}

STEP-BY-STEP ANALYSIS:
1. The task was: "{task}"
2. I have executed: {len(history)} tool(s)
3. Did I list files? {any('list_dir' in h['tool'] for h in history)}
4. Did I read the file mentioned? {any('read_file' in h['tool'] for h in history)}
5. Did I count lines or provide the answer? NO - I just got raw data

CONCLUSION:
- If the task asks for info from a FILE (lines, content), and I only listed files → I need read_file
- If I read the file but didn't count/analyze → I may need python_exec

RESPOND WITH:
- A JSON tool call if more work needed: {{"tool": "...", "params": {{...}}}}
- The word DONE only if the user's question is FULLY answered

YOUR RESPONSE:"""
        
        return self.llm.generate(prompt, temp=0.3)
    
    def _handle_error(self, task: str, failed_tool: str, error: str) -> str:
        """When a tool fails, ask LLM to try a different approach"""
        
        tools_schema = self.registry.get_tools_prompt()
        
        # Get tips from memory if available
        memory_tips = ""
        if self.orchestrator:
            try:
                # Quick context check for this specific error
                ctx = self.orchestrator.get_context(f"{failed_tool} error {error}", use_llm=False)
                if ctx.tips:
                    memory_tips = f"\n💡 MEMORY TIPS:\n{ctx.tips}\n"
                
                # New: Learn from this error immediately
                self.orchestrator.learn(
                    lesson=f"AVOID: {failed_tool} failed with {error[:100]}",
                    category="tool_error",
                    tools=[failed_tool],
                    error_type="execution_failure"
                )
            except Exception as e:
                print(f"      ⚠️ Memory error in loop: {e}")

        prompt = f"""A tool execution FAILED. You need to try a different approach.

ORIGINAL TASK: {task}

FAILED TOOL: {failed_tool}
ERROR: {error}
{memory_tips}
AVAILABLE TOOLS (use ONLY these exact names):
{tools_schema}

IMPORTANT:
- The tool '{failed_tool}' does NOT exist or had an error.
- Use ONLY the tools listed above.
- For reading files, use 'read_file' with param 'path'.
- For counting lines, use 'python_exec' with code like: print(len(open('file.txt').readlines()))

TRY AGAIN with a valid tool:
{{"tool": "valid_tool_name", "params": {{...}}}}"""
        
        return self.llm.generate(prompt, temp=0.3)
    
    def _is_task_complete(self, response: str) -> bool:
        """Check if LLM indicates task is complete (only if no tool call present)"""
        # If there's a tool call in the response, task is NOT complete
        if '{"tool"' in response or '"tool":' in response:
            return False
        
        response_lower = response.lower().strip()
        return (
            response_lower.startswith("done") or
            "task is complete" in response_lower or
            "tarea completada" in response_lower or
            (len(response_lower) < 50 and "done" in response_lower)
        )


def run_agentic(task: str, initial_response: str, executor) -> Dict[str, Any]:
    """Convenience function to run agentic loop"""
    loop = AgenticLoop(executor)
    return loop.run(task, initial_response)
