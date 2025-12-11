# Vector Memory Store with ChromaDB
# For semantic search over long-term memories

import os
from typing import List, Dict, Optional
from datetime import datetime

# ChromaDB import with fallback
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    print("⚠️ ChromaDB not installed. Run: pip install chromadb")


class VectorMemory:
    """
    Vector-based memory using ChromaDB.
    Stores memories as embeddings for semantic search.
    """
    
    def __init__(self, persist_dir: str = "data/vector_memory"):
        self.persist_dir = persist_dir
        self.collection = None
        
        if CHROMA_AVAILABLE:
            self._init_chroma()
    
    def _init_chroma(self):
        """Initialize ChromaDB with Server -> Persistent -> Ephemeral cascade"""
        try:
            # 1. Try connecting to Server (Preferred for concurrency)
            print("CONNECTING TO CHROMA SERVER (Port 8100)...")
            self.client = chromadb.HttpClient(host='localhost', port=8100)
            self.collection = self.client.get_or_create_collection(
                name="agent_memory",
                metadata={"description": "Poetiq agent long-term memory"}
            )
            # Test connection
            self.client.heartbeat()
            print("✅ Connected to ChromaDB Server")
            return
            
        except Exception as e_http:
            print(f"⚠️ Chroma Server not found ({e_http}). Trying local...")
            
            try:
                # 2. Try Persistent Client (Local file)
                os.makedirs(self.persist_dir, exist_ok=True)
                self.client = chromadb.PersistentClient(path=self.persist_dir)
                
                self.collection = self.client.get_or_create_collection(
                    name="agent_memory",
                    metadata={"description": "Poetiq agent long-term memory"}
                )
            except Exception as e_persist:
                print(f"⚠️ Chroma Persistence failed: {e_persist}")
                
                try:
                    # 3. Fallback to Ephemeral (RAM)
                    print("🔄 Falling back to Ephemeral (In-Memory) Client...")
                    print("⚠️  WARNING: Memory vectors will NOT persist between runs!")
                    self.client = chromadb.EphemeralClient()
                    self.collection = self.client.get_or_create_collection(name="agent_memory")
                except Exception as e_crit:
                    print(f"❌ Critical ChromaDB Failure: {e_crit}")
                    print("❌ Vector memory is DISABLED - semantic search will not work!")
                    self.collection = None
    
    def add(self, text: str, metadata: Dict = None) -> bool:
        """Add a memory to the vector store"""
        if not CHROMA_AVAILABLE or not self.collection:
            return False
        
        doc_id = f"mem_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Lock to prevent concurrent modification if fallback to persistent client
        import threading
        _chroma_lock = threading.Lock()
        
        with _chroma_lock:
            self.collection.add(
                documents=[text],
                ids=[doc_id],
                metadatas=[metadata or {"type": "lesson"}]
            )
        return True
    
    def search(self, query: str, n_results: int = 5) -> List[str]:
        """Search for relevant memories"""
        if not CHROMA_AVAILABLE or not self.collection:
            return []
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            return results.get("documents", [[]])[0]
        except:
            return []
    
    def get_context(self, query: str) -> str:
        """Get relevant context for a query"""
        memories = self.search(query, n_results=3)
        
        if not memories:
            return ""
        
        return "RELEVANT MEMORIES:\n" + "\n".join(f"- {m}" for m in memories)
    
    def stats(self) -> Dict:
        """Get memory statistics"""
        if not CHROMA_AVAILABLE or not self.collection:
            return {"available": False, "count": 0}
        
        return {
            "available": True,
            "count": self.collection.count()
        }
    
    def close(self):
        """Cleanup ChromaDB client"""
        try:
            if hasattr(self, 'client') and self.client:
                # Some clients might not have close(), check first
                if hasattr(self.client, 'close'):
                    self.client.close()
        except:
            pass
            
    def __del__(self):
        self.close()


import threading

# Global instance and lock
_vector_memory: Optional[VectorMemory] = None
_vm_lock = threading.Lock()

def get_vector_memory() -> VectorMemory:
    global _vector_memory
    if _vector_memory is None:
        with _vm_lock:
            # Double check inside lock
            if _vector_memory is None:
                _vector_memory = VectorMemory()
    return _vector_memory
