# Ejecuta código generado y captura output - Self-Refine Architecture

import io
import traceback
import signal
import threading
from typing import Dict, List, Optional, Any
from contextlib import redirect_stdout, redirect_stderr
from config.settings import EXECUTION_TIMEOUT


class TimeoutException(Exception):
    """Exception raised when code execution times out"""
    pass


class CodeExecutor:
    def __init__(self):
        self.globals_dict = {"__builtins__": __builtins__}
        self.timeout = EXECUTION_TIMEOUT
    
    def _execute_with_timeout(self, code: str, result: Dict) -> None:
        """Execute code in thread with result capture"""
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, self.globals_dict)
            
            result["status"] = "success"
            result["output"] = stdout_capture.getvalue()
            result["stderr"] = stderr_capture.getvalue()
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    
    def execute(self, code: str) -> Dict[str, str]:
        """
        Ejecuta código Python con timeout y captura resultado
        Returns: {status, output, error}
        """
        result = {
            "status": "timeout",
            "output": "",
            "error": "",
            "stderr": ""
        }
        
        # Run in thread with timeout
        thread = threading.Thread(target=self._execute_with_timeout, args=(code, result))
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            result["status"] = "timeout"
            result["error"] = f"Ejecución excedió {self.timeout} segundos - posible loop infinito"
        
        return result
    
    def execute_safe(self, code: str) -> Dict[str, str]:
        """
        Ejecuta código con restricciones de seguridad adicionales
        Bloquea: open(), exec(), eval(), __import__(), etc.
        """
        # Restricted builtins for sandboxing
        safe_builtins = {
            'print': print,
            'len': len,
            'range': range,
            'int': int,
            'float': float,
            'str': str,
            'list': list,
            'dict': dict,
            'tuple': tuple,
            'set': set,
            'bool': bool,
            'abs': abs,
            'min': min,
            'max': max,
            'sum': sum,
            'sorted': sorted,
            'reversed': reversed,
            'enumerate': enumerate,
            'zip': zip,
            'map': map,
            'filter': filter,
            'any': any,
            'all': all,
            'isinstance': isinstance,
            'type': type,
            'round': round,
            'pow': pow,
            'divmod': divmod,
            'input': lambda *args: "mock_input",  # Mock input
            'True': True,
            'False': False,
            'None': None,
        }
        
        # Use safe globals
        old_globals = self.globals_dict
        self.globals_dict = {"__builtins__": safe_builtins}
        
        result = self.execute(code)
        
        # Restore globals
        self.globals_dict = old_globals
        
        return result
    
    def test_code(self, code: str, test_cases: Optional[List[str]] = None) -> Dict:
        """Ejecuta código y casos de test"""
        exec_result = self.execute(code)
        
        if exec_result["status"] == "error":
            return exec_result
        
        if test_cases:
            test_results = []
            for test in test_cases:
                test_exec = self.execute(test)
                test_results.append(test_exec)
            exec_result["test_results"] = test_results
        
        return exec_result
    
    def format_result(self, result: Dict) -> str:
        """Formatea resultado de ejecución para feedback"""
        if result["status"] == "success":
            output = result.get("output", "").strip()
            if output:
                return f"✓ Ejecutado exitosamente\nOutput:\n{output}"
            else:
                return "✓ Ejecutado exitosamente (sin output)"
        elif result["status"] == "timeout":
            return f"⏱️ Timeout: {result.get('error', 'Ejecución excedió tiempo límite')}"
        else:
            return f"✗ Error:\n{result.get('error', 'Error desconocido')}"
