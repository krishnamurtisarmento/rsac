"""Exercise catalogue — single source of truth, shared by the app and screenshot_ocr.

This lives in its own module on purpose. Both `RSAC_Freeware_1_00.py` and
`screenshot_ocr/check_scores_standalone_6_0.py` need EXERCISE_DEFS, and having the OCR
package import it from the main application module created a circular dependency that
silently broke when the application file was renamed (see FREEWARE_HANDOFF.md 5.7).

This module must not import anything from the application.

EXERCISE_DEFS below is the catalogue actually in force. Settings > Exercises > Skill
Ratings edits it and rewrites the block between the BEGIN/END markers in place, so the
values you read here are always the live ones.

The pristine baseline lives beside this file in exercise_defs_default.json. It is only
ever read — it is what "revert to default" restores from. Keep it in version control; if it
is lost, reverting is no longer possible (see `write_defaults_file`).

The region between the markers is generated. Anything you add by hand inside it will be
discarded on the next save; put it outside the markers.
"""

from __future__ import annotations

# --- BEGIN EXERCISE_DEFS (rewritten by Settings > Exercises > Skill Ratings) ---
EXERCISE_DEFS: dict[str, dict[str, int | str | None]] = {
    "pp1": {"exerc_number": 1, "exerc_full": "Pick & Place", "id": 638, "exerc_cat": "inm", "bimd": 1, "enwm": 1, "caac": 0, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 2, "skill_stringency": 1, "skill_overall": 3},
    "ppc": {"exerc_number": 2, "exerc_full": "Pick & Place - Clutching", "id": 869, "exerc_cat": "inm", "bimd": 1, "enwm": 2, "caac": 10, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 13, "skill_stringency": 5, "skill_overall": 18},
    "ct1": {"exerc_number": 3, "exerc_full": "Camera Targeting 1", "id": 628, "exerc_cat": "inm", "bimd": 1, "enwm": 0, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 7, "skill_stringency": 3, "skill_overall": 10},
    "ct2": {"exerc_number": 4, "exerc_full": "Camera Targeting 2", "id": 672, "exerc_cat": "inm", "bimd": 2, "enwm": 3, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 11, "skill_stringency": 4, "skill_overall": 15},
    "pb1": {"exerc_number": 5, "exerc_full": "Peg Board 1", "id": 683, "exerc_cat": "inm", "bimd": 3, "enwm": 3, "caac": 4, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 10, "skill_stringency": 3, "skill_overall": 13},
    "pb2": {"exerc_number": 6, "exerc_full": "Peg Board 2", "id": 684, "exerc_cat": "inm", "bimd": 4, "enwm": 4, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 14, "skill_stringency": 4, "skill_overall": 18},
    "pb3": {"exerc_number": 7, "exerc_full": "Peg Board 3", "id": 685, "exerc_cat": "inm", "bimd": 5, "enwm": 5, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 18, "skill_stringency": 5, "skill_overall": 23},
    "30d": {"exerc_number": 8, "exerc_full": "30 Degree Camera Flip", "id": 786, "exerc_cat": "inm", "bimd": 5, "enwm": 12, "caac": 15, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 32, "skill_stringency": 8, "skill_overall": 40},
    "mb1": {"exerc_number": 9, "exerc_full": "Match Board 1", "id": 678, "exerc_cat": "inm", "bimd": 2, "enwm": 5, "caac": 1, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 8, "skill_stringency": 4, "skill_overall": 12},
    "mb2": {"exerc_number": 10, "exerc_full": "Match Board 2", "id": 679, "exerc_cat": "inm", "bimd": 4, "enwm": 3, "caac": 3, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 10, "skill_stringency": 5, "skill_overall": 15},
    "mb3": {"exerc_number": 11, "exerc_full": "Match Board 3", "id": 680, "exerc_cat": "3au", "bimd": 5, "enwm": 4, "caac": 5, "necs": 0, "caut": 0, "trda": 8, "skill_intrinsic": 22, "skill_stringency": 6, "skill_overall": 28},
    "mbc": {"exerc_number": 12, "exerc_full": "Match Board - Clutching", "id": 870, "exerc_cat": "inm", "bimd": 5, "enwm": 3, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 16, "skill_stringency": 7, "skill_overall": 23},
    "ttr": {"exerc_number": 13, "exerc_full": "Tower Transfer", "id": 898, "exerc_cat": "inm", "bimd": 3, "enwm": 5, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 16, "skill_stringency": 3, "skill_overall": 19},
    "rtt": {"exerc_number": 14, "exerc_full": "Ring Tower Transfer", "id": 888, "exerc_cat": "inm", "bimd": 6, "enwm": 7, "caac": 12, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 25, "skill_stringency": 4, "skill_overall": 29},
    "4ac": {"exerc_number": 15, "exerc_full": "4th Arm Cutting", "id": 889, "exerc_cat": "3au", "bimd": 4, "enwm": 5, "caac": 3, "necs": 0, "caut": 0, "trda": 10, "skill_intrinsic": 22, "skill_stringency": 3, "skill_overall": 25},
    "rr1": {"exerc_number": 16, "exerc_full": "Ring & Rail 1", "id": 686, "exerc_cat": "inm", "bimd": 8, "enwm": 7, "caac": 7, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 22, "skill_stringency": 4, "skill_overall": 26},
    "rr2": {"exerc_number": 17, "exerc_full": "Ring & Rail 2", "id": 640, "exerc_cat": "inm", "bimd": 10, "enwm": 11, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 29, "skill_stringency": 8, "skill_overall": 37},
    "rc1": {"exerc_number": 18, "exerc_full": "Roller Coaster 1", "id": 890, "exerc_cat": "inm", "bimd": 6, "enwm": 7, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 19, "skill_stringency": 5, "skill_overall": 24},
    "rc2": {"exerc_number": 19, "exerc_full": "Roller Coaster 2", "id": 891, "exerc_cat": "inm", "bimd": 8, "enwm": 9, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 25, "skill_stringency": 5, "skill_overall": 30},
    "rc3": {"exerc_number": 20, "exerc_full": "Roller Coaster 3", "id": 892, "exerc_cat": "inm", "bimd": 9, "enwm": 11, "caac": 11, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 31, "skill_stringency": 6, "skill_overall": 37},
    "rc4": {"exerc_number": 21, "exerc_full": "Roller Coaster 4", "id": 893, "exerc_cat": "inm", "bimd": 10, "enwm": 12, "caac": 13, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 35, "skill_stringency": 6, "skill_overall": 41},
    "rw1": {"exerc_number": 22, "exerc_full": "Ring Walk 1", "id": 687, "exerc_cat": "inm", "bimd": 6, "enwm": 5, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 17, "skill_stringency": 5, "skill_overall": 22},
    "rw2": {"exerc_number": 23, "exerc_full": "Ring Walk 2", "id": 688, "exerc_cat": "inm", "bimd": 7, "enwm": 7, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 22, "skill_stringency": 6, "skill_overall": 28},
    "rw3": {"exerc_number": 24, "exerc_full": "Ring Walk 3", "id": 689, "exerc_cat": "3au", "bimd": 8, "enwm": 8, "caac": 13, "necs": 0, "caut": 0, "trda": 15, "skill_intrinsic": 44, "skill_stringency": 5, "skill_overall": 49},
    "vop": {"exerc_number": 25, "exerc_full": "Vitruvian Operation", "id": 644, "exerc_cat": "inm", "bimd": 2, "enwm": 6, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 16, "skill_stringency": 8, "skill_overall": 24},
    "sc1": {"exerc_number": 26, "exerc_full": "Stacking Challenge 1", "id": 641, "exerc_cat": "inm", "bimd": 8, "enwm": 7, "caac": 6, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 21, "skill_stringency": 9, "skill_overall": 30},
    "sc2": {"exerc_number": 27, "exerc_full": "Stacking Challenge 2", "id": 642, "exerc_cat": "inm", "bimd": 10, "enwm": 9, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 27, "skill_stringency": 10, "skill_overall": 37},
    "ppd": {"exerc_number": 28, "exerc_full": "Puzzle Piece Dissection", "id": 904, "exerc_cat": "inm", "bimd": 11, "enwm": 13, "caac": 8, "necs": 0, "caut": 0, "trda": 0, "skill_intrinsic": 32, "skill_stringency": 8, "skill_overall": 40},
    "es1": {"exerc_number": 29, "exerc_full": "Energy Switching 1", "id": 637, "exerc_cat": "cat", "bimd": 2, "enwm": 1, "caac": 4, "necs": 0, "caut": 5, "trda": 0, "skill_intrinsic": 12, "skill_stringency": 5, "skill_overall": 17},
    "es2": {"exerc_number": 30, "exerc_full": "Energy Switching 2", "id": 871, "exerc_cat": "cat", "bimd": 3, "enwm": 2, "caac": 2, "necs": 0, "caut": 10, "trda": 0, "skill_intrinsic": 17, "skill_stringency": 6, "skill_overall": 23},
    "ech": {"exerc_number": 31, "exerc_full": "Energy Challenge", "id": 885, "exerc_cat": "cat", "bimd": 6, "enwm": 4, "caac": 10, "necs": 0, "caut": 15, "trda": 0, "skill_intrinsic": 35, "skill_stringency": 7, "skill_overall": 42},
    "ed2": {"exerc_number": 32, "exerc_full": "Energy Dissection 2", "id": 675, "exerc_cat": "cat", "bimd": 2, "enwm": 3, "caac": 2, "necs": 0, "caut": 6, "trda": 0, "skill_intrinsic": 13, "skill_stringency": 4, "skill_overall": 17},
    "ed3": {"exerc_number": 33, "exerc_full": "Energy Dissection 3", "id": 872, "exerc_cat": "cat", "bimd": 2, "enwm": 3, "caac": 2, "necs": 0, "caut": 8, "trda": 0, "skill_intrinsic": 15, "skill_stringency": 4, "skill_overall": 19},
    "nt1": {"exerc_number": 34, "exerc_full": "Needle Targeting", "id": 681, "exerc_cat": "ned", "bimd": 4, "enwm": 3, "caac": 7, "necs": 4, "caut": 0, "trda": 0, "skill_intrinsic": 18, "skill_stringency": 6, "skill_overall": 24},
    "tr1": {"exerc_number": 35, "exerc_full": "Thread the Rings 1", "id": 646, "exerc_cat": "ned", "bimd": 4, "enwm": 4, "caac": 9, "necs": 6, "caut": 0, "trda": 0, "skill_intrinsic": 23, "skill_stringency": 8, "skill_overall": 31},
    "tr2": {"exerc_number": 36, "exerc_full": "Thread the Rings 2", "id": 668, "exerc_cat": "ned", "bimd": 4, "enwm": 5, "caac": 11, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 28, "skill_stringency": 9, "skill_overall": 37},
    "ss0": {"exerc_number": 37, "exerc_full": "Basic Suture Sponge", "id": 787, "exerc_cat": "ned", "bimd": 5, "enwm": 4, "caac": 2, "necs": 5, "caut": 0, "trda": 0, "skill_intrinsic": 16, "skill_stringency": 3, "skill_overall": 19},
    "ss1": {"exerc_number": 38, "exerc_full": "Suture Sponge 1", "id": 643, "exerc_cat": "ned", "bimd": 4, "enwm": 4, "caac": 2, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 18, "skill_stringency": 8, "skill_overall": 26},
    "ss2": {"exerc_number": 39, "exerc_full": "Suture Sponge 2", "id": 692, "exerc_cat": "ned", "bimd": 5, "enwm": 4, "caac": 3, "necs": 9, "caut": 0, "trda": 0, "skill_intrinsic": 21, "skill_stringency": 9, "skill_overall": 30},
    "ss3": {"exerc_number": 40, "exerc_full": "Suture Sponge 3", "id": 693, "exerc_cat": "ned", "bimd": 5, "enwm": 6, "caac": 4, "necs": 10, "caut": 0, "trda": 0, "skill_intrinsic": 25, "skill_stringency": 10, "skill_overall": 35},
    "ss4": {"exerc_number": 41, "exerc_full": "Mobile Suture Sponge", "id": 915, "exerc_cat": "ned", "bimd": 8, "enwm": 8, "caac": 6, "necs": 11, "caut": 0, "trda": 0, "skill_intrinsic": 33, "skill_stringency": 7, "skill_overall": 40},
    "bgd": {"exerc_number": 42, "exerc_full": "Big Dipper", "id": 908, "exerc_cat": "ned", "bimd": 6, "enwm": 6, "caac": 6, "necs": 6, "caut": 0, "trda": 0, "skill_intrinsic": 24, "skill_stringency": 6, "skill_overall": 30},
    "tu1": {"exerc_number": 43, "exerc_full": "Tubes 1", "id": 694, "exerc_cat": "ned", "bimd": 6, "enwm": 5, "caac": 4, "necs": 7, "caut": 0, "trda": 0, "skill_intrinsic": 22, "skill_stringency": 4, "skill_overall": 26},
    "tu2": {"exerc_number": 44, "exerc_full": "Tubes 2", "id": 875, "exerc_cat": "ned", "bimd": 7, "enwm": 6, "caac": 5, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 26, "skill_stringency": 6, "skill_overall": 32},
    "tu3": {"exerc_number": 45, "exerc_full": "Tubes 3", "id": 876, "exerc_cat": "ned", "bimd": 7, "enwm": 6, "caac": 6, "necs": 12, "caut": 0, "trda": 0, "skill_intrinsic": 31, "skill_stringency": 8, "skill_overall": 39},
    "row": {"exerc_number": 46, "exerc_full": "Rope Walk", "id": 691, "exerc_cat": "sut", "bimd": 3, "enwm": 2, "caac": 3, "necs": 1, "caut": 0, "trda": 0, "skill_intrinsic": 9, "skill_stringency": 3, "skill_overall": 12},
    "wch": {"exerc_number": 47, "exerc_full": "Wound Closure - Horizontal", "id": 882, "exerc_cat": "sut", "bimd": 7, "enwm": 6, "caac": 2, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 23, "skill_stringency": 7, "skill_overall": 30},
    "wcv": {"exerc_number": 48, "exerc_full": "Wound Closure Vertical", "id": 881, "exerc_cat": "sut", "bimd": 6, "enwm": 5, "caac": 2, "necs": 9, "caut": 0, "trda": 0, "skill_intrinsic": 22, "skill_stringency": 7, "skill_overall": 29},
    "tch": {"exerc_number": 49, "exerc_full": "Tube Closure - Horizontal", "id": 695, "exerc_cat": "sut", "bimd": 7, "enwm": 7, "caac": 2, "necs": 10, "caut": 0, "trda": 0, "skill_intrinsic": 26, "skill_stringency": 7, "skill_overall": 33},
    "tcv": {"exerc_number": 50, "exerc_full": "Tube Closure - Vertical", "id": 696, "exerc_cat": "sut", "bimd": 6, "enwm": 6, "caac": 2, "necs": 11, "caut": 0, "trda": 0, "skill_intrinsic": 25, "skill_stringency": 7, "skill_overall": 32},
    "sug": {"exerc_number": 51, "exerc_full": "Suturing", "id": 902, "exerc_cat": "sut", "bimd": 8, "enwm": 8, "caac": 2, "necs": 9, "caut": 0, "trda": 0, "skill_intrinsic": 27, "skill_stringency": 5, "skill_overall": 32},
    "rrt": {"exerc_number": 52, "exerc_full": "Railroad Tracks", "id": 910, "exerc_cat": "sut", "bimd": 9, "enwm": 9, "caac": 3, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 29, "skill_stringency": 6, "skill_overall": 35},
    "tah": {"exerc_number": 53, "exerc_full": "Tube Anastomosis Horizontal", "id": 884, "exerc_cat": "sut", "bimd": 14, "enwm": 14, "caac": 7, "necs": 14, "caut": 0, "trda": 0, "skill_intrinsic": 49, "skill_stringency": 9, "skill_overall": 58},
    "tav": {"exerc_number": 54, "exerc_full": "Tube Anastomosis Vertical", "id": 883, "exerc_cat": "sut", "bimd": 15, "enwm": 15, "caac": 9, "necs": 15, "caut": 0, "trda": 0, "skill_intrinsic": 54, "skill_stringency": 9, "skill_overall": 63},
    "kr1": {"exerc_number": 55, "exerc_full": "Knot the Ring 1", "id": 676, "exerc_cat": "not", "bimd": 5, "enwm": 6, "caac": 4, "necs": 4, "caut": 0, "trda": 0, "skill_intrinsic": 19, "skill_stringency": 6, "skill_overall": 25},
    "kr2": {"exerc_number": 56, "exerc_full": "Knot the Ring 2", "id": 677, "exerc_cat": "not", "bimd": 6, "enwm": 7, "caac": 5, "necs": 5, "caut": 0, "trda": 0, "skill_intrinsic": 23, "skill_stringency": 7, "skill_overall": 30},
    "kr3": {"exerc_number": 57, "exerc_full": "Knot the Ring 3", "id": 877, "exerc_cat": "not", "bimd": 7, "enwm": 8, "caac": 6, "necs": 8, "caut": 0, "trda": 0, "skill_intrinsic": 29, "skill_stringency": 7, "skill_overall": 36},
    "kr4": {"exerc_number": 58, "exerc_full": "Knot the Ring 4", "id": 878, "exerc_cat": "not", "bimd": 7, "enwm": 9, "caac": 6, "necs": 9, "caut": 0, "trda": 0, "skill_intrinsic": 31, "skill_stringency": 7, "skill_overall": 38},
    "is1": {"exerc_number": 59, "exerc_full": "Interrupted Suture 1", "id": 879, "exerc_cat": "not", "bimd": 8, "enwm": 9, "caac": 4, "necs": 10, "caut": 0, "trda": 0, "skill_intrinsic": 31, "skill_stringency": 8, "skill_overall": 39},
    "is2": {"exerc_number": 60, "exerc_full": "Interrupted Suture 2", "id": 880, "exerc_cat": "not", "bimd": 8, "enwm": 10, "caac": 5, "necs": 10, "caut": 0, "trda": 0, "skill_intrinsic": 33, "skill_stringency": 8, "skill_overall": 41},
}
# --- END EXERCISE_DEFS ---

# ---------------------------------------------------------------------------
#  Field roles
# ---------------------------------------------------------------------------

# The six skill components a rater scores directly.
SKILL_COMPONENT_KEYS: tuple[str, ...] = ("bimd", "enwm", "caac", "necs", "caut", "trda")

# Display names for the component codes. These are *inferred* from how the codes
# are used in the shipped data and are not documented anywhere in the codebase:
# only "cat" exercises carry `caut`, only "3au" exercises carry `trda`, only "ned"
# and "sut" exercises carry `necs`, `caac` peaks on the Camera Targeting and
# Clutching exercises. Correct them here if the intended meaning differs — nothing
# but the UI reads these.
SKILL_COMPONENT_LABELS: dict[str, str] = {
    "bimd": "Bimanual Dexterity",
    "enwm": "EndoWrist Manipulation",
    "caac": "Camera and Clutching",
    "necs": "Needle Control & Suturing",
    "caut": "Cautery / Energy",
    "trda": "Third Arm Use",
}

# Derived, never authored by hand. Verified to hold for all 60 shipped exercises:
#   skill_intrinsic = sum(SKILL_COMPONENT_KEYS)
#   skill_overall   = skill_intrinsic + skill_stringency
# Any editor must recompute these rather than accept typed values, or the
# catalogue will silently disagree with itself.
DERIVED_KEYS: tuple[str, ...] = ("skill_intrinsic", "skill_overall")

# Everything a site may legitimately change, in display order.
EDITABLE_KEYS: tuple[str, ...] = (
    "exerc_number",
    "exerc_full",
    "id",
    "exerc_cat",
) + SKILL_COMPONENT_KEYS + ("skill_stringency",)

INT_KEYS: tuple[str, ...] = (
    ("exerc_number", "id") + SKILL_COMPONENT_KEYS + ("skill_stringency",) + DERIVED_KEYS
)


def recompute_derived(entry: dict) -> dict:
    """Fill in DERIVED_KEYS from the authored fields. Mutates and returns `entry`."""
    intrinsic = sum(int(entry.get(k) or 0) for k in SKILL_COMPONENT_KEYS)
    entry["skill_intrinsic"] = intrinsic
    entry["skill_overall"] = intrinsic + int(entry.get("skill_stringency") or 0)
    return entry


# Key order used when the catalogue is written back out, so that a saved file is a
# minimal diff against the previous one rather than a reshuffle.
CATALOGUE_KEY_ORDER: tuple[str, ...] = (
    ("exerc_number", "exerc_full", "id", "exerc_cat")
    + SKILL_COMPONENT_KEYS
    + ("skill_intrinsic", "skill_stringency", "skill_overall")
)


def check_derived_consistency(entries: dict[str, dict] | None = None) -> list[str]:
    """Report entries whose stored derived values disagree with the rule.

    Deliberately a report rather than a silent fix: the editor always writes
    consistent values, so a disagreement means someone hand-edited the file and
    should be told, not quietly overruled.
    """
    if entries is None:
        entries = EXERCISE_DEFS
    problems: list[str] = []
    for abb, entry in entries.items():
        expected = recompute_derived(dict(entry))
        for key in DERIVED_KEYS:
            if entry.get(key) != expected[key]:
                problems.append(
                    f"{abb}: {key} is {entry.get(key)}, rule gives {expected[key]}"
                )
    return problems


# ---------------------------------------------------------------------------
#  Defaults baseline
# ---------------------------------------------------------------------------
# exercise_defs_default.json is a read-only snapshot of the pristine catalogue.
# Nothing in the application writes to it; it exists so that "revert to default"
# has something to restore from once EXERCISE_DEFS above has been edited.

DEFAULTS_FILENAME = "exercise_defs_default.json"


def defaults_path() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULTS_FILENAME)


def load_defaults() -> dict[str, dict]:
    """The pristine baseline. Returns {} if the file is missing or unreadable.

    An empty result is not fatal — the application runs off EXERCISE_DEFS — but it
    does mean reverting is unavailable, which the editor surfaces rather than
    silently offering a reset that would do nothing.
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
    return {
        abb: recompute_derived(dict(entry))
        for abb, entry in data.items()
        if isinstance(entry, dict)
    }


EXERCISE_DEFS_DEFAULTS: dict[str, dict] = load_defaults()


def diff_from_defaults(abb: str, entry: dict) -> dict:
    """The subset of `entry` that differs from the baseline, for change marking.

    Only authored fields are compared; the derived ones follow from them, so
    reporting those too would double-count every edit.
    """
    default = EXERCISE_DEFS_DEFAULTS.get(abb) or {}
    if not default:
        return {}
    out: dict = {}
    for key in EDITABLE_KEYS:
        if key in entry and entry[key] != default.get(key):
            out[key] = entry[key]
    return out


def write_defaults_file(entries: dict[str, dict] | None = None, force: bool = False) -> str:
    """Create the baseline snapshot from `entries` (default: the live catalogue).

    Refuses to overwrite an existing file unless `force`, because doing so would
    enshrine already-edited values as the thing to revert to — destroying the only
    copy of the original ratings. Intended as a one-off at packaging time, not a
    UI action.
    """
    import json
    import os

    path = defaults_path()
    if os.path.exists(path) and not force:
        raise FileExistsError(
            f"{path} already exists. Overwriting it would make the current (possibly "
            f"edited) values the new baseline. Pass force=True only if that is intended."
        )

    source = EXERCISE_DEFS if entries is None else entries
    payload = {
        abb: {key: entry.get(key) for key in CATALOGUE_KEY_ORDER}
        for abb, entry in sorted(
            source.items(), key=lambda kv: (kv[1].get("exerc_number") or 0, kv[0])
        )
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
#  Writing the catalogue back into this file
# ---------------------------------------------------------------------------

_CATALOGUE_BEGIN = "# --- BEGIN EXERCISE_DEFS (rewritten by Settings > Exercises > Skill Ratings) ---"
_CATALOGUE_DECL = "EXERCISE_DEFS: dict[str, dict[str, int | str | None]] = {"
_CATALOGUE_END = "# --- END EXERCISE_DEFS ---"


def format_catalogue_source(entries: dict[str, dict]) -> str:
    """Render `entries` as the marker-delimited source block, one exercise per line."""
    import json

    lines = [_CATALOGUE_BEGIN, _CATALOGUE_DECL]
    for abb, entry in sorted(
        entries.items(), key=lambda kv: (kv[1].get("exerc_number") or 0, kv[0])
    ):
        fields = ", ".join(
            f"{json.dumps(key)}: {json.dumps(entry.get(key), ensure_ascii=False)}"
            for key in CATALOGUE_KEY_ORDER
        )
        lines.append(f"    {json.dumps(abb, ensure_ascii=False)}: {{{fields}}},")
    lines.append("}")
    lines.append(_CATALOGUE_END)
    return "\n".join(lines)


def save_catalogue(entries: dict[str, dict]) -> str:
    """Rewrite the catalogue block in this file and update the live dict. Returns the path.

    The rewritten source is parsed and compared against `entries` *before* it
    replaces anything, and the write itself is atomic. A bug in the editor can
    therefore fail the save, but cannot leave a corrupt or truncated catalogue on
    disk — which for a file that is imported at startup would be unrecoverable
    without git.

    EXERCISE_DEFS is updated **in place**, because both `RSAC_Freeware_1_00.py` and
    `screenshot_ocr/check_scores_standalone_6_0.py` hold this very object via
    `from exercise_defs import EXERCISE_DEFS`; rebinding would leave them stale.
    """
    import os

    path = os.path.abspath(__file__)
    if not path.endswith(".py"):
        raise RuntimeError(
            f"Cannot edit the catalogue: {path} is not editable Python source. "
            f"This happens in a frozen/bundled build."
        )

    # Coerce and type-check up front. Without this a stray string in a numeric
    # field surfaces as a TypeError from inside a sort, which tells the caller
    # nothing about which exercise is at fault.
    prepared: dict[str, dict] = {}
    for abb, entry in entries.items():
        clean: dict = {}
        for key in CATALOGUE_KEY_ORDER:
            value = entry.get(key)
            if key in INT_KEYS:
                try:
                    clean[key] = int(value)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"{abb}: {key!r} must be a whole number, not {value!r}"
                    ) from None
            else:
                clean[key] = "" if value is None else str(value)
        prepared[abb] = recompute_derived(clean)

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    start = original.find(_CATALOGUE_BEGIN)
    end = original.find(_CATALOGUE_END)
    if start < 0 or end < 0 or end < start:
        raise RuntimeError(
            f"Could not find the BEGIN/END EXERCISE_DEFS markers in {path}. "
            f"Refusing to guess where the catalogue starts."
        )

    updated = (
        original[:start]
        + format_catalogue_source(prepared)
        + original[end + len(_CATALOGUE_END):]
    )

    _verify_catalogue_source(updated, prepared, path)

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    os.replace(tmp, path)

    for abb, entry in prepared.items():
        live = EXERCISE_DEFS.get(abb)
        if live is None:
            EXERCISE_DEFS[abb] = dict(entry)
        else:
            live.clear()
            live.update(entry)
    for abb in [a for a in EXERCISE_DEFS if a not in prepared]:
        del EXERCISE_DEFS[abb]

    return path


def _verify_catalogue_source(source: str, expected: dict[str, dict], path: str) -> None:
    """Parse the about-to-be-written source and confirm it round-trips `expected`."""
    try:
        compile(source, path, "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Generated catalogue is not valid Python: {e}") from e

    start = source.find(_CATALOGUE_DECL)
    end = source.find(_CATALOGUE_END)
    namespace: dict = {}
    try:
        exec(compile(source[start:end], path, "exec"), namespace)
    except Exception as e:
        raise RuntimeError(f"Generated catalogue does not evaluate: {e}") from e

    parsed = namespace.get("EXERCISE_DEFS")
    if not isinstance(parsed, dict):
        raise RuntimeError("Generated catalogue did not define EXERCISE_DEFS as a dict.")
    if set(parsed) != set(expected):
        missing = sorted(set(expected) - set(parsed))
        extra = sorted(set(parsed) - set(expected))
        raise RuntimeError(
            f"Generated catalogue has the wrong exercises "
            f"(missing {missing}, unexpected {extra})."
        )
    for abb, entry in expected.items():
        if parsed[abb] != entry:
            raise RuntimeError(
                f"Generated catalogue does not round-trip {abb}: "
                f"wrote {entry}, read back {parsed[abb]}."
            )


def revert_to_defaults(abbs: list[str] | None = None) -> dict[str, dict]:
    """The catalogue with `abbs` (default: all) restored from the baseline.

    Returns a fresh dict for the caller to review and save; nothing is written and
    the live catalogue is untouched, so a mis-click is recoverable.
    """
    if not EXERCISE_DEFS_DEFAULTS:
        raise RuntimeError(
            f"No baseline to revert to: {defaults_path()} is missing or unreadable."
        )

    out = {abb: dict(entry) for abb, entry in EXERCISE_DEFS.items()}
    for abb in EXERCISE_DEFS_DEFAULTS if abbs is None else abbs:
        default = EXERCISE_DEFS_DEFAULTS.get(abb)
        if default is not None:
            out[abb] = dict(default)
    return out
