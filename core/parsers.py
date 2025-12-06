# Parsers Module - Extract data from LLM responses

import re
import json
from typing import Dict, Any, Optional, List


def extract_tool_call(response: str) -> Optional[Dict[str, Any]]:
    """Extract tool call from LLM response"""
    patterns = [
        r'```tool\s*\n?(.+?)\n?```',        # ```tool
        r'```json\s*\n?(.+?)\n?```',         # ```json
        r'```\s*\n?(\{.+?\})\s*\n?```',      # ``` bare with JSON
    ]
    
    raw = None
    for pattern in patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            raw = match.group(1).strip()
            break
    
    if not raw:
        json_match = re.search(r'(\{"tool":\s*"[^"]+".+?\})', response, re.DOTALL)
        if json_match:
            raw = json_match.group(1)
    
    if not raw:
        return None
    
    def try_parse(text):
        try:
            obj = json.loads(text)
            if isinstance(obj, dict) and 'tool' in obj:
                return obj
        except:
            pass
        return None
    
    # Strategy 1: Direct parse
    result = try_parse(raw)
    if result:
        return result
    
    # Strategy 2: Clean whitespace
    cleaned = re.sub(r'\s+', ' ', raw)
    result = try_parse(cleaned)
    if result:
        return result
    
    # Strategy 3: Fix quotes
    fixed = raw.replace("'", '"')
    fixed = re.sub(r',\s*}', '}', fixed)
    result = try_parse(fixed)
    if result:
        return result
    
    # Strategy 4: Extract first JSON object
    start = raw.find('{')
    end = raw.rfind('}')
    if start >= 0 and end > start:
        json_str = re.sub(r'\s+', ' ', raw[start:end+1])
        return try_parse(json_str)
    
    return None


def extract_score(feedback: str) -> int:
    """Extract score from evaluation feedback"""
    feedback_lower = feedback.lower()
    
    # Explicit score patterns
    patterns = [
        r'TOTAL_SCORE[:\s]+(\d+)/25',
        r'TOTAL[:\s]+(\d+)/25',
        r'(\d+)/25',
    ]
    
    for p in patterns:
        match = re.search(p, feedback, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            if score <= 25:
                return score
    
    # Sum individual /5 scores
    dimension_scores = re.findall(r'(\d)/5', feedback)
    if len(dimension_scores) >= 5:
        return sum(int(s) for s in dimension_scores[:5])
    
    # Heuristic: positive indicators
    positive = ['✅', 'correct', 'excelente', 'excellent', 'passed', 'optimal']
    negative = ['❌', 'failed', 'missing', '0/25', 'score: 0']
    
    pos_count = sum(1 for p in positive if p in feedback_lower)
    neg_count = sum(1 for n in negative if n in feedback_lower)
    
    if pos_count >= 3 and neg_count == 0:
        return 23
    
    if 'optimal_response' in feedback_lower:
        return 25
    
    return 0


def extract_code_block(response: str) -> Optional[str]:
    """Extract Python code from response"""
    pattern = r'```python\s*\n?(.+?)\n?```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def detect_language(text: str) -> str:
    """Detect user's language (Spanish or English)"""
    spanish = ['hola', 'que', 'qué', 'cómo', 'como', 'para', 'lee', 'lista', 'archivo', 'crea', 'dame']
    if sum(1 for w in spanish if w in text.lower()) >= 2:
        return "es"
    return "en"


def detect_required_tools(user_input: str) -> List[str]:
    """Detect which tools should be used based on user input"""
    required = []
    lower = user_input.lower()
    
    if any(kw in lower for kw in ['lee', 'leer', 'read', 'muestra', 'mira', 'código', 'analiza']):
        required.append('read_file')
    if any(kw in lower for kw in ['lista', 'archivos', 'carpeta', 'directorio', 'folder']):
        required.append('list_dir')
    if any(kw in lower for kw in ['crea', 'crear', 'create', 'escribe', 'write', 'genera']):
        required.append('write_file')
    if any(kw in lower for kw in ['ejecuta', 'corre', 'run', 'test']):
        required.append('python_exec')
    
    return required
