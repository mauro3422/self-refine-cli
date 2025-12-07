# Working Memory - Project-specific temporary memory
# Indexes current workspace files and keeps temporary context

import os
import glob
from typing import List, Dict, Optional
from memory.vector_store import get_vector_memory, CHROMA_AVAILABLE
try:
    import chromadb
except ImportError:
    pass

class WorkingMemory:
    """
    Temporary memory for the current active project.
    Indexes codebase files and keeps short-term notes.
    """
    
    ACCEPTED_EXTENSIONS = {'.py', '.md', '.txt', '.json', '.js', '.html', '.css', '.sh', '.bat', '.ps1'}
    
    def __init__(self, project_name: str = "current_project"):
        self.project_name = project_name
        self.collection = None
        self.indexed_files = set()
        
        if CHROMA_AVAILABLE:
            self._init_collection()
            
    def _init_collection(self):
        """Initialize a temporary collection for this project"""
        try:
            # We access the client from the main vector memory to share the connection
            main_vec = get_vector_memory()
            if main_vec.client:
                # Create specific collection for this project
                # If it exists, we might want to reset it or keep it
                # For now, let's keep it but provide a method to clear
                self.collection = main_vec.client.get_or_create_collection(
                    name=f"project_{self.project_name}",
                    metadata={"description": "Temporary project memory"}
                )
        except Exception as e:
            print(f"⚠️ WorkingMemory init failed: {e}")
            
    def index_workspace(self, workspace_path: str):
        """
        Scan and index all relevant files in the workspace.
        This allows the agent to 'know' the code structure.
        """
        if not self.collection:
            return
            
        print(f"📂 Indexing workspace: {workspace_path}...")
        count = 0
        
        for root, _, files in os.walk(workspace_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.ACCEPTED_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, workspace_path)
                    
                    try:
                        self._index_file(full_path, rel_path)
                        count += 1
                    except Exception as e:
                        print(f"  ❌ Failed to index {rel_path}: {e}")
                        
        print(f"✅ Indexed {count} project files.")
    
    def _index_file(self, full_path: str, rel_path: str):
        """Read and vectorise a single file"""
        # Skip if already indexed (MVP logic, could be improved with timestamps)
        if rel_path in self.indexed_files:
            return

        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        if not content.strip():
            return
            
        # Chunking strategy could be added here.
        # For now, we store the full file content if reasonably small,
        # or just the beginning/summary if huge. 
        # DeepSeek-OCR style would be "visual", here we use "semantic text".
        
        # Limit content size for embedding (model dependent, usually 8k tokens approx)
        # Taking first 6000 chars as a heuristic safe limit for embedding context
        truncated_content = content[:6000] 
        
        self.collection.add(
            documents=[truncated_content],
            ids=[f"file_{rel_path}"],
            metadatas=[{
                "type": "file_content", 
                "path": rel_path,
                "timestamp": str(os.path.getmtime(full_path))
            }]
        )
        self.indexed_files.add(rel_path)

    def search_project(self, query: str, n: int = 3) -> List[Dict]:
        """Search specifically in project files"""
        if not self.collection:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n
            )
            
            hits = []
            if results and results['documents']:
                for i, doc in enumerate(results['documents'][0]):
                    meta = results['metadatas'][0][i]
                    hits.append({
                        "content": doc,
                        "path": meta.get("path", "unknown"),
                        "score": results['distances'][0][i] if 'distances' in results else 0
                    })
            return hits
        except Exception as e:
            print(f"⚠️ WorkingMemory search failed: {e}")
            return []

    def clear(self):
        """Clear the project memory (e.g., when switching projects)"""
        if self.collection:
            # Re-creating is often easier than deleting all items
            try:
                # Note: Chroma deletion semantics vary by version. 
                # Deleting collection and recreating is safest.
                main_vec = get_vector_memory()
                main_vec.client.delete_collection(f"project_{self.project_name}")
                self._init_collection()
                self.indexed_files.clear()
                print("🧹 Project memory cleared")
            except Exception as e:
                print(f"⚠️ Failed to clear project memory: {e}")

    def get_file_count(self) -> int:
        """Get number of indexed files from the DB (cross-process safe)"""
        if self.collection:
            return self.collection.count()
        return 0

import threading

# Global instance
_working_memory: Optional[WorkingMemory] = None
_wm_lock = threading.Lock()

def get_working_memory() -> WorkingMemory:
    global _working_memory
    if _working_memory is None:
        with _wm_lock:
            if _working_memory is None:
                _working_memory = WorkingMemory()
    return _working_memory
