# Context Vectors - ICV and Function Vectors for intelligent memory
# Inspired by Representation Engineering research

from typing import Dict, List, Optional, Tuple
from memory.vector_store import get_vector_memory, CHROMA_AVAILABLE

# Predefined function vectors (keywords that define behaviors)
FUNCTION_VECTORS = {
    "file_create": {
        "keywords": ["crear", "create", "escribir", "write", "nuevo", "new", "archivo", "file"],
        "tools": ["write_file"],
        "description": "Creating or writing files"
    },
    "file_read": {
        "keywords": ["leer", "read", "ver", "mostrar", "contenido", "content", "abrir", "open"],
        "tools": ["read_file"],
        "description": "Reading file contents"
    },
    "file_list": {
        "keywords": ["listar", "list", "archivos", "files", "directorio", "directory", "carpeta", "folder"],
        "tools": ["list_dir"],
        "description": "Listing directory contents"
    },
    "code_exec": {
        "keywords": ["ejecutar", "execute", "correr", "run", "python", "código", "code", "script"],
        "tools": ["python_exec"],
        "description": "Executing code"
    },
    "analysis": {
        "keywords": ["analizar", "analyze", "revisar", "review", "debug", "error", "problema", "problem"],
        "tools": [],
        "description": "Code analysis and debugging"
    }
}


class ContextVectors:
    """
    Manages context vectors for intelligent category detection.
    Uses function vectors to determine task type before memory search.
    """
    
    def __init__(self):
        self.vectors = FUNCTION_VECTORS
        self.vector_store = get_vector_memory() if CHROMA_AVAILABLE else None
        self._init_category_embeddings()
    
    def _init_category_embeddings(self):
        """Pre-compute embeddings for each category (if ChromaDB available)"""
        if not self.vector_store or not CHROMA_AVAILABLE:
            return
        
        # Store category keywords in vector DB for semantic matching
        for category, data in self.vectors.items():
            keywords_text = " ".join(data["keywords"])
            self.vector_store.add(
                keywords_text, 
                {"type": "function_vector", "category": category}
            )
    
    def detect_category(self, query: str) -> Tuple[str, float]:
        """
        Detect the category of a query using function vectors.
        Returns (category, confidence).
        """
        query_lower = query.lower()
        scores = {}
        
        for category, data in self.vectors.items():
            # Count keyword matches
            matches = sum(1 for kw in data["keywords"] if kw in query_lower)
            if matches > 0:
                # Normalize score
                scores[category] = matches / len(data["keywords"])
        
        if not scores:
            return ("general", 0.0)
        
        # Return best match
        best = max(scores.items(), key=lambda x: x[1])
        return best
    
    def get_relevant_tools(self, query: str) -> List[str]:
        """Get tools likely needed for this query"""
        category, confidence = self.detect_category(query)
        
        if confidence < 0.1:
            return []
        
        return self.vectors.get(category, {}).get("tools", [])
    
    def get_category_context(self, category: str) -> str:
        """Get context prompt for a category"""
        data = self.vectors.get(category)
        if not data:
            return ""
        
        tools = ", ".join(data["tools"]) if data["tools"] else "none"
        return f"Task type: {data['description']}. Relevant tools: {tools}."


class InContextVector:
    """
    In-Context Vector (ICV) implementation.
    Creates compressed representations of examples for guiding responses.
    """
    
    def __init__(self):
        self.examples: Dict[str, List[str]] = {
            "file_create": [
                "Use write_file with path and content parameters",
                "Always specify full path relative to sandbox/",
            ],
            "file_read": [
                "Use read_file to get file contents",
                "Check if file exists first with list_dir",
            ],
            "file_list": [
                "Use list_dir to see directory contents",
                "Default path is sandbox/",
            ],
            "code_exec": [
                "Use python_exec to run Python code",
                "Capture output for verification",
            ]
        }
    
    def get_icv(self, category: str) -> str:
        """
        Get the In-Context Vector (compressed examples) for a category.
        Returns a concise prompt addition.
        """
        examples = self.examples.get(category, [])
        if not examples:
            return ""
        
        return "TIPS: " + ". ".join(examples)
    
    def build_context(self, query: str, context_vectors: ContextVectors) -> str:
        """
        Build full context using ICV based on detected category.
        """
        category, confidence = context_vectors.detect_category(query)
        
        parts = []
        
        # Add category context
        cat_context = context_vectors.get_category_context(category)
        if cat_context:
            parts.append(cat_context)
        
        # Add ICV examples
        icv = self.get_icv(category)
        if icv:
            parts.append(icv)
        
        return "\n".join(parts) if parts else ""


# Global instances
_context_vectors: Optional[ContextVectors] = None
_icv: Optional[InContextVector] = None

def get_context_vectors() -> ContextVectors:
    global _context_vectors
    if _context_vectors is None:
        _context_vectors = ContextVectors()
    return _context_vectors

def get_icv() -> InContextVector:
    global _icv
    if _icv is None:
        _icv = InContextVector()
    return _icv

def build_smart_context(query: str) -> str:
    """
    Convenience function: build smart context for a query.
    Combines category detection + ICV.
    """
    cv = get_context_vectors()
    icv = get_icv()
    return icv.build_context(query, cv)
