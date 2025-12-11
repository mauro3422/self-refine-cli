# Poetiq Session Logger - Detailed logging for all phases

import json
import os
import glob
from datetime import datetime
from typing import Dict, Any, List
from config.settings import OUTPUT_DIR, MAX_SESSIONS_SAVED


class PoetiqLogger:
    """Logs all Poetiq session activity for analysis"""
    
    MAX_SESSIONS = MAX_SESSIONS_SAVED  # From settings.py
    
    def __init__(self):
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = os.path.join(OUTPUT_DIR, "sessions")
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, f"session_{self.session_id}.json")
        self.events: List[Dict] = []
        self.task = ""
        self._cleanup_old_sessions()  # Clean old sessions
        self._save()  # Create file immediately
    
    def _cleanup_old_sessions(self):
        """Keep only the last MAX_SESSIONS session files"""
        try:
            files = glob.glob(os.path.join(self.log_dir, "session_*.json"))
            if len(files) > self.MAX_SESSIONS:
                # Sort by creation time, oldest first
                files.sort(key=os.path.getctime)
                # Delete oldest files
                for f in files[:-self.MAX_SESSIONS]:
                    try:
                        os.remove(f)
                    except:
                        pass
        except:
            pass
    
    def set_task(self, task: str):
        self.task = task
        self._save()

    def log_info(self, message: str):
        """Log general info message"""
        self.events.append({
            "phase": "info",
            "time": datetime.now().isoformat(),
            "message": message
        })
        self._save()
    
    def log_parallel(self, responses):
        """Log parallel worker responses - includes True Poetiq verification status"""
        self.events.append({
            "phase": "parallel",
            "time": datetime.now().isoformat(),
            "workers": [
                {
                    "id": r.worker_id,
                    "duration": round(r.duration, 1),
                    "tool": r.tool_call.get("tool") if r.tool_call else None,
                    "verified": getattr(r, 'verified', False),  # True Poetiq field
                    "attempts": getattr(r, 'attempts', 1),  # How many retries
                    "execution_result": getattr(r, 'execution_result', '')[:100],  # Exec result
                    "response": r.raw_response[:400]
                }
                for r in responses
            ]
        })
        self._save()
    
    def log_aggregation(self, response: str, duration: float):
        """Log aggregator output"""
        self.events.append({
            "phase": "aggregation",
            "time": datetime.now().isoformat(),
            "duration": round(duration, 1),
            "response": response[:500]
        })
        self._save()
    
    def log_extraction(self, hallucinated_tool: str, code_length: int, source: str):
        """Log code extraction when tool was hallucinated"""
        self.events.append({
            "phase": "extraction",
            "time": datetime.now().isoformat(),
            "hallucinated_tool": hallucinated_tool,
            "code_length": code_length,
            "source": source  # "worker", "synthesized", or "placeholder"
        })
        self._save()
    
    def log_refine(self, iteration: int, score: int, feedback: str, 
                   pre_score: int = None, verified_workers: int = None, total_workers: int = None):
        """Log self-refine iteration with score comparison for True Poetiq analysis"""
        event = {
            "phase": "refine",
            "time": datetime.now().isoformat(),
            "iteration": iteration,
            "score": score,
            "feedback": feedback[:400]
        }
        # True Poetiq tracking fields
        if pre_score is not None:
            event["pre_refine_score"] = pre_score
            event["score_delta"] = score - pre_score  # Positive = improvement
        if verified_workers is not None:
            event["verified_workers"] = verified_workers
            event["total_workers"] = total_workers
        
        self.events.append(event)
        self._save()
    
    def log_tool(self, tool_name: str, result: str):
        """Log tool execution"""
        self.events.append({
            "phase": "tool",
            "time": datetime.now().isoformat(),
            "tool": tool_name,
            "result": result[:300]
        })
        self._save()
        
    def log_memory(self, query: str, context: Dict):
        """Log memory retrieval context"""
        self.events.append({
            "phase": "memory",
            "time": datetime.now().isoformat(),
            "query": query,
            "category": context.get("category"),
            "confidence": context.get("confidence"),
            "suggested_tools": context.get("tools_suggested"),
            "memories_found": len(context.get("memories", [])),
            "memories_preview": [m.get("lesson", "")[:100] for m in context.get("memories", [])][:3]
        })
        self._save()
    
    def log_final(self, response: str, score: int, total_time: float):
        """Log final result"""
        self.events.append({
            "phase": "final",
            "time": datetime.now().isoformat(),
            "score": score,
            "total_time": round(total_time, 1),
            "response": response[:600]
        })
        self._save()
    
    def _save(self):
        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump({
                "session": self.session_id,
                "task": self.task,
                "events": self.events
            }, f, indent=2, ensure_ascii=False)
    
    def get_recent_logs(self, n=10) -> List[Dict]:
        """Get recent events for dashboard"""
        return self.events[-n:]

def get_latest_session_logs(n=20) -> List[Dict]:
    """Read latest session logs from disk (for dashboard)"""
    try:
        log_dir = os.path.join(OUTPUT_DIR, "sessions")
        if not os.path.exists(log_dir):
            return []
            
        files = glob.glob(os.path.join(log_dir, "*.json"))
        if not files:
            return []
            
        # Get newest file
        latest_file = max(files, key=os.path.getctime)
        
        with open(latest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("events", [])[-n:]
    except Exception as e:
        print(f"Error reading logs: {e}")
        return []

# Global instance
_logger = None

def get_logger() -> PoetiqLogger:
    global _logger
    if _logger is None:
        _logger = PoetiqLogger()
    return _logger

def new_session() -> PoetiqLogger:
    global _logger
    _logger = PoetiqLogger()
    return _logger
