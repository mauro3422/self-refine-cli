# utils/metrics.py - Performance Metrics Tracking
# Tracks latency and performance across system components

import time
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
from functools import wraps
from contextlib import contextmanager

from config.settings import OUTPUT_DIR


class MetricsCollector:
    """
    Collects and reports performance metrics for the system.
    Tracks latency per phase, success rates, and resource usage.
    """
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(OUTPUT_DIR, "metrics.json")
        self.current_session: Dict[str, Any] = {}
        self.history: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load historical metrics"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get("history", [])[-100:]  # Keep last 100
            except:
                self.history = []
    
    def _save(self):
        """Save metrics to disk"""
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({
                    "history": self.history[-100:],
                    "updated": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    def start_session(self, task: str):
        """Start tracking a new session"""
        self.current_session = {
            "task": task[:100],
            "started": datetime.now().isoformat(),
            "phases": {},
            "total_time": 0
        }
    
    @contextmanager
    def track_phase(self, phase_name: str):
        """Context manager to track phase timing"""
        start = time.time()
        try:
            yield
        finally:
            duration = time.time() - start
            self.current_session.setdefault("phases", {})[phase_name] = {
                "duration": round(duration, 3),
                "timestamp": datetime.now().isoformat()
            }
    
    def record_metric(self, name: str, value: Any):
        """Record a custom metric for current session"""
        self.current_session.setdefault("metrics", {})[name] = value
    
    def end_session(self, success: bool = True, score: int = 0):
        """End current session and save"""
        self.current_session["ended"] = datetime.now().isoformat()
        self.current_session["success"] = success
        self.current_session["score"] = score
        
        # Calculate total time
        if "started" in self.current_session:
            start = datetime.fromisoformat(self.current_session["started"])
            end = datetime.fromisoformat(self.current_session["ended"])
            self.current_session["total_time"] = (end - start).total_seconds()
        
        self.history.append(self.current_session)
        self.current_session = {}
        self._save()
    
    def get_summary(self, last_n: int = 10) -> Dict:
        """Get summary statistics for recent sessions"""
        recent = self.history[-last_n:] if last_n else self.history
        
        if not recent:
            return {"sessions": 0}
        
        # Calculate averages
        total_times = [s.get("total_time", 0) for s in recent]
        scores = [s.get("score", 0) for s in recent]
        success_count = sum(1 for s in recent if s.get("success", False))
        
        # Phase breakdown
        phase_totals: Dict[str, List[float]] = {}
        for session in recent:
            for phase, data in session.get("phases", {}).items():
                phase_totals.setdefault(phase, []).append(data.get("duration", 0))
        
        phase_avgs = {
            phase: round(sum(times) / len(times), 2)
            for phase, times in phase_totals.items()
        }
        
        return {
            "sessions": len(recent),
            "avg_time": round(sum(total_times) / len(total_times), 2) if total_times else 0,
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "success_rate": round(success_count / len(recent) * 100, 1),
            "phase_avg_times": phase_avgs
        }
    
    def get_phase_breakdown(self) -> Dict[str, float]:
        """Get average time per phase across all sessions"""
        phase_totals: Dict[str, List[float]] = {}
        
        for session in self.history[-50:]:
            for phase, data in session.get("phases", {}).items():
                phase_totals.setdefault(phase, []).append(data.get("duration", 0))
        
        return {
            phase: round(sum(times) / len(times), 2)
            for phase, times in phase_totals.items()
        }


# Singleton instance
_metrics_instance = None

def get_metrics() -> MetricsCollector:
    """Get singleton metrics collector"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MetricsCollector()
    return _metrics_instance


# Decorator for timing functions
def timed(phase_name: str = None):
    """Decorator to time a function and record to metrics"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = phase_name or func.__name__
            metrics = get_metrics()
            
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metrics.current_session.setdefault("phases", {})[name] = {
                    "duration": round(duration, 3)
                }
        
        return wrapper
    return decorator
