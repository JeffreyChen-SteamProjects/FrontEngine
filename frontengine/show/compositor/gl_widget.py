import ctypes

import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram, compileShader
from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QImage, QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

_VERTEX = '''#version 330 core
layout(location = 0) in vec2 position;
layout(location = 1) in vec2 uv;
out vec2 texcoord;
void main() { gl_Position = vec4(position, 0.0, 1.0); texcoord = uv; }
'''
_FRAGMENT = '''#version 330 core
in vec2 texcoord;
uniform sampler2D layerTexture;
uniform float opacity;
out vec4 color;
void main() { color = texture(layerTexture, texcoord) * opacity; }
'''


class GLCompositor(QOpenGLWidget):
    failed = Signal(str)
    ready = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setAlphaBufferSize(8)
        self.setFormat(fmt)
        self.layers = []
        self._program = self._vbo = self._vao = 0
        self._textures = {}

    def initializeGL(self) -> None:
        self.context().aboutToBeDestroyed.connect(self.cleanup)
        try:
            self._program = compileProgram(compileShader(_VERTEX, GL.GL_VERTEX_SHADER),
                                           compileShader(_FRAGMENT, GL.GL_FRAGMENT_SHADER))
            self._vao = GL.glGenVertexArrays(1)
            self._vbo = GL.glGenBuffers(1)
            GL.glBindVertexArray(self._vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
            for index in (0, 1):
                GL.glEnableVertexAttribArray(index)
                GL.glVertexAttribPointer(index, 2, GL.GL_FLOAT, False, 16, ctypes.c_void_p(index * 8))
            self.ready.emit()
        except Exception as error:
            self.failed.emit(f'OpenGL initialization failed: {error}')

    def paintGL(self) -> None:
        if not self._program:
            return
        try:
            self._paint_layers()
        except Exception as error:
            self.failed.emit(f'OpenGL composition failed: {error}')

    def _paint_layers(self) -> None:
        ratio = self.devicePixelRatioF()
        width, height = round(self.width() * ratio), round(self.height() * ratio)
        GL.glViewport(0, 0, width, height)
        GL.glClearColor(0, 0, 0, 0)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glUseProgram(self._program)
        GL.glBindVertexArray(self._vao)
        GL.glActiveTexture(GL.GL_TEXTURE0)
        GL.glUniform1i(GL.glGetUniformLocation(self._program, 'layerTexture'), 0)
        present = {layer.key for layer in self.layers}
        for key in list(self._textures):
            if key not in present:
                GL.glDeleteTextures([self._textures.pop(key)[0]])
        for layer in sorted(self.layers, key=lambda item: item.z):
            self._draw_layer(layer, ratio, width, height)
        GL.glDisable(GL.GL_SCISSOR_TEST)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

    def _texture(self, layer):
        cached = self._textures.get(layer.key)
        if cached is not None and cached[1] == layer.image.cacheKey():
            return cached[0]
        texture = cached[0] if cached else GL.glGenTextures(1)
        image = layer.image.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
        GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
        GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_NEAREST)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE)
        GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)
        GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, image.width(), image.height(), 0,
                        GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(image.constBits()))
        self._textures[layer.key] = (texture, layer.image.cacheKey())
        return texture

    def _draw_layer(self, layer, ratio, width, height) -> None:
        GL.glBindTexture(GL.GL_TEXTURE_2D, self._texture(layer))
        if layer.clip is None:
            GL.glDisable(GL.GL_SCISSOR_TEST)
        else:
            rect = layer.clip
            GL.glEnable(GL.GL_SCISSOR_TEST)
            GL.glScissor(round(rect.x() * ratio), height - round(rect.bottom() * ratio),
                          max(0, round(rect.width() * ratio)), max(0, round(rect.height() * ratio)))
        logical = layer.image.deviceIndependentSize()
        vertices = []
        for x, y, u, v in ((0, 0, 0, 0), (logical.width(), 0, 1, 0),
                           (0, logical.height(), 0, 1), (logical.width(), logical.height(), 1, 1)):
            point = layer.transform.map(QPointF(x, y))
            vertices.extend((2 * point.x() * ratio / max(1, width) - 1,
                             1 - 2 * point.y() * ratio / max(1, height), u, v))
        data = np.asarray(vertices, dtype=np.float32)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._vbo)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
        GL.glUniform1f(GL.glGetUniformLocation(self._program, 'opacity'), max(0, min(1, layer.opacity)))
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)

    def cleanup(self) -> None:
        context = self.context()
        if context is None or not context.isValid():
            return
        self.makeCurrent()
        for texture, _ in self._textures.values():
            GL.glDeleteTextures([texture])
        self._textures.clear()
        if self._vbo:
            GL.glDeleteBuffers(1, [self._vbo])
        if self._vao:
            GL.glDeleteVertexArrays(1, [self._vao])
        if self._program:
            GL.glDeleteProgram(self._program)
        self._program = self._vbo = self._vao = 0
        self.doneCurrent()
