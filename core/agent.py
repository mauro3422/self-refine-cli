# Agent Module - Simplified orchestration using modular components
# Now uses: prompts, parsers, evaluator, parallel, verification

import json
from typing import Dict, List, Any, Optional

from core.llm_client import LLMClient
from core.prompts import AGENT_SYSTEM_PROMPT, REFINE_PROMPT
from core.parsers import extract_tool_call, detect_language, detect_required_tools
from core.evaluator import Evaluator
from core.parallel import ParallelExecutor, CandidateGenerator
from core.verification import CodeVerifier
from tools.registry import get_registry
from tools.file_tools import register_file_tools
from tools.command_tools import register_command_tools
from config.settings import AGENT_MAX_ITERATIONS, AGENT_WORKSPACE


def init_tools():
    print("\n🔧 Initializing tools...")
    register_file_tools()
    register_command_tools()
    print()


class Agent:
    """
    Self-Refine Agent with multi-threading and verification capabilities
    
    Architecture:
    - Uses modular components for prompts, parsing, evaluation
    - Can generate multiple candidates in parallel
    - Can verify generated code execution
    """
    
    def __init__(
        self, 
        max_iterations: int = None, 
        max_refine: int = 3,
        use_parallel: bool = False,
        num_candidates: int = 3,
        debug: bool = True
    ):
        self.llm = LLMClient()
        self.registry = get_registry()
        self.evaluator = Evaluator(self.llm)
        self.verifier = CodeVerifier(AGENT_WORKSPACE)
        self.parallel = ParallelExecutor() if use_parallel else None
        self.candidate_gen = CandidateGenerator(self.llm, self.parallel) if use_parallel else None
        
        self.max_iterations = max_iterations or AGENT_MAX_ITERATIONS
        self.max_refine = max_refine
        self.num_candidates = num_candidates
        self.use_parallel = use_parallel
        
        self.conversation_history: List[Dict[str, str]] = []
        self.workspace = AGENT_WORKSPACE
        self.tools_used: List[str] = []
        self.debug_mode = debug
        self.last_score = 0
        self.initial_score = 0
        
        # Debug logger
        if debug:
            try:
                from utils.debug_logger import get_debug_logger
                self.logger = get_debug_logger()
                print(f"  📝 Debug log: {self.logger.get_log_path()}")
            except:
                self.logger = None
        else:
            self.logger = None
        
        # Memory
        try:
            from utils.memory import get_memory
            self.memory = get_memory()
        except:
            self.memory = None
    
    def _log(self, log_type: str, **kwargs):
        if not self.logger:
            return
        
        if log_type == "tool":
            self.logger.log_tool_call(
                kwargs.get("name", ""),
                kwargs.get("params", {}),
                kwargs.get("result", ""),
                kwargs.get("success", False)
            )
        elif log_type == "llm":
            self.logger.log_llm_call(
                kwargs.get("type", ""),
                kwargs.get("prompt", ""),
                kwargs.get("response", ""),
                kwargs.get("temp", 0.7)
            )
        elif log_type == "refinement":
            self.logger.log_refinement(
                kwargs.get("iteration", 0),
                kwargs.get("score", 0),
                kwargs.get("feedback", "")
            )
    
    def _get_system_prompt(self) -> str:
        tools_brief = self.registry.get_tool_names_brief()
        memory_context = ""
        if self.memory:
            memory_context = self.memory.get_relevant_context("")
        
        return AGENT_SYSTEM_PROMPT.format(
            tools_brief=tools_brief,
            workspace=self.workspace,
            memory_context=memory_context
        )
    
    def _execute_tool(self, tool_call: Dict[str, Any]) -> str:
        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {})
        
        self.tools_used.append(tool_name)
        
        print(f"  🔧 {tool_name}", end="")
        if 'path' in params:
            print(f"({params['path']})", end="")
        print()
        
        result = self.registry.execute_tool(tool_name, **params)
        success = result.get("success", False)
        
        if success:
            output = result.get("result", "")
            if isinstance(output, list):
                output = json.dumps(output, indent=2, ensure_ascii=False)
            print(f"  ✅ OK ({len(str(output))} chars)")
            self._log("tool", name=tool_name, params=params, result=output, success=True)
            return f"[RESULT: {tool_name}]\n{output}"
        else:
            error = result.get("error", "Error")
            print(f"  ❌ {error[:50]}")
            self._log("tool", name=tool_name, params=params, result=error, success=False)
            return f"[ERROR: {tool_name}]\n{error}"
    
    def _run_with_tools(self, messages: List[Dict], max_iter: int = None) -> str:
        max_iter = max_iter or self.max_iterations
        
        for i in range(max_iter):
            response = self.llm.chat(messages)
            self._log("llm", type="chat", prompt=str(messages[-1]), response=response)
            
            tool_call = extract_tool_call(response)
            
            if tool_call:
                tool_result = self._execute_tool(tool_call)
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": tool_result})
            else:
                return response
        
        return response
    
    def _self_refine(self, response: str, user_input: str) -> str:
        current_response = response
        self.initial_score = 0
        
        for i in range(self.max_refine):
            # Evaluate
            eval_result = self.evaluator.evaluate(
                user_input, 
                current_response, 
                self.tools_used
            )
            
            score = eval_result["score"]
            feedback = eval_result["feedback"]
            
            if not eval_result["tools_ok"] and self.memory:
                self.memory.learn_from_tool_mistake(
                    eval_result["required_tools"], 
                    self.tools_used
                )
            
            if i == 0:
                self.initial_score = score
            
            self._log("refinement", iteration=i+1, score=score, feedback=feedback)
            
            print(f"  📊 Score: {score}/25", end="")
            self.last_score = score
            
            if eval_result["passed"]:
                print(" ✨")
                if self.memory and score > self.initial_score + 5:
                    self.memory.learn_from_refinement(
                        response, current_response, feedback,
                        self.initial_score, score
                    )
                break
            
            if i == self.max_refine - 1:
                print(f" (max iter)")
                break
            
            print(f" → refining...")
            
            # Refine
            tools_str = ", ".join(self.tools_used) if self.tools_used else "None"
            refine_prompt = REFINE_PROMPT.format(
                user_input=user_input,
                tools_used=tools_str,
                feedback=feedback[:800]
            )
            
            refine_messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": refine_prompt}
            ]
            
            current_response = self._run_with_tools(refine_messages, max_iter=3)
        
        return current_response
    
    def run(self, user_input: str) -> str:
        """Main entry point - process user request"""
        self.tools_used = []
        
        if self.logger:
            self.logger.start_interaction(user_input)
        
        lang = detect_language(user_input)
        if self.logger:
            self.logger.log_language(lang)
        
        required_tools = detect_required_tools(user_input)
        if self.logger:
            self.logger.log_required_tools(required_tools)
        
        messages = [{"role": "system", "content": self._get_system_prompt()}]
        messages.extend(self.conversation_history[-20:])
        messages.append({"role": "user", "content": user_input})
        
        print(f"\n🤔 Processing... (lang={lang})")
        
        if required_tools:
            print(f"  📋 Required: {required_tools}")
        
        # Generate response (with optional parallel candidates)
        if self.use_parallel and self.candidate_gen:
            eval_fn = lambda r: self.evaluator.evaluate(user_input, r, self.tools_used)
            best = self.candidate_gen.generate_with_voting(
                messages, eval_fn, self.num_candidates
            )
            response = best.get("response", "")
        else:
            response = self._run_with_tools(messages)
        
        final_response = response.strip()
        
        # Self-refine
        if len(final_response) > 30:
            print("  🔄 Self-Refine...")
            final_response = self._self_refine(final_response, user_input)
        
        # End logging
        if self.logger:
            self.logger.end_interaction(final_response, self.last_score)
        
        # Update history
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": final_response})
        
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]
        
        return final_response
    
    def verify_last_code(self, expected_output: str = None) -> Dict[str, Any]:
        """Verify code from the last interaction"""
        if not self.conversation_history:
            return {"success": False, "error": "No history"}
        
        from core.parsers import extract_code_block
        last_response = self.conversation_history[-1].get("content", "")
        code = extract_code_block(last_response)
        
        if not code:
            return {"success": False, "error": "No code found"}
        
        return self.verifier.execute_code(code)
    
    def get_debug_summary(self) -> str:
        if self.logger:
            return self.logger.get_latest_interaction_summary()
        return "Debug logging disabled"
    
    def clear_history(self):
        self.conversation_history = []
        print("🧹 History cleared")
