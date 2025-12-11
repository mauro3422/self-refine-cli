# Dynamic Skills Module (DreamCoder-inspired)
# Extracts verified functions and saves them as reusable tools

import re
import os
import ast
import json
from typing import List, Dict, Optional
from datetime import datetime

# Where to store learned skills
SKILLS_DIR = "data/skills"
SKILLS_INDEX = "data/skills/index.json"


class DynamicSkillHarvester:
    """
    Extracts verified code functions and saves them as reusable skills.
    
    DreamCoder-inspired: When code works, learn from it!
    - Extracts function definitions from verified worker code
    - Saves them to skills/ directory
    - Can inject them into future prompts as available functions
    """
    
    def __init__(self):
        self._ensure_dirs()
        self.index = self._load_index()
    
    def _ensure_dirs(self):
        """Create skills directory if needed"""
        os.makedirs(SKILLS_DIR, exist_ok=True)
        if not os.path.exists(SKILLS_INDEX):
            with open(SKILLS_INDEX, 'w') as f:
                json.dump({"skills": [], "last_updated": None}, f)
    
    def _load_index(self) -> Dict:
        """Load skills index"""
        try:
            with open(SKILLS_INDEX, 'r') as f:
                return json.load(f)
        except:
            return {"skills": [], "last_updated": None}
    
    def _save_index(self):
        """Save skills index"""
        self.index["last_updated"] = datetime.now().isoformat()
        with open(SKILLS_INDEX, 'w') as f:
            json.dump(self.index, f, indent=2)
    
    def harvest_from_code(self, code: str, task_hint: str = "") -> List[Dict]:
        """
        Extract function definitions from verified code.
        Returns list of harvested skills.
        """
        if not code or len(code) < 20:
            return []
        
        harvested = []
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    skill = self._extract_function(node, code, task_hint)
                    if skill:
                        harvested.append(skill)
                        print(f"    🔧 Skill harvested: {skill['name']}")
        except SyntaxError:
            # Code might have issues, try regex fallback
            harvested = self._regex_extract(code, task_hint)
        except Exception as e:
            print(f"    ⚠️ Skill harvest error: {e}")
        
        # Save new skills
        for skill in harvested:
            self._save_skill(skill)
        
        return harvested
    
    def _extract_function(self, node: ast.FunctionDef, code: str, task_hint: str) -> Optional[Dict]:
        """Extract a function definition as a skill"""
        name = node.name
        
        # Skip private/dunder functions
        if name.startswith('_'):
            return None
        
        # Get function source
        lines = code.split('\n')
        start = node.lineno - 1
        end = node.end_lineno if hasattr(node, 'end_lineno') else start + 10
        func_code = '\n'.join(lines[start:end])
        
        # Get docstring if exists
        docstring = ast.get_docstring(node) or f"Function from task: {task_hint[:50]}"
        
        # Get parameters
        params = [arg.arg for arg in node.args.args]
        
        return {
            "name": name,
            "code": func_code,
            "docstring": docstring,
            "params": params,
            "task_hint": task_hint[:100],
            "harvested_at": datetime.now().isoformat()
        }
    
    def _regex_extract(self, code: str, task_hint: str) -> List[Dict]:
        """Fallback: extract functions via regex"""
        skills = []
        
        # Match function definitions
        pattern = r'def\s+(\w+)\s*\([^)]*\):\s*\n((?:[ \t]+[^\n]+\n?)+)'
        matches = re.finditer(pattern, code)
        
        for match in matches:
            name = match.group(1)
            if not name.startswith('_'):
                skills.append({
                    "name": name,
                    "code": match.group(0),
                    "docstring": f"Function from task: {task_hint[:50]}",
                    "params": [],
                    "task_hint": task_hint[:100],
                    "harvested_at": datetime.now().isoformat()
                })
        
        return skills
    
    def _save_skill(self, skill: Dict):
        """Save individual skill and update index"""
        # Check if skill already exists (by name)
        existing = [s for s in self.index["skills"] if s["name"] == skill["name"]]
        if existing:
            print(f"    📝 Skill '{skill['name']}' already exists, skipping")
            return
        
        # Save skill file
        filename = f"{skill['name']}.py"
        filepath = os.path.join(SKILLS_DIR, filename)
        
        with open(filepath, 'w') as f:
            f.write(f'"""{skill["docstring"]}"""\n\n')
            f.write(skill["code"])
        
        # Update index
        self.index["skills"].append({
            "name": skill["name"],
            "file": filename,
            "params": skill["params"],
            "docstring": skill["docstring"][:100],
            "harvested_at": skill["harvested_at"]
        })
        self._save_index()
    
    def get_skills_for_prompt(self, task: str, max_skills: int = 3) -> str:
        """
        Get relevant skills to inject into prompt.
        Returns formatted string with available helper functions.
        """
        if not self.index["skills"]:
            return ""
        
        # Simple relevance: match keywords in task
        task_lower = task.lower()
        relevant = []
        
        for skill in self.index["skills"]:
            name_lower = skill["name"].lower()
            doc_lower = skill["docstring"].lower()
            
            # Check if skill might be relevant
            if any(word in task_lower for word in name_lower.split('_')):
                relevant.append(skill)
            elif any(word in task_lower for word in doc_lower.split()[:5]):
                relevant.append(skill)
        
        if not relevant:
            return ""
        
        # Format for prompt
        lines = ["\n## AVAILABLE HELPER FUNCTIONS (you can use these):"]
        for skill in relevant[:max_skills]:
            lines.append(f"- `{skill['name']}({', '.join(skill['params'])})`: {skill['docstring'][:80]}")
        
        return '\n'.join(lines)
    
    def get_stats(self) -> Dict:
        """Get statistics about harvested skills"""
        return {
            "total_skills": len(self.index["skills"]),
            "skill_names": [s["name"] for s in self.index["skills"]],
            "last_updated": self.index.get("last_updated")
        }
    
    def list_skills(self) -> List[str]:
        """
        Get list of skill names with signatures for lightweight listing.
        Used in two-phase tool selection.
        
        Returns:
            List of strings like ["func_name(arg1, arg2)", ...]
        """
        result = []
        for skill in self.index.get("skills", []):
            name = skill.get("name", "unknown")
            params = skill.get("params", [])
            signature = f"{name}({', '.join(params)})"
            result.append(signature)
        return result


# Global instance
_harvester = None


def get_harvester() -> DynamicSkillHarvester:
    """Get or create global skill harvester"""
    global _harvester
    if _harvester is None:
        _harvester = DynamicSkillHarvester()
    return _harvester


# Quick test
if __name__ == "__main__":
    harvester = DynamicSkillHarvester()
    
    test_code = '''
def validate_email(email):
    """Check if email is valid format"""
    import re
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(pattern, email))

def calculate_sum(numbers):
    """Sum a list of numbers"""
    return sum(numbers)
'''
    
    skills = harvester.harvest_from_code(test_code, "email validation task")
    print(f"\nHarvested {len(skills)} skills")
    print(f"Stats: {harvester.get_stats()}")
