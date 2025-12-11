
# HTML Template for the Dashboard
# This file separates the view layer from the logic

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
            <!-- TREND CARD - New -->
            <div class="card full-width" style="background: linear-gradient(135deg, rgba(0,212,255,0.1), rgba(0,255,136,0.1));">
                <h2>📊 Performance Trends</h2>
                <div style="display: flex; gap: 40px; align-items: center; margin: 20px 0;">
                    <div style="flex: 1;">
                        <div style="font-size: 3rem; letter-spacing: 3px; font-family: monospace;" id="sparkline">▁▂▃▄▅▆▇█</div>
                        <div style="color: #888; font-size: 0.8rem; margin-top: 5px;">Last 10 Sessions</div>
                    </div>
                    <div style="text-align: center;">
                        <div id="trend-direction" style="font-size: 4rem;">→</div>
                        <div id="trend-delta" style="font-size: 1.2rem; color: #00ff88;">+0.0</div>
                    </div>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                        <div class="graph-stat">
                            <div class="graph-stat-value" id="current-score">-</div>
                            <div class="stat-label">Current</div>
                        </div>
                        <div class="graph-stat">
                            <div class="graph-stat-value" id="avg-all-time">-</div>
                            <div class="stat-label">All-Time Avg</div>
                        </div>
                        <div class="graph-stat">
                            <div class="graph-stat-value" id="best-score">-</div>
                            <div class="stat-label">Best Score</div>
                        </div>
                        <div class="graph-stat">
                            <div class="graph-stat-value" id="trend-sessions">-</div>
                            <div class="stat-label">Total Sessions</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>📈 Performance</h2>
                <div class="graph-stats">
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="global-verify-rate">-</div>
                        <div class="stat-label">Verify Rate</div>
                    </div>
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="global-avg-score">-</div>
                        <div class="stat-label">Avg Score</div>
                    </div>
                    <div class="graph-stat">
                        <div class="graph-stat-value" id="total-sessions">-</div>
                        <div class="stat-label">Sessions</div>
                    </div>
                </div>
                <div style="margin-top: 15px; text-align: center; font-size: 0.9rem; color: #888;">
                    Total Tasks Completed: <span id="total-tasks">-</span>
                </div>
            </div>

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
                    
                    if (data.performance) {
                        document.getElementById('global-verify-rate').textContent = data.performance.global_verify_rate + '%';
                        document.getElementById('global-avg-score').textContent = data.performance.global_avg_score;
                        document.getElementById('total-sessions').textContent = data.performance.sessions;
                        document.getElementById('total-tasks').textContent = data.performance.total_tasks;
                    }
                    
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
                    document.getElementById('context-vectors').innerHTML = '<div style="color: #666; padding: 10px;">Context vectors not yet implemented</div>';
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
        
        function loadTrends() {
            fetch('/api/trends')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('sparkline').textContent = data.sparkline || '─────────';
                    document.getElementById('trend-direction').textContent = data.direction_icon || '→';
                    
                    const delta = data.delta || 0;
                    const deltaEl = document.getElementById('trend-delta');
                    deltaEl.textContent = (delta >= 0 ? '+' : '') + delta;
                    deltaEl.style.color = delta >= 0 ? '#00ff88' : '#ff6b6b';
                    
                    document.getElementById('current-score').textContent = data.current_score || '-';
                    document.getElementById('avg-all-time').textContent = data.avg_all_time || '-';
                    document.getElementById('best-score').textContent = data.best_score || '-';
                    document.getElementById('trend-sessions').textContent = data.total_sessions || '-';
                })
                .catch(e => console.log('Trends not available:', e));
        }
        
        refresh();
        loadTrends();
        setInterval(refresh, 10000);  // Refresh every 10 seconds
        setInterval(loadTrends, 10000);
    </script>
</body>
</html>
"""
