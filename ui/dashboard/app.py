
# Main Dashboard Application
# Ties together templates and data access

from flask import Flask, render_template_string, jsonify, request
from utils.logger import get_latest_session_logs
import threading
import webbrowser
from .templates import DASHBOARD_HTML
from .data import (
    read_history_file, 
    read_memory_file, 
    read_graph_file, 
    get_project_file_count,
    clear_data_files
)

app = Flask(__name__)

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/stats')
def api_stats():
    """Get stats - uses ChromaDB if available, falls back to disk"""
    memories = read_memory_file()
    graph = read_graph_file()
    history = read_history_file()
    project_files = get_project_file_count()
    
    total = len(memories)
    with_links = sum(1 for m in memories if m.get("links"))
    avg_importance = sum(m.get("importance", 5) for m in memories) / total if total else 0
    
    return jsonify({
        "memory": {
            "total": total,
            "with_links": with_links,
            "avg_importance": round(avg_importance, 1),
            "vector_available": True
        },
        "graph": graph,
        "project_files": project_files,
        "performance": {
            "global_avg_score": round(history.get("global_avg_score", 0), 2),
            "global_verify_rate": round(history.get("global_verify_rate", 0) * 100, 1),
            "total_tasks": sum(s.get("tasks", 0) for s in history.get("sessions", [])),
            "sessions": len(history.get("sessions", []))
        }
    })

@app.route('/api/memories')
def api_memories():
    """Get memories by reading directly from disk"""
    memories = read_memory_file()
    return jsonify({"memories": memories[-20:]})  # Last 20

@app.route('/api/categories')
def api_categories():
    try:
        from memory.context_vectors import FUNCTION_VECTORS
        return jsonify({"categories": FUNCTION_VECTORS})
    except ImportError:
        return jsonify({"categories": {}})

@app.route('/api/logs')
def api_logs():
    # Read from disk to see other process logs
    return jsonify({"logs": get_latest_session_logs(15)})

@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear memory by writing empty file"""
    clear_data_files()
    return jsonify({"status": "cleared"})

def run_dashboard(port=5000, open_browser=True):
    """Run the dashboard server"""
    print(f"\n🧠 Memory Dashboard starting at http://localhost:{port}")
    
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    run_dashboard()
