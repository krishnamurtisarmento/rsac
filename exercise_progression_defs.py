"""Exercise progression graph — which exercise a subject can move to, and how.

Extracted from `RSAC_Freeware_1_00.py` for the same reason as `exercise_defs.py`: this
is site-specific configuration a new centre must replace, and burying it in a 12,000-line
application module made that hard to find and risky to change.

This module must not import anything from the application. It may read
`exercise_defs.EXERCISE_DEFS`, which is itself app-independent, for validation only.

CURRICULA is the source of truth for NAED-3. Three consumers read it, each a different
subset of the edges, so a change here does not affect them uniformly:

  * `compute_naed3_recommendation`  — all four connection types, directed.
  * `_build_equivalence_map`        — "lateral" only, treated as UNDIRECTED.
  * `_compute_curriculum_ranks`     — "upgrade" + "hp_upgrade" only; laterals ignored.

Run `check_progression_consistency()` after editing. It catches the mistakes that would
otherwise fail silently at runtime: a typo'd destination simply yields "no option
available" and the tutor is told to keep the subject where they are, with nothing logged.

CURRICULA below is the graph actually in force. Settings > Exercises > Exercise Progression
edits it and rewrites the block between the BEGIN/END markers in place, so what you read
here is always live. The pristine baseline lives beside this file in
exercise_progression_defs_default.json and is only ever read — it is what "revert to
default" restores from. Keep it in version control.

The region between the markers is generated. Anything you add by hand inside it will be
discarded on the next save; put it outside the markers.
"""

from __future__ import annotations

from exercise_defs import EXERCISE_DEFS

# The four ways one exercise can connect to another. Order is display order.
CONNECTION_TYPES: tuple[str, ...] = ("upgrade", "hp_upgrade", "downgrade", "lateral")

# Assigned to a subject at creation and persisted in subjects.json; this is the
# fallback when a subject has no curriculum recorded.
DEFAULT_CURRICULUM = "grad"

# Terminal sentinel: a connection list of exactly ["END"] means training is complete.
END_SENTINEL = "END"

CONNECTION_TYPE_COLORS: dict[str, str] = {
    "upgrade": "#2ca02c",
    "hp_upgrade": "#1f77b4",
    "downgrade": "#cc0000",
    "lateral": "#daa520",
}

CONNECTION_TYPE_LABELS: dict[str, str] = {
    "upgrade": "Upgrade",
    "hp_upgrade": "HP Upgrade",
    "downgrade": "Downgrade",
    "lateral": "Lateral",
}

# --- Curricula (v7.0) --------------------------------------------------------
# Each subject is assigned ONE curriculum when they are created (persisted in
# subjects.json). Every connection type maps to a LIST of candidate destinations:
#   - single-element list  -> forced progression (no user choice)
#   - multi-element list   -> the user picks the destination from the list
# "END" is the terminal sentinel.

# --- BEGIN CURRICULA (rewritten by Settings > Exercises > Exercise Progression) ---
CURRICULA: dict[str, dict] = {
    "grad": {
        "label": "Grad Students",
        "connections": {
            "pp1": {"upgrade": ["pb1"], "hp_upgrade": ["mb1"]},
            "ppc": {"upgrade": ["rtt", "rw2"], "lateral": ["mbc"]},
            "ct1": {"upgrade": ["ct2"]},
            "ct2": {"upgrade": ["pb2"], "hp_upgrade": ["mb2"]},
            "pb1": {"upgrade": ["pb2", "mb2"], "hp_upgrade": ["ppc"], "lateral": ["mb1"], "downgrade": ["ct1"]},
            "pb2": {"upgrade": ["ppc", "mbc"], "lateral": ["mb2"]},
            "mb1": {"upgrade": ["pb2", "mb2"], "hp_upgrade": ["mbc"], "lateral": ["pb1"], "downgrade": ["ct1"]},
            "mb2": {"upgrade": ["ppc", "mbc"], "lateral": ["pb2"]},
            "mb3": {"upgrade": ["rw3"], "lateral": ["4ac"]},
            "mbc": {"upgrade": ["rtt", "rw2"], "lateral": ["ppc"]},
            "ttr": {"upgrade": ["rtt", "rw2"]},
            "rtt": {"upgrade": ["mb3", "4ac"], "lateral": ["rw2"], "downgrade": ["ttr"]},
            "4ac": {"upgrade": ["rw3"], "lateral": ["mb3"]},
            "rw2": {"upgrade": ["mb3", "4ac"], "lateral": ["rtt"], "downgrade": ["ttr"]},
            "rw3": {"upgrade": ["ed2"]},
            "es2": {"upgrade": ["nt1", "tr1"]},
            "ed2": {"upgrade": ["es2"]},
            "nt1": {"upgrade": ["ss1", "tu1"], "lateral": ["tr1"]},
            "tr1": {"upgrade": ["ss1", "tu1"], "lateral": ["nt1"]},
            "ss0": {"upgrade": ["ss1", "tu1"]},
            "ss1": {"upgrade": ["tch", "sug"], "lateral": ["tu1"], "downgrade": ["ss0"]},
            "tu1": {"upgrade": ["tch", "sug"], "lateral": ["ss1"], "downgrade": ["ss0"]},
            "wch": {"upgrade": ["tch", "sug"]},
            "tch": {"upgrade": ["kr1"], "lateral": ["sug"], "downgrade": ["wch"]},
            "sug": {"upgrade": ["kr1"], "lateral": ["tch"], "downgrade": ["wch"]},
            "kr1": {"upgrade": ["kr2"]},
            "kr2": {"upgrade": ["END"]},
        },
    },
    "resident_ext": {
        "label": "Resident - Fellow - Extensive",
        "connections": {
            "pp1": {"upgrade": ["pb1"], "hp_upgrade": ["mb1"]},
            "ppc": {"upgrade": ["rr1", "rc1", "rw1"], "lateral": ["mbc"]},
            "ct1": {"upgrade": ["ct2"]},
            "ct2": {"upgrade": ["pb2"], "hp_upgrade": ["mb2"]},
            "pb1": {"upgrade": ["pb2"], "hp_upgrade": ["ppc", "pb3"], "lateral": ["mb1"], "downgrade": ["ct1"]},
            "pb2": {"upgrade": ["pb3"], "lateral": ["mb2"]},
            "pb3": {"upgrade": ["ppc"], "hp_upgrade": ["mbc"], "downgrade": ["mb2"]},
            "30d": {"upgrade": ["mb3", "4ac"], "lateral": ["ppd"]},
            "mb1": {"upgrade": ["mb2"], "hp_upgrade": ["mbc"], "lateral": ["pb1"], "downgrade": ["ct1"]},
            "mb2": {"upgrade": ["mbc"], "lateral": ["pb2"]},
            "mb3": {"upgrade": ["rw3"], "lateral": ["4ac"]},
            "mbc": {"upgrade": ["rr1", "rc1", "rw1"], "lateral": ["ppc"]},
            "ttr": {"upgrade": ["rtt", "rw2"]},
            "rtt": {"upgrade": ["30d", "sc2", "ppd"], "lateral": ["rw2"], "downgrade": ["ttr"]},
            "4ac": {"upgrade": ["rw3"], "lateral": ["mb3"]},
            "rr1": {"upgrade": ["rc3", "sc1"], "lateral": ["rw1"]},
            "rr2": {"upgrade": ["rtt", "rw2"], "lateral": ["rc4", "vop"]},
            "rc1": {"upgrade": ["rc3", "sc1"], "lateral": ["rw1"]},
            "rc2": {"upgrade": ["rc3", "sc1"]},
            "rc3": {"upgrade": ["rr2", "rc4", "vop"], "lateral": ["sc1"], "downgrade": ["rc2"]},
            "rc4": {"upgrade": ["rtt", "rw2"], "lateral": ["rr2"]},
            "rw1": {"upgrade": ["rc3", "sc1"], "lateral": ["rr1", "rc1"]},
            "rw2": {"upgrade": ["30d", "sc2", "ppd"], "lateral": ["rtt"], "downgrade": ["ttr"]},
            "rw3": {"upgrade": ["ed2"]},
            "vop": {"upgrade": ["rtt", "rw2"], "lateral": ["rr2"]},
            "sc1": {"upgrade": ["rr2", "rc4", "vop"], "lateral": ["rc3"], "downgrade": ["rc2"]},
            "sc2": {"upgrade": ["mb3", "4ac"], "lateral": ["ppd"]},
            "ppd": {"upgrade": ["mb3", "4ac"], "lateral": ["30d", "sc2"]},
            "es1": {"upgrade": ["ech"]},
            "es2": {"upgrade": ["ech"], "downgrade": ["es1"]},
            "ech": {"upgrade": ["nt1", "tr1"]},
            "ed2": {"upgrade": ["es2"]},
            "nt1": {"upgrade": ["ss1", "tu1"], "hp_upgrade": ["ss2"], "lateral": ["tr1"]},
            "tr1": {"upgrade": ["ss1", "tu1"], "hp_upgrade": ["tu2"], "lateral": ["nt1"]},
            "tr2": {"upgrade": ["ss4", "tu3"], "lateral": ["ss3"]},
            "ss0": {"upgrade": ["ss1", "tu1"]},
            "ss1": {"upgrade": ["ss2", "bgd", "tu2"], "lateral": ["tu1"], "downgrade": ["ss0"]},
            "ss2": {"upgrade": ["tr2", "ss3"], "hp_upgrade": ["ss4"], "lateral": ["bgd"]},
            "ss3": {"upgrade": ["ss4", "tu3"], "lateral": ["tr2"]},
            "ss4": {"upgrade": ["wch", "wcv", "rrt"], "hp_upgrade": ["tch"], "lateral": ["tu3"]},
            "bgd": {"upgrade": ["tr2", "ss3"], "hp_upgrade": ["tu3"], "lateral": ["ss2", "tu2"]},
            "tu1": {"upgrade": ["ss2", "bgd", "tu2"], "lateral": ["ss1"], "downgrade": ["ss0"]},
            "tu2": {"upgrade": ["tr2", "ss3"], "hp_upgrade": ["tu3"], "lateral": ["bgd"]},
            "tu3": {"upgrade": ["wch", "wcv", "rrt"], "hp_upgrade": ["sug"], "lateral": ["ss4"]},
            "row": {"upgrade": ["wch", "wcv", "rrt"]},
            "wch": {"upgrade": ["tcv", "sug"], "lateral": ["wcv", "rrt"], "downgrade": ["row"]},
            "wcv": {"upgrade": ["tch", "tcv", "sug"], "lateral": ["wch"], "downgrade": ["row"]},
            "tch": {"upgrade": ["tah", "tav"], "lateral": ["tcv", "sug"]},
            "tcv": {"upgrade": ["tah", "tav"], "lateral": ["tch", "sug"]},
            "sug": {"upgrade": ["tah", "tav"], "lateral": ["tch", "tcv"]},
            "rrt": {"upgrade": ["tch", "tcv", "sug"], "lateral": ["wch"], "downgrade": ["row"]},
            "tah": {"upgrade": ["kr1"], "lateral": ["tav"]},
            "tav": {"upgrade": ["kr1"], "lateral": ["tah"]},
            "kr1": {"upgrade": ["kr2"]},
            "kr2": {"upgrade": ["kr3"]},
            "kr3": {"upgrade": ["kr4"]},
            "kr4": {"upgrade": ["is1"], "hp_upgrade": ["is2"]},
            "is1": {"upgrade": ["is2"]},
            "is2": {"upgrade": ["END"]},
        },
    },
}
# --- END CURRICULA ---


def connections_for(curriculum: str) -> dict[str, dict]:
    """The connection map for `curriculum`, or an empty map if it is unknown.

    Callers treat "no entry" as "no recommendation available", so an unknown
    curriculum degrades to advising KEEP rather than raising.
    """
    return CURRICULA.get(curriculum, {}).get("connections", {})


def curriculum_label(curriculum: str) -> str:
    """Human label for a curriculum, falling back to its key."""
    return CURRICULA.get(curriculum, {}).get("label", curriculum)


def check_progression_consistency(curricula: dict[str, dict] | None = None) -> list[str]:
    """Report structural problems in `curricula` (default: the live graph).

    These are all failures that are otherwise silent: NAED-3 reports "no option
    available" for a typo'd destination exactly as it does for a deliberate dead end,
    so nothing distinguishes a data-entry error from intended behaviour at runtime.

    The editor runs this on a candidate graph before saving, which is why it takes an
    argument rather than only ever inspecting the module global.
    """
    if curricula is None:
        curricula = CURRICULA
    problems: list[str] = []

    for cur_key, cur in sorted(curricula.items()):
        if not isinstance(cur, dict):
            problems.append(f"{cur_key}: curriculum is not a dict")
            continue
        if not (cur.get("label") or "").strip():
            problems.append(f"{cur_key}: has no label")

        connections = cur.get("connections")
        if not isinstance(connections, dict) or not connections:
            problems.append(f"{cur_key}: has no connections")
            continue

        for source, links in sorted(connections.items()):
            where = f"{cur_key}/{source}"
            if source not in EXERCISE_DEFS:
                problems.append(f"{where}: source exercise is not in EXERCISE_DEFS")
            if not isinstance(links, dict):
                problems.append(f"{where}: connections entry is not a dict")
                continue

            for conn_type, targets in sorted(links.items()):
                if conn_type not in CONNECTION_TYPES:
                    problems.append(
                        f"{where}: unknown connection type {conn_type!r} "
                        f"(expected one of {', '.join(CONNECTION_TYPES)})"
                    )
                    continue
                if isinstance(targets, str):
                    problems.append(
                        f"{where}/{conn_type}: is a bare string {targets!r}, expected a list"
                    )
                    targets = [targets]
                if not isinstance(targets, (list, tuple)):
                    problems.append(f"{where}/{conn_type}: is not a list")
                    continue
                if not targets:
                    problems.append(f"{where}/{conn_type}: is an empty list; omit the key instead")
                if len(set(targets)) != len(targets):
                    problems.append(f"{where}/{conn_type}: has duplicate destinations")
                for target in targets:
                    if target == END_SENTINEL:
                        if len(targets) > 1:
                            problems.append(
                                f"{where}/{conn_type}: mixes {END_SENTINEL!r} with real "
                                f"destinations; the sentinel must stand alone"
                            )
                        continue
                    if target == source:
                        problems.append(f"{where}/{conn_type}: points at itself")
                    if target not in EXERCISE_DEFS:
                        problems.append(
                            f"{where}/{conn_type}: destination {target!r} is not in EXERCISE_DEFS"
                        )
                    elif target not in connections:
                        # Reachable but has no outgoing edges: a dead end mid-curriculum.
                        # Legitimate only if it is genuinely terminal.
                        problems.append(
                            f"{where}/{conn_type}: destination {target!r} has no connections "
                            f"entry, so a subject arriving there can never progress"
                        )

    return problems


def asymmetric_laterals(curricula: dict[str, dict] | None = None) -> list[str]:
    """Lateral pairs declared in only one direction.

    Not necessarily a bug, but worth knowing: NAED-3 follows "lateral" as declared
    (directed), while `_build_equivalence_map` treats it as undirected. An asymmetric
    pair therefore behaves differently in the two consumers.
    """
    if curricula is None:
        curricula = CURRICULA
    out: list[str] = []
    for cur_key, cur in sorted(curricula.items()):
        connections = cur.get("connections", {})
        for source, links in sorted(connections.items()):
            for target in links.get("lateral", []) or []:
                back = (connections.get(target) or {}).get("lateral") or []
                if source not in back:
                    out.append(f"{cur_key}: {source} -> {target} is not mirrored back")
    return out


# ---------------------------------------------------------------------------
#  Defaults baseline
# ---------------------------------------------------------------------------
# exercise_progression_defs_default.json is a read-only snapshot of the pristine graph.
# Nothing in the application writes to it; it exists so that "revert to default" has
# something to restore from once CURRICULA above has been edited.

DEFAULTS_FILENAME = "exercise_progression_defs_default.json"


def defaults_path() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULTS_FILENAME)


def normalize_curricula(curricula: dict[str, dict]) -> dict[str, dict]:
    """Return a deep, canonically-ordered copy of `curricula`.

    Canonical means: sources ordered by their exercise number, connection types in
    CONNECTION_TYPES order, and empty types dropped. Saving a normalized graph keeps the
    file a minimal diff instead of a reshuffle, and makes equality comparisons against
    the baseline meaningful regardless of the order the editor happened to build them in.
    """
    out: dict[str, dict] = {}
    for cur_key, cur in curricula.items():
        connections = cur.get("connections") or {}
        ordered_sources = sorted(
            connections,
            key=lambda abb: (
                (EXERCISE_DEFS.get(abb) or {}).get("exerc_number") or 0,
                abb,
            ),
        )
        new_connections: dict[str, dict] = {}
        for abb in ordered_sources:
            links = connections.get(abb) or {}
            new_links = {
                conn_type: [str(t) for t in links[conn_type]]
                for conn_type in CONNECTION_TYPES
                if links.get(conn_type)
            }
            if new_links:
                new_connections[abb] = new_links
        out[cur_key] = {
            "label": str(cur.get("label") or cur_key),
            "connections": new_connections,
        }
    return out


def load_defaults() -> dict[str, dict]:
    """The pristine baseline. Returns {} if the file is missing or unreadable.

    An empty result is not fatal — the application runs off CURRICULA — but it does mean
    reverting is unavailable, which the editor surfaces rather than silently offering a
    reset that would do nothing.
    """
    import json
    import os

    path = defaults_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return normalize_curricula(
        {k: v for k, v in data.items() if isinstance(v, dict)}
    )


CURRICULA_DEFAULTS: dict[str, dict] = load_defaults()


def revert_to_defaults() -> dict[str, dict]:
    """A fresh copy of the baseline graph, for the editor to load. Never the live object."""
    return normalize_curricula(CURRICULA_DEFAULTS)


def changed_from_defaults(curricula: dict[str, dict] | None = None) -> dict[str, list[str]]:
    """Which sources differ from the baseline, keyed by curriculum.

    Used for the editor's change marks. Returns {} when there is no baseline, so a
    missing baseline reads as "nothing to compare" rather than "everything changed".
    """
    if not CURRICULA_DEFAULTS:
        return {}
    current = normalize_curricula(CURRICULA if curricula is None else curricula)
    out: dict[str, list[str]] = {}
    for cur_key, cur in current.items():
        base = (CURRICULA_DEFAULTS.get(cur_key) or {}).get("connections") or {}
        live = cur.get("connections") or {}
        changed = [abb for abb in set(base) | set(live) if base.get(abb) != live.get(abb)]
        if cur.get("label") != (CURRICULA_DEFAULTS.get(cur_key) or {}).get("label"):
            changed.append("__label")
        if changed:
            out[cur_key] = sorted(changed)
    return out


def write_defaults_file(curricula: dict[str, dict] | None = None, force: bool = False) -> str:
    """Create the baseline snapshot from `curricula` (default: the live graph).

    Refuses to overwrite an existing file unless `force`, because doing so would enshrine
    already-edited values as the thing to revert to, destroying the only copy of the
    original graph. Intended as a one-off at packaging time, not a UI action.
    """
    import json
    import os

    path = defaults_path()
    if os.path.exists(path) and not force:
        raise FileExistsError(
            f"{path} already exists. Overwriting it would make the current (possibly "
            f"edited) graph the new baseline. Pass force=True only if that is intended."
        )

    payload = normalize_curricula(CURRICULA if curricula is None else curricula)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
#  Writing the graph back into this file
# ---------------------------------------------------------------------------

_CURRICULA_BEGIN = (
    "# --- BEGIN CURRICULA "
    "(rewritten by Settings > Exercises > Exercise Progression) ---"
)
_CURRICULA_DECL = "CURRICULA: dict[str, dict] = {"
_CURRICULA_END = "# --- END CURRICULA ---"


def format_curricula_source(curricula: dict[str, dict]) -> str:
    """Render `curricula` as the marker-delimited source block, one source per line."""
    import json

    def q(value) -> str:
        return json.dumps(value, ensure_ascii=False)

    normalized = normalize_curricula(curricula)
    lines = [_CURRICULA_BEGIN, _CURRICULA_DECL]
    for cur_key, cur in normalized.items():
        lines.append(f"    {q(cur_key)}: {{")
        lines.append(f"        {q('label')}: {q(cur['label'])},")
        lines.append(f"        {q('connections')}: {{")
        for abb, links in cur["connections"].items():
            body = ", ".join(f"{q(t)}: {q(dests)}" for t, dests in links.items())
            lines.append(f"            {q(abb)}: {{{body}}},")
        lines.append("        },")
        lines.append("    },")
    lines.append("}")
    lines.append(_CURRICULA_END)
    return "\n".join(lines)


def _verify_curricula_source(source: str, expected: dict[str, dict], path: str) -> None:
    """Parse the about-to-be-written source and confirm it round-trips `expected`."""
    try:
        compile(source, path, "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Generated progression graph is not valid Python: {e}") from e

    start = source.find(_CURRICULA_DECL)
    end = source.find(_CURRICULA_END)
    if start < 0 or end < 0:
        raise RuntimeError("Generated source lost the CURRICULA declaration or END marker.")

    namespace: dict = {}
    try:
        exec(compile(source[start:end], path, "exec"), namespace)
    except Exception as e:
        raise RuntimeError(f"Generated progression graph does not evaluate: {e}") from e

    written = namespace.get("CURRICULA")
    if written != expected:
        raise RuntimeError(
            "Generated progression graph does not match the values it was built from; "
            "refusing to write."
        )


def save_curricula(curricula: dict[str, dict]) -> str:
    """Rewrite the CURRICULA block in this file and update the live dict. Returns the path.

    The rewritten source is parsed and compared against `curricula` *before* it replaces
    anything, and the write itself is atomic. A bug in the editor can therefore fail the
    save, but cannot leave a corrupt or truncated graph on disk — which for a file
    imported at startup would be unrecoverable without git.

    CURRICULA is updated **in place**, because `RSAC_Freeware_1_00.py` holds this very
    object via `from exercise_progression_defs import CURRICULA`; rebinding would leave
    it on a stale graph.

    Refuses to write a structurally broken graph: `check_progression_consistency` is run
    on the candidate first, since every problem it reports is invisible at runtime.
    """
    import os

    path = os.path.abspath(__file__)
    if not path.endswith(".py"):
        raise RuntimeError(
            f"Cannot edit the progression graph: {path} is not editable Python source. "
            f"This happens in a frozen/bundled build."
        )

    prepared = normalize_curricula(curricula)
    if not prepared:
        raise ValueError("Refusing to save an empty progression graph.")
    for cur_key, cur in prepared.items():
        if not cur["connections"]:
            raise ValueError(f"Curriculum {cur_key!r} has no connections; refusing to save.")

    problems = check_progression_consistency(prepared)
    if problems:
        raise ValueError(
            "The progression graph has unresolved problems:\n  - "
            + "\n  - ".join(problems)
        )

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    start = original.find(_CURRICULA_BEGIN)
    end = original.find(_CURRICULA_END)
    if start < 0 or end < 0 or end < start:
        raise RuntimeError(
            f"Could not find the BEGIN/END CURRICULA markers in {path}. "
            f"Refusing to guess where the graph starts."
        )

    updated = (
        original[:start]
        + format_curricula_source(prepared)
        + original[end + len(_CURRICULA_END):]
    )

    _verify_curricula_source(updated, prepared, path)

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    os.replace(tmp, path)

    # Mutate in place — the app holds this exact object.
    CURRICULA.clear()
    CURRICULA.update(prepared)

    return path
