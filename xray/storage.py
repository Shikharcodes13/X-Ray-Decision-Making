"""
Storage layer for X-Ray execution data.

Provides abstract base class and implementations for different storage backends.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime


class StorageBackend(ABC):
    """
    Abstract base class for X-Ray storage backends.
    
    Implement this interface to create custom storage backends
    (e.g., PostgreSQL, MongoDB, Redis, file-based, etc.)
    """
    
    @abstractmethod
    def save_execution(
        self,
        execution_id: str,
        metadata: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ):
        """
        Save an execution with all its steps.
        
        Args:
            execution_id: Unique execution identifier
            metadata: Execution metadata
            steps: List of step dictionaries
        """
        pass
    
    @abstractmethod
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an execution by ID.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Dictionary with metadata and steps, or None if not found
        """
        pass
    
    @abstractmethod
    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent executions.
        
        Args:
            limit: Maximum number of executions to return
            
        Returns:
            List of execution summaries
        """
        pass
    
    @abstractmethod
    def delete_execution(self, execution_id: str):
        """Delete an execution and all its steps."""
        pass


class InMemoryStorage(StorageBackend):
    """
    In-memory storage backend (default, no dependencies).
    
    Stores executions in memory. Data is lost when the process exits.
    Useful for testing, development, or when persistence isn't needed.
    """
    
    def __init__(self):
        """Initialize in-memory storage."""
        self._executions: Dict[str, Dict[str, Any]] = {}
        self._execution_order: List[str] = []
    
    def save_execution(
        self,
        execution_id: str,
        metadata: Dict[str, Any],
        steps: List[Dict[str, Any]]
    ):
        """Save execution to memory."""
        if execution_id not in self._execution_order:
            self._execution_order.append(execution_id)
        
        self._executions[execution_id] = {
            "execution_id": execution_id,
            "metadata": metadata,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve execution from memory."""
        return self._executions.get(execution_id)
    
    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List executions from memory."""
        executions = []
        # Return in reverse order (most recent first)
        for execution_id in reversed(self._execution_order[-limit:]):
            exec_data = self._executions.get(execution_id)
            if exec_data:
                executions.append({
                    "execution_id": execution_id,
                    "metadata": exec_data["metadata"],
                    "created_at": exec_data["created_at"]
                })
        return executions
    
    def delete_execution(self, execution_id: str):
        """Delete execution from memory."""
        if execution_id in self._executions:
            del self._executions[execution_id]
        if execution_id in self._execution_order:
            self._execution_order.remove(execution_id)


# Export the abstract base and default implementation
Storage = InMemoryStorage  # Default storage (no dependencies)
