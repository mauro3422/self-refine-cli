# File operation tools
import os
from typing import Dict, Any
from tools.base import Tool


class ReadFileTool(Tool):
    """Tool to read file contents"""
    
    @property
    def name(self) -> str:
        return "read_file"
    
    @property
    def description(self) -> str:
        return "Lee el contenido de un archivo. Útil para leer código, configs, docs, etc."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al archivo a leer (absoluta o relativa)"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"Archivo no encontrado: {path}"}
            
            if not os.path.isfile(path):
                return {"success": False, "error": f"No es un archivo: {path}"}
            
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
        return "Escribe contenido a un archivo. Crea el archivo si no existe."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al archivo a escribir"
            },
            "content": {
                "type": "string",
                "description": "Contenido a escribir en el archivo"
            }
        }
    
    def execute(self, path: str, content: str) -> Dict[str, Any]:
        try:
            # Create directory if needed
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "result": f"Archivo escrito: {path}",
                "path": path,
                "bytes_written": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class ListDirectoryTool(Tool):
    """Tool to list directory contents"""
    
    @property
    def name(self) -> str:
        return "list_dir"
    
    @property
    def description(self) -> str:
        return "Lista el contenido de un directorio (archivos y carpetas)."
    
    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "path": {
                "type": "string",
                "description": "Ruta al directorio a listar"
            }
        }
    
    def execute(self, path: str) -> Dict[str, Any]:
        try:
            if not os.path.exists(path):
                return {"success": False, "error": f"Directorio no encontrado: {path}"}
            
            if not os.path.isdir(path):
                return {"success": False, "error": f"No es un directorio: {path}"}
            
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
