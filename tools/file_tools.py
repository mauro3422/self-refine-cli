# File operation tools
import os
from typing import Dict, Any
from tools.base import Tool
from config.settings import AGENT_WORKSPACE

# Ensure sandbox exists
if not os.path.exists(AGENT_WORKSPACE):
    os.makedirs(AGENT_WORKSPACE)

def _is_safe_path(path: str) -> bool:
    """
    SECURITY: Checks if path is within the sandbox directory.
    Prevents path traversal attacks (e.g., ../../windows).
    """
    try:
        # Get absolute path of sandbox
        sandbox_abs = os.path.abspath(AGENT_WORKSPACE)
        
        # Get absolute path of requested file
        requested_abs = os.path.abspath(path)
        
        # Check if requested path starts with sandbox path
        return requested_abs.startswith(sandbox_abs)
    except Exception:
        return False

class ReadFileTool(Tool):
    """Tool to read file contents"""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Reads the contents of a file. Restricted to 'sandbox/' directory."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Path to the file to read (must be inside sandbox)"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            # SECURITY CHECK
            if not _is_safe_path(path):
                return {"success": False, "error": f"SECURITY ERROR: Access denied to '{path}'. You can only access files inside '{AGENT_WORKSPACE}/'."}
                
            if not os.path.exists(path):
                # NEW: Smart suggestions when file not found
                dir_path = os.path.dirname(path) or "."
                filename = os.path.basename(path)
                
                suggestions = []
                
                # Check if directory exists
                if os.path.exists(dir_path) and os.path.isdir(dir_path):
                    # Find similar files in the directory
                    try:
                        existing_files = os.listdir(dir_path)
                        # Simple similarity: files with same extension or similar name
                        ext = os.path.splitext(filename)[1]
                        similar = [f for f in existing_files if f.endswith(ext) or filename.lower() in f.lower()][:5]
                        if similar:
                            suggestions.append(f"Similar files in {dir_path}: {', '.join(similar)}")
                    except:
                        pass
                    suggestions.append(f"TIP: Use list_dir('{dir_path}') to see available files")
                else:
                    suggestions.append(f"Directory '{dir_path}' does not exist. Use list_dir('.') to explore")
                
                suggestion_text = ". ".join(suggestions) if suggestions else ""
                
                return {
                    "success": False, 
                    "error": f"File not found: {path}. {suggestion_text}"
                }
            
            if not os.path.isfile(path):
                return {"success": False, "error": f"Not a file: {path}"}
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "result": content,
                "path": path,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class WriteFileTool(Tool):
    """Tool to write content to a file"""
    
    @property
    def name(self) -> str:
        return "write_file"
    
    @property
    def description(self) -> str:
        return "Writes content to a file. PREFERRED for creating new files. Restricted to 'sandbox/' directory."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Path to the file to write (must be inside sandbox)"
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file"
            }
        }
    
    def execute(self, path: str, content: str) -> Dict[str, Any]:
        # Retry logic for Windows file locking
        max_retries = 3
        import time
        
        # SECURITY CHECK
        if not _is_safe_path(path):
            return {"success": False, "error": f"SECURITY ERROR: Write denied to '{path}'. You can only write to files inside '{AGENT_WORKSPACE}/'."}
        
        for attempt in range(max_retries):
            try:
                # Create directory if needed
                dir_path = os.path.dirname(path)
                if dir_path and not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()  # Flush buffer to OS
                    os.fsync(f.fileno())  # Force write to disk
                
                return {
                    "success": True,
                    "result": f"File written: {path}",
                    "path": path,
                    "bytes_written": len(content)
                }
            except (PermissionError, OSError) as e:
                # If locking error and checks remain, wait and retry
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                return {"success": False, "error": f"Failed after {max_retries} attempts: {str(e)}"}
            except Exception as e:
                return {"success": False, "error": str(e)}


class ListDirectoryTool(Tool):
    """Tool to list directory contents"""
    
    @property
    def name(self) -> str:
        return "list_dir"
    
    @property
    def description(self) -> str:
        return "Lists the contents of a directory. Restricted to 'sandbox/'."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Path to the directory to list (must be inside sandbox)"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            # SECURITY CHECK
            if not _is_safe_path(path):
                return {"success": False, "error": f"SECURITY ERROR: Access denied to '{path}'. You can only List files inside '{AGENT_WORKSPACE}/'."}
            
            if not os.path.exists(path):
                return {"success": False, "error": f"Directory not found: {path}"}
            
            if not os.path.isdir(path):
                return {"success": False, "error": f"Not a directory: {path}"}
            
            entries = []
            for entry in os.listdir(path):
                full_path = os.path.join(path, entry)
                entry_type = "dir" if os.path.isdir(full_path) else "file"
                size = os.path.getsize(full_path) if entry_type == "file" else None
                entries.append({
                    "name": entry,
                    "type": entry_type,
                    "size": size
                })
            
            return {
                "success": True,
                "result": entries,
                "path": path,
                "count": len(entries)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Register tools
def register_file_tools():
    """Register all file tools"""
    from tools.registry import get_registry
    registry = get_registry()
    registry.register(ReadFileTool())
    registry.register(WriteFileTool())
    registry.register(ListDirectoryTool())
