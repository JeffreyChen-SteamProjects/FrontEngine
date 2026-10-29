"""Sprite destination that ends in the shared greeting action."""
from frontengine.show.pet.light_toy import LightToy


class CallTarget(LightToy):
    arrival_action = 'greet'

    def __init__(self, pet, *, offset=None):
        super().__init__(pet, offset=offset, appearance='call')
