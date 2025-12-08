# core/poetiq/executor.py
# Tool execution with validation and tracking

from typing import Dict
from tools.registry import get_registry


class ToolExecutor:
    """Executes tools from winning response with granular tracking"""
    
    # Required params for each tool 
    REQUIRED_PARAMS = {
        "read_file": ["path"],
        "write_file": ["path", "content"],
        "python_exec": ["code"],
        "search_files": ["pattern"],
        "replace_in_file": ["path", "old_text", "new_text"],
        "run_command": ["command"],
    }
    
    def __init__(self, working_memory=None):
        self.registry = get_registry()
        self.tools_used = []
        self.tool_results = []  # Track individual results
        self.working_memory = working_memory
    
    def _validate_params(self, tool_name: str, params: Dict) -> str:
        """Validate required params are present. Returns error message or empty string."""
        required = self.REQUIRED_PARAMS.get(tool_name, [])
        missing = [p for p in required if p not in params or not params[p]]
        if missing:
            return f"Missing required param(s): {', '.join(missing)}"
        return ""
    
    def execute(self, tool_call: Dict) -> str:
        if not tool_call:
            return ""
        
        tool_name = tool_call.get("tool", "")
        params = tool_call.get("params", {})
        
        # Validate params before execution
        validation_error = self._validate_params(tool_name, params)
        if validation_error:
            print(f"    ⚠️ {tool_name}: {validation_error}")
            self.tool_results.append({
                "tool": tool_name,
                "success": False,
                "error": validation_error
            })
            return f"[ERROR] {tool_name}: {validation_error}"
        
        self.tools_used.append(tool_name)
        result = self.registry.execute_tool(tool_name, **params)
        
        # Track granular result
        self.tool_results.append({
            "tool": tool_name,
            "success": result.get("success", False),
            "error": result.get("error") if not result.get("success") else None
        })
        
        # Re-index if we created/modified files
        if result.get("success") and tool_name == "write_file" and self.working_memory:
            file_path = params.get("path", "")
            if file_path:
                try:
                    self.working_memory._index_file(file_path, file_path)
                    print(f"    📂 Indexed: {file_path}")
                except Exception as e:
                    pass  # Non-critical
        
        if result.get("success"):
            return f"[OK] {tool_name}: {result.get('result', '')}"
        else:
            return f"[ERROR] {tool_name}: {result.get('error', 'Unknown')}"
    
    def get_success_rate(self) -> float:
        """Calculate overall tool success rate"""
        if not self.tool_results:
            return 0.0
        successes = sum(1 for r in self.tool_results if r["success"])
        return successes / len(self.tool_results)
    
    def had_any_failure(self) -> bool:
        """Check if any tool failed"""
        return any(not r["success"] for r in self.tool_results)
