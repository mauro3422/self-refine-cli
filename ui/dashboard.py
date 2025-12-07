# Memory Dashboard - Web UI for monitoring and controlling memory
# Run with: python -m ui.dashboard

from flask import Flask, render_template_string, jsonify, request
from memory import get_orchestrator, get_memory, get_memory_graph
from utils.logger import get_logger, get_latest_session_logs
import threading
import webbrowser

app = Flask(__name__)

# HTML Template
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Poetiq Memory Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', sans-serif; 
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
        }
        .container { max-width: 1400px; margin: 0 auto; padding: 20px; }
        
        header {
            background: rgba(255,255,255,0.05);
            padding: 20px 30px;
            border-radius: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 { font-size: 1.8rem; color: #00d4ff; }
        .stats {
            display: flex;
            gap: 30px;
        }
        .stat {
            text-align: center;
        }
        .stat-value { 
            font-size: 2rem; 
            font-weight: bold; 
            color: #00ff88;
        }
        .stat-label { font-size: 0.8rem; color: #888; }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        
        .card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
        }
        .card h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }
        
        .memory-item {
            background: rgba(0,0,0,0.2);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 3px solid #00ff88;
            transition: all 0.2s;
        }
        .memory-item:hover {
            background: rgba(0,212,255,0.1);
            transform: translateX(5px);
        }
        .memory-lesson {
            font-size: 0.95rem;
            margin-bottom: 8px;
        }
        .memory-meta {
            display: flex;
            gap: 15px;
            font-size: 0.75rem;
            color: #888;
        }
        .memory-meta span {
            background: rgba(255,255,255,0.1);
            padding: 3px 8px;
            border-radius: 5px;
        }
        
        .category-file_create { border-left-color: #00ff88; }
        .category-file_read { border-left-color: #00d4ff; }
        .category-code_exec { border-left-color: #ff6b6b; }
        .category-general { border-left-color: #ffd93d; }
        
        .graph-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        .graph-stat {
            background: rgba(0,0,0,0.2);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .graph-stat-value { font-size: 1.5rem; color: #00d4ff; }
        
        .btn {
            background: linear-gradient(135deg, #00d4ff, #0099ff);
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            color: white;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
        }
        .btn:hover { transform: scale(1.05); }
        .btn-danger { background: linear-gradient(135deg, #ff6b6b, #ff4757); }
        
        .refresh-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        
        #last-update { color: #888; font-size: 0.8rem; }
        
        .full-width { grid-column: 1 / -1; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧠 Poetiq Memory Dashboard</h1>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value" id="total-memories">-</div>
                    <div class="stat-label">Memories</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="total-links">-</div>
                    <div class="stat-label">Links</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="avg-importance">-</div>
                    <div class="stat-label">Avg Importance</div>
                </div>
                <div class="stat">
                    <div class="stat-value" id="project-files">-</div>
                    <div class="stat-label">Project Files</div>
                </div>
            </div>
        </header>
        
        <div class="refresh-bar">
            <span id="last-update">Last update: never</span>
            <div>
                <button class="btn" onclick="refresh()">🔄 Refresh</button>
                <button class="btn btn-danger" onclick="clearMemory()">🗑️ Clear All</button>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📚 Recent Memories</h2>
                <div id="memories-list">Loading...</div>
            </div>
            
            <div class="card">
                <h2>🔗 Graph Statistics</h2>
                <div class="graph-stats" id="graph-stats">
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="graph-nodes">-</div>
                        <div class="stat-label">Nodes</div>
                    </div>
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="graph-edges">-</div>
                        <div class="stat-label">Edges</div>
                    </div>
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="graph-clusters">-</div>
                        <div class="stat-label">Clusters</div>
                    </div>
                </div>
                
                <h2 style="margin-top: 20px;">📊 Categories</h2>
                <div id="categories">Loading...</div>
            </div>
            
            <div class="card full-width">
                <h2>⚡ Live Agent Logs</h2>
                <div id="live-logs" style="font-family: monospace; font-size: 0.85rem; max-height: 300px; overflow-y: auto;">
                    Loading...
                </div>
            </div>

            <div class="card full-width">
                <h2>🎯 Context Vectors</h2>
                <div id="context-vectors">Loading...</div>
            </div>
        </div>
    </div>
    
    <script>
        function refresh() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('total-memories').textContent = data.memory.total;
                    document.getElementById('total-links').textContent = data.memory.with_links;
                    document.getElementById('avg-importance').textContent = data.memory.avg_importance;
                    document.getElementById('project-files').textContent = data.project_files;
                    
                    document.getElementById('graph-nodes').textContent = data.graph.nodes;
                    document.getElementById('graph-edges').textContent = data.graph.edges;
                    document.getElementById('graph-clusters').textContent = data.graph.clusters;
                    
                    document.getElementById('last-update').textContent = 
                        'Last update: ' + new Date().toLocaleTimeString();
                });
            
            fetch('/api/memories')
                .then(r => r.json())
                .then(data => {
                    const html = data.memories.slice(0, 10).map(m => `
                        <div class="memory-item category-${m.category}">
                            <div class="memory-lesson">${m.lesson}</div>
                            <div class="memory-meta">
                                <span>📁 ${m.category}</span>
                                <span>⭐ ${m.importance}</span>
                                <span>👁️ ${m.access_count}</span>
                                <span>🔗 ${(m.links || []).length} links</span>
                            </div>
                        </div>
                    `).join('');
                    document.getElementById('memories-list').innerHTML = html || 'No memories yet';
                });
                
            fetch('/api/categories')
                .then(r => r.json())
                .then(data => {
                    const html = Object.entries(data.categories).map(([name, cat]) => `
                        <div style="margin: 5px 0; padding: 10px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                            <strong>${name}</strong>: ${cat.tools.join(', ') || 'No tools'}
                        </div>
                    `).join('');
                    document.getElementById('categories').innerHTML = html;
                    document.getElementById('context-vectors').innerHTML = html;
                });
            fetch('/api/logs')
                .then(r => r.json())
                .then(data => {
                    if (data.logs && data.logs.length > 0) {
                        const html = data.logs.reverse().map(l => {
                            let color = '#ccc';
                            if (l.phase === 'parallel') color = '#00d4ff';
                            if (l.phase === 'refine') color = '#ffd93d';
                            if (l.phase === 'final') color = '#00ff88';
                            if (l.phase === 'info') color = '#aaaaaa';
                            
                            let content = l.message || l.response || l.result || JSON.stringify(l);
                            if (typeof content !== 'string') content = JSON.stringify(content);

                            return `<div style="margin-bottom: 5px; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 5px;">
                                <span style="color: #666;">[${l.time.split('T')[1].split('.')[0]}]</span> 
                                <strong style="color: ${color}">${l.phase.toUpperCase()}</strong>: 
                                <span style="color: #ddd;">${content.substring(0, 200)}${content.length > 200 ? '...' : ''}</span>
                            </div>`;
                        }).join('');
                        document.getElementById('live-logs').innerHTML = html;
                    } else {
                         document.getElementById('live-logs').innerHTML = '<div style="color: #666; padding: 20px; text-align: center;">Waiting for agent activity...</div>';
                    }
                });
        }
        
        function clearMemory() {
            if (confirm('Are you sure you want to clear all memories?')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(() => refresh());
            }
        }
        
        refresh();
        setInterval(refresh, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

# === FRESH DATA FUNCTIONS (read from disk, no singletons) ===
import json
import os
from config.settings import DATA_DIR, OUTPUT_DIR

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

@app.route('/api/stats')
def api_stats():
    """Get stats - uses ChromaDB if available, falls back to disk"""
    memories = read_memory_file()
    graph = read_graph_file()
    
    total = len(memories)
    with_links = sum(1 for m in memories if m.get("links"))
    avg_importance = sum(m.get("importance", 5) for m in memories) / total if total else 0
    
    # Try ChromaDB first for accurate project file count
    project_files = 0
    try:
        orch = get_orchestrator()
        project_files = orch.working_memory.get_file_count()
    except:
        # Fallback to counting sandbox files
        try:
            sandbox_path = os.path.join(os.path.dirname(OUTPUT_DIR), "sandbox")
            if os.path.exists(sandbox_path):
                project_files = len([f for f in os.listdir(sandbox_path) 
                                    if os.path.isfile(os.path.join(sandbox_path, f))])
        except:
            pass
    
    return jsonify({
        "memory": {
            "total": total,
            "with_links": with_links,
            "avg_importance": round(avg_importance, 1),
            "vector_available": True
        },
        "graph": graph,
        "project_files": project_files
    })

@app.route('/api/memories')
def api_memories():
    """Get memories by reading directly from disk"""
    memories = read_memory_file()
    return jsonify({"memories": memories[-20:]})  # Last 20

@app.route('/api/categories')
def api_categories():
    from memory.context_vectors import FUNCTION_VECTORS
    return jsonify({"categories": FUNCTION_VECTORS})

@app.route('/api/logs')
def api_logs():
    # Read from disk to see other process logs
    return jsonify({"logs": get_latest_session_logs(15)})

@app.route('/api/clear', methods=['POST'])
def api_clear():
    """Clear memory by writing empty file"""
    path = os.path.join(DATA_DIR, "agent_memory.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({"memories": [], "updated": "", "count": 0}, f)
    
    # Also clear graph
    graph_path = os.path.join(DATA_DIR, "memory_graph.json")
    with open(graph_path, 'w', encoding='utf-8') as f:
        json.dump({"nodes": [], "edges": []}, f)
    
    return jsonify({"status": "cleared"})


def run_dashboard(port=5000, open_browser=True):
    """Run the dashboard server"""
    print(f"\n🧠 Memory Dashboard starting at http://localhost:{port}")
    
    if open_browser:
        threading.Timer(1.5, lambda: webbrowser.open(f'http://localhost:{port}')).start()
    
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)


if __name__ == '__main__':
    run_dashboard()
