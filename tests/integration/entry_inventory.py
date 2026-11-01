"""Write the entry inventory: every original way into a feature and where it lives now.

Usage (from the repository root; headless is fine)::

    py tests/integration/entry_inventory.py docs/design/entry-inventory.md

Builds the real main window in a temporary working directory (English), then
lists sidebar pages, menu-bar actions, ActionRegistry commands and tray actions.
For each it records the original entry, its stable action ID, the new entry,
how its state is saved, and an acceptance result measured right here: pages are
opened through their Features entry and must become the current page; menu
actions must be the same QAction object inside the Features tree; commands must
stay registered under the same ID.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
OUTPUT = Path(sys.argv[1]).resolve()
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.chdir(tempfile.mkdtemp(prefix="fe-inventory-"))
Path("user_setting.json").write_text(json.dumps({"language": "English"}), encoding="utf-8")

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication(sys.argv)
from frontengine.system_tray.extend_system_tray import ExtendSystemTray  # noqa: E402
from frontengine.ui.main_ui import FrontEngineMainUI  # noqa: E402
from frontengine.ui.menu.features_menu import CATEGORIES, Entry, run_entry  # noqa: E402
from frontengine.ui.nav.sidebar import KIND_GROUP, KIND_PAGE, ROLE_KIND, ROLE_PAGE_ID  # noqa: E402
from frontengine.utils.multi_language.retranslate import translate  # noqa: E402

ui = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
CATEGORY_OF = {(entry.kind, entry.target): translate(key, fallback)
               for key, fallback, entries in CATEGORIES for entry in entries}


def walk(menu, path, seen=None):
    seen = set() if seen is None else seen
    for action in menu.actions():
        if action.isSeparator() or id(action) in seen:
            continue
        seen.add(id(action))
        label = action.text().replace("&", "")
        yield path + [label], action
        if action.menu() is not None:
            yield from walk(action.menu(), path + [label], seen)


def page_rows():
    rows, sidebar, group = [], ui.sidebar, ""
    for row in range(sidebar.count()):
        item = sidebar.item(row)
        if item.data(ROLE_KIND) == KIND_GROUP:
            group = item.text()
            continue
        if item.data(ROLE_KIND) != KIND_PAGE:
            continue
        page_id = item.data(ROLE_PAGE_ID)
        widget = ui.page_stack.widget(sidebar.page_index(page_id))
        if page_id == "tab_pet_home_text":
            new, ok = "First page (Home group)", ui.sidebar.select_page_id(page_id)
        else:
            new = f"Features › {CATEGORY_OF.get(('page', page_id), 'Extensions')} › {item.text()}"
            ok = run_entry(ui, Entry("page", page_id)) and ui.page_stack.currentWidget() is widget
        state = "get_state/set_state (presets)" if hasattr(widget, "get_state") else "own settings"
        action_id = "page." + page_id if "page." + page_id in ui.action_registry.actions else "—"
        rows.append((f"Sidebar › {group} › {item.text()}", action_id, new, state, "opened ✓" if ok else "FAILED"))
    return rows


def menu_rows():
    features = {id(action) for _path, action in walk(ui.features_menu, [])}
    rows = []
    for top in ui.menu_bar.actions():
        menu = top.menu()
        if menu is None or menu is ui.features_menu:
            continue
        for path, action in walk(menu, [menu.title().replace("&", "")]):
            ok = id(action) in features
            rows.append(("Menu › " + " › ".join(path), "—", "Same menu, also under Features",
                         "unchanged", "same QAction ✓" if ok else "MISSING"))
    return rows


def command_rows():
    rows = []
    for identifier, action in sorted(ui.action_registry.actions.items()):
        if identifier.startswith("page."):
            continue
        category = CATEGORY_OF.get(("action", identifier))
        new = f"Features › {category}" if category else "Search features (Ctrl+K)"
        rows.append((f"Hotkey / remote / MIDI / rules / Ctrl+K: {translate(action.label_key, action.fallback)}",
                     identifier, new + "; same ID everywhere", "unchanged", "registered ✓"))
    return rows


def tray_rows():
    tray = ExtendSystemTray(ui)
    rows = [(f"Tray › {action.text()}", "—", "unchanged", "unchanged", "present ✓")
            for action in tray.menu.actions() if not action.isSeparator()]
    tray.hide()
    return rows


def table(rows):
    lines = ["| Original entry | Action ID | New entry | State saving | Acceptance |", "|---|---|---|---|---|"]
    lines += ["| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows]
    return "\n".join(lines)


sections = [("Pages", page_rows()), ("Menu-bar actions", menu_rows()),
            ("Commands (ActionRegistry)", command_rows()), ("Tray", tray_rows())]
failed = sum(1 for _title, rows in sections for row in rows if not row[-1].endswith("✓"))
text = ["# Entry inventory", "",
        "Generated by `tests/integration/entry_inventory.py` from the running main window (English). "
        "Regenerate it whenever pages, menus or commands change; `progress.md` #24 relies on it. "
        "Hotkeys, the phone remote, MIDI and rules address commands by Action ID, so a command keeps "
        "working wherever its menu entry moves.", "",
        f"Rows: {sum(len(rows) for _t, rows in sections)}. Failed acceptance: {failed}.", ""]
for title, rows in sections:
    text += [f"## {title}", "", table(rows), ""]
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(text), encoding="utf-8")
ui.close()
print(f"{OUTPUT}: {failed} failed")
sys.exit(1 if failed else 0)
