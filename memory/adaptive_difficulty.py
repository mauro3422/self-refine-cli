# Adaptive Difficulty Module - Curriculum Learning for Autonomous Loop
# Tracks performance by difficulty level and category, adjusts task generation

import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict

# Storage
ADAPTIVE_DATA_FILE = "data/adaptive_learning.json"


class AdaptiveDifficultyTracker:
    """
    Tracks task performance by difficulty level and category.
    Enables curriculum learning: start easy, increase difficulty on success.
    
    Difficulty Levels (1-5):
    1. Basic: single operation, simple types
    2. Easy: 2-3 operations, basic edge cases
    3. Medium: multiple steps, various input types
    4. Hard: complex logic, many edge cases
    5. Expert: optimization needed, tricky algorithms
    """
    
    # Difficulty level definitions
    DIFFICULTY_LEVELS = {
        1: {"name": "Basic", "examples": ["reverse string", "sum list", "check even"]},
        2: {"name": "Easy", "examples": ["count vowels", "find max", "remove duplicates"]},
        3: {"name": "Medium", "examples": ["validate email", "parse date", "word frequency"]},
        4: {"name": "Hard", "examples": ["merge intervals", "balanced brackets", "LRU cache"]},
        5: {"name": "Expert", "examples": ["regex parser", "expression evaluator", "graph algorithms"]},
    }
    
    # Start at this level
    DEFAULT_DIFFICULTY = 2
    
    # Thresholds for difficulty adjustment
    UPGRADE_THRESHOLD = 0.75  # Upgrade if success rate >= 75%
    DOWNGRADE_THRESHOLD = 0.4  # Downgrade if success rate < 40%
    MIN_SAMPLES = 3  # Minimum samples before adjusting
    
    def __init__(self):
        self._ensure_file()
        self.data = self._load()
    
    def _ensure_file(self):
        """Create data file if needed"""
        os.makedirs(os.path.dirname(ADAPTIVE_DATA_FILE), exist_ok=True)
        if not os.path.exists(ADAPTIVE_DATA_FILE):
            with open(ADAPTIVE_DATA_FILE, 'w') as f:
                json.dump({
                    "current_difficulty": self.DEFAULT_DIFFICULTY,
                    "performance": {},  # {category: {level: {success, total}}}
                    "weakness_categories": [],
                    "history": [],
                    "last_updated": None
                }, f)
    
    def _load(self) -> Dict:
        """Load tracking data"""
        try:
            with open(ADAPTIVE_DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "current_difficulty": self.DEFAULT_DIFFICULTY,
                "performance": {},
                "weakness_categories": [],
                "history": [],
                "last_updated": None
            }
    
    def _save(self):
        """Save tracking data"""
        self.data["last_updated"] = datetime.now().isoformat()
        with open(ADAPTIVE_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)
    
    def record_result(self, category: str, difficulty: int, success: bool, 
                      score: int = 0, verified: bool = False) -> Dict:
        """
        Record a task result and update performance metrics.
        
        Args:
            category: Task category (string, math, list, etc.)
            difficulty: Difficulty level 1-5
            success: Whether task was completed successfully
            score: Final score (0-25)
            verified: Whether code was verified
        
        Returns:
            Dict with updated metrics and any adjustments made
        """
        # Initialize category if needed
        if category not in self.data["performance"]:
            self.data["performance"][category] = {}
        
        level_key = str(difficulty)
        if level_key not in self.data["performance"][category]:
            self.data["performance"][category][level_key] = {"success": 0, "total": 0, "scores": []}
        
        # Update metrics
        perf = self.data["performance"][category][level_key]
        perf["total"] += 1
        if success:
            perf["success"] += 1
        perf["scores"].append(score)
        perf["scores"] = perf["scores"][-20:]  # Keep last 20
        
        # Record in history
        self.data["history"].append({
            "category": category,
            "difficulty": difficulty,
            "success": success,
            "score": score,
            "verified": verified,
            "timestamp": datetime.now().isoformat()
        })
        self.data["history"] = self.data["history"][-100:]  # Keep last 100
        
        # Check for difficulty adjustment
        adjustment = self._check_adjustment(category, difficulty)
        
        # Update weakness categories
        self._update_weaknesses()
        
        self._save()
        
        return {
            "recorded": True,
            "category": category,
            "difficulty": difficulty,
            "success_rate": perf["success"] / perf["total"] if perf["total"] > 0 else 0,
            "adjustment": adjustment
        }
    
    def _check_adjustment(self, category: str, current_level: int) -> Optional[str]:
        """Check if difficulty should be adjusted based on recent performance"""
        perf = self.data["performance"].get(category, {}).get(str(current_level), {})
        total = perf.get("total", 0)
        
        if total < self.MIN_SAMPLES:
            return None
        
        success_rate = perf.get("success", 0) / total
        
        # Only adjust global difficulty, not per-category
        current_global = self.data["current_difficulty"]
        
        if success_rate >= self.UPGRADE_THRESHOLD and current_global < 5:
            self.data["current_difficulty"] = current_global + 1
            print(f"    📈 Difficulty UPGRADED: {current_global} → {current_global + 1}")
            return "upgraded"
        
        if success_rate < self.DOWNGRADE_THRESHOLD and current_global > 1:
            self.data["current_difficulty"] = current_global - 1
            print(f"    📉 Difficulty DOWNGRADED: {current_global} → {current_global - 1}")
            return "downgraded"
        
        return None
    
    def _update_weaknesses(self):
        """Identify categories with low performance"""
        weaknesses = []
        
        for category, levels in self.data["performance"].items():
            total_success = 0
            total_tasks = 0
            
            for level_data in levels.values():
                total_success += level_data.get("success", 0)
                total_tasks += level_data.get("total", 0)
            
            if total_tasks >= 3:  # Minimum samples
                success_rate = total_success / total_tasks
                if success_rate < 0.5:  # Below 50% = weakness
                    weaknesses.append({
                        "category": category,
                        "success_rate": round(success_rate, 2),
                        "total_tasks": total_tasks
                    })
        
        # Sort by success rate (worst first)
        weaknesses.sort(key=lambda x: x["success_rate"])
        self.data["weakness_categories"] = weaknesses[:5]  # Top 5 weaknesses
    
    def get_current_difficulty(self) -> int:
        """Get current difficulty level"""
        return self.data.get("current_difficulty", self.DEFAULT_DIFFICULTY)
    
    def get_weakness_categories(self) -> List[str]:
        """Get list of weak categories for targeted practice"""
        return [w["category"] for w in self.data.get("weakness_categories", [])]
    
    def get_difficulty_prompt_modifier(self) -> str:
        """Get prompt modifier based on current difficulty"""
        level = self.get_current_difficulty()
        level_info = self.DIFFICULTY_LEVELS.get(level, self.DIFFICULTY_LEVELS[2])
        
        modifiers = {
            1: "Keep it SIMPLE - one basic operation, no edge cases.",
            2: "Make it EASY - straightforward logic, test basic cases.",
            3: "MEDIUM difficulty - include some edge cases, require proper handling.",
            4: "HARD task - complex logic, multiple edge cases, require careful implementation.",
            5: "EXPERT level - tricky algorithm, optimization matters, comprehensive tests."
        }
        
        return f"Difficulty: {level_info['name']} ({level}/5). {modifiers[level]}"
    
    def should_target_weakness(self) -> Tuple[bool, Optional[str]]:
        """
        Decide if we should target a weakness category.
        Returns (should_target, category_name)
        
        Uses probability: 30% chance to target weakness if we have any
        """
        import random
        
        weaknesses = self.get_weakness_categories()
        if not weaknesses:
            return False, None
        
        # 30% chance to target a weakness
        if random.random() < 0.3:
            category = random.choice(weaknesses)
            return True, category
        
        return False, None
    
    def get_stats(self) -> Dict:
        """Get performance statistics"""
        return {
            "current_difficulty": self.get_current_difficulty(),
            "weakness_categories": self.get_weakness_categories(),
            "total_tasks": len(self.data.get("history", [])),
            "performance_by_category": {
                cat: {
                    "total": sum(l.get("total", 0) for l in levels.values()),
                    "success": sum(l.get("success", 0) for l in levels.values())
                }
                for cat, levels in self.data.get("performance", {}).items()
            }
        }


# Global instance
_tracker: Optional[AdaptiveDifficultyTracker] = None


def get_difficulty_tracker() -> AdaptiveDifficultyTracker:
    """Get or create global tracker"""
    global _tracker
    if _tracker is None:
        _tracker = AdaptiveDifficultyTracker()
    return _tracker


# Quick test
if __name__ == "__main__":
    tracker = AdaptiveDifficultyTracker()
    
    # Simulate some results
    tracker.record_result("string", 2, True, 20, True)
    tracker.record_result("string", 2, True, 22, True)
    tracker.record_result("math", 2, False, 8, False)
    tracker.record_result("math", 2, False, 10, False)
    
    print(f"Stats: {tracker.get_stats()}")
    print(f"Difficulty modifier: {tracker.get_difficulty_prompt_modifier()}")
    print(f"Should target weakness: {tracker.should_target_weakness()}")
