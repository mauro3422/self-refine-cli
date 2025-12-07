# Code analysis tools using AST
import ast
import os
from typing import Dict, Any, List
from tools.base import Tool


class CodeStructureTool(Tool):
    """Tool to analyze Python code structure (classes, methods, functions)"""
    
    @property
    def name(self) -> str:
        return "analyze_code_structure"
    
    @property
    def description(self) -> str:
        return "Analiza la estructura de un archivo Python (AST). Lista clases, métodos y funciones con sus argumentos y docstrings. Útil para entender código desconocido."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al archivo Python a analizar"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"Archivo no encontrado: {path}"}
            
            if not path.endswith('.py'):
                return {"success": False, "error": "Solo se pueden analizar archivos .py"}
            
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            tree = ast.parse(code)
            structure = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    methods = []
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            args = [arg.arg for arg in child.args.args]
                            methods.append({
                                "name": child.name,
                                "args": args,
                                "line": child.lineno,
                                "docstring": ast.get_docstring(child) or ""
                            })
                    
                    structure.append({
                        "type": "class",
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "docstring": ast.get_docstring(node) or ""
                    })
                    
                elif isinstance(node, ast.FunctionDef):
                    args = [arg.arg for arg in node.args.args]
                    structure.append({
                        "type": "function",
                        "name": node.name,
                        "args": args,
                        "line": node.lineno,
                        "docstring": ast.get_docstring(node) or ""
                    })
            
            return {
                "success": True,
                "path": path,
                "structure": structure,
                "summary": f"Found {len(structure)} top-level items"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Error parsing AST: {str(e)}"}


def register_code_tools():
    """Register code tools"""
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(CodeStructureTool())
