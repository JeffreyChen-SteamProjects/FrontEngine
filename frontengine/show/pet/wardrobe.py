"""Detached wardrobe edits and preloaded, conflict-checked appearance commits."""
from __future__ import annotations

import copy
from uuid import uuid4

from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_profile_schema import checked_profile, SLOTS
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.pet_pack.layered import LayeredAsset


class AssetCatalog:
    """Resolve stable references without substituting another asset version."""

    def __init__(self, assets: tuple[LayeredAsset, ...]) -> None:
        self._assets = {}
        for asset in assets:
            key = (asset.identifier, asset.version)
            if key in self._assets:
                raise ValueError(f'Duplicate asset identity: {key}')
            self._assets[key] = asset

    def resolve(self, reference: dict, kind: str) -> LayeredAsset:
        asset = self._assets.get((reference['id'], reference['version']))
        if asset is None:
            raise ValueError(f"Missing asset: {reference['id']}@{reference['version']}")
        if asset.kind != kind:
            raise ValueError(f'Expected {kind}: {asset.name}')
        return asset

    def assets(self, kind: str) -> tuple[LayeredAsset, ...]:
        return tuple(asset for asset in self._assets.values() if asset.kind == kind)

    def prepare(self, appearance: dict) -> LayeredRenderer | None:
        """Decode a complete candidate before any state is persisted."""
        if appearance['character'] is None:
            if any(appearance['equipped'].values()) or appearance.get('colors') or appearance.get('variants'):
                raise ValueError('Choose a layered character before equipping clothes')
            return None
        character = self.resolve(appearance['character'], 'character')
        garments = {}
        for slot, reference in appearance['equipped'].items():
            if reference is None:
                continue
            garment = self.resolve(reference, 'garment')
            if slot not in garment.slots:
                raise ValueError(f'{garment.name} cannot occupy {slot}')
            if any(appearance['equipped'][occupied] != reference for occupied in garment.slots):
                raise ValueError(f'{garment.name} must occupy all its declared slots')
            garments[(garment.identifier, garment.version)] = garment
        return LayeredRenderer(character, tuple(garments.values()), colors=appearance.get('colors', {}),
                               variants=appearance.get('variants', {}))


def asset_reference(asset: LayeredAsset) -> dict:
    return {'id': asset.identifier, 'version': asset.version}


class WardrobeDraft:
    """Preview and outfit collection edits never mutate a live profile until Apply."""

    def __init__(self, profiles: PetProfiles, identifier: str, catalog: AssetCatalog) -> None:
        self.profiles, self.identifier, self.catalog = profiles, identifier, catalog
        self._expected = profiles.get(identifier)['appearance']
        self._candidate = copy.deepcopy(self._expected)
        self.preview: LayeredRenderer | None = None

    @property
    def appearance(self) -> dict:
        return copy.deepcopy(self._candidate)

    def _validate(self, candidate: dict) -> None:
        checked_profile({**self.profiles.get(self.identifier), 'appearance': candidate})

    def _stage(self, candidate: dict) -> None:
        self._validate(candidate)
        preview = self.catalog.prepare(candidate)
        self._candidate, self.preview = candidate, preview

    def prepare_preview(self) -> LayeredRenderer | None:
        self._stage(self.appearance)
        return self.preview

    def choose_character(self, reference: dict | None) -> None:
        """Changing body explicitly starts a bare outfit; saved outfits remain intact."""
        candidate = self.appearance
        candidate['character'] = copy.deepcopy(reference)
        candidate['equipped'] = dict.fromkeys(SLOTS)
        candidate.pop('colors', None)
        candidate.pop('variants', None)
        self._stage(candidate)

    def set_variant(self, group: str, choice: str | None) -> None:
        candidate = self.appearance
        variants = candidate.setdefault('variants', {})
        if choice is None:
            variants.pop(group, None)
        else:
            variants[group] = choice
        self._stage(candidate)

    def equip(self, reference: dict) -> None:
        garment = self.catalog.resolve(reference, 'garment')
        candidate = self.appearance
        occupied = candidate['equipped']
        for slot in garment.slots:
            if occupied[slot] is not None and occupied[slot] != reference:
                raise ValueError(f'Unequip the current item in {slot} first')
            occupied[slot] = copy.deepcopy(reference)
        self._stage(candidate)

    def unequip(self, slot: str) -> None:
        if slot not in SLOTS:
            raise ValueError('Unknown garment slot')
        candidate = self.appearance
        reference = candidate['equipped'][slot]
        # Clear all occurrences even when the asset is missing from the catalog.
        if reference is not None:
            candidate.get('colors', {}).pop(reference['id'] + '@' + reference['version'], None)
            for occupied in SLOTS:
                if candidate['equipped'][occupied] == reference:
                    candidate['equipped'][occupied] = None
        self._stage(candidate)

    def set_color(self, reference: dict, region: str, color: str | None) -> None:
        candidate = self.appearance
        key = reference['id'] + '@' + reference['version']
        colors = candidate.setdefault('colors', {})
        if color is None:
            colors.get(key, {}).pop(region, None)
            if not colors.get(key):
                colors.pop(key, None)
        else:
            colors.setdefault(key, {})[region] = color
        self._stage(candidate)

    def save_outfit(self, name: str, identifier: str | None = None) -> str:
        candidate = self.appearance
        outfits = candidate['saved_outfits']
        if identifier is None:
            identifier = uuid4().hex
            outfits.append({'id': identifier, 'name': name, 'equipped': copy.deepcopy(candidate['equipped'])})
        else:
            outfit = next((item for item in outfits if item['id'] == identifier), None)
            if outfit is None:
                raise ValueError('Saved outfit no longer exists')
            outfit.update(name=name, equipped=copy.deepcopy(candidate['equipped']))
        saved = next(item for item in outfits if item['id'] == identifier)
        saved['colors'] = copy.deepcopy(candidate.get('colors', {}))
        saved['character'] = copy.deepcopy(candidate['character'])
        saved['variants'] = copy.deepcopy(candidate.get('variants', {}))
        self._stage(candidate)
        return identifier

    def wear_outfit(self, identifier: str) -> None:
        candidate = self.appearance
        outfit = next((item for item in candidate['saved_outfits'] if item['id'] == identifier), None)
        if outfit is None:
            raise ValueError('Saved outfit no longer exists')
        candidate['equipped'] = copy.deepcopy(outfit['equipped'])
        candidate['colors'] = copy.deepcopy(outfit.get('colors', {}))
        if 'character' in outfit:
            candidate['character'] = copy.deepcopy(outfit['character'])
        candidate['variants'] = copy.deepcopy(outfit.get('variants', {}))
        self._stage(candidate)

    def delete_outfit(self, identifier: str) -> None:
        candidate = self.appearance
        candidate['saved_outfits'] = [item for item in candidate['saved_outfits'] if item['id'] != identifier]
        self._validate(candidate)
        self._candidate = candidate

    def cancel(self) -> None:
        self._candidate = copy.deepcopy(self._expected)
        self.preview = None

    def apply(self) -> LayeredRenderer | None:
        """Preload, compare and persist. Failure leaves the draft and saved state intact."""
        candidate = self.appearance
        self._validate(candidate)
        prepared = self.catalog.prepare(candidate)
        session = PetProfileSession.active(self.profiles, self.identifier)
        if session:
            if not getattr(session.parent(), 'supports_layered_wardrobe', True):
                raise ValueError('This active pet does not support layered sprite clothing')
            session.apply_appearance(self._expected, candidate, prepared)
        else:
            if self.profiles.get(self.identifier)['appearance'] != self._expected:
                raise ValueError('Pet appearance changed while previewing')
            self.profiles.update(self.identifier, {'appearance': candidate})
        self._expected = copy.deepcopy(candidate)
        self.preview = prepared
        return prepared
