"""Where RSAC reads and writes.

Two layouts are supported:

* **Source install** (`python RSAC_Freeware_1_00.py`) — everything lives beside
  the application file, exactly as it always has. Nothing below changes any path.

* **Frozen build** (PyInstaller) — read-only assets are read from the bundle,
  while everything the tutor creates or edits lives in a writable per-user
  folder. This split is not optional: a one-file bundle unpacks into a temporary
  directory that Windows deletes on exit, so subjects and attempt records
  written there would silently disappear, and a one-folder bundle installed
  under Program Files is not writable without elevation.

The three configuration modules are copied into the writable folder on first run
and that folder is placed first on `sys.path`, so they are imported from a real,
writable `.py` file. That is what lets the Settings > Exercises editors keep
rewriting their own source, and what makes each module's `defaults_path()`
resolve to the baseline JSON sitting beside it. Those modules need no knowledge
of any of this.

> **Packaging requirement.** PyInstaller's `FrozenImporter` is consulted before
> any `sys.path` finder, so a module compiled into the bundle wins regardless of
> `sys.path`. The three configuration modules must therefore be shipped as
> *data* and excluded from the module analysis — see `rsac.spec`. If they are
> ever bundled as modules, the editors will appear to save and then silently
> revert on restart, because the writable copies would never be imported.
"""

from __future__ import annotations

import os
import shutil
import sys

APP_NAME = "RSAC"

# Copied into the writable folder on first run: each editable configuration
# module, and the pristine baseline its "revert to defaults" action reads.
SEEDED_FILES: tuple[str, ...] = (
    "exercise_defs.py",
    "exercise_defs_default.json",
    "exercise_progression_defs.py",
    "exercise_progression_defs_default.json",
    "exercise_proficiency_scores.py",
    "exercise_proficiency_scores_default.json",
)

# Folders the application creates on demand under the writable root.
DATA_SUBFOLDERS: tuple[str, ...] = (
    "csv_simulator",
    "csv_clean",
    "analysis_history",
)


def is_frozen() -> bool:
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def bundle_dir() -> str:
    """Folder holding read-only resources (images, seed copies of the configs)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return str(meipass)
    return os.path.dirname(os.path.abspath(__file__))


def user_data_dir() -> str:
    """Writable root for everything the tutor creates or edits.

    In a source install this is the application folder, so behaviour is
    unchanged. In a frozen build it is a per-user application-data folder.
    """
    if not is_frozen():
        return os.path.dirname(os.path.abspath(__file__))

    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, APP_NAME)


def data_path(*parts: str) -> str:
    """Path to a writable file or folder: config, subjects, CSVs, history."""
    return os.path.join(user_data_dir(), *parts)


def asset_path(*parts: str) -> str:
    """Path to a read-only resource shipped with the application."""
    return os.path.join(bundle_dir(), *parts)


def bootstrap() -> str:
    """Prepare the writable folder and make it the source of the config modules.

    Call this **before** importing exercise_defs, exercise_progression_defs or
    exercise_proficiency_scores. Safe to call more than once, and a no-op in a
    source install. Returns the writable root.
    """
    target = user_data_dir()
    if not is_frozen():
        return target

    os.makedirs(target, exist_ok=True)

    source = bundle_dir()
    for name in SEEDED_FILES:
        destination = os.path.join(target, name)
        if os.path.exists(destination):
            continue  # never overwrite a tutor's edits
        origin = os.path.join(source, name)
        if os.path.isfile(origin):
            shutil.copy2(origin, destination)

    # Ahead of the bundle's own directory, so the writable copies are imported.
    while target in sys.path:
        sys.path.remove(target)
    sys.path.insert(0, target)

    return target
