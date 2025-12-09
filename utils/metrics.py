# utils/metrics.py
# Comprehensive metrics tracking for True Poetiq system

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from config.settings import DATA_DIR

METRICS_FILE = os.path.join(DATA_DIR, "metrics.json")


@dataclass
class SessionMetrics:
    """Metrics for a single session/task"""
    session_id: str
    task: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Phase timings (seconds)
    parallel_time: float = 0.0
    aggregation_time: float = 0.0
    pre_score_time: float = 0.0
    refine_time: float = 0.0
    execute_time: float = 0.0
    total_time: float = 0.0
    
    # Worker stats
    workers_count: int = 3
    workers_verified: int = 0
    verification_rate: float = 0.0
    
    # Refinement stats
    skipped_refiner: bool = False
    skipped_execute: bool = False
    pre_score: int = 0
    final_score: int = 0
    score_delta: int = 0
    refine_iterations: int = 0
    
    # LLM call counts
    llm_calls_workers: int = 0
    llm_calls_aggregate: int = 0
    llm_calls_eval: int = 0
    llm_calls_refine: int = 0
    llm_calls_total: int = 0
    
    # Pattern learning
    patterns_learned: int = 0
    lessons_added: int = 0
    lessons_evolved: int = 0


class MetricsTracker:
    """Track and persist metrics across sessions"""
    
    def __init__(self):
        self.current: Optional[SessionMetrics] = None
        self.history: List[Dict] = []
        self._load()
    
    def _load(self):
        """Load metrics history from file"""
        if os.path.exists(METRICS_FILE):
            try:
                with open(METRICS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.history = data.get('sessions', [])
            except:
                self.history = []
    
    def _save(self):
        """Persist metrics to file"""
        os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
        
        # Keep only last 100 sessions
        recent = self.history[-100:]
        
        with open(METRICS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'sessions': recent,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def start_session(self, session_id: str, task: str):
        """Start tracking a new session"""
        self.current = SessionMetrics(session_id=session_id, task=task[:100])
    
    def record_parallel(self, time: float, workers_count: int, verified_count: int):
        """Record parallel phase metrics"""
        if not self.current:
            return
        self.current.parallel_time = time
        self.current.workers_count = workers_count
        self.current.workers_verified = verified_count
        self.current.verification_rate = verified_count / workers_count if workers_count > 0 else 0
        # Each worker makes ~2-6 LLM calls (generate + up to 3 refine attempts)
        self.current.llm_calls_workers = workers_count * 3  # Estimate
    
    def record_aggregation(self, time: float, llm_calls: int = 1):
        """Record aggregation phase"""
        if not self.current:
            return
        self.current.aggregation_time = time
        self.current.llm_calls_aggregate = llm_calls
    
    def record_pre_score(self, time: float, score: int):
        """Record pre-score evaluation"""
        if not self.current:
            return
        self.current.pre_score_time = time
        self.current.pre_score = score
        self.current.llm_calls_eval += 1
    
    def record_refine(self, time: float, iterations: int, final_score: int, skipped: bool):
        """Record refinement phase"""
        if not self.current:
            return
        self.current.refine_time = time
        self.current.refine_iterations = iterations
        self.current.final_score = final_score
        self.current.skipped_refiner = skipped
        self.current.score_delta = final_score - self.current.pre_score
        # 3 eval + 3 refine calls per iteration
        if not skipped:
            self.current.llm_calls_refine = iterations * 6
    
    def record_execute(self, time: float, skipped: bool):
        """Record execute phase"""
        if not self.current:
            return
        self.current.execute_time = time
        self.current.skipped_execute = skipped
    
    def record_learning(self, patterns: int, added: int, evolved: int):
        """Record learning phase"""
        if not self.current:
            return
        self.current.patterns_learned = patterns
        self.current.lessons_added = added
        self.current.lessons_evolved = evolved
    
    def end_session(self, total_time: float):
        """Finalize and save session metrics"""
        if not self.current:
            return
        
        self.current.total_time = total_time
        self.current.llm_calls_total = (
            self.current.llm_calls_workers +
            self.current.llm_calls_aggregate +
            self.current.llm_calls_eval +
            self.current.llm_calls_refine
        )
        
        # Print summary
        self._print_session_summary()
        
        # Add to history and save
        self.history.append(asdict(self.current))
        self._save()
        self.current = None
    
    def _print_session_summary(self):
        """Print a compact summary of the session"""
        m = self.current
        if not m:
            return
        
        print(f"\n📊 METRICS SUMMARY")
        print(f"  ⏱️ Time: parallel={m.parallel_time:.1f}s, refine={m.refine_time:.1f}s, total={m.total_time:.1f}s")
        print(f"  ✅ Verified: {m.workers_verified}/{m.workers_count} ({m.verification_rate:.0%})")
        print(f"  📈 Score: {m.pre_score} → {m.final_score} (Δ{m.score_delta:+d})")
        print(f"  ⚡ Skipped: refiner={'Y' if m.skipped_refiner else 'N'}, exec={'Y' if m.skipped_execute else 'N'}")
        print(f"  🧠 LLM calls: ~{m.llm_calls_total}")
    
    def get_summary(self, last_n: int = 20) -> Dict:
        """Get aggregate summary of recent sessions"""
        recent = self.history[-last_n:]
        if not recent:
            return {}
        
        total_sessions = len(recent)
        verified_sessions = sum(1 for s in recent if s.get('workers_verified', 0) > 0)
        skipped_sessions = sum(1 for s in recent if s.get('skipped_refiner', False))
        
        avg_verification = sum(s.get('verification_rate', 0) for s in recent) / total_sessions
        avg_total_time = sum(s.get('total_time', 0) for s in recent) / total_sessions
        avg_score = sum(s.get('final_score', 0) for s in recent) / total_sessions
        total_patterns = sum(s.get('patterns_learned', 0) for s in recent)
        
        return {
            'total_sessions': total_sessions,
            'verified_sessions': verified_sessions,
            'verified_rate': verified_sessions / total_sessions,
            'skip_rate': skipped_sessions / total_sessions,
            'avg_verification': avg_verification,
            'avg_total_time': avg_total_time,
            'avg_score': avg_score,
            'total_patterns': total_patterns
        }


# Singleton
_metrics: Optional[MetricsTracker] = None

def get_metrics() -> MetricsTracker:
    """Get or create metrics tracker singleton"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsTracker()
    return _metrics


def print_metrics_dashboard():
    """Print a dashboard of recent metrics"""
    metrics = get_metrics()
    summary = metrics.get_summary(20)
    
    if not summary:
        print("No metrics data yet.")
        return
    
    print("\n" + "="*50)
    print("📊 TRUE POETIQ METRICS DASHBOARD")
    print("="*50)
    print(f"Sessions analyzed: {summary['total_sessions']}")
    print(f"Verified sessions: {summary['verified_sessions']} ({summary['verified_rate']:.0%})")
    print(f"Skip rate: {summary['skip_rate']:.0%}")
    print(f"Avg verification: {summary['avg_verification']:.1%}")
    print(f"Avg total time: {summary['avg_total_time']:.1f}s")
    print(f"Avg final score: {summary['avg_score']:.1f}/25")
    print(f"Total patterns learned: {summary['total_patterns']}")
    print("="*50)
