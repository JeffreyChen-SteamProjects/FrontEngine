"""Model and render the pet home's furniture in Blender, one PNG per piece and theme.

Run with Blender 4.2 LTS (no add-ons needed)::

    blender -b --factory-startup -P tools/blender_furniture.py -- frontengine/show/pet_game/furniture
    blender -b --factory-startup -P tools/blender_furniture.py -- --items frontengine/show/pet_game/items

Every piece is built from bevelled, subdivided primitives (no imported meshes),
shaded with a cel ramp so it sits with the flat three-ink pets, outlined by
Freestyle, and rendered orthographically with a transparent background. One
grid cell is one Blender unit and 96 pixels; the image is as wide as the piece's
footprint and its bottom edge is the floor. Each theme only swaps colours.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

PIXELS_PER_CELL = 96
THEMES = {
    "warm_home": {"wood": "#C98A4B", "dark_wood": "#8C5A33", "fabric": "#FFF3D9", "accent": "#F56A24",
                  "accent_2": "#FFC56B", "metal": "#3A3835"},
    "green_studio": {"wood": "#BFA67C", "dark_wood": "#7E6A4A", "fabric": "#ECF3E2", "accent": "#5E9B57",
                     "accent_2": "#A9CF7A", "metal": "#3A3F38"},
    "night_studio": {"wood": "#7B6A9A", "dark_wood": "#4E4368", "fabric": "#DCD8F2", "accent": "#E2A93B",
                     "accent_2": "#8FA7E8", "metal": "#2E2C3E"},
}
FIXED = {"ink": "#171715", "leaf": "#6FA34F", "leaf_dark": "#467A35", "soil": "#5B3A26", "paper": "#FFFDF6",
         "water": "#7FB6E0", "ball": "#F56A24"}


# ----- scene ---------------------------------------------------------------------------------

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.render.use_freestyle = True
    scene.render.line_thickness_mode = "ABSOLUTE"
    scene.render.line_thickness = 2.2
    linesets = scene.view_layers[0].freestyle_settings.linesets
    while len(linesets):                    # the empty default set has no line style and errors
        linesets.remove(linesets[0])
    lineset = linesets.new("outline")
    lineset.select_by_visibility = True
    lineset.select_by_edge_types = True
    lineset.select_silhouette = True
    lineset.select_border = True
    lineset.select_crease = True
    lineset.linestyle.color = hex_rgb(FIXED["ink"])
    lineset.linestyle.thickness = 2.2
    scene.view_layers[0].freestyle_settings.crease_angle = math.radians(135)
    world = bpy.data.worlds.new("world")
    world.color = (1, 1, 1)
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    light = bpy.data.objects.new("sun", sun)
    light.rotation_euler = (math.radians(50), math.radians(-25), math.radians(-35))
    scene.collection.objects.link(light)


def hex_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    srgb = [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


def cel_material(name: str, color: str) -> bpy.types.Material:
    """Lit diffuse turned into three flat bands: shadow, base and a small highlight."""
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    diffuse = nodes.new("ShaderNodeBsdfDiffuse")
    to_rgb = nodes.new("ShaderNodeShaderToRGB")
    ramp = nodes.new("ShaderNodeValToRGB")
    mix = nodes.new("ShaderNodeMix")
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    base = hex_rgb(color)
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs["Factor"].default_value = 1.0
    mix.inputs[6].default_value = (*base, 1)
    ramp.color_ramp.interpolation = "CONSTANT"
    elements = ramp.color_ramp.elements
    elements[0].position, elements[0].color = 0.0, (0.62, 0.6, 0.66, 1)
    elements[1].position, elements[1].color = 0.28, (1, 1, 1, 1)
    highlight = elements.new(0.82)
    highlight.color = (1.12, 1.12, 1.1, 1)
    links.new(diffuse.outputs["BSDF"], to_rgb.inputs["Shader"])
    links.new(to_rgb.outputs["Color"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[7])
    links.new(mix.outputs[2], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    return material


class Palette:
    def __init__(self, theme: dict) -> None:
        self.colors = {**FIXED, **theme}

    def __getitem__(self, role: str) -> bpy.types.Material:
        return cel_material(f"{role}:{self.colors[role]}", self.colors[role])


# ----- modelling helpers -------------------------------------------------------------------------

def _finish(obj, material, bevel: float, smooth: bool) -> bpy.types.Object:
    obj.data.materials.append(material)
    if bevel > 0:
        modifier = obj.modifiers.new("bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = 4
        modifier.limit_method = "ANGLE"
        obj.modifiers.new("normals", "WEIGHTED_NORMAL")
    if smooth:
        bpy.ops.object.shade_smooth()
    return obj


def box(size, location, material, bevel=0.03, rotation=(0, 0, 0)) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(size=1, location=location, rotation=rotation)
    obj = bpy.context.active_object
    obj.scale = size
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, material, bevel, smooth=bevel > 0)


def cylinder(radius, depth, location, material, rotation=(0, 0, 0), bevel=0.02, vertices=48):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, location=location, rotation=rotation,
                                        vertices=vertices)
    return _finish(bpy.context.active_object, material, bevel, smooth=True)


def cone(radius1, radius2, depth, location, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_cone_add(radius1=radius1, radius2=radius2, depth=depth, location=location,
                                    rotation=rotation, vertices=48)
    return _finish(bpy.context.active_object, material, 0.015, smooth=True)


def sphere(radius, location, material, scale=(1, 1, 1)):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location, segments=48, ring_count=24)
    obj = bpy.context.active_object
    obj.scale = scale
    bpy.ops.object.transform_apply(scale=True)
    return _finish(obj, material, 0, smooth=True)


def cushion(size, location, material, softness=2):
    """A rounded box: subdivided so pillows and mattresses look soft."""
    obj = box(size, location, material, bevel=min(size) * 0.3)
    subdivision = obj.modifiers.new("soft", "SUBSURF")
    subdivision.levels = softness
    subdivision.render_levels = softness
    return obj


def torus(major, minor, location, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, location=location, rotation=rotation,
                                     major_segments=48, minor_segments=16)
    return _finish(bpy.context.active_object, material, 0, smooth=True)


def bush(center, size, light, dark, seed=1) -> None:
    """Foliage as overlapping rounded blobs, the way a cartoon draws a plant; deterministic."""
    offsets = ((0, 0, 0.55), (-0.45, 0.1, 0.35), (0.45, -0.1, 0.38), (-0.2, -0.25, 0.85), (0.25, 0.2, 0.9),
               (0, 0, 1.15))
    for index, (x, y, z) in enumerate(offsets):
        radius = size * (0.42 - 0.04 * ((index + seed) % 3))
        material = dark if (index + seed) % 2 else light
        sphere(radius, Vector(center) + Vector((x, y, z)) * size, material, scale=(1.0, 0.85, 0.85))


# ----- furniture ----------------------------------------------------------------------------------
# Each builder works in cells: x across the footprint from 0 to width, z up from the floor at 0.

def bed_basic(p: Palette) -> None:
    box((4.0, 1.6, 0.35), (2.0, 0, 0.42), p["wood"])
    for x in (0.12, 3.88):
        box((0.18, 1.6, 0.42), (x, 0, 0.21), p["dark_wood"])
    box((0.22, 1.7, 1.35), (0.11, 0, 0.68), p["wood"], bevel=0.06)
    box((0.2, 1.7, 0.85), (3.9, 0, 0.42), p["wood"], bevel=0.06)
    cushion((3.6, 1.45, 0.32), (2.0, 0, 0.75), p["fabric"])
    cushion((0.75, 1.1, 0.28), (0.65, 0, 1.0), p["fabric"])
    cushion((2.4, 1.5, 0.12), (2.55, 0, 0.93), p["accent"], softness=1)


def bed_cozy(p: Palette) -> None:
    box((4.0, 1.7, 0.3), (2.0, 0, 0.36), p["dark_wood"], bevel=0.08)
    for x in (0.25, 3.75):
        cylinder(0.12, 0.3, (x, 0.6, 0.15), p["dark_wood"])
        cylinder(0.12, 0.3, (x, -0.6, 0.15), p["dark_wood"])
    head = cushion((0.35, 1.8, 1.55), (0.18, 0, 1.0), p["accent"], softness=2)
    head.name = "headboard"
    cushion((3.7, 1.6, 0.5), (2.05, 0, 0.75), p["fabric"])
    cushion((0.8, 0.7, 0.32), (0.75, 0.38, 1.12), p["fabric"])
    cushion((0.8, 0.7, 0.32), (0.85, -0.38, 1.08), p["accent_2"])
    quilt = cushion((2.6, 1.68, 0.16), (2.55, 0, 1.0), p["accent"], softness=2)
    quilt.name = "quilt"
    cushion((0.35, 1.7, 0.2), (1.35, 0, 1.06), p["accent_2"], softness=2)        # folded-back edge


def table_basic(p: Palette) -> None:
    box((4.0, 1.4, 0.18), (2.0, 0, 1.45), p["wood"], bevel=0.05)
    box((3.7, 1.2, 0.12), (2.0, 0, 1.31), p["dark_wood"], bevel=0.02)
    for x in (0.35, 3.65):
        for y in (0.5, -0.5):
            box((0.16, 0.16, 1.3), (x, y, 0.65), p["dark_wood"], bevel=0.03)
    cylinder(0.32, 0.08, (1.0, 0, 1.58), p["fabric"])
    torus(0.32, 0.06, (1.0, 0, 1.66), p["fabric"])
    cylinder(0.32, 0.08, (3.0, 0, 1.58), p["fabric"])
    torus(0.32, 0.06, (3.0, 0, 1.66), p["fabric"])
    sphere(0.16, (3.0, 0, 1.74), p["accent"], scale=(1, 1, 0.6))
    cylinder(0.13, 0.42, (2.0, 0.1, 1.75), p["accent_2"], bevel=0.03)


def desk_basic(p: Palette) -> None:
    box((3.0, 1.3, 0.16), (1.5, 0, 1.72), p["wood"], bevel=0.05)
    box((1.0, 1.2, 1.6), (2.45, 0, 0.82), p["wood"], bevel=0.04)
    for z in (0.45, 0.95, 1.4):
        box((0.85, 0.08, 0.38), (2.45, -0.62, z), p["dark_wood"], bevel=0.02)
        cylinder(0.05, 0.08, (2.45, -0.68, z), p["metal"], rotation=(math.radians(90), 0, 0))
    for y in (0.5, -0.5):
        box((0.12, 0.12, 1.65), (0.12, y, 0.82), p["dark_wood"], bevel=0.02)
    box((1.0, 0.75, 0.03), (1.0, -0.05, 1.82), p["paper"], bevel=0.0, rotation=(0, 0, math.radians(8)))
    cylinder(0.035, 0.75, (1.25, -0.1, 1.86), p["accent"], rotation=(0, math.radians(90), math.radians(30)))
    cylinder(0.14, 0.25, (2.6, 0.25, 1.92), p["metal"])
    for index, color in enumerate(("accent", "accent_2", "fabric")):
        box((0.12, 0.6, 0.45), (2.25 + index * 0.14, 0.3, 2.02), p[color], bevel=0.02)


def plant_pot(p: Palette) -> None:
    cone(0.36, 0.26, 0.6, (0.5, 0, 0.3), p["accent"])
    torus(0.36, 0.05, (0.5, 0, 0.6), p["accent"])
    cylinder(0.31, 0.04, (0.5, 0, 0.58), p["soil"], bevel=0.0)
    bush((0.5, 0, 0.45), 0.62, p["leaf"], p["leaf_dark"], seed=2)


def wall_lamp(p: Palette) -> None:
    cylinder(0.28, 0.08, (0.5, 0, 0.04), p["metal"])
    cylinder(0.04, 1.2, (0.5, 0, 0.66), p["metal"], bevel=0.0)
    cone(0.36, 0.2, 0.42, (0.5, 0, 1.38), p["accent_2"])
    sphere(0.1, (0.5, 0, 1.2), p["fabric"])


def toy_box(p: Palette) -> None:
    box((2.0, 1.2, 0.95), (1.0, 0, 0.48), p["accent"], bevel=0.06)
    for x in (0.25, 1.75):
        box((0.12, 1.25, 0.9), (x, 0, 0.48), p["dark_wood"], bevel=0.02)
    lid = box((2.05, 1.25, 0.12), (1.0, 0.25, 1.15), p["accent"], bevel=0.04,
              rotation=(math.radians(-28), 0, 0))
    lid.name = "lid"
    sphere(0.22, (0.6, -0.1, 1.08), p["ball"])
    box((0.32, 0.32, 0.32), (1.1, -0.1, 1.02), p["fabric"], bevel=0.04, rotation=(0, 0, math.radians(20)))
    box((0.26, 0.26, 0.26), (1.45, 0.05, 1.05), p["accent_2"], bevel=0.04, rotation=(0, 0, math.radians(-15)))
    torus(0.13, 0.04, (1.0, -0.62, 0.65), p["metal"], rotation=(math.radians(90), 0, 0))


def armchair(p: Palette) -> None:
    cushion((1.9, 1.3, 0.55), (1.0, 0, 0.55), p["accent"])
    cushion((0.42, 1.35, 1.35), (0.24, 0, 0.95), p["accent"])
    for y in (0.62, -0.62):
        cushion((1.8, 0.3, 0.75), (1.0, y, 0.75), p["accent"])
    cushion((1.35, 1.0, 0.25), (1.15, 0, 0.92), p["fabric"])
    for x in (0.2, 1.8):
        cone(0.07, 0.04, 0.3, (x, -0.5, 0.15), p["dark_wood"])
        cone(0.07, 0.04, 0.3, (x, 0.5, 0.15), p["dark_wood"])


def stool(p: Palette) -> None:
    cylinder(0.42, 0.14, (0.5, 0, 0.8), p["wood"], bevel=0.04)
    for angle in (45, 135, 225, 315):
        x = 0.5 + math.cos(math.radians(angle)) * 0.28
        y = math.sin(math.radians(angle)) * 0.28
        cylinder(0.05, 0.8, (x, y, 0.38), p["dark_wood"], rotation=(0, math.radians(6), math.radians(angle)))
    torus(0.27, 0.025, (0.5, 0, 0.32), p["dark_wood"])


def planter(p: Palette) -> None:
    box((2.0, 1.1, 0.75), (1.0, 0, 0.55), p["wood"], bevel=0.05)
    for x in (0.12, 1.88):
        box((0.14, 1.12, 0.95), (x, 0, 0.48), p["dark_wood"], bevel=0.02)
    for z in (0.35, 0.6):
        box((1.9, 0.05, 0.05), (1.0, -0.57, z), p["dark_wood"], bevel=0.0)
    box((1.8, 0.95, 0.1), (1.0, 0, 0.92), p["soil"], bevel=0.02)
    for index, x in enumerate((0.42, 1.0, 1.5)):
        bush((x, 0, 0.82), 0.32 + 0.04 * index, p["leaf"], p["leaf_dark"], seed=index)
    cylinder(0.16, 0.3, (1.7, -0.25, 1.12), p["accent"])
    cylinder(0.03, 0.3, (1.88, -0.25, 1.22), p["accent"], rotation=(0, math.radians(55), 0))


def workbench(p: Palette) -> None:
    box((3.0, 1.3, 0.22), (1.5, 0, 1.4), p["wood"], bevel=0.05)
    for x in (0.2, 2.8):
        for y in (0.5, -0.5):
            box((0.18, 0.18, 1.3), (x, y, 0.65), p["dark_wood"], bevel=0.03)
    box((2.7, 1.1, 0.08), (1.5, 0, 0.35), p["dark_wood"], bevel=0.02)
    for index in range(3):
        box((1.8, 0.28, 0.1), (1.4, -0.3 + index * 0.3, 0.45 + index * 0.1), p["wood"], bevel=0.02)
    box((0.35, 0.5, 0.3), (2.6, -0.3, 1.65), p["metal"], bevel=0.03)
    cylinder(0.04, 0.5, (2.6, -0.6, 1.62), p["metal"], rotation=(math.radians(90), 0, 0))
    box((0.5, 0.3, 0.25), (1.3, 0, 1.64), p["fabric"], bevel=0.03)
    cylinder(0.035, 0.6, (0.75, -0.2, 1.6), p["wood"], rotation=(0, math.radians(90), math.radians(-20)))
    box((0.22, 0.14, 0.14), (0.48, -0.1, 1.6), p["metal"], bevel=0.02, rotation=(0, 0, math.radians(-20)))
    for x in (0.4, 1.2, 2.0):
        torus(0.06, 0.015, (x, -0.66, 1.1), p["metal"], rotation=(math.radians(90), 0, 0))


PIECES = {"bed_basic": (4, bed_basic), "bed_cozy": (4, bed_cozy), "table_basic": (4, table_basic),
          "desk_basic": (3, desk_basic), "plant_pot": (1, plant_pot), "wall_lamp": (1, wall_lamp),
          "toy_box": (2, toy_box), "armchair": (2, armchair), "stool": (1, stool), "planter": (2, planter),
          "workbench": (3, workbench)}


# ----- items: materials, harvests and goods -------------------------------------------------------
# Square icons for the backpack, shop and work lists, centred on the origin, warm-home colours.

def item_wood(p: Palette) -> None:
    for index, (y, z) in enumerate(((-0.28, 0.22), (0.28, 0.22), (0.0, 0.62))):
        log = cylinder(0.24, 1.3, (0, y, z), p["wood"], rotation=(0, math.radians(90), math.radians(12)))
        log.name = f"log{index}"
        for side in (-1, 1):
            cap = Vector((0, 0, side * 0.655))             # along the log's own axis
            cap.rotate(log.rotation_euler)
            cylinder(0.2, 0.02, Vector((0, y, z)) + cap, p["fabric"],
                     rotation=(0, math.radians(90), math.radians(12)), bevel=0.0)
    torus(0.5, 0.035, (0, 0, 0.38), p["accent"], rotation=(0, math.radians(90), math.radians(12)))


def item_herb(p: Palette) -> None:
    for index, angle in enumerate((-22, -8, 6, 20)):
        stem = cylinder(0.025, 1.0, (0, 0, 0.5), p["leaf_dark"], rotation=(0, math.radians(angle), 0), bevel=0.0)
        top = Vector((0, 0, 0.5))
        top.rotate(stem.rotation_euler)
        sphere(0.18, Vector((0, 0, 0.5)) + top * 1.6, p["leaf"] if index % 2 else p["leaf_dark"],
               scale=(1.0, 0.6, 1.4))
    torus(0.07, 0.03, (0, 0, 0.35), p["accent_2"])


def item_flower(p: Palette) -> None:
    cone(0.36, 0.08, 0.8, (0, 0, 0.4), p["fabric"], rotation=(math.radians(180), 0, 0))
    for (x, y, z), color in (((-0.18, 0, 1.0), "accent"), ((0.2, 0.05, 1.05), "accent_2"), ((0.0, -0.1, 1.2), "ball")):
        center = Vector((x, y, z))
        for k in range(6):
            angle = k * math.tau / 6
            sphere(0.09, center + Vector((math.cos(angle) * 0.12, 0, math.sin(angle) * 0.12)), p[color],
                   scale=(1, 0.5, 1))
        sphere(0.07, center + Vector((0, -0.04, 0)), p["accent_2"] if color != "accent_2" else p["fabric"])
    for x in (-0.1, 0.1):
        sphere(0.12, (x, 0.05, 0.85), p["leaf"], scale=(1.2, 0.5, 0.6))


def item_toy(p: Palette) -> None:
    sphere(0.42, (0, 0, 0.42), p["accent_2"], scale=(1, 0.9, 1))
    sphere(0.32, (0, 0, 1.05), p["accent_2"])
    for side in (-1, 1):
        sphere(0.12, (side * 0.24, 0, 1.3), p["accent_2"])
        sphere(0.06, (side * 0.11, -0.29, 1.1), p["ink"])
        sphere(0.13, (side * 0.38, -0.05, 0.55), p["accent_2"])
    sphere(0.1, (0, -0.28, 0.98), p["fabric"], scale=(1.2, 0.6, 0.8))
    torus(0.18, 0.04, (0, -0.12, 0.78), p["accent"], rotation=(math.radians(70), 0, 0))


def item_coin(p: Palette) -> None:
    for index in range(3):
        cylinder(0.42, 0.11, (0.04 * index, 0, 0.06 + index * 0.12), p["accent_2"], bevel=0.03)
    cylinder(0.3, 0.02, (0.08, 0, 0.4), p["accent"], bevel=0.0)


def item_letter(p: Palette) -> None:
    box((1.3, 0.06, 0.85), (0, 0, 0.43), p["paper"], bevel=0.03)
    for side in (-1, 1):                                   # the flap's two folds
        box((0.78, 0.02, 0.06), (side * 0.3, -0.04, 0.6), p["fabric"], bevel=0.0,
            rotation=(0, side * math.radians(-33), 0))
    cylinder(0.11, 0.04, (0, -0.06, 0.43), p["accent"], rotation=(math.radians(90), 0, 0))


def item_story(p: Palette) -> None:
    box((1.0, 0.24, 1.3), (0, 0, 0.65), p["accent"], bevel=0.05)
    box((0.9, 0.2, 1.22), (0.06, -0.03, 0.65), p["paper"], bevel=0.02)
    box((0.12, 0.26, 1.3), (-0.5, 0, 0.65), p["dark_wood"], bevel=0.03)
    box((0.5, 0.02, 0.08), (0.05, -0.13, 0.95), p["accent_2"], bevel=0.0)


ITEMS = {"wood": item_wood, "herb": item_herb, "flower": item_flower, "toy": item_toy, "coin": item_coin,
         "letter": item_letter, "story": item_story}
ITEM_PIXELS = 128


def frame_icon(target: Path) -> None:
    """A three-quarter view filling a square icon with a little margin."""
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    camera_data = bpy.data.cameras.new("camera")
    camera_data.type = "ORTHO"
    camera = bpy.data.objects.new("camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.rotation_euler = (math.radians(62), 0, math.radians(-24))
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for obj in meshes for c in obj.bound_box]
    view = camera.matrix_world.to_3x3().inverted()
    xs = [(view @ point).x for point in corners]
    ys = [(view @ point).y for point in corners]
    camera_data.ortho_scale = max(max(xs) - min(xs), max(ys) - min(ys)) * 1.12
    scene.render.resolution_x = scene.render.resolution_y = ITEM_PIXELS
    scene.render.resolution_percentage = 100
    center = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    camera.location = camera.matrix_world.to_3x3() @ center + camera.matrix_world.to_3x3() @ Vector((0, 0, 30))
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)


def render_items(output: Path, only: set) -> None:
    for name, build in ITEMS.items():
        if name not in only:
            continue
        reset_scene()
        build(Palette(THEMES["warm_home"]))
        target = output / f"{name}.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        frame_icon(target)
        print(f"rendered {target}")


# ----- framing and rendering ------------------------------------------------------------------------

def frame_and_render(width_cells: int, target: Path) -> None:
    """Turn the piece a little for depth, then frame it so the floor is the image's bottom edge."""
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    pivot = Vector((width_cells / 2, 0, 0))
    for obj in meshes:
        obj.location -= pivot
    bpy.ops.object.select_all(action="DESELECT")
    camera_data = bpy.data.cameras.new("camera")
    camera_data.type = "ORTHO"
    camera_data.sensor_fit = "HORIZONTAL"        # ortho_scale is the width even for tall pieces
    camera = bpy.data.objects.new("camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    elevation = math.radians(14)
    camera.rotation_euler = (math.radians(90) - elevation, 0, math.radians(-18))
    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(c) for obj in meshes for c in obj.bound_box]
    view = camera.matrix_world.to_3x3().inverted()
    xs = [(view @ point).x for point in corners]
    ys = [(view @ point).y for point in corners]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    camera_data.ortho_scale = span_x * 1.04
    width_px = width_cells * PIXELS_PER_CELL
    height_px = max(32, round(width_px * span_y / span_x * 1.0) + 8)
    scene.render.resolution_x, scene.render.resolution_y = width_px, height_px
    scene.render.resolution_percentage = 100
    center = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    world_center = camera.matrix_world.to_3x3() @ center
    camera.location = world_center + camera.matrix_world.to_3x3() @ Vector((0, 0, 30))   # looks down its -Z
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)


def main() -> None:
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if arguments and arguments[0] == "--items":           # -- --items <folder> [names]
        render_items(Path(arguments[1]).resolve(), set(arguments[2].split(",")) if len(arguments) > 2 else set(ITEMS))
        return
    output = Path(arguments[0] if arguments else "furniture").resolve()
    only = set(arguments[1].split(",")) if len(arguments) > 1 else set(PIECES)
    for theme, colors in THEMES.items():
        for name, (width, build) in PIECES.items():
            if name not in only:
                continue
            reset_scene()
            build(Palette(colors))
            target = output / theme / f"{name}.png"
            target.parent.mkdir(parents=True, exist_ok=True)
            frame_and_render(width, target)
            print(f"rendered {target}")


if __name__ == "__main__":
    main()
