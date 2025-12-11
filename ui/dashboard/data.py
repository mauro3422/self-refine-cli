
# Data Access Layer for Dashboard
# Handles reading JSON files from disk

import json
import os
from config.settings import DATA_DIR, OUTPUT_DIR
from memory import get_orchestrator

def read_history_file():
    """Read global history for performance metrics"""
    path = os.path.join(OUTPUT_DIR, "history.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"sessions": [], "global_avg_score": 0, "global_verify_rate": 0}

def read_memory_file():
    """Read memory directly from disk file"""
    path = os.path.join(DATA_DIR, "agent_memory.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("memories", [])
        except:
            pass
    return []

def read_graph_file():
    """Read graph directly from disk file"""
    path = os.path.join(DATA_DIR, "memory_graph.json")
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                nodes = len(data.get("nodes", []))
                edges = len(data.get("edges", []))
                return {"nodes": nodes, "edges": edges, "clusters": 0}
        except:
            pass
    return {"nodes": 0, "edges": 0, "clusters": 0}

def get_project_file_count():
    """Get accurate or estimated project file count"""
    # Try ChromaDB first for accurate project file count
    try:
        orch = get_orchestrator()
        return orch.working_memory.get_file_count()
    except:
        # Fallback to counting sandbox files
        try:
            sandbox_path = os.path.join(os.path.dirname(OUTPUT_DIR), "sandbox")
            if os.path.exists(sandbox_path):
                return len([f for f in os.listdir(sandbox_path) 
                           if os.path.isfile(os.path.join(sandbox_path, f))])
        except:
            pass
    return 0

def clear_data_files():
    """Clear memory and graph files"""
    path = os.path.join(DATA_DIR, "agent_memory.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"memories": [], "updated": "", "count": 0}, f)
    
    # Also clear graph
    graph_path = os.path.join(DATA_DIR, "memory_graph.json")
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump({"nodes": [], "edges": []}, f)
