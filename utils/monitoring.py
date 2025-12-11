# Enhanced Monitoring Logger for Autonomous Night Operation
# Provides detailed metrics and status for agent supervision

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict


class MonitoringLogger:
    """
    Enhanced logging for autonomous operation monitoring.
    
    Features:
    - Real-time status tracking
    - Performance metrics
    - Error aggregation
    - Health indicators
    
    The agent uses this to monitor the system during night operation.
    """
    
    LOG_FILE = "outputs/monitoring.json"
    STATUS_FILE = "outputs/status.json"
    
    def __init__(self):
        self.session_start = datetime.now()
        self.events = []
        self.metrics = defaultdict(list)
        self.errors = []
        self.current_status = "initializing"
        self._ensure_files()  # Call AFTER setting instance variables
    
    def _ensure_files(self):
        """Create log files if needed"""
        os.makedirs("outputs", exist_ok=True)
        if not os.path.exists(self.LOG_FILE):
            self._save_log()
        if not os.path.exists(self.STATUS_FILE):
            self._save_status()
    
    def _save_log(self):
        """Save full log to file"""
        data = {
            "session_start": self.session_start.isoformat(),
            "last_updated": datetime.now().isoformat(),
            "events": self.events[-100:],  # Keep last 100 events
            "metrics": dict(self.metrics),
            "errors": self.errors[-50:],  # Keep last 50 errors
        }
        with open(self.LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _save_status(self):
        """Save current status for quick checking"""
        data = {
            "status": self.current_status,
            "last_updated": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.session_start).total_seconds(),
            "event_count": len(self.events),
            "error_count": len(self.errors),
            "last_event": self.events[-1] if self.events else None,
            "last_error": self.errors[-1] if self.errors else None,
            "health": self._calculate_health()
        }
        with open(self.STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
            
    def _load_history(self) -> Dict:
        """Load historical session data"""
        history_file = "outputs/history.json"
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {"sessions": [], "global_avg_score": 0, "global_verify_rate": 0}

    def _save_history_snapshot(self):
        """Save current session summary to history (on exit or periodic)"""
        summary = self.get_summary()
        history = self._load_history()
        
        # Update or append current session
        # We use a simplified key based on session_start to avoid duplicates
        session_key = self.session_start.isoformat()
        
        # Remove if exists (update)
        history["sessions"] = [s for s in history["sessions"] if s["start"] != session_key]
        
        history["sessions"].append({
            "start": session_key,
            "tasks": summary["tasks_completed"],
            "avg_score": summary["avg_score"],
            "verify_rate": summary["verification_rate"]
        })
        
        # Recalculate globals
        total_tasks = sum(s["tasks"] for s in history["sessions"])
        if total_tasks > 0:
            weighted_score = sum(s["avg_score"] * s["tasks"] for s in history["sessions"]) / total_tasks
            weighted_verify = sum(s["verify_rate"] * s["tasks"] for s in history["sessions"]) / total_tasks
            history["global_avg_score"] = weighted_score
            history["global_verify_rate"] = weighted_verify
            
        with open("outputs/history.json", 'w') as f:
            json.dump(history, f, indent=2)

    def get_trend(self) -> str:
        """Compare current performance vs history"""
        history = self._load_history()
        current = self.get_summary()
        
        if not history["sessions"]:
            return "🆕 First Session"
            
        hist_score = history["global_avg_score"]
        curr_score = current["avg_score"]
        
        delta = curr_score - hist_score
        icon = "📈" if delta > 0 else "📉"
        
        return f"{icon} Trend: {curr_score:.1f} (vs {hist_score:.1f} avg)"
    
    def get_score_history(self, n: int = 10) -> List[float]:
        """Get last N session scores for sparkline"""
        history = self._load_history()
        sessions = history.get("sessions", [])
        scores = [s["avg_score"] for s in sessions[-n:] if s.get("avg_score", 0) > 0]
        return scores
    
    @staticmethod
    def generate_sparkline(values: List[float], max_value: float = 25.0) -> str:
        """
        Generate ASCII sparkline from values.
        Uses block characters: ▁▂▃▄▅▆▇█
        """
        if not values:
            return "─" * 10
            
        chars = "▁▂▃▄▅▆▇█"
        result = ""
        
        for val in values:
            # Normalize to 0-1 range (assuming max score is 25)
            normalized = min(max(val / max_value, 0), 1)
            # Map to character index
            idx = int(normalized * (len(chars) - 1))
            result += chars[idx]
        
        return result
    
    def get_trend_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive trend data for dashboard.
        
        Returns:
            {
                "sparkline": "▁▂▃▅▆▇",
                "direction": "up" | "down" | "stable",
                "direction_icon": "↑" | "↓" | "→",
                "delta": +2.3,
                "current_score": 21.5,
                "avg_last_5": 20.1,
                "avg_all_time": 19.2,
                "total_sessions": 15,
                "total_tasks": 47,
                "best_score": 24.0,
                "sessions": [...last 10...]
            }
        """
        history = self._load_history()
        current = self.get_summary()
        sessions = history.get("sessions", [])
        
        scores = self.get_score_history(10)
        sparkline = self.generate_sparkline(scores)
        
        # Calculate averages
        avg_all_time = history.get("global_avg_score", 0)
        avg_last_5 = sum(scores[-5:]) / len(scores[-5:]) if scores else 0
        current_score = current.get("avg_score", 0)
        
        # Determine direction
        delta = current_score - avg_all_time
        if delta > 1.0:
            direction = "up"
            direction_icon = "↑"
        elif delta < -1.0:
            direction = "down"
            direction_icon = "↓"
        else:
            direction = "stable"
            direction_icon = "→"
        
        # Best score
        best_score = max(scores) if scores else 0
        
        # Total tasks
        total_tasks = sum(s.get("tasks", 0) for s in sessions)
        
        return {
            "sparkline": sparkline,
            "direction": direction,
            "direction_icon": direction_icon,
            "delta": round(delta, 1),
            "current_score": round(current_score, 1),
            "avg_last_5": round(avg_last_5, 1),
            "avg_all_time": round(avg_all_time, 1),
            "total_sessions": len(sessions),
            "total_tasks": total_tasks,
            "best_score": round(best_score, 1),
            "sessions": sessions[-10:]  # Last 10 sessions for table
        }

    def _calculate_health(self) -> str:
        """Calculate system health indicator"""
        if len(self.errors) == 0:
            return "🟢 HEALTHY"
        
        # Check recent error rate (last 5 minutes)
        from datetime import timedelta
        cutoff_time = datetime.now() - timedelta(minutes=5)
        recent_errors = [e for e in self.errors[-10:] 
                        if datetime.fromisoformat(e['time']) > cutoff_time]
        
        if len(recent_errors) >= 5:
            return "🔴 CRITICAL"
        elif len(recent_errors) >= 2:
            return "🟡 WARNING"
        else:
            return "🟢 HEALTHY"
    
    # === Event Logging ===
    
    def log_event(self, event_type: str, details: Dict[str, Any]):
        """Log a general event"""
        event = {
            "time": datetime.now().isoformat(),
            "type": event_type,
            "details": details
        }
        self.events.append(event)
        self._save_log()
        self._save_status()
    
    def log_task_start(self, task: str, session_id: str):
        """Log task start"""
        self.current_status = f"processing: {task[:30]}..."
        self.log_event("task_start", {
            "session_id": session_id,
            "task": task[:100]
        })
    
    def log_task_complete(self, session_id: str, score: int, duration: float, 
                          verified: bool, skipped_refine: bool):
        """Log task completion with metrics"""
        self.current_status = "idle"
        self.log_event("task_complete", {
            "session_id": session_id,
            "score": score,
            "duration": duration,
            "verified": verified,
            "skipped_refine": skipped_refine
        })
        
        # Update metrics
        self.metrics["scores"].append(score)
        self.metrics["durations"].append(duration)
        self.metrics["verified_count"].append(1 if verified else 0)
        self.metrics["skip_count"].append(1 if skipped_refine else 0)
        
        # Update history
        self._save_history_snapshot()
    
    def log_worker_result(self, worker_id: int, verified: bool, attempts: int, 
                          duration: float, slot_id: int = -1):
        """Log individual worker result"""
        self.log_event("worker_result", {
            "worker_id": worker_id,
            "verified": verified,
            "attempts": attempts,
            "duration": duration,
            "slot_id": slot_id
        })
    
    def log_skill_harvested(self, skill_name: str, from_worker: int):
        """Log skill harvesting"""
        self.log_event("skill_harvested", {
            "skill_name": skill_name,
            "from_worker": from_worker
        })
    
    def log_reflection_added(self, iteration: int, error_type: str):
        """Log reflexion buffer addition"""
        self.log_event("reflection_added", {
            "iteration": iteration,
            "error_type": error_type
        })
    
    def log_pruning(self, candidates: int, survivors: int, best_score: int):
        """Log ToT pruning action"""
        self.log_event("tot_pruning", {
            "candidates": candidates,
            "survivors": survivors,
            "best_score": best_score
        })
    
    # === Error Logging ===
    
    def log_error(self, error_type: str, message: str, context: Dict = None):
        """Log an error"""
        error = {
            "time": datetime.now().isoformat(),
            "type": error_type,
            "message": message[:200],
            "context": context or {}
        }
        self.errors.append(error)
        self.current_status = f"error: {error_type}"
        self._save_log()
        self._save_status()
    
    # === Metrics Retrieval ===
    
    def get_summary(self) -> Dict:
        """Get summary of monitoring data for agent review"""
        scores = self.metrics.get("scores", [])
        durations = self.metrics.get("durations", [])
        
        return {
            "uptime": str(datetime.now() - self.session_start),
            "tasks_completed": len(scores),
            "errors_count": len(self.errors),
            "health": self._calculate_health(),
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "verification_rate": sum(self.metrics.get("verified_count", [])) / len(scores) * 100 if scores else 0,
            "skip_rate": sum(self.metrics.get("skip_count", [])) / len(scores) * 100 if scores else 0,
            "last_error": self.errors[-1] if self.errors else None
        }
    
    def get_status_line(self) -> str:
        """Get one-line status for quick check"""
        summary = self.get_summary()
        return (f"{summary['health']} | "
                f"Tasks: {summary['tasks_completed']} | "
                f"Avg Score: {summary['avg_score']:.1f}/25 | "
                f"Verify: {summary['verification_rate']:.0f}% | "
                f"Errors: {summary['errors_count']}")


# Global instance
_logger = None


def get_monitoring_logger() -> MonitoringLogger:
    """Get or create global monitoring logger"""
    global _logger
    if _logger is None:
        _logger = MonitoringLogger()
    return _logger


# Quick test
if __name__ == "__main__":
    logger = MonitoringLogger()
    
    # Simulate some events
    logger.log_task_start("Test email validation", "test_001")
    logger.log_worker_result(0, True, 1, 45.2, 0)
    logger.log_worker_result(1, False, 3, 52.1, 1)
    logger.log_pruning(3, 1, 18)
    logger.log_task_complete("test_001", 18, 120.5, True, True)
    
    print("\n=== Monitoring Logger Test ===\n")
    print(f"Status: {logger.get_status_line()}")
    print(f"\nSummary: {json.dumps(logger.get_summary(), indent=2)}")
