"""
SQLite storage backend for X-Ray execution data.

Optional dependency - only needed if you want persistent storage.
Installation: SQLite is included with Python, no extra dependencies needed.
"""

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from .storage import StorageBackend


class SQLiteStorage(StorageBackend):
    """
    SQLite-based storage for X-Ray execution data.
    
    Provides persistent file-based storage. SQLite is included with Python,
    so no additional dependencies are required.
    """
    
    def __init__(self, db_path: str = "xray.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        if not SQLITE_AVAILABLE:
            raise ImportError(
                "SQLite is not available. This is unusual as SQLite "
                "is included with Python. Please check your Python installation."
            )
        
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Executions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                execution_id TEXT PRIMARY KEY,
                metadata TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        # Steps table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                step_data TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES executions(execution_id)
            )
        """)
        
        # Index for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_execution 
            ON steps(execution_id, step_order)
        """)
        
        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                workflow_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Index for workflows
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_workflows_updated 
            ON workflows(updated_at DESC)
        """)
        
        conn.commit()
        conn.close()
    
    def save_execution(
        self,
        execution_id: str,
        metadata: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ):
        """
        Save execution to SQLite database.
        
        Accepts either canonical format or legacy format and normalizes it.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Normalize metadata - extract canonical fields if present
            # If metadata contains canonical fields, extract them
            normalized_metadata = metadata.copy()
            
            # Save execution metadata
            # Use started_at from metadata if available, otherwise use current time
            started_at = normalized_metadata.get("started_at") or datetime.utcnow().isoformat()
            
            cursor.execute("""
                INSERT OR REPLACE INTO executions (execution_id, metadata, created_at)
                VALUES (?, ?, ?)
            """, (
                execution_id,
                json.dumps(normalized_metadata),
                started_at
            ))
            
            # Delete existing steps for this execution
            cursor.execute("DELETE FROM steps WHERE execution_id = ?", (execution_id,))
            
            # Save steps (already in canonical format from core.py)
            for order, step in enumerate(steps):
                cursor.execute("""
                    INSERT INTO steps (execution_id, step_order, step_data)
                    VALUES (?, ?, ?)
                """, (
                    execution_id,
                    order,
                    json.dumps(step)
                ))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve execution from SQLite database in canonical format.
        
        Returns:
            Dictionary with canonical structure:
            {
                "id": "exec_12345",
                "name": "competitor_selection",
                "started_at": "2025-01-20T10:15:00Z",
                "ended_at": "2025-01-20T10:15:03Z",
                "metadata": {...},
                "steps": [...]
            }
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get execution metadata
            cursor.execute("""
                SELECT metadata, created_at FROM executions WHERE execution_id = ?
            """, (execution_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            metadata_json, created_at = row
            metadata = json.loads(metadata_json)
            
            # Get steps
            cursor.execute("""
                SELECT step_data FROM steps 
                WHERE execution_id = ? 
                ORDER BY step_order
            """, (execution_id,))
            
            steps = [json.loads(row[0]) for row in cursor.fetchall()]
            
            # Build canonical format
            # Extract name from metadata if available
            name = metadata.get("name") or metadata.get("workflow") or "unnamed_execution"
            
            # Extract timestamps
            started_at = metadata.get("started_at") or created_at
            ended_at = metadata.get("ended_at") or metadata.get("completed_at")
            
            # If steps exist, use their timestamps to infer execution times
            if steps and not ended_at:
                last_step = steps[-1]
                if "ended_at" in last_step:
                    ended_at = last_step["ended_at"]
                elif "timestamp" in last_step:
                    ended_at = last_step["timestamp"]
            
            # Normalize timestamps to ISO format with Z
            def normalize_timestamp(ts):
                if not ts:
                    return None
                if isinstance(ts, str):
                    # Handle various timestamp formats
                    try:
                        # Try parsing with timezone
                        if 'Z' in ts or '+' in ts or ts.count(':') >= 2:
                            # Remove Z and try parsing
                            ts_clean = ts.replace('Z', '').replace('+00:00', '')
                            if '+' in ts_clean:
                                # Has timezone offset
                                parts = ts_clean.split('+')
                                ts_clean = parts[0]
                            try:
                                dt = datetime.fromisoformat(ts_clean)
                            except:
                                # Try with just date and time
                                if 'T' in ts_clean:
                                    date_part, time_part = ts_clean.split('T')
                                    dt = datetime.fromisoformat(f"{date_part}T{time_part.split('.')[0]}")
                                else:
                                    dt = datetime.fromisoformat(ts_clean)
                        else:
                            dt = datetime.fromisoformat(ts)
                        return dt.isoformat() + "Z"
                    except Exception as e:
                        # If parsing fails, return as-is or current time
                        return datetime.utcnow().isoformat() + "Z"
                return ts.isoformat() + "Z" if hasattr(ts, 'isoformat') else str(ts)
            
            return {
                "id": execution_id,
                "name": name,
                "started_at": normalize_timestamp(started_at) or datetime.utcnow().isoformat() + "Z",
                "ended_at": normalize_timestamp(ended_at) or datetime.utcnow().isoformat() + "Z",
                "metadata": {k: v for k, v in metadata.items() if k not in ["name", "started_at", "ended_at", "completed_at"]},
                "steps": steps
            }
        finally:
            conn.close()
    
    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List executions from SQLite database in canonical format.
        
        Returns list of execution summaries with canonical structure.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT execution_id, metadata, created_at 
                FROM executions 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            executions = []
            for row in cursor.fetchall():
                execution_id, metadata_json, created_at = row
                metadata = json.loads(metadata_json)
                
                # Build canonical format summary
                name = metadata.get("name") or metadata.get("workflow") or "unnamed_execution"
                started_at = metadata.get("started_at") or created_at
                ended_at = metadata.get("ended_at") or metadata.get("completed_at")
                
                # Normalize timestamps
                def normalize_timestamp(ts):
                    if not ts:
                        return None
                    if isinstance(ts, str):
                        try:
                            ts_clean = ts.replace('Z', '').replace('+00:00', '')
                            if '+' in ts_clean:
                                ts_clean = ts_clean.split('+')[0]
                            try:
                                dt = datetime.fromisoformat(ts_clean)
                            except:
                                if 'T' in ts_clean:
                                    date_part, time_part = ts_clean.split('T')
                                    dt = datetime.fromisoformat(f"{date_part}T{time_part.split('.')[0]}")
                                else:
                                    dt = datetime.fromisoformat(ts_clean)
                            return dt.isoformat() + "Z"
                        except:
                            return ts
                    return ts.isoformat() + "Z" if hasattr(ts, 'isoformat') else str(ts)
                
                executions.append({
                    "id": execution_id,
                    "name": name,
                    "started_at": normalize_timestamp(started_at) or created_at,
                    "ended_at": normalize_timestamp(ended_at),
                    "metadata": {k: v for k, v in metadata.items() if k not in ["name", "started_at", "ended_at", "completed_at"]},
                    "steps": []  # Summary doesn't include steps
                })
            
            return executions
        finally:
            conn.close()
    
    def delete_execution(self, execution_id: str):
        """Delete execution from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM steps WHERE execution_id = ?", (execution_id,))
            cursor.execute("DELETE FROM executions WHERE execution_id = ?", (execution_id,))
            conn.commit()
        finally:
            conn.close()
    
    def save_workflow(self, workflow_id: str, workflow_data: Dict[str, Any]):
        """Save workflow to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            now = datetime.utcnow().isoformat()
            
            # Check if workflow exists
            cursor.execute("SELECT workflow_id FROM workflows WHERE workflow_id = ?", (workflow_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing workflow
                cursor.execute("""
                    UPDATE workflows 
                    SET workflow_data = ?, updated_at = ?
                    WHERE workflow_id = ?
                """, (json.dumps(workflow_data), now, workflow_id))
            else:
                # Insert new workflow
                cursor.execute("""
                    INSERT INTO workflows (workflow_id, workflow_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (workflow_id, json.dumps(workflow_data), now, now))
            
            conn.commit()
        finally:
            conn.close()
    
    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT workflow_data FROM workflows WHERE workflow_id = ?
            """, (workflow_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return json.loads(row[0])
        finally:
            conn.close()
    
    def list_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT workflow_id, workflow_data, updated_at 
                FROM workflows 
                ORDER BY updated_at DESC
            """)
            
            workflows = []
            for row in cursor.fetchall():
                workflow_id, workflow_data_json, updated_at = row
                workflow_data = json.loads(workflow_data_json)
                
                workflows.append({
                    "workflow_id": workflow_id,
                    "name": workflow_data.get("name", "Unnamed"),
                    "steps_count": len(workflow_data.get("steps", [])),
                    "updated_at": updated_at
                })
            
            return workflows
        finally:
            conn.close()
    
    def delete_workflow(self, workflow_id: str):
        """Delete workflow from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("DELETE FROM workflows WHERE workflow_id = ?", (workflow_id,))
            conn.commit()
        finally:
            conn.close()

