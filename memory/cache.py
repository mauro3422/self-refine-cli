# memory/cache.py - Embedding Cache for Performance
# Caches query embeddings to avoid redundant ChromaDB calls

import hashlib
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from config.settings import OUTPUT_DIR


class EmbeddingCache:
    """
    LRU-style cache for embeddings and query results.
    Reduces repeated calls to ChromaDB for similar queries.
    """
    
    MAX_SIZE = 100  # Max cached entries
    TTL_HOURS = 24  # Cache validity
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(OUTPUT_DIR, "embedding_cache.json")
        self.cache: Dict[str, Dict] = {}
        self._load()
    
    def _hash_query(self, query: str) -> str:
        """Create a hash key for the query"""
        return hashlib.md5(query.lower().strip().encode()).hexdigest()[:16]
    
    def _load(self):
        """Load cache from disk"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache = data.get("entries", {})
                    self._cleanup_expired()
            except:
                self.cache = {}
    
    def _save(self):
        """Save cache to disk"""
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump({
                    "entries": self.cache,
                    "updated": datetime.now().isoformat()
                }, f, indent=2)
        except:
            pass
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        expired = []
        
        for key, entry in self.cache.items():
            created = datetime.fromisoformat(entry.get("created", now.isoformat()))
            if (now - created) > timedelta(hours=self.TTL_HOURS):
                expired.append(key)
        
        for key in expired:
            del self.cache[key]
        
        # Also enforce max size (LRU-style)
        if len(self.cache) > self.MAX_SIZE:
            # Sort by access time and remove oldest
            sorted_keys = sorted(
                self.cache.keys(),
                key=lambda k: self.cache[k].get("accessed", "")
            )
            for key in sorted_keys[:len(self.cache) - self.MAX_SIZE]:
                del self.cache[key]
    
    def get(self, query: str) -> Optional[List[Dict]]:
        """Get cached results for a query"""
        key = self._hash_query(query)
        
        if key in self.cache:
            entry = self.cache[key]
            # Update access time
            entry["accessed"] = datetime.now().isoformat()
            entry["hits"] = entry.get("hits", 0) + 1
            return entry.get("results")
        
        return None
    
    def set(self, query: str, results: List[Dict]):
        """Cache results for a query"""
        key = self._hash_query(query)
        
        self.cache[key] = {
            "query": query[:100],  # Store truncated query for debugging
            "results": results,
            "created": datetime.now().isoformat(),
            "accessed": datetime.now().isoformat(),
            "hits": 0
        }
        
        self._cleanup_expired()
        self._save()
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries matching pattern"""
        if pattern is None:
            self.cache = {}
        else:
            to_remove = [
                k for k, v in self.cache.items()
                if pattern.lower() in v.get("query", "").lower()
            ]
            for k in to_remove:
                del self.cache[k]
        
        self._save()
    
    def stats(self) -> Dict:
        """Get cache statistics"""
        total_hits = sum(e.get("hits", 0) for e in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.MAX_SIZE,
            "total_hits": total_hits,
            "ttl_hours": self.TTL_HOURS
        }


# Singleton instance
_cache_instance = None

def get_cache() -> EmbeddingCache:
    """Get singleton cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = EmbeddingCache()
    return _cache_instance
