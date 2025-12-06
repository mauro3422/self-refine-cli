# Verification Module - Execute and verify generated code

import subprocess
import tempfile
import os
from typing import Optional, Dict, Any
from config.settings import EXECUTION_TIMEOUT


class CodeVerifier:
    """Execute generated code and verify it works"""
    
    def __init__(self, workspace: str = "sandbox"):
        self.workspace = workspace
    
    def execute_code(self, code: str, timeout: int = None) -> Dict[str, Any]:
        """
        Execute Python code and capture output
        
        Returns:
            {"success": bool, "output": str, "error": str}
        """
        timeout = timeout or EXECUTION_TIMEOUT
        
        try:
            # Create temp file
            with tempfile.NamedTemporaryFile(
                mode='w', 
                suffix='.py', 
                delete=False,
                encoding='utf-8'
            ) as f:
                f.write(code)
                temp_path = f.name
            
            # Execute
            result = subprocess.run(
                ['python', temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.workspace
            )
            
            # Clean up
            os.unlink(temp_path)
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout,
                    "error": ""
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout,
                    "error": result.stderr
                }
                
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Timeout after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def execute_file(self, filepath: str, timeout: int = None) -> Dict[str, Any]:
        """Execute a Python file"""
        timeout = timeout or EXECUTION_TIMEOUT
        
        full_path = os.path.join(self.workspace, filepath) if not os.path.isabs(filepath) else filepath
        
        if not os.path.exists(full_path):
            return {
                "success": False,
                "output": "",
                "error": f"File not found: {filepath}"
            }
        
        try:
            result = subprocess.run(
                ['python', full_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else ""
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": f"Timeout after {timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }
    
    def verify_function(
        self, 
        filepath: str, 
        function_name: str, 
        test_input: Any, 
        expected_output: Any
    ) -> Dict[str, Any]:
        """
        Verify a specific function in a file
        
        Args:
            filepath: Path to the Python file
            function_name: Name of function to test
            test_input: Input to pass to function
            expected_output: Expected return value
            
        Returns:
            {"passed": bool, "actual": Any, "expected": Any, "error": str}
        """
        test_code = f"""
import sys
sys.path.insert(0, '.')
from {os.path.splitext(os.path.basename(filepath))[0]} import {function_name}

result = {function_name}({repr(test_input)})
print(repr(result))
"""
        
        exec_result = self.execute_code(test_code)
        
        if not exec_result["success"]:
            return {
                "passed": False,
                "actual": None,
                "expected": expected_output,
                "error": exec_result["error"]
            }
        
        try:
            actual = eval(exec_result["output"].strip())
            passed = actual == expected_output
            return {
                "passed": passed,
                "actual": actual,
                "expected": expected_output,
                "error": "" if passed else f"Expected {expected_output}, got {actual}"
            }
        except Exception as e:
            return {
                "passed": False,
                "actual": exec_result["output"],
                "expected": expected_output,
                "error": str(e)
            }
