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
        return "Executes a shell/terminal command. Useful for running scripts, checking system, etc."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "command": {
                "type": "string",
                "description": "Command to execute (e.g., 'dir', 'python script.py', 'git status')"
            }
        }
    
    def execute(self, command: str) -> Dict[str, Any]:
        import shlex
        try:
            # SECURITY: Avoid shell=True preventing injection
            # Only use shell=True if pipes/redirection detected (less secure but necessary sometimes)
            use_shell = any(c in command for c in ['|', '>', '<', '&'])
            
            if use_shell:
                # Warning: complex commands still need shell
                args = command
            else:
                # Safe mode: split arguments
                args = shlex.split(command, posix=False) # posix=False for Windows paths
            
            # Run command with timeout
            result = subprocess.run(
                args,
                shell=use_shell,
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
                "result": output if output else "(no output)",
                "error": error if error else None,
                "return_code": return_code
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command exceeded timeout of {EXECUTION_TIMEOUT}s"
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
        return "Executes Python code directly. DO NOT use for creating files (use write_file). Returns the result."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "code": {
                "type": "string",
                "description": "Python code to execute"
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
