"""
X-Ray Library - A debugging tool for multi-step algorithmic systems.

Provides transparency into decision-making processes by capturing
inputs, outputs, reasoning, and intermediate states at each step.

The library is designed to be plug-and-play with zero dependencies.
Use it standalone or with optional storage backends.
"""

from .core import XRay, xray_step
from .storage import Storage, StorageBackend, InMemoryStorage

# Optional SQLite storage (no extra dependencies, SQLite is built into Python)
try:
    from .storage_sqlite import SQLiteStorage
    __all__ = ["XRay", "xray_step", "Storage", "StorageBackend", "InMemoryStorage", "SQLiteStorage"]
except ImportError:
    __all__ = ["XRay", "xray_step", "Storage", "StorageBackend", "InMemoryStorage"]

__version__ = "0.1.0"

