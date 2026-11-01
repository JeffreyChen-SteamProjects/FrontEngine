"""Draw the built-in characters' home poses with Codex, then cut them into shipped atlases.

Two steps, each rerunnable (finished sheets are skipped)::

    py tools/codex_home_poses.py sheets <work folder> [mochi,moss,...] [sit,sleep,...]
    py tools/codex_home_poses.py atlases <work folder>

``sheets`` runs ``codex exec`` once per character and pose in its own folder with the
cast reference sheet and the character's walk atlas attached; the prompt asks the
image model for a 2 x 2 loop on flat #FF00FF and never for drawing code. ``atlases``
keys, cleans and aligns every sheet with ``inkside/sprite_sheet.py`` and writes
``inkside-<name>-<pose>.png`` into the package. Check the sheets by eye in between.
"""
from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - developer tool: runs only the resolved codex executable, argv list, shell=False
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CONCEPTS = REPO / "docs/design/assets/pet-concepts-2026-10-28"
SPRITES = REPO / "frontengine/show/pet/inkside/sprites"
CHARACTERS = json.loads((Path(__file__).resolve().parent / "codex_characters.json").read_text(encoding="utf-8"))
# Character height in the 256 px canvas: standing poses match the walk (225), sitting ones are
# shorter and lying down shorter still; fit_frames still keeps the widest frame inside.
HEIGHTS = {"sit": 180, "feed": 180, "write": 185, "sleep": 120, "play": 225, "garden": 225, "craft": 225}

POSES = {
    "sit": "SITTING calmly on an invisible low stool (do NOT draw the stool), seen in SIDE VIEW facing RIGHT, feet forward. A gentle idle loop: a slight breathing bob, one slow blink, the tail sways a little.",
    "sleep": "ASLEEP, lying curled on its side on the ground (do NOT draw a bed or pillow), seen from the side, head to the RIGHT, eyes closed as thin lines. A slow breathing loop: the body rises and falls, the tail twitches once. No 'z' letters or any text.",
    "feed": "SITTING and EATING from a small plain off-white bowl held in front of it, seen in SIDE VIEW facing RIGHT: lifts the bowl to its mouth, chews with puffed cheeks, lowers the bowl, chews again.",
    "play": "PLAYING happily with a small plain orange ball, seen in SIDE VIEW facing RIGHT: tosses the ball up, watches it, catches it, does a small hop.",
    "write": "SITTING at an invisible desk at chest height on its RIGHT (do NOT draw the desk or chair), seen in SIDE VIEW facing RIGHT, writing on one off-white sheet of paper with a short black pencil: the pencil moves across the paper, the head nods slightly, a short pause to think.",
    "garden": "STANDING, seen in SIDE VIEW facing RIGHT, watering an invisible plant on the ground to its RIGHT with a small orange watering can: the can tilts forward, three black water drops fall from the spout, the can tilts back.",
    "craft": "STANDING at an invisible workbench on its RIGHT (do NOT draw the bench), seen in SIDE VIEW facing RIGHT, hammering a small off-white wooden block with a small black mallet: mallet raised, mallet coming down, impact, recovering.",
}
NO_HANDS = {"ink": " INK has no hands: it holds and uses items with its wing tips or its beak."}


def prompt(character: str, action: str) -> str:
    return (
        "Use your built-in image generation tool to create ONE game sprite sheet image, then save the final PNG file "
        f"in the current directory as {character}_{action}_sheet.png (copy it from wherever the tool writes it). "
        "Do not write any code that draws the sprites; the art must come from the image generation tool.\n\n"
        f"Character: {CHARACTERS[character]}{NO_HANDS.get(character, '')}\n\n"
        "Sheet layout: a 2 columns x 2 rows grid of 4 equal cells, read left-to-right then top-to-bottom, forming one "
        f"seamless looping animation. Pose and motion: {POSES[action]} Any prop uses only the same three inks. "
        "Same character size, same design and same ground baseline in every cell; the whole body and any prop fit "
        "inside each cell with margin; no cell borders, no grid lines, no numbers, no text, no shadows on the ground. "
        "The attached walk-cycle strip shows this exact character already drawn in this style; match it.\n\n"
        "Background: perfectly flat solid pure magenta #FF00FF everywhere outside the character and props, so it can "
        "be removed exactly. Do not use magenta anywhere on the character or props."
    )


def codex_executable() -> str:
    """The installed Codex CLI as an absolute path; nothing from the command line forms it."""
    found = shutil.which("codex")
    if found is None or not Path(found).is_absolute() or Path(found).stem.lower() != "codex":
        raise SystemExit("The Codex CLI (codex) is not on PATH")
    return str(Path(found).resolve())


def run(folder_root: Path, character: str, action: str) -> tuple[str, bool]:
    folder = folder_root / f"{character}_{action}"
    target = folder / f"{character}_{action}_sheet.png"
    if target.is_file():
        return folder.name, True
    folder.mkdir(parents=True, exist_ok=True)
    references = [CONCEPTS / "inkside-cast-v1.png", SPRITES / f"inkside-{character}-walk.png"]
    if character == "mochi":
        references.insert(0, CONCEPTS / "mochi-v3-ink-chibi.png")
    images = []
    for reference in references:
        shutil.copy2(reference, folder / reference.name)
        images.append(f"--image={folder / reference.name}")
    text = prompt(character, action)
    (folder / "prompt.txt").write_text(text, encoding="utf-8")
    argv = [codex_executable(), "exec", "--skip-git-repo-check", "-s", "workspace-write", "-C", str(folder), *images]
    with open(folder / "codex.log", "w", encoding="utf-8") as log:
        subprocess.run(argv, input=text, text=True, stdout=log, stderr=subprocess.STDOUT,  # nosec B603 # nosemgrep - absolute codex path, argv list, shell=False
                       timeout=900, check=False, encoding="utf-8")
    return folder.name, target.is_file()


def sheets(folder_root: Path, characters: list[str], actions: list[str]) -> None:
    jobs = [(character, action) for character in characters for action in actions]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name, ok in pool.map(lambda job: run(folder_root, *job), jobs):
            print(f"{name}: {'ok' if ok else 'MISSING'}", flush=True)


def atlases(folder_root: Path) -> None:
    sys.path.insert(0, str(REPO))            # this checkout, not an installed frontengine
    from PySide6.QtWidgets import QApplication
    from frontengine.show.pet.inkside.sprite_sheet import load_sheet, write_atlas
    app = QApplication.instance() or QApplication([])
    for character in CHARACTERS:
        for action, height in HEIGHTS.items():
            sheet = folder_root / f"{character}_{action}" / f"{character}_{action}_sheet.png"
            if sheet.is_file():
                print(write_atlas(load_sheet(sheet, 2, 2, height=height), f"inkside-{character}-{action}.png"))
    del app


def main() -> None:
    if len(sys.argv) < 3 or sys.argv[1] not in ("sheets", "atlases"):
        raise SystemExit(__doc__)
    folder_root = Path(sys.argv[2]).resolve()
    if sys.argv[1] == "atlases":
        atlases(folder_root)
        return
    characters = sys.argv[3].split(",") if len(sys.argv) > 3 else list(CHARACTERS)
    actions = sys.argv[4].split(",") if len(sys.argv) > 4 else list(POSES)
    sheets(folder_root, characters, actions)


if __name__ == "__main__":
    main()
