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
        
        conn.commit()
        conn.close()
    
    def save_execution(
        self,
        execution_id: str,
        metadata: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ):
        """Save execution to SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Save execution metadata
            cursor.execute("""
                INSERT OR REPLACE INTO executions (execution_id, metadata, created_at)
                VALUES (?, ?, ?)
            """, (
                execution_id,
                json.dumps(metadata),
                datetime.utcnow().isoformat()
            ))
            
            # Delete existing steps for this execution
            cursor.execute("DELETE FROM steps WHERE execution_id = ?", (execution_id,))
            
            # Save steps
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
        """Retrieve execution from SQLite database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get execution metadata
            cursor.execute("""
                SELECT metadata FROM executions WHERE execution_id = ?
            """, (execution_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            metadata = json.loads(row[0])
            
            # Get steps
            cursor.execute("""
                SELECT step_data FROM steps 
                WHERE execution_id = ? 
                ORDER BY step_order
            """, (execution_id,))
            
            steps = [json.loads(row[0]) for row in cursor.fetchall()]
            
            return {
                "execution_id": execution_id,
                "metadata": metadata,
                "steps": steps
            }
        finally:
            conn.close()
    
    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List executions from SQLite database."""
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
                executions.append({
                    "execution_id": execution_id,
                    "metadata": metadata,
                    "created_at": created_at
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

