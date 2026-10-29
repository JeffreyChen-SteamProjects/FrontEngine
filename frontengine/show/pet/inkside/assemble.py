"""Turn a template and a pose into the ordered elements of one frame."""
from __future__ import annotations

from pathlib import Path

from frontengine.show.pet.inkside.builder import AssetWriter, Element, build_actions, manifest
from frontengine.show.pet.inkside.garments import Garment
from frontengine.show.pet.inkside.rig import Pose
from frontengine.show.pet.inkside.template import Template

# Back pieces sit below 15, torso garments 31..39, neckwear 46..49 and hats 60..64,
# between the character layers listed here.
Z = {'tail': 10, 'foot_l': 20, 'foot_r': 21, 'body': 30, 'arm_l': 40, 'arm_r': 42,
     'ears_back': 45, 'head': 50, 'head_front': 52, 'raised': 53, 'ears_front': 66, 'fx': 90}


def _context(group: str, pose: Pose) -> str:
    return pose.eyes if group == 'eyes' else pose.mouth if group == 'mouth' else pose.torso


def _group_elements(template: Template, pose: Pose) -> list[Element]:
    elements = []
    for name, group in template.groups().items():
        context = _context(name, pose)
        angle = pose.angle('head' if group.part == 'face' else group.part)
        for choice in group.choices:
            def draw(b, group=group, choice=choice, context=context):
                group.draw(b, choice, context)
            key = (template.ident, 'group', name, choice, context)
            if group.ear:
                elements.append(Element(group.part, Z['ears_back'], draw, key, angle, None, (name, choice)))
                elements.append(Element(group.part, Z['ears_front'], draw, key, angle, template.crown[0],
                                        (name, choice)))
            else:
                elements.append(Element(group.part, group.z, draw, key, angle, None, (name, choice)))
    return elements


def _arm_z(part: str, pose: Pose) -> int:
    # Paws brought to the mouth pass in front of the head, still below the eyes.
    return Z['raised'] + 2 * (part == 'arm_r') if part in pose.front else Z[part]


def character_elements(template: Template, pose: Pose) -> list[Element]:
    head = pose.angle('head')
    ident = template.ident
    elements = [
        Element('tail', Z['tail'], template.tail, (ident, 'tail'), pose.angle('tail')),
        Element('foot_l', Z['foot_l'], lambda b: template.foot(b, 'l'), (ident, 'foot', 'l')),
        Element('foot_r', Z['foot_r'], lambda b: template.foot(b, 'r'), (ident, 'foot', 'r')),
        Element('body', Z['body'], lambda b: template.body(b, pose.torso), (ident, 'body', pose.torso)),
        Element('arm_l', _arm_z('arm_l', pose), lambda b: template.arm(b, 'l'), (ident, 'arm', 'l'),
                pose.angle('arm_l')),
        Element('arm_r', _arm_z('arm_r', pose), lambda b: template.arm(b, 'r'), (ident, 'arm', 'r'),
                pose.angle('arm_r')),
        Element('head', Z['ears_back'], template.ears, (ident, 'ears'), head),
        Element('head', Z['head'], template.head, (ident, 'head'), head),
        Element('head', Z['head_front'], template.head_front, (ident, 'head_front'), head),
        Element('head', Z['ears_front'], template.ears, (ident, 'ears'), head, template.crown[0]),
    ]
    elements += _group_elements(template, pose)
    for name in pose.fx:
        elements.append(Element('head', Z['fx'], lambda b, name=name: template.fx(b, name), (ident, 'fx', name)))
    return elements


def build_character(template: Template, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    writer = AssetWriter(folder, template.palette)
    actions = build_actions(writer, template.base, template.palette,
                            lambda pose: character_elements(template, pose), template.nudge)
    variants = {name: {'name': group.name, 'default': group.default, 'choices': dict(group.choices)}
                for name, group in template.groups().items()}
    writer.write(manifest(template.ident, template.name, 'character', template.template, [],
                          template.palette, actions, variants))
    return folder


def garment_identifier(garment: Garment, template: Template) -> str:
    return f'{template.ident}-{garment.ident}'


def garment_elements(garment: Garment, template: Template, pose: Pose) -> list[Element]:
    elements = []
    for index, piece in enumerate(garment.pieces):
        def draw(b, piece=piece):
            piece.draw(b, template, pose.torso)
        angle = pose.angle(piece.part)
        # Sleeves sit directly above their own arm, wherever that arm is drawn.
        z = _arm_z(piece.part, pose) + 1 if piece.part in ('arm_l', 'arm_r') else piece.z
        key = (garment.ident, template.ident, index, pose.torso)
        # A garment frame needs at least one layer, even where a piece hides.
        elements.append(Element(piece.part, z, draw, key, angle, None, None, index == 0))
    return elements


def build_garment(garment: Garment, template: Template, folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    writer = AssetWriter(folder, garment.palette)
    actions = build_actions(writer, template.base, garment.palette,
                            lambda pose: garment_elements(garment, template, pose), template.nudge)
    name = f'{garment.outfit} · {garment.name}'
    writer.write(manifest(garment_identifier(garment, template), name, 'garment', template.template,
                          list(garment.slots), garment.palette, actions))
    return folder
