"""
X-Ray Library - A debugging tool for multi-step algorithmic systems.

Provides transparency into decision-making processes by capturing
inputs, outputs, reasoning, and intermediate states at each step.
"""

from .core import XRay, xray_step
from .storage import Storage

__version__ = "0.1.0"
__all__ = ["XRay", "xray_step", "Storage"]

