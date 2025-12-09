# Test Patterns Module - Learnable test case patterns
# Similar to SkillHarvester but for test patterns

import os
import json
from typing import List, Dict, Optional
from datetime import datetime

# Storage location
TEST_PATTERNS_DIR = "data/test_patterns"
PATTERNS_INDEX = "data/test_patterns/index.json"


class TestPatternLearner:
    """
    Learns and stores successful test case patterns.
    
    When a task completes with verified=True:
    1. Extract the test case structure used
    2. Categorize by task type
    3. Store for future use
    
    When generating new tasks:
    1. Lookup patterns for task category
    2. Suggest diverse test cases based on learned patterns
    """
    
    # Edge case patterns to always suggest
    EDGE_CASE_TEMPLATES = [
        {"type": "empty_string", "pattern": "solve('') -> {expected}", "description": "Empty input"},
        {"type": "empty_list", "pattern": "solve([]) -> {expected}", "description": "Empty list"},
        {"type": "zero", "pattern": "solve(0) -> {expected}", "description": "Zero input"},
        {"type": "negative", "pattern": "solve(-1) -> {expected}", "description": "Negative number"},
        {"type": "large", "pattern": "solve(999999) -> {expected}", "description": "Large number"},
        {"type": "unicode", "pattern": "solve('café') -> {expected}", "description": "Unicode chars"},
        {"type": "whitespace", "pattern": "solve('  ') -> {expected}", "description": "Whitespace only"},
        {"type": "special_chars", "pattern": "solve('@#$%') -> {expected}", "description": "Special chars"},
    ]
    
    def __init__(self):
        self._ensure_dirs()
        self.index = self._load_index()
    
    def _ensure_dirs(self):
        """Create directory structure"""
        os.makedirs(TEST_PATTERNS_DIR, exist_ok=True)
        if not os.path.exists(PATTERNS_INDEX):
            with open(PATTERNS_INDEX, 'w') as f:
                json.dump({
                    "patterns": [],
                    "categories": {},
                    "last_updated": None
                }, f)
    
    def _load_index(self) -> Dict:
        """Load patterns index"""
        try:
            with open(PATTERNS_INDEX, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"patterns": [], "categories": {}, "last_updated": None}
    
    def _save_index(self):
        """Save patterns index"""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(PATTERNS_INDEX, 'w', encoding='utf-8') as f:
            json.dump(self.index, f, indent=2, ensure_ascii=False)
    
    def learn_from_success(self, task: str, test_cases: List[Dict], 
                           category: str = None) -> Dict:
        """
        Learn patterns from a successful task completion.
        
        Args:
            task: The task description
            test_cases: List of {input, expected} that worked
            category: Optional category (auto-detected if not provided)
        
        Returns:
            Dict with learning stats
        """
        if not test_cases:
            return {"learned": 0}
        
        # Auto-detect category from task
        if not category:
            category = self._detect_category(task)
        
        learned = 0
        for tc in test_cases:
            input_val = tc.get("input")
            expected = tc.get("expected")
            
            # Determine input type
            input_type = self._get_type_name(input_val)
            output_type = self._get_type_name(expected)
            
            # Create pattern entry
            pattern = {
                "category": category,
                "input_type": input_type,
                "output_type": output_type,
                "example_input": str(input_val)[:50],
                "example_output": str(expected)[:50],
                "task_hint": task[:100],
                "learned_at": datetime.now().isoformat(),
                "use_count": 0
            }
            
            # Check for duplicate
            if not self._pattern_exists(pattern):
                self.index["patterns"].append(pattern)
                learned += 1
                
                # Update category stats
                if category not in self.index["categories"]:
                    self.index["categories"][category] = {"count": 0, "input_types": []}
                self.index["categories"][category]["count"] += 1
                if input_type not in self.index["categories"][category]["input_types"]:
                    self.index["categories"][category]["input_types"].append(input_type)
        
        if learned > 0:
            self._save_index()
            print(f"  📝 Learned {learned} test patterns for '{category}'")
        
        return {"learned": learned, "category": category}
    
    def _pattern_exists(self, new_pattern: Dict) -> bool:
        """Check if similar pattern already exists"""
        for p in self.index["patterns"]:
            if (p["category"] == new_pattern["category"] and
                p["input_type"] == new_pattern["input_type"] and
                p["output_type"] == new_pattern["output_type"]):
                return True
        return False
    
    def _get_type_name(self, value) -> str:
        """Get a descriptive type name for a value"""
        if value is None:
            return "none"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            if value < 0:
                return "negative_int"
            if value == 0:
                return "zero"
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            if not value:
                return "empty_string"
            if value.isspace():
                return "whitespace"
            return "string"
        if isinstance(value, list):
            if not value:
                return "empty_list"
            return "list"
        if isinstance(value, dict):
            return "dict"
        if isinstance(value, tuple):
            return "tuple"
        return "unknown"
    
    def _detect_category(self, task: str) -> str:
        """Detect task category from description"""
        task_lower = task.lower()
        
        if any(w in task_lower for w in ["email", "url", "phone", "valid"]):
            return "validation"
        if any(w in task_lower for w in ["string", "reverse", "palindrome", "vowel"]):
            return "string_manipulation"
        if any(w in task_lower for w in ["prime", "fibonacci", "factorial", "sum", "math"]):
            return "math"
        if any(w in task_lower for w in ["list", "array", "sort", "duplicate", "merge"]):
            return "list_operations"
        if any(w in task_lower for w in ["dict", "frequency", "group", "key"]):
            return "dict_operations"
        if any(w in task_lower for w in ["parse", "date", "json", "extract"]):
            return "parsing"
        
        return "general"
    
    def get_patterns_for_category(self, category: str, n: int = 5) -> List[Dict]:
        """Get learned patterns for a category"""
        patterns = [p for p in self.index["patterns"] if p["category"] == category]
        
        # Sort by use_count (most used first)
        patterns.sort(key=lambda p: p.get("use_count", 0), reverse=True)
        
        return patterns[:n]
    
    def suggest_test_patterns(self, task: str, existing_cases: int = 0) -> List[str]:
        """
        Suggest test case patterns for a task.
        
        Returns list of pattern strings like:
        "- solve('example') -> expected_output"
        """
        category = self._detect_category(task)
        suggestions = []
        
        # Get learned patterns for this category
        learned = self.get_patterns_for_category(category, n=3)
        for p in learned:
            suggestions.append(
                f"- solve({p['example_input']}) -> {p['example_output']}  # {p['input_type']}"
            )
            p["use_count"] = p.get("use_count", 0) + 1
        
        # Add edge cases if we don't have many
        if len(suggestions) < 3:
            for edge in self.EDGE_CASE_TEMPLATES[:3 - len(suggestions)]:
                suggestions.append(f"- {edge['pattern']}  # {edge['description']}")
        
        # Save use counts
        if learned:
            self._save_index()
        
        return suggestions
    
    def get_stats(self) -> Dict:
        """Get pattern learning statistics"""
        return {
            "total_patterns": len(self.index["patterns"]),
            "categories": list(self.index["categories"].keys()),
            "last_updated": self.index.get("last_updated")
        }


# Global instance
_test_patterns: Optional[TestPatternLearner] = None


def get_test_patterns() -> TestPatternLearner:
    """Get or create global test pattern learner"""
    global _test_patterns
    if _test_patterns is None:
        _test_patterns = TestPatternLearner()
    return _test_patterns


# Quick test
if __name__ == "__main__":
    learner = TestPatternLearner()
    
    # Simulate learning from a successful task
    test_cases = [
        {"input": "test@example.com", "expected": True},
        {"input": "invalid", "expected": False},
        {"input": "", "expected": False},
    ]
    result = learner.learn_from_success(
        task="Validate email addresses",
        test_cases=test_cases
    )
    print(f"Learning result: {result}")
    
    # Get suggestions for new task
    suggestions = learner.suggest_test_patterns("Check if email is valid")
    print(f"\nSuggestions for email validation:")
    for s in suggestions:
        print(f"  {s}")
    
    print(f"\nStats: {learner.get_stats()}")
