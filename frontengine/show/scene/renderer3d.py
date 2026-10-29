"""OpenGL 3.3 scene renderer shared by editor, desktop and offscreen output."""
from __future__ import annotations

import ctypes
import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram, compileShader
from PySide6.QtGui import QImage

VERTEX = '''#version 330 core
layout(location=0) in vec3 position;
layout(location=1) in vec3 normal;
layout(location=2) in vec2 uv;
layout(location=3) in vec2 uv1;
layout(location=4) in vec4 vertexColor;
uniform mat4 model, viewProjection;
out vec3 worldPosition, worldNormal;
out vec2 texcoord, texcoord1;
out vec4 tint;
void main() {
    vec4 p=model*vec4(position,1);
    worldPosition=p.xyz;
    worldNormal=transpose(inverse(mat3(model)))*normal;
    texcoord=uv; texcoord1=uv1; tint=vertexColor;
    gl_Position=viewProjection*p;
}
'''
FRAGMENT = '''#version 330 core
in vec3 worldPosition, worldNormal;
in vec2 texcoord, texcoord1;
in vec4 tint;
out vec4 color;
uniform sampler2D baseTexture, metalTexture, normalTexture, occlusionTexture, emissiveTexture;
uniform bool hasTexture[5];
uniform mat3 uvTransform[5];
uniform int uvSet[5];
uniform vec4 baseColor;
uniform vec3 emissive, eye;
uniform float metallic, roughness, opacity, cutoff, normalStrength, occlusionStrength;
uniform int alphaMode, lightCount;
uniform bool unlit, selected;
uniform vec3 lightPosition[8], lightColor[8], lightDirection[8];
uniform float lightIntensity[8];
uniform int lightKind[8];
const float PI=3.14159265;
vec2 tc(int i) { return (uvTransform[i]*vec3(uvSet[i]==0?texcoord:texcoord1,1)).xy; }
vec3 linearColor(vec3 c) { return pow(max(c,vec3(0)),vec3(2.2)); }
void main() {
    if(selected) { color=vec4(1,.78,.08,1); return; }
    vec4 base=baseColor*tint;
    if(hasTexture[0]) { vec4 t=texture(baseTexture,tc(0)); base*=vec4(linearColor(t.rgb),t.a); }
    if(alphaMode==1 && base.a<cutoff) discard;
    float alpha=(alphaMode==2?base.a:1)*opacity;
    vec3 n=normalize(worldNormal);
    if(!gl_FrontFacing) n=-n;
    if(hasTexture[2]) {
        vec3 q1=dFdx(worldPosition), q2=dFdy(worldPosition);
        vec2 st1=dFdx(tc(2)), st2=dFdy(tc(2));
        vec3 t=normalize(q1*st2.y-q2*st1.y);
        vec3 b=-normalize(cross(n,t));
        vec3 mapped=texture(normalTexture,tc(2)).xyz*2-1;
        mapped.xy*=normalStrength;
        n=normalize(mat3(t,b,n)*mapped);
    }
    float metal=metallic, rough=max(.045,roughness);
    if(hasTexture[1]) { vec4 mr=texture(metalTexture,tc(1)); metal*=mr.b; rough=max(.045,rough*mr.g); }
    vec3 v=normalize(eye-worldPosition), f0=mix(vec3(.04),base.rgb,metal);
    float ao=hasTexture[3]?mix(1,texture(occlusionTexture,tc(3)).r,occlusionStrength):1;
    vec3 result=base.rgb*.16*ao;
    for(int i=0;i<lightCount;i++) {
        vec3 delta=lightPosition[i]-worldPosition;
        vec3 l=lightKind[i]==0?normalize(-lightDirection[i]):normalize(delta);
        float attenuation=lightKind[i]==0?1:1/max(1,dot(delta,delta));
        vec3 h=normalize(v+l);
        float ndl=max(dot(n,l),0), ndv=max(dot(n,v),.001), ndh=max(dot(n,h),0), vdh=max(dot(v,h),0);
        float a=rough*rough, a2=a*a, d=ndh*ndh*(a2-1)+1;
        float distribution=a2/max(PI*d*d,.0001);
        float k=(rough+1)*(rough+1)/8;
        float geometry=ndv/(ndv*(1-k)+k)*ndl/max(ndl*(1-k)+k,.0001);
        vec3 fresnel=f0+(1-f0)*pow(1-vdh,5);
        vec3 specular=distribution*geometry*fresnel/max(4*ndv*ndl,.0001);
        vec3 diffuse=(1-fresnel)*(1-metal)*base.rgb/PI;
        result+=(diffuse+specular)*lightColor[i]*lightIntensity[i]*attenuation*ndl;
    }
    vec3 emission=emissive;
    if(hasTexture[4]) emission*=linearColor(texture(emissiveTexture,tc(4)).rgb);
    result=(unlit?base.rgb:result)+emission;
    color=vec4(pow(max(result,vec3(0)),vec3(1/2.2))*alpha,alpha);
}
'''


class Scene3DRenderer:
    """All methods require the owner's context current. Never binds framebuffer zero."""
    def __init__(self):
        self.program = 0
        self.meshes, self.textures, self.locations = {}, {}, {}
        self._post_program = self._post_vao = self._post_texture = 0
        self._post_image_key = None
        self._mesh_data = {}
        self._gpu_bytes, self._framebuffer_bytes, self._texture_sizes = 0, 0, {}

    def _reserve(self, size):
        if self._gpu_bytes+self._framebuffer_bytes+size > 512*1024*1024:
            raise ValueError('3D scene exceeds the 512 MiB GPU resource budget')
        self._gpu_bytes += size

    @staticmethod
    def _texture_signature(image, sampler):
        sampler = sampler or {}
        return (image.cacheKey(), sampler.get('wrapS', GL.GL_REPEAT), sampler.get('wrapT', GL.GL_REPEAT),
                sampler.get('magFilter', GL.GL_LINEAR), sampler.get('minFilter', GL.GL_LINEAR_MIPMAP_LINEAR))

    def initialize(self):
        version = GL.glGetString(GL.GL_VERSION)
        if not version:
            raise RuntimeError('A desktop OpenGL 3.3 context is required')
        self.program = compileProgram(compileShader(VERTEX, GL.GL_VERTEX_SHADER),
                                      compileShader(FRAGMENT, GL.GL_FRAGMENT_SHADER))

    def uniform(self, name):
        if name not in self.locations:
            self.locations[name] = GL.glGetUniformLocation(self.program, name)
        return self.locations[name]

    def matrix(self, name, value):
        value = np.ascontiguousarray(np.asarray(value, np.float32).T)
        GL.glUniformMatrix4fv(self.uniform(name), 1, False, value)

    def texture(self, image, sampler=None):
        sampler = sampler or {}
        signature = self._texture_signature(image, sampler)
        if signature not in self.textures:
            maximum = GL.glGetIntegerv(GL.GL_MAX_TEXTURE_SIZE)
            if image.width() > maximum or image.height() > maximum:
                raise ValueError('Texture exceeds the GPU texture size limit')
            size = (image.width()*image.height()*16+2)//3
            self._reserve(size)
            self._texture_sizes[signature] = size
            texture = GL.glGenTextures(1)
            self.textures[signature] = texture
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            image = image.convertToFormat(QImage.Format.Format_RGBA8888)
            GL.glPixelStorei(GL.GL_UNPACK_ALIGNMENT, 1)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, image.width(), image.height(), 0,
                            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(image.constBits()))
            for name, value in ((GL.GL_TEXTURE_WRAP_S, signature[1]), (GL.GL_TEXTURE_WRAP_T, signature[2]),
                                (GL.GL_TEXTURE_MAG_FILTER, signature[3]), (GL.GL_TEXTURE_MIN_FILTER, signature[4])):
                GL.glTexParameteri(GL.GL_TEXTURE_2D, name, value)
            GL.glGenerateMipmap(GL.GL_TEXTURE_2D)
        self._used_textures.add(signature)
        return self.textures[signature]

    def mesh(self, source, positions, normals):
        key = id(source)
        if key not in self.meshes:
            self._reserve(len(positions)*56+source.indices.nbytes)
            vao, vbo, ebo = GL.glGenVertexArrays(1), GL.glGenBuffers(1), GL.glGenBuffers(1)
            self.meshes[key] = (vao, vbo, ebo)
            GL.glBindVertexArray(vao)
            GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
            for index, count, offset in ((0, 3, 0), (1, 3, 3), (2, 2, 6), (3, 2, 8), (4, 4, 10)):
                GL.glEnableVertexAttribArray(index)
                GL.glVertexAttribPointer(index, count, GL.GL_FLOAT, False, 56, ctypes.c_void_p(offset*4))
            GL.glBindBuffer(GL.GL_ELEMENT_ARRAY_BUFFER, ebo)
            GL.glBufferData(GL.GL_ELEMENT_ARRAY_BUFFER, source.indices.nbytes, source.indices, GL.GL_STATIC_DRAW)
        vao, vbo, _ = self.meshes[key]
        GL.glBindVertexArray(vao)
        cached = self._mesh_data.get(key)
        if cached is not None and cached[0] is positions and cached[1] is normals:
            return
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, vbo)
        uv1 = source.uv1 if source.uv1 is not None else source.uv
        colors = source.colors if source.colors is not None else np.ones((len(positions), 4), np.float32)
        data = np.ascontiguousarray(np.column_stack([positions, normals, source.uv, uv1, colors]), np.float32)
        GL.glBufferData(GL.GL_ARRAY_BUFFER, data.nbytes, data, GL.GL_DYNAMIC_DRAW)
        self._mesh_data[key] = positions, normals

    def blend_transition(self, current_texture, previous, ratio, framebuffer, width, height):
        if not self._post_program:
            vertex = '''#version 330 core
            out vec2 uv;
            void main() { vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);
                uv=p; gl_Position=vec4(p*2-1,0,1); }'''
            fragment = '''#version 330 core
            in vec2 uv; out vec4 color;
            uniform sampler2D currentFrame, previousFrame; uniform float ratio;
            void main() { color=mix(texture(previousFrame,vec2(uv.x,1-uv.y)),texture(currentFrame,uv),ratio); }'''
            self._post_program = compileProgram(compileShader(vertex, GL.GL_VERTEX_SHADER),
                                                 compileShader(fragment, GL.GL_FRAGMENT_SHADER))
            self._post_vao = GL.glGenVertexArrays(1)
        if self._post_image_key != previous.cacheKey():
            if self._post_texture:
                GL.glDeleteTextures([self._post_texture])
            self._post_texture = GL.glGenTextures(1)
            self._post_image_key = previous.cacheKey()
            image = previous.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
            GL.glBindTexture(GL.GL_TEXTURE_2D, self._post_texture)
            GL.glTexImage2D(GL.GL_TEXTURE_2D, 0, GL.GL_RGBA8, image.width(), image.height(), 0,
                            GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, bytes(image.constBits()))
            for name, value in ((GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR), (GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR),
                                (GL.GL_TEXTURE_WRAP_S, GL.GL_CLAMP_TO_EDGE), (GL.GL_TEXTURE_WRAP_T, GL.GL_CLAMP_TO_EDGE)):
                GL.glTexParameteri(GL.GL_TEXTURE_2D, name, value)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, framebuffer)
        GL.glViewport(0, 0, width, height)
        GL.glDisable(GL.GL_DEPTH_TEST)
        GL.glDisable(GL.GL_CULL_FACE)
        GL.glDisable(GL.GL_BLEND)
        GL.glUseProgram(self._post_program)
        GL.glBindVertexArray(self._post_vao)
        for index, name, texture in ((0, 'currentFrame', current_texture), (1, 'previousFrame', self._post_texture)):
            GL.glActiveTexture(GL.GL_TEXTURE0+index)
            GL.glBindTexture(GL.GL_TEXTURE_2D, texture)
            GL.glUniform1i(GL.glGetUniformLocation(self._post_program, name), index)
        GL.glUniform1f(GL.glGetUniformLocation(self._post_program, 'ratio'), ratio)
        GL.glDrawArrays(GL.GL_TRIANGLES, 0, 3)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)

    def render(self, runtime, width, height, framebuffer, camera=None, selected=(), data=None, framebuffer_copies=1):
        if not self.program:
            raise RuntimeError('3D renderer is not initialized')
        if width*height > 16_777_216:
            raise ValueError('3D viewport exceeds the 16 megapixel framebuffer budget')
        self._framebuffer_bytes = width*height*8*framebuffer_copies
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, framebuffer)
        GL.glViewport(0, 0, width, height)
        background = runtime.document.background
        GL.glClearColor(background[0]*background[3], background[1]*background[3], background[2]*background[3], background[3])
        GL.glDepthMask(True)
        GL.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)
        canvas = runtime.document.canvas
        scale = min(width/canvas[0], height/canvas[1])
        viewport = (round((width-canvas[0]*scale)/2), round((height-canvas[1]*scale)/2),
                    max(1, round(canvas[0]*scale)), max(1, round(canvas[1]*scale)))
        GL.glViewport(*viewport)
        GL.glUseProgram(self.program)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_ONE, GL.GL_ONE_MINUS_SRC_ALPHA)
        GL.glEnable(GL.GL_DEPTH_TEST)
        GL.glDepthFunc(GL.GL_LEQUAL)
        self._used_textures = set()
        data = runtime.render_data(camera) if data is None else data
        expected = {self._texture_signature(info['image'], info.get('sampler')) for draw in data['draws']
                    for info in draw['mesh'].material.textures.values()}
        for signature in set(self.textures)-expected:
            GL.glDeleteTextures([self.textures.pop(signature)])
            self._gpu_bytes -= self._texture_sizes.pop(signature)
        self._reserve(0)
        self.matrix('viewProjection', data['vp'])
        GL.glUniform3f(self.uniform('eye'), *data['eye'])
        lights = data['lights'][:8]
        GL.glUniform1i(self.uniform('lightCount'), len(lights))
        for i, (kind, matrix, color, intensity) in enumerate(lights):
            GL.glUniform3f(self.uniform(f'lightPosition[{i}]'), *matrix[:3, 3])
            GL.glUniform3f(self.uniform(f'lightDirection[{i}]'), *(-matrix[:3, 2]))
            GL.glUniform3f(self.uniform(f'lightColor[{i}]'), *color)
            GL.glUniform1f(self.uniform(f'lightIntensity[{i}]'), intensity)
            GL.glUniform1i(self.uniform(f'lightKind[{i}]'), 0 if kind == 'directional' else 1)
        world, screen = [], []
        for draw in data['draws']:
            (screen if draw['screen'] else world).append(draw)
        opaque = [d for d in world if d['mesh'].material.alpha_mode != 'BLEND' and d['opacity'] >= 1]
        transparent = [d for d in world if d['mesh'].material.alpha_mode == 'BLEND' or d['opacity'] < 1]
        transparent.sort(key=lambda d: -np.linalg.norm(d['matrix'][:3, 3]-data['eye']))
        for draw in opaque+transparent:
            GL.glDepthMask(draw['mesh'].material.alpha_mode != 'BLEND' and draw['opacity'] >= 1)
            self.draw(draw)
        GL.glDepthMask(False)
        GL.glDisable(GL.GL_DEPTH_TEST)
        self.matrix('viewProjection', data['screen_vp'])
        for draw in sorted(screen, key=lambda d: d['z']):
            self.draw(draw)
        self.matrix('viewProjection', data['vp'])
        if selected:
            GL.glEnable(GL.GL_DEPTH_TEST)
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_LINE)
            for draw in world:
                if draw['key'] in selected:
                    self.draw(draw, selected=True)
            GL.glPolygonMode(GL.GL_FRONT_AND_BACK, GL.GL_FILL)
        GL.glDepthMask(True)
        GL.glBindVertexArray(0)
        GL.glUseProgram(0)
        for key in set(self.textures)-self._used_textures:
            GL.glDeleteTextures([self.textures.pop(key)])
            self._gpu_bytes -= self._texture_sizes.pop(key)

    def draw(self, draw, selected=False):
        mesh, material = draw['mesh'], draw['mesh'].material
        if material.double_sided:
            GL.glDisable(GL.GL_CULL_FACE)
        else:
            GL.glEnable(GL.GL_CULL_FACE)
            GL.glCullFace(GL.GL_BACK)
        GL.glFrontFace(GL.GL_CW if np.linalg.det(draw['matrix'][:3, :3]) < 0 else GL.GL_CCW)
        self.mesh(mesh, draw['positions'], draw['normals'])
        self.matrix('model', draw['matrix'])
        GL.glUniform4f(self.uniform('baseColor'), *material.color)
        GL.glUniform3f(self.uniform('emissive'), *material.emissive)
        GL.glUniform1f(self.uniform('metallic'), material.metallic)
        GL.glUniform1f(self.uniform('roughness'), material.roughness)
        GL.glUniform1f(self.uniform('opacity'), draw['opacity'])
        GL.glUniform1f(self.uniform('cutoff'), material.cutoff)
        GL.glUniform1i(self.uniform('alphaMode'), {'OPAQUE': 0, 'MASK': 1, 'BLEND': 2}[material.alpha_mode])
        GL.glUniform1i(self.uniform('unlit'), material.unlit)
        GL.glUniform1i(self.uniform('selected'), selected)
        for i, name in enumerate(('base', 'metal', 'normal', 'occlusion', 'emissive')):
            info = material.textures.get(name)
            GL.glUniform1i(self.uniform(f'hasTexture[{i}]'), info is not None)
            GL.glUniform1i(self.uniform(f'{name}Texture'), i)
            if info:
                GL.glActiveTexture(GL.GL_TEXTURE0+i)
                GL.glBindTexture(GL.GL_TEXTURE_2D, self.texture(info['image'], info.get('sampler')))
                transform = info.get('transform', {})
                offset, scale, angle = transform.get('offset', [0, 0]), transform.get('scale', [1, 1]), transform.get('rotation', 0)
                c, s = np.cos(angle), np.sin(angle)
                matrix = np.array([[c*scale[0], -s*scale[1], offset[0]], [s*scale[0], c*scale[1], offset[1]], [0, 0, 1]], np.float32)
                GL.glUniformMatrix3fv(self.uniform(f'uvTransform[{i}]'), 1, False, np.ascontiguousarray(matrix.T))
                GL.glUniform1i(self.uniform(f'uvSet[{i}]'), info.get('uv', 0))
            if name in ('normal', 'occlusion'):
                GL.glUniform1f(self.uniform(name+'Strength'), info.get('strength', 1) if info else 1)
        GL.glDrawElements(GL.GL_TRIANGLES, len(mesh.indices), GL.GL_UNSIGNED_INT, None)

    def close(self):
        for vao, vbo, ebo in self.meshes.values():
            GL.glDeleteBuffers(2, [vbo, ebo])
            GL.glDeleteVertexArrays(1, [vao])
        for texture in self.textures.values():
            GL.glDeleteTextures([texture])
        if self.program:
            GL.glDeleteProgram(self.program)
        if self._post_program:
            GL.glDeleteProgram(self._post_program)
            GL.glDeleteVertexArrays(1, [self._post_vao])
        if self._post_texture:
            GL.glDeleteTextures([self._post_texture])
        self._post_program = self._post_vao = self._post_texture = 0
        self._post_image_key = None
        self.program = 0
        self.meshes.clear()
        self.textures.clear()
        self.locations.clear()
        self._mesh_data.clear()
        self._gpu_bytes, self._framebuffer_bytes = 0, 0
        self._texture_sizes.clear()
