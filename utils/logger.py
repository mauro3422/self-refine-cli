# Logging de iteraciones

import json
import os
from datetime import datetime
from typing import Dict, List
from config.settings import OUTPUT_DIR, LOG_FILE


class RefineLogger:
    def __init__(self):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        self.log_file = LOG_FILE
    
    def log_session(self, session_data: Dict) -> str:
        """Guarda sesión de refinamiento"""
        # Cargar historial existente
        history = []
        if os.path.exists(self.log_file):
            with open(self.log_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # Agregar nueva sesión
        session_data['timestamp'] = datetime.now().isoformat()
        history.append(session_data)
        
        # Guardar
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
        
        return self.log_file
    
    def get_similar_tasks(self, task: str, limit: int = 3) -> List[Dict]:
        """Busca tareas similares en historial (caché simple)"""
        if not os.path.exists(self.log_file):
            return []
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # Búsqueda simple por keywords
        keywords = set(task.lower().split())
        similar = []
        
        for session in history:
            session_task = session.get('task', '').lower()
            session_keywords = set(session_task.split())
            
            # Similitud por intersección de palabras
            similarity = len(keywords & session_keywords) / max(len(keywords), 1)
            
            if similarity > 0.3:  # 30% de palabras en común
                similar.append({
                    'task': session.get('task'),
                    'similarity': similarity,
                    'iterations': session.get('total_iterations'),
                    'timestamp': session.get('timestamp')
                })
        
        # Ordenar por similitud
        similar.sort(key=lambda x: x['similarity'], reverse=True)
        return similar[:limit]
