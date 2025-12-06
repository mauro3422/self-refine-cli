# Debug Logger - Saves complete processing details for analysis

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from config.settings import OUTPUT_DIR


class DebugLogger:
    """Logs all agent processing details for debugging"""
    
    def __init__(self, log_dir: str = None):
        self.log_dir = log_dir or os.path.join(OUTPUT_DIR, "debug_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create new log file for each session
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(self.log_dir, f"session_{timestamp}.json")
        
        self.session_data = {
            "session_start": datetime.now().isoformat(),
            "interactions": []
        }
        
        self.current_interaction = None
    
    def start_interaction(self, user_input: str):
        """Start logging a new interaction"""
        self.current_interaction = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "detected_language": None,
            "required_tools": [],
            "tool_calls": [],
            "llm_calls": [],
            "refinement_iterations": [],
            "final_response": None,
            "final_score": None,
            "tools_used": [],
            "errors": []
        }
    
    def log_language(self, language: str):
        """Log detected language"""
        if self.current_interaction:
            self.current_interaction["detected_language"] = language
    
    def log_required_tools(self, tools: List[str]):
        """Log which tools were required"""
        if self.current_interaction:
            self.current_interaction["required_tools"] = tools
    
    def log_tool_call(self, tool_name: str, params: Dict, result: Any, success: bool):
        """Log a tool execution"""
        if self.current_interaction:
            self.current_interaction["tool_calls"].append({
                "timestamp": datetime.now().isoformat(),
                "tool": tool_name,
                "params": params,
                "result": str(result)[:2000],  # Truncate large results
                "success": success
            })
            if tool_name not in self.current_interaction["tools_used"]:
                self.current_interaction["tools_used"].append(tool_name)
    
    def log_llm_call(self, prompt_type: str, prompt: str, response: str, temp: float = 0.7):
        """Log an LLM call"""
        if self.current_interaction:
            self.current_interaction["llm_calls"].append({
                "timestamp": datetime.now().isoformat(),
                "type": prompt_type,
                "prompt_preview": prompt[:500],
                "prompt_length": len(prompt),
                "response_preview": response[:500],
                "response_length": len(response),
                "temperature": temp
            })
    
    def log_refinement(self, iteration: int, score: int, feedback_preview: str):
        """Log a refinement iteration"""
        if self.current_interaction:
            self.current_interaction["refinement_iterations"].append({
                "iteration": iteration,
                "score": score,
                "feedback_preview": feedback_preview[:300]
            })
    
    def log_error(self, error: str):
        """Log an error"""
        if self.current_interaction:
            self.current_interaction["errors"].append({
                "timestamp": datetime.now().isoformat(),
                "error": error
            })
    
    def end_interaction(self, final_response: str, final_score: int):
        """End current interaction and save"""
        if self.current_interaction:
            self.current_interaction["final_response"] = final_response[:1000]
            self.current_interaction["final_score"] = final_score
            self.current_interaction["end_timestamp"] = datetime.now().isoformat()
            
            self.session_data["interactions"].append(self.current_interaction)
            self._save()
            
            self.current_interaction = None
    
    def _save(self):
        """Save session data to file"""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)
    
    def get_log_path(self) -> str:
        """Get current log file path"""
        return self.log_file
    
    def get_latest_interaction_summary(self) -> str:
        """Get summary of latest interaction for display"""
        if not self.session_data["interactions"]:
            return "No interactions logged yet"
        
        latest = self.session_data["interactions"][-1]
        summary = f"""
📋 INTERACTION SUMMARY
=====================
User input: {latest['user_input'][:100]}...
Language: {latest.get('detected_language', 'Unknown')}
Required tools: {latest.get('required_tools', [])}
Tools used: {latest.get('tools_used', [])}
LLM calls: {len(latest.get('llm_calls', []))}
Refinement iterations: {len(latest.get('refinement_iterations', []))}
Final score: {latest.get('final_score', 0)}/25
Errors: {len(latest.get('errors', []))}
"""
        return summary


# Global instance
_debug_logger: Optional[DebugLogger] = None

def get_debug_logger() -> DebugLogger:
    global _debug_logger
    if _debug_logger is None:
        _debug_logger = DebugLogger()
    return _debug_logger
