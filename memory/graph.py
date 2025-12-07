# Memory Graph - NetworkX-based weighted graph for memory relationships
# Features: weighted edges, temporal decay, composite ranking

import networkx as nx
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import os
from config.settings import OUTPUT_DIR


class MemoryGraph:
    """
    Knowledge graph for memory relationships.
    Uses NetworkX for graph operations with weighted edges.
    """
    
    def __init__(self, path: str = None):
        self.path = path or os.path.join(OUTPUT_DIR, "memory_graph.json")
        self.graph = nx.DiGraph()  # Directed graph for relationships
        self._load()
    
    def _load(self):
        """Load graph from JSON"""
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Rebuild graph from saved data
                    for node in data.get("nodes", []):
                        self.graph.add_node(node["id"], **node.get("data", {}))
                    for edge in data.get("edges", []):
                        self.graph.add_edge(
                            edge["from"], 
                            edge["to"], 
                            weight=edge.get("weight", 0.5),
                            type=edge.get("type", "related")
                        )
            except:
                self.graph = nx.DiGraph()
    
    def _save(self):
        """Save graph to JSON"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        
        nodes = [{"id": n, "data": dict(self.graph.nodes[n])} for n in self.graph.nodes]
        edges = [
            {
                "from": u, 
                "to": v, 
                "weight": d.get("weight", 0.5),
                "type": d.get("type", "related")
            } 
            for u, v, d in self.graph.edges(data=True)
        ]
        
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2)
    
    def add_memory_node(self, memory_id: int, metadata: Dict) -> None:
        """Add a memory as a node in the graph"""
        self.graph.add_node(memory_id, **metadata)
        self._save()
    
    def add_link(self, from_id: int, to_id: int, weight: float = 0.5, 
                 link_type: str = "related") -> None:
        """Add a weighted edge between memories"""
        self.graph.add_edge(from_id, to_id, weight=weight, type=link_type)
        self._save()
    
    def get_related(self, memory_id: int, min_weight: float = 0.3) -> List[Tuple[int, float]]:
        """Get related memories above minimum weight"""
        if memory_id not in self.graph:
            return []
        
        related = []
        # Outgoing edges
        for _, to_id, data in self.graph.out_edges(memory_id, data=True):
            if data.get("weight", 0) >= min_weight:
                related.append((to_id, data["weight"]))
        
        # Incoming edges (bidirectional relevance)
        for from_id, _, data in self.graph.in_edges(memory_id, data=True):
            if data.get("weight", 0) >= min_weight:
                related.append((from_id, data["weight"]))
        
        # Sort by weight descending
        related.sort(key=lambda x: x[1], reverse=True)
        return related[:5]  # Top 5
    
    def find_path(self, from_id: int, to_id: int) -> List[int]:
        """Find shortest path between two memories"""
        try:
            return nx.shortest_path(self.graph, from_id, to_id)
        except nx.NetworkXNoPath:
            return []
    
    def get_clusters(self) -> List[List[int]]:
        """Find clusters of related memories"""
        undirected = self.graph.to_undirected()
        return [list(c) for c in nx.connected_components(undirected)]
    
    def get_central_memories(self, top_k: int = 5) -> List[Tuple[int, float]]:
        """Get most central (important) memories by PageRank"""
        if len(self.graph) == 0:
            return []
        
        try:
            pagerank = nx.pagerank(self.graph, weight="weight")
            sorted_pr = sorted(pagerank.items(), key=lambda x: x[1], reverse=True)
            return sorted_pr[:top_k]
        except:
            return []
    
    def strengthen_link(self, from_id: int, to_id: int, boost: float = 0.1) -> None:
        """Strengthen a link when it's useful"""
        if self.graph.has_edge(from_id, to_id):
            current = self.graph[from_id][to_id].get("weight", 0.5)
            self.graph[from_id][to_id]["weight"] = min(1.0, current + boost)
            self._save()
    
    def weaken_link(self, from_id: int, to_id: int, decay: float = 0.05) -> None:
        """Weaken a link over time"""
        if self.graph.has_edge(from_id, to_id):
            current = self.graph[from_id][to_id].get("weight", 0.5)
            self.graph[from_id][to_id]["weight"] = max(0.0, current - decay)
            self._save()
    
    def stats(self) -> Dict:
        return {
            "nodes": len(self.graph.nodes),
            "edges": len(self.graph.edges),
            "clusters": len(self.get_clusters())
        }


# Global instance
_graph: Optional[MemoryGraph] = None

def get_memory_graph() -> MemoryGraph:
    global _graph
    if _graph is None:
        _graph = MemoryGraph()
    return _graph
