"""Install validated layered assets into a local, version-exact library."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import tempfile
from threading import Event

from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.show.pet.wardrobe import AssetCatalog
from frontengine.utils.pet_pack.layered import check_sources, image_bounds, image_path, load_layered_asset


class PetAssetLibrary:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path.cwd() / 'pet-assets'
        self.root = self.root.absolute()

    @staticmethod
    def _resources(asset) -> tuple[str, ...]:
        return tuple(sorted({layer.image for animation in asset.actions.values()
                             for frame in animation.frames for layer in frame.layers}))

    @staticmethod
    def _folder(asset) -> str:
        return sha256((asset.identifier + '\0' + asset.version).encode('utf-8')).hexdigest()

    def _check_root(self) -> None:
        if self.root.is_symlink() or (self.root.exists() and not self.root.is_dir()):
            raise ValueError('Pet asset library must be a regular directory')

    def scan(self) -> tuple[AssetCatalog, tuple[str, ...]]:
        """Keep valid installed assets while reporting individual broken packages."""
        self._check_root()
        if not self.root.exists():
            return AssetCatalog(()), ()
        assets, errors = [], []
        for index, folder in enumerate(self.root.iterdir()):
            if index >= 512:
                raise ValueError('Pet asset library exceeds 512 entries')
            if folder.name.startswith('.install-'):
                continue
            try:
                asset = load_layered_asset(folder)
                if folder.name != self._folder(asset):
                    raise ValueError('Installed asset identity does not match its folder')
                assets.append(asset)
            except (OSError, ValueError) as error:
                errors.append(f'{folder.name}: {error}')
        return AssetCatalog(tuple(assets)), tuple(errors)

    def is_installed(self, identifier: str, version: str) -> bool:
        return (self.root / sha256((identifier + '\0' + version).encode('utf-8')).hexdigest()).exists()

    def install(self, source: str | Path, *, cancel: Event | None = None, scanned: bool = False):
        """Copy only referenced images, verify staging, then publish without overwrite."""
        self._check_root()
        cancel = cancel or Event()
        asset = load_layered_asset(source)
        self.root.mkdir(parents=True, exist_ok=True)
        # Scan first to enforce the same bound on disk and in the picker; a batch
        # scans once up front instead of once per asset.
        if not scanned:
            self.scan()
        if sum(1 for _ in self.root.iterdir()) >= 512:
            raise ValueError('Pet asset library is full')
        target = self.root / self._folder(asset)
        if target.exists():
            raise ValueError('This asset version is already installed; existing files were preserved')
        with tempfile.TemporaryDirectory(prefix='.install-', dir=self.root) as staging:
            stage = Path(staging)
            self._copy_resources(asset, stage, cancel)
            candidate = load_layered_asset(stage)
            if (candidate.identifier, candidate.version) != (asset.identifier, asset.version):
                raise ValueError('Asset changed during installation')
            self._validate_images(candidate)
            if cancel.is_set():
                raise InterruptedError('Asset installation cancelled')
            stage.rename(target)
        return load_layered_asset(target)

    def install_many(self, sources, *, cancel: Event | None = None) -> list:
        """Install a batch after a single scan; any invalid asset stops the batch."""
        self._check_root()
        cancel = cancel or Event()
        self.scan()
        installed = []
        for source in sources:
            if cancel.is_set():
                raise InterruptedError('Asset installation cancelled')
            installed.append(self.install(source, cancel=cancel, scanned=True))
        return installed

    def _copy_resources(self, asset, stage: Path, cancel: Event) -> None:
        total = 0
        for relative in ('layered-pet.json', *self._resources(asset)):
            if cancel.is_set():
                raise InterruptedError('Asset installation cancelled')
            source = asset.root / relative if relative == 'layered-pet.json' else image_path(asset.root, relative)
            maximum = 1024 * 1024 if relative == 'layered-pet.json' else 16 * 1024 * 1024
            if source.is_symlink():
                raise ValueError('Asset resources cannot be symlinks')
            with source.open('rb') as stream:
                data = stream.read(maximum + 1)
            if relative != 'layered-pet.json':
                total += len(data)
            if len(data) > maximum or total > 64 * 1024 * 1024:
                raise ValueError('Asset resources exceed installation limits')
            destination = stage.joinpath(*relative.split('/'))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

    def _validate_images(self, asset) -> None:
        pixels = 0
        bounds = image_bounds(asset)
        for relative in self._resources(asset):
            limit, rects = bounds[relative]
            image = LayeredRenderer._read_image(image_path(asset.root, relative), limit)
            check_sources(image.width(), image.height(), rects)
            pixels += image.width() * image.height()
            if pixels > 16 * 1024 * 1024:
                raise ValueError('Asset decoded images exceed 16 megapixels')
