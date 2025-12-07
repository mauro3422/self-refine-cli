# memory/persistence.py - Memory Export/Import for Backup
# Allows exporting and importing the learned knowledge

import json
import os
import shutil
from typing import Dict, Any, Optional
from datetime import datetime
from zipfile import ZipFile

from config.settings import OUTPUT_DIR


class MemoryPersistence:
    """
    Handles export/import of memory state for backup and sharing.
    """
    
    EXPORT_FILES = [
        "agent_memory.json",
        "memory_graph.json",
        "embedding_cache.json"
    ]
    
    def __init__(self, output_dir: str = None):
        self.output_dir = output_dir or OUTPUT_DIR
    
    def export_to_json(self, export_path: str = None) -> str:
        """Export all memory to a single JSON file"""
        export_path = export_path or os.path.join(
            self.output_dir, 
            f"memory_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        export_data = {
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "files": {}
        }
        
        for filename in self.EXPORT_FILES:
            filepath = os.path.join(self.output_dir, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        export_data["files"][filename] = json.load(f)
                except:
                    export_data["files"][filename] = None
        
        with open(export_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        return export_path
    
    def export_to_zip(self, export_path: str = None) -> str:
        """Export all memory files to a ZIP archive"""
        export_path = export_path or os.path.join(
            self.output_dir,
            f"memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        )
        
        with ZipFile(export_path, 'w') as zipf:
            for filename in self.EXPORT_FILES:
                filepath = os.path.join(self.output_dir, filename)
                if os.path.exists(filepath):
                    zipf.write(filepath, filename)
            
            # Add metadata
            metadata = {
                "exported_at": datetime.now().isoformat(),
                "files": self.EXPORT_FILES
            }
            zipf.writestr("metadata.json", json.dumps(metadata, indent=2))
        
        return export_path
    
    def import_from_json(self, import_path: str, merge: bool = False) -> Dict[str, int]:
        """
        Import memory from a JSON export file.
        
        Args:
            import_path: Path to the export JSON file
            merge: If True, merge with existing; if False, replace
            
        Returns:
            Stats about what was imported
        """
        stats = {"imported": 0, "merged": 0, "errors": 0}
        
        with open(import_path, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        for filename, content in import_data.get("files", {}).items():
            if content is None:
                continue
            
            filepath = os.path.join(self.output_dir, filename)
            
            try:
                if merge and os.path.exists(filepath):
                    # Merge logic
                    with open(filepath, 'r', encoding='utf-8') as f:
                        existing = json.load(f)
                    
                    merged = self._merge_data(existing, content)
                    
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(merged, f, indent=2, ensure_ascii=False)
                    
                    stats["merged"] += 1
                else:
                    # Replace
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(content, f, indent=2, ensure_ascii=False)
                    
                    stats["imported"] += 1
            except Exception as e:
                stats["errors"] += 1
        
        return stats
    
    def import_from_zip(self, import_path: str, merge: bool = False) -> Dict[str, int]:
        """Import memory from a ZIP backup"""
        stats = {"imported": 0, "errors": 0}
        
        with ZipFile(import_path, 'r') as zipf:
            for filename in self.EXPORT_FILES:
                if filename in zipf.namelist():
                    try:
                        content = zipf.read(filename)
                        filepath = os.path.join(self.output_dir, filename)
                        
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        stats["imported"] += 1
                    except:
                        stats["errors"] += 1
        
        return stats
    
    def _merge_data(self, existing: Dict, new: Dict) -> Dict:
        """Merge two data dictionaries"""
        # For memories, append new ones that don't exist
        if "memories" in existing and "memories" in new:
            existing_lessons = {m.get("lesson") for m in existing["memories"]}
            
            for mem in new.get("memories", []):
                if mem.get("lesson") not in existing_lessons:
                    existing["memories"].append(mem)
            
            existing["count"] = len(existing["memories"])
            existing["updated"] = datetime.now().isoformat()
        
        # For graphs, merge nodes and edges
        if "nodes" in existing and "nodes" in new:
            existing_nodes = {n.get("id") for n in existing.get("nodes", [])}
            for node in new.get("nodes", []):
                if node.get("id") not in existing_nodes:
                    existing["nodes"].append(node)
            
            existing_edges = {(e.get("source"), e.get("target")) for e in existing.get("edges", [])}
            for edge in new.get("edges", []):
                if (edge.get("source"), edge.get("target")) not in existing_edges:
                    existing["edges"].append(edge)
        
        return existing
    
    def create_backup(self) -> str:
        """Create a timestamped backup of all memory files"""
        backup_dir = os.path.join(self.output_dir, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)
        
        for filename in self.EXPORT_FILES:
            src = os.path.join(self.output_dir, filename)
            if os.path.exists(src):
                shutil.copy2(src, backup_path)
        
        return backup_path


# Convenience functions
def export_memories(path: str = None, format: str = "json") -> str:
    """Export all memories to file"""
    p = MemoryPersistence()
    if format == "zip":
        return p.export_to_zip(path)
    return p.export_to_json(path)

def import_memories(path: str, merge: bool = False) -> Dict:
    """Import memories from file"""
    p = MemoryPersistence()
    if path.endswith(".zip"):
        return p.import_from_zip(path, merge)
    return p.import_from_json(path, merge)

def backup_memories() -> str:
    """Create a backup of all memory files"""
    return MemoryPersistence().create_backup()
