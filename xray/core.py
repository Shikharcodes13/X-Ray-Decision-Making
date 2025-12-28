"""
Core X-Ray library for capturing decision context.
"""

import uuid
import json
from datetime import datetime
from typing import Any, Dict, Optional, Callable
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
    
    def __init__(self, execution_id: Optional[str] = None, storage: Optional[Any] = None, auto_save: bool = True):
        """
        Initialize X-Ray context.
        
        Args:
            execution_id: Optional execution ID. If None, generates a new UUID.
            storage: Storage instance implementing StorageBackend interface.
                    If None, no persistence (data only available during execution).
            auto_save: If True, automatically save to storage on context exit.
                      If False, you must manually call get_execution() to access data.
        """
        self.execution_id = execution_id or str(uuid.uuid4())
        self.storage = storage
        self.auto_save = auto_save
        self.steps: list = []
        self.metadata: Dict[str, Any] = {
            "started_at": datetime.utcnow().isoformat(),
            "execution_id": self.execution_id
        }
        self._active = False
    
    def __enter__(self):
        """Enter context manager."""
        self._active = True
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and optionally save execution."""
        self._active = False
        self.metadata["completed_at"] = datetime.utcnow().isoformat()
        self.metadata["total_steps"] = len(self.steps)
        
        if self.storage and self.auto_save:
            self.storage.save_execution(
                execution_id=self.execution_id,
                metadata=self.metadata,
                steps=self.steps
            )
        
        return False
    
    def get_execution(self) -> Dict[str, Any]:
        """
        Get the current execution data.
        
        Returns:
            Dictionary containing execution_id, metadata, and steps
        """
        return {
            "execution_id": self.execution_id,
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
        
        self.storage.save_execution(
            execution_id=self.execution_id,
            metadata=self.metadata,
            steps=self.steps
        )
    
    def record_step(
        self,
        step_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        reasoning: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Record a step in the execution.
        
        Args:
            step_name: Name/identifier of the step
            input_data: Input data for this step
            output_data: Output data from this step
            reasoning: Human-readable explanation of the decision
            **kwargs: Additional fields to include in the step record
        
        Returns:
            The recorded step dictionary
        """
        if not self._active:
            raise RuntimeError("XRay context is not active. Use 'with XRay() as xray:'")
        
        step = {
            "step": step_name,
            "timestamp": datetime.utcnow().isoformat(),
            "input": input_data or {},
            "output": output_data or {},
            "reasoning": reasoning,
            **kwargs
        }
        
        self.steps.append(step)
        return step
    
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

