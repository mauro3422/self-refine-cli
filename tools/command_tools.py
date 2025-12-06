# Command execution tools
import subprocess
import threading
from typing import Dict, Any
from tools.base import Tool
from config.settings import EXECUTION_TIMEOUT


class RunCommandTool(Tool):
    """Tool to execute shell commands"""
    
    @property
    def name(self) -> str:
        return "run_command"
    
    @property
    def description(self) -> str:
        return "Ejecuta un comando en la terminal/shell. Útil para ejecutar scripts, ver sistema, etc."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "command": {
                "type": "string",
                "description": "Comando a ejecutar (ej: 'dir', 'python script.py', 'git status')"
            }
        }
    
    def execute(self, command: str) -> Dict[str, Any]:
        try:
            # Run command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT,
                cwd="."
            )
            
            output = result.stdout
            error = result.stderr
            return_code = result.returncode
            
            return {
                "success": return_code == 0,
                "result": output if output else "(sin output)",
                "error": error if error else None,
                "return_code": return_code
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Comando excedió timeout de {EXECUTION_TIMEOUT}s"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class PythonExecTool(Tool):
    """Tool to execute Python code directly"""
    
    @property
    def name(self) -> str:
        return "python_exec"
    
    @property
    def description(self) -> str:
        return "Ejecuta código Python directamente y retorna el resultado."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "code": {
                "type": "string",
                "description": "Código Python a ejecutar"
            }
        }
    
    def execute(self, code: str) -> Dict[str, Any]:
        from core.executor import CodeExecutor
        executor = CodeExecutor()
        result = executor.execute(code)
        
        return {
            "success": result["status"] == "success",
            "result": result.get("output", ""),
            "error": result.get("error", None) if result["status"] != "success" else None
        }


# Register tools
def register_command_tools():
    """Register all command tools"""
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(RunCommandTool())
    registry.register(PythonExecTool())
