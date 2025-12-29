"""
Core X-Ray library for capturing decision context.
"""

import uuid
import json
from datetime import datetime
from typing import Any, Dict, Optional, Callable, List
from contextlib import contextmanager
from functools import wraps


class XRay:
    """
    Main X-Ray context manager for tracking multi-step decision processes.
    
    Usage:
        with XRay() as xray:
            xray.record_step(
                step_name="keyword_generation",
                input_data={"product_title": "..."},
                output_data={"keywords": [...]},
                reasoning="Extracted key attributes..."
            )
    """
    
    def __init__(self, execution_id: Optional[str] = None, name: Optional[str] = None, storage: Optional[Any] = None, auto_save: bool = True):
        """
        Initialize X-Ray context.
        
        Args:
            execution_id: Optional execution ID. If None, generates a new UUID.
            name: Optional execution name (e.g., "competitor_selection", "product_filtering")
            storage: Storage instance implementing StorageBackend interface.
                    If None, no persistence (data only available during execution).
            auto_save: If True, automatically save to storage on context exit.
                      If False, you must manually call get_execution() to access data.
        """
        self.execution_id = execution_id or f"exec_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.storage = storage
        self.auto_save = auto_save
        self.steps: list = []
        self.started_at = datetime.utcnow()
        self.metadata: Dict[str, Any] = {}
        self._active = False
        self._step_counter = 0
    
    def __enter__(self):
        """Enter context manager."""
        self._active = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and optionally save execution."""
        self._active = False
        self.ended_at = datetime.utcnow()
        
        if self.storage and self.auto_save:
            execution_data = self.get_execution()
            self.storage.save_execution(
                execution_id=self.execution_id,
                metadata=execution_data.get("metadata", {}),
                steps=execution_data.get("steps", [])
            )
        
        return False
    
    def get_execution(self) -> Dict[str, Any]:
        """
        Get the current execution data in canonical format.
        
        Returns:
            Dictionary with canonical X-Ray structure:
            {
                "id": "exec_12345",
                "name": "competitor_selection",
                "started_at": "2025-01-20T10:15:00Z",
                "ended_at": "2025-01-20T10:15:03Z",
                "metadata": {...},
                "steps": [...]
            }
        """
        ended_at = getattr(self, 'ended_at', datetime.utcnow())
        return {
            "id": self.execution_id,
            "name": self.name or "unnamed_execution",
            "started_at": self.started_at.isoformat() + "Z",
            "ended_at": ended_at.isoformat() + "Z",
            "metadata": self.metadata,
            "steps": self.steps
        }
    
    def save(self):
        """
        Manually save execution to storage.
        
        Useful when auto_save=False or when you want to save before context exit.
        """
        if not self.storage:
            raise RuntimeError("No storage backend configured. Provide a storage instance when creating XRay.")
        
        execution_data = self.get_execution()
        self.storage.save_execution(
            execution_id=self.execution_id,
            metadata=execution_data.get("metadata", {}),
            steps=execution_data.get("steps", [])
        )
    
    def record_step(
        self,
        step_name: str,
        step_type: Optional[str] = None,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        evaluations: Optional[List[Dict[str, Any]]] = None,
        reasoning: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Record a step in the execution using canonical format.
        
        Args:
            step_name: Name/identifier of the step (e.g., "filter_candidates")
            step_type: Type of step (e.g., "filter", "ranking", "transformation", "selection")
            input_data: Input data for this step
            output_data: Output data from this step
            rules: List of rules used in this step. Each rule should have:
                   {"name": str, "type": str, "value": Any, "source": str}
            evaluations: List of evaluation objects. Each should have:
                        {"entity_id": str, "attributes": dict, "checks": list, "final_decision": str}
            reasoning: Human-readable explanation of the decision
            **kwargs: Additional fields to include in the step record
        
        Returns:
            The recorded step dictionary in canonical format
        """
        if not self._active:
            raise RuntimeError("XRay context is not active. Use 'with XRay() as xray:'")
        
        self._step_counter += 1
        step_id = f"step_{self._step_counter}"
        started_at = datetime.utcnow()
        
        # Build canonical step structure
        step = {
            "id": step_id,
            "name": step_name,
            "type": step_type or "general",
            "input": input_data or {},
            "rules": rules or [],
            "evaluations": evaluations or [],
            "output": output_data or {},
            "reasoning": reasoning or "",
            "started_at": started_at.isoformat() + "Z",
            "ended_at": started_at.isoformat() + "Z",  # Will be updated if needed
            **kwargs
        }
        
        self.steps.append(step)
        return step
    
    def update_step(self, step_id: Optional[str] = None, step_index: Optional[int] = None, **updates):
        """
        Update an existing step with additional data.
        
        Args:
            step_id: ID of the step to update
            step_index: Index of the step to update (alternative to step_id)
            **updates: Fields to update in the step
        """
        if step_index is not None:
            if 0 <= step_index < len(self.steps):
                self.steps[step_index].update(updates)
                if "ended_at" not in updates:
                    self.steps[step_index]["ended_at"] = datetime.utcnow().isoformat() + "Z"
        elif step_id:
            for step in self.steps:
                if step.get("id") == step_id:
                    step.update(updates)
                    if "ended_at" not in updates:
                        step["ended_at"] = datetime.utcnow().isoformat() + "Z"
                    break
    
    def add_metadata(self, key: str, value: Any):
        """Add custom metadata to the execution."""
        self.metadata[key] = value


def xray_step(step_name: Optional[str] = None):
    """
    Decorator to automatically record a function call as an X-Ray step.
    
    Usage:
        @xray_step("keyword_generation")
        def generate_keywords(product_title: str):
            # function implementation
            return {"keywords": [...]}
    
    The decorator will automatically capture:
    - Function arguments as input_data
    - Return value as output_data
    - Function name as step_name (if not provided)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get XRay instance from global context or thread-local
            # For simplicity, we'll use a thread-local storage
            import threading
            thread_local = threading.local()
            xray = getattr(thread_local, 'xray', None)
            
            if not xray:
                # If no XRay context, just call the function normally
                return func(*args, **kwargs)
            
            # Prepare input data
            input_data = {
                "args": [str(arg) for arg in args],
                "kwargs": kwargs
            }
            
            # Execute function
            try:
                result = func(*args, **kwargs)
                output_data = {"result": result} if result is not None else {}
                
                xray.record_step(
                    step_name=step_name or func.__name__,
                    input_data=input_data,
                    output_data=output_data,
                    reasoning=f"Executed {func.__name__}"
                )
                
                return result
            except Exception as e:
                xray.record_step(
                    step_name=step_name or func.__name__,
                    input_data=input_data,
                    output_data={"error": str(e)},
                    reasoning=f"Error in {func.__name__}: {str(e)}"
                )
                raise
        
        return wrapper
    return decorator

