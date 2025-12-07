# Search tools
import os
from typing import Dict, Any, List
from tools.base import Tool


class SearchFilesTool(Tool):
    """Tool to search for text patterns in files"""
    
    @property
    def name(self) -> str:
        return "search_files"
    
    @property
    def description(self) -> str:
        return "Busca un texto o patrón dentro de archivos en un directorio. Útil para encontrar definiciones, TODOs, o referencias en el código."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "query": {
                "type": "string",
                "description": "Texto a buscar dentro de los archivos"
            },
            "path": {
                "type": "string",
                "description": "Directorio donde buscar (default: .)"
            },
            "extensions": {
                "type": "string",
                "description": "Extensiones separadas por coma (ej: .py,.md) para filtrar"
            }
        }
    
    def execute(self, query: str, path: str = ".", extensions: str = None) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"Path no encontrado: {path}"}
            
            # Parse extensions
            valid_exts = None
            if extensions:
                valid_exts = [e.strip() if e.strip().startswith('.') else f".{e.strip()}" 
                             for e in extensions.split(',')]
            
            matches = []
            
            # Walk directory
            for root, _, files in os.walk(path):
                # Skip .git, __pycache__, etc.
                if '.git' in root or '__pycache__' in root or '.gemini' in root:
                    continue
                    
                for file in files:
                    # Check extension
                    if valid_exts:
                        if not any(file.endswith(ext) for ext in valid_exts):
                            continue
                    
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                matches.append({
                                    "file": full_path,
                                    "line": i + 1,
                                    "content": line.strip()
                                })
                                # Limit matches per file to avoid huge output
                                if len(matches) > 50:
                                    break
                    except Exception:
                        continue # Skip unreadable files
                        
                if len(matches) > 50:
                    break
            
            return {
                "success": True,
                "result": matches[:50],  # Limit to 50 matches
                "count": len(matches),
                "truncated": len(matches) > 50
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def register_search_tools():
    """Register search tools"""
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(SearchFilesTool())
