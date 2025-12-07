import sys
import io
import contextlib
import traceback
from typing import Dict, Any

class CodeExecutor:
    """
    Executes Python code in a controlled environment.
    Captures stdout/stderr and handles exceptions.
    """
    
    def __init__(self, globals_dict: Dict = None, locals_dict: Dict = None):
        self.globals = globals_dict if globals_dict is not None else {}
        self.locals = locals_dict if locals_dict is not None else {}
        
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Execute code and return result/output.
        """
        # Create string buffers for stdout/stderr
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        
        status = "success"
        error_msg = None
        
        try:
            # Redirect stdout/stderr
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                # Execute the code
                exec(code, self.globals, self.locals)
                
        except Exception:
            status = "error"
            # Get the full traceback
            error_msg = traceback.format_exc()
            
        # Get output
        stdout_content = stdout_buffer.getvalue()
        stderr_content = stderr_buffer.getvalue()
        
        # Combine output
        full_output = stdout_content
        if stderr_content:
            full_output += "\n--- STDERR ---\n" + stderr_content
            
        return {
            "status": status,
            "output": full_output,
            "error": error_msg
        }
