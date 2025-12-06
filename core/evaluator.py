# Evaluator Module - Self-evaluation logic

from typing import List, Optional
from core.llm_client import LLMClient
from core.prompts import EVAL_PROMPT
from core.parsers import extract_score, detect_required_tools


class Evaluator:
    """Evaluates agent responses using LLM"""
    
    def __init__(self, llm: LLMClient = None):
        self.llm = llm or LLMClient()
    
    def evaluate(
        self, 
        user_input: str, 
        response: str, 
        tools_used: List[str]
    ) -> dict:
        """
        Evaluate a response and return score + feedback
        
        Returns:
            {"score": int, "feedback": str, "passed": bool}
        """
        tools_str = ", ".join(tools_used) if tools_used else "None"
        
        prompt = EVAL_PROMPT.format(
            user_input=user_input,
            tools_used=tools_str,
            response=response[:2000]
        )
        
        feedback = self.llm.generate(prompt, temp=0.3)
        score = extract_score(feedback)
        
        # Check if required tools were used
        required = detect_required_tools(user_input)
        tools_ok = not required or any(t in tools_used for t in required)
        
        if not tools_ok and score > 0:
            score = 0
        
        return {
            "score": score,
            "feedback": feedback,
            "passed": score >= 22,
            "required_tools": required,
            "tools_ok": tools_ok
        }
