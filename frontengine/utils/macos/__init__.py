"""Lazy public-framework macOS integration; importing it does not request TCC access."""
from .backend import Capability, MacOSBackend, get_backend

__all__ = ['Capability', 'MacOSBackend', 'get_backend']
