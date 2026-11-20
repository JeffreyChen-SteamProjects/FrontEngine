"""Can this OpenGL widget draw a see-through window without turning it black?

A see-through overlay keeps the desktop visible only if the transparent pixels reach the desktop
compositor with their alpha intact. A context created without an alpha channel - which some GPUs
and drivers hand back even when one was requested - draws them black instead, and a full-screen
overlay then blacks out the whole screen. Every OpenGL surface in a see-through window checks
this once its context exists: the GPU compositor falls back to software, particles and 3D scenes
stop and say why.
"""
from __future__ import annotations

from PySide6.QtCore import Qt

NO_CONTEXT = 'OpenGL context could not be created'
NO_ALPHA = 'OpenGL surface has no alpha channel'


def alpha_bits(gl) -> int:
    """Alpha bits of the context actually created (the requested format may differ)."""
    context = gl.context()
    surface_format = context.format() if context is not None else gl.format()
    return surface_format.alphaBufferSize()


def see_through_problem(gl) -> str:
    """Why gl cannot draw its window as intended, or '' when it can."""
    if not gl.isValid():
        return NO_CONTEXT
    if gl.window().testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) and alpha_bits(gl) < 8:
        return NO_ALPHA
    return ''
