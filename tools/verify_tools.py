# Verification tools
import sys
import io
import unittest
import ast
from typing import Dict, Any, List
from tools.base import Tool


class LinterTool(Tool):
    """Tool to check Python code syntax and basic style using AST"""
    
    @property
    def name(self) -> str:
        return "linter"
    
    @property
    def description(self) -> str:
        return "Analiza código Python en busca de errores de sintaxis y problemas estructurales básicos. Úsalo antes de ejecutar código nuevo."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al archivo .py a lintear"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # Syntax Check
            try:
                ast.parse(code)
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"SyntaxError on line {e.lineno}: {e.msg}",
                    "valid_syntax": False
                }
            
            # Basic Static Analysis
            tree = ast.parse(code)
            issues = []
            
            # Check for empty except blocks (bad practice)
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                        issues.append(f"Line {node.lineno}: Empty except block (silent failure)")
            
            return {
                "success": True,
                "valid_syntax": True,
                "issues": issues,
                "message": "Syntax OK" if not issues else f"Syntax OK but found {len(issues)} issues"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class TestRunnerTool(Tool):
    """Tool to run specific unit tests"""
    
    @property
    def name(self) -> str:
        return "run_tests"
    
    @property
    def description(self) -> str:
        return "Ejecuta un archivo de tests (unittest o pytest style) y devueve los resultados."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al archivo de tests"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        import subprocess
        try:
            # Run via subprocess to avoid polluting current process space
            # and to handle segfaults/infinite loops safely
            cmd = [sys.executable, path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Test execution timed out (30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def register_verify_tools():
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(LinterTool())
    registry.register(TestRunnerTool())
