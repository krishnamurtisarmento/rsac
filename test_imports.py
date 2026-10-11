"""Smoke test: the cross-module import chain, the normative tables, and the live loop.

Run directly (no pytest needed):

    python test_imports.py

The import checks exist because renaming the main application module silently broke
the scoring module (then screenshot_ocr/check_scores_standalone_6_0.py, now
exercise_proficiency_scores.py), which took the live session down and made
Proficiency Margin return None for every attempt with no error shown at all
(FREEWARE_HANDOFF.md 5.7). Nothing in the codebase would have caught that.

The live-loop checks guard the section 11 refactor: the manual-entry and screenshot
producers must keep emitting identical attempts, and AttemptProcessor must stay free of
Qt and of screenshot concerns or the two producers will drift apart again.

pytest will also collect the test_* functions below if it is ever added.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

APP_MODULE = "RSAC_Freeware_1_00"

# Imported by the app at runtime; a failure here disables a user-visible feature.
REQUIRED_MODULES = [
    "exercise_defs",
    "exercise_progression_defs",
    "exercise_proficiency_scores",
    "attempt_csv",
]


def _load_app():
    """Import the main application module, Qt first (it needs a QApplication)."""
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is None:
        QApplication([])
    return importlib.import_module(APP_MODULE)


def test_required_modules_import():
    for name in REQUIRED_MODULES:
        importlib.import_module(name)


def test_export_row_filter_is_not_site_specific():
    """A simulator export from any centre must be accepted, not silently dropped.

    The filter used to be `raw.startswith("Aluno")` — the subject-naming
    convention of the centre where RSAC was developed. Anywhere else, every row
    failed the test, so the import finished reporting zero attempts and raised
    nothing: the worst possible failure mode for a tool other people install.

    The replacement identifies a data row by its structure, so this test also
    pins the two behaviours that structure has to keep: the header line is not a
    data row, and the simulator's own service accounts are not trainees (which
    the "Aluno" test excluded only by coincidence).
    """
    app = _load_app()

    def row(subject, status="Complete"):
        return (f"{subject},a@b.com,Student,Other,CIEX da Vinci Si Based,"
                f"2. Ring Tower Transfer,2026-07-08 14:06:37,{status},"
                f"1200,Drops,0,200,,")

    assert app.is_export_data_row(row("Aluno0111")), (
        "the original naming convention must still work"
    )
    assert app.is_export_data_row(row("Trainee_07")), (
        "a subject not named 'Aluno...' is still being discarded — the "
        "site-specific filter is back and other centres will import nothing"
    )
    assert app.is_export_data_row(row("Aluno0111", status="Incomplete")), (
        "incomplete attempts are data rows too; they are filtered later"
    )

    assert not app.is_export_data_row(
        "Username,Email,Profession,Specialty,Curriculum,Exercise,"
        "Date and Time,Status,Overall Score,Metric,Raw Value,Metric Score,,"
    ), "the header line is being treated as an attempt"
    assert not app.is_export_data_row(row("Administrator")), (
        "simulator service-account sessions are being counted as trainee attempts"
    )
    assert not app.is_export_data_row(""), "a blank line is not a data row"
    assert not app.is_export_data_row("a,b,c"), "a truncated row is not a data row"


def test_retrospective_gate_is_not_site_specific():
    """The retrospective-analysis menu must appear for any subject naming scheme.

    Its filename gate was `startswith("MimicClean_Aluno")`, so at another centre
    the context-menu item never appeared — the feature was absent rather than
    broken, which is far harder to notice. The real requirement is only that the
    file holds a single identifiable subject.
    """
    app = _load_app()
    ok = app.is_single_subject_clean_filename

    assert ok("MimicClean_Aluno0111_11_08_2026-15_42_39.csv")
    assert ok("MimicClean_Trainee07_11_08_2026-15_42_39.csv"), (
        "a non-'Aluno' subject no longer offers retrospective analysis"
    )
    assert ok("MimicClean_Trainee_07_11_08_2026-15_42_39.csv"), (
        "a subject code containing an underscore must still be recognised; the "
        "filename pattern has to backtrack past it to find the timestamp"
    )

    assert not ok("MimicClean_Multiple_11_08_2026-15_42_39.csv"), (
        "a multi-subject file cannot be replayed as one subject's progression"
    )
    assert not ok("MimicClean_11_08_2026-15_42_39.csv"), (
        "the legacy untagged format carries no subject to replay"
    )
    assert not ok("IncompleteAttempts_Aluno0111_11_08_2026-15_42_39.csv")
    assert not ok("")


def test_source_install_paths_are_unchanged():
    """In a source install every path must still resolve beside the application.

    The writable-folder indirection exists for frozen builds. It must be
    completely invisible to anyone running from source, which is how the tool is
    distributed and how every existing installation works.
    """
    import app_paths

    assert not app_paths.is_frozen(), "the test suite is not a frozen build"
    assert os.path.normcase(app_paths.user_data_dir()) == os.path.normcase(ROOT)
    assert os.path.normcase(app_paths.bundle_dir()) == os.path.normcase(ROOT)
    assert app_paths.bootstrap() == app_paths.user_data_dir()

    app = _load_app()
    assert os.path.normcase(app._script_dir()) == os.path.normcase(ROOT), (
        "_script_dir no longer points at the application folder, so an existing "
        "installation would stop finding its own subjects.json and CSVs"
    )
    assert os.path.dirname(app._config_path()) == app._script_dir(), (
        "rsac_config.json is no longer read from the folder RSAC writes to"
    )


def test_frozen_build_separates_writable_from_readonly():
    """Frozen, writable files must leave the bundle and assets must stay in it.

    A one-file bundle unpacks to a temporary folder that is deleted on exit, and
    an installed one-folder bundle is not writable without elevation. Either way
    subjects, attempt records and history cannot live beside the executable.
    """
    import app_paths

    saved_frozen = getattr(sys, "frozen", None)
    saved_meipass = getattr(sys, "_MEIPASS", None)
    bundle = os.path.join(tempfile.gettempdir(), "_MEI_rsac_test")
    try:
        sys.frozen = True           # type: ignore[attr-defined]
        sys._MEIPASS = bundle       # type: ignore[attr-defined]

        assert app_paths.is_frozen()
        assert os.path.normcase(app_paths.bundle_dir()) == os.path.normcase(bundle), (
            "read-only assets must be read from the bundle"
        )

        writable = app_paths.user_data_dir()
        assert os.path.normcase(writable) != os.path.normcase(bundle), (
            "writable files would be placed inside the bundle, so everything the "
            "tutor records would be lost when the application exits"
        )
        assert os.path.normcase(writable) != os.path.normcase(ROOT)
        assert app_paths.APP_NAME in writable

        # Assets resolve into the bundle, data resolves out of it.
        assert app_paths.asset_path("img", "RASC_logo.jpg").startswith(bundle)
        assert app_paths.data_path("subjects.json").startswith(writable)

        # Each editable module must be seeded together with the baseline its
        # "revert to defaults" action reads, or reverting would fail at runtime.
        for name in app_paths.SEEDED_FILES:
            assert os.path.isfile(os.path.join(ROOT, name)), (
                f"{name} is listed for seeding but is not in the project"
            )
        for module_name in ("exercise_defs", "exercise_progression_defs",
                            "exercise_proficiency_scores"):
            assert f"{module_name}.py" in app_paths.SEEDED_FILES, (
                f"{module_name} is editable through the GUI but is not seeded into "
                f"the writable folder, so the editor would have no source to rewrite"
            )
            assert f"{module_name}_default.json" in app_paths.SEEDED_FILES, (
                f"{module_name} is seeded without its defaults baseline, so "
                f"'revert to defaults' would fail in a frozen build"
            )
    finally:
        if saved_frozen is None:
            delattr(sys, "frozen")
        else:
            sys.frozen = saved_frozen       # type: ignore[attr-defined]
        if saved_meipass is None:
            delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = saved_meipass    # type: ignore[attr-defined]


def test_exercise_defs_has_no_app_dependency():
    """exercise_defs must stay importable on its own, or the cycle is back."""
    for stale in [m for m in sys.modules if m.startswith(APP_MODULE)]:
        del sys.modules[stale]
    importlib.import_module("exercise_defs")
    assert not any(m.startswith(APP_MODULE) for m in sys.modules), (
        "exercise_defs pulled in the application module — the circular dependency "
        "that broke on the last rename has been reintroduced"
    )


def test_exercise_defs_is_shared_not_copied():
    app = _load_app()
    import exercise_defs

    assert app.EXERCISE_DEFS is exercise_defs.EXERCISE_DEFS, (
        "the app has its own EXERCISE_DEFS copy again; the two will drift"
    )


def test_progression_defs_has_no_app_dependency():
    """exercise_progression_defs must stay importable on its own.

    It is extracted configuration, like exercise_defs; if it ever imports the app back
    we have the same cycle that broke on the last rename.
    """
    for stale in [m for m in sys.modules if m.startswith(APP_MODULE)]:
        del sys.modules[stale]
    importlib.import_module("exercise_progression_defs")
    assert not any(m.startswith(APP_MODULE) for m in sys.modules), (
        "exercise_progression_defs pulled in the application module"
    )


def test_progression_defs_are_shared_not_copied():
    """The app must read the progression graph, not keep its own copy of it."""
    app = _load_app()
    import exercise_progression_defs as ep

    for name in ("CURRICULA", "CONNECTION_TYPES", "CONNECTION_TYPE_COLORS",
                 "CONNECTION_TYPE_LABELS", "DEFAULT_CURRICULUM"):
        assert hasattr(app, name), (
            f"{name} is no longer reachable from the app module; references to it "
            f"elsewhere in the app will raise NameError"
        )
        assert getattr(app, name) is getattr(ep, name), (
            f"the app has its own {name} again; the two copies will drift"
        )


def test_progression_graph_is_consistent():
    """Every connection destination must exist and be able to progress.

    This is the silent one: NAED-3 reports a typo'd destination as "no option
    available", exactly as it reports a deliberate dead end, so a data-entry error is
    indistinguishable from intended behaviour at runtime.
    """
    import exercise_progression_defs as ep

    problems = ep.check_progression_consistency()
    assert not problems, (
        "exercise_progression_defs.py has a broken progression graph: "
        + "; ".join(problems)
    )


def test_every_curriculum_reaches_its_end():
    """Each curriculum must terminate, and every exercise in it must be reachable.

    A subject stranded in an unreachable component, or in a curriculum with no END,
    would simply never be told they had finished.
    """
    import exercise_progression_defs as ep

    for cur in ep.CURRICULA:
        connections = ep.connections_for(cur)
        assert any(
            ep.END_SENTINEL in targets
            for links in connections.values()
            for targets in links.values()
        ), f"curriculum {cur!r} has no {ep.END_SENTINEL} sentinel, so it never completes"

        targeted = {
            t
            for links in connections.values()
            for targets in links.values()
            for t in targets
            if t != ep.END_SENTINEL
        }
        roots = [abb for abb in connections if abb not in targeted]
        assert roots, f"curriculum {cur!r} has no entry point (every exercise is a target)"

        reachable: set[str] = set()
        stack = list(roots)
        while stack:
            node = stack.pop()
            if node in reachable or node == ep.END_SENTINEL:
                continue
            reachable.add(node)
            for targets in (connections.get(node) or {}).values():
                stack.extend(targets)

        stranded = sorted(set(connections) - reachable)
        assert not stranded, (
            f"curriculum {cur!r}: {stranded} cannot be reached from {sorted(roots)}"
        )


def test_progression_baseline_matches_the_live_graph():
    """The baseline must exist and describe the same curricula as the live graph.

    Without it 'reset to defaults' is impossible, and the editor disables the buttons
    rather than offering a reset that would silently do nothing.
    """
    import exercise_progression_defs as ep

    assert ep.CURRICULA_DEFAULTS, (
        f"baseline missing or unreadable at {ep.defaults_path()} — 'revert to default' "
        f"would be impossible"
    )
    assert set(ep.CURRICULA_DEFAULTS) == set(ep.CURRICULA), (
        "the baseline and the live graph describe different curricula"
    )


def test_progression_normalization_preserves_the_graph():
    """Canonical ordering must not change what the graph means."""
    import exercise_progression_defs as ep

    assert ep.normalize_curricula(ep.CURRICULA) == ep.CURRICULA, (
        "normalize_curricula altered the live graph rather than just reordering it"
    )


def test_progression_source_round_trips():
    """Rewriting the graph must reproduce it exactly, and verify before writing.

    Saving edits `exercise_progression_defs.py` itself, so a formatting bug here would
    corrupt a file imported at startup. Runs entirely on strings — nothing is written.
    """
    import exercise_progression_defs as ep

    expected = ep.normalize_curricula(ep.CURRICULA)
    block = ep.format_curricula_source(ep.CURRICULA)

    namespace: dict = {}
    start = block.find(ep._CURRICULA_DECL)
    end = block.find(ep._CURRICULA_END)
    exec(compile(block[start:end], "<generated>", "exec"), namespace)
    assert namespace["CURRICULA"] == expected, (
        "the generated CURRICULA block does not round-trip the current graph"
    )

    # The pre-write verification must actually reject a mismatch.
    wrong = {k: v for k, v in expected.items()}
    wrong.pop(next(iter(wrong)))
    try:
        ep._verify_curricula_source(block, wrong, "<generated>")
    except RuntimeError:
        pass
    else:
        raise AssertionError("_verify_curricula_source accepted the wrong graph")


def test_progression_save_refuses_a_broken_graph():
    """Save must reject what the consistency check rejects, and write nothing.

    A typo'd destination is invisible at runtime, so the save path is the last place it
    can be caught. Uses a graph built in memory; the real file is never opened.
    """
    import copy

    import exercise_progression_defs as ep

    for label, mutate in (
        ("typo destination", lambda g: g["grad"]["connections"]["pp1"].update({"upgrade": ["pb9"]})),
        ("self reference", lambda g: g["grad"]["connections"]["pp1"].update({"upgrade": ["pp1"]})),
        ("empty graph", lambda g: g.clear()),
    ):
        candidate = copy.deepcopy(ep.normalize_curricula(ep.CURRICULA))
        mutate(candidate)
        try:
            ep.save_curricula(candidate)
        except ValueError:
            pass
        else:
            raise AssertionError(f"save_curricula accepted a broken graph: {label}")

    # The live graph must be untouched by the refusals above.
    assert not ep.check_progression_consistency(), (
        "a refused save mutated the live graph"
    )


def test_naed3_resolves_for_every_exercise_and_decision():
    """NAED-3 must return a result for every exercise/decision pair, never raise."""
    app = _load_app()
    import exercise_progression_defs as ep

    for cur in ep.CURRICULA:
        for abb in ep.connections_for(cur):
            for decision in ("UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL"):
                result = app.compute_naed3_recommendation(abb, decision, cur)
                assert result.get("status"), (
                    f"NAED-3 returned no status for {cur}/{abb}/{decision}"
                )


def test_normative_tables_resolve():
    """The silent failure mode: tables import, but every lookup returns None."""
    app = _load_app()
    for abb in ("pp1", "pb1", "rtt"):
        assert app.get_overall_score_proficiency_floor(abb) is not None, (
            f"no proficiency floor for {abb} — Proficiency Margin will be silently "
            f"unavailable for every attempt"
        )
        assert app.get_overall_score_ceiling(abb) is not None, (
            f"no overall-score ceiling for {abb} — bad OCR reads will not be rejected"
        )


def test_norm_max_scaling_is_invertible_and_per_exercise():
    """norm_max drives the scale conversion, and the two directions must agree.

    Guards the bug this replaced: a flat x5 applied to mwr for every exercise,
    which multiplied an already-canonical score by 5 again on any exercise whose
    simulator setting had been changed to 0..200.
    """
    import exercise_proficiency_scores as eps

    # A metric on the canonical range must not be touched at all.
    assert eps.metric_norm_max("pp1", "ttc") == 200
    assert eps.simulator_to_canonical(137.5, "pp1", "ttc") == 137.5
    assert eps.canonical_to_simulator(137.5, "pp1", "ttc") == 137.5

    # mwr ships on 0..40, so proficiency 20 must land exactly on canonical 100.
    assert eps.metric_norm_max("pp1", "mwr") == 40
    assert eps.simulator_to_canonical(20.0, "pp1", "mwr") == 100.0
    assert eps.metric_pass_min_score("pp1", "mwr") == 20.0

    # Round trip, both ways, for every declared exercise/metric pair.
    for abb, metrics in eps.PROFICIENCY_BASELINES.items():
        for code in metrics:
            for value in (0.0, 7.25, 40.0):
                there = eps.simulator_to_canonical(value, abb, code)
                back = eps.canonical_to_simulator(there, abb, code)
                assert abs(back - value) < 1e-9, (
                    f"{abb}/{code}: scale conversion is not invertible "
                    f"({value} -> {there} -> {back})"
                )

    # norm_max must be declared on every metric line, not inferred.
    for abb, metrics in eps.PROFICIENCY_BASELINES.items():
        for code, entry in metrics.items():
            assert "norm_max" in entry, f"{abb}/{code} has no norm_max declared"
            assert entry["norm_max"] > 0, f"{abb}/{code} has a non-positive norm_max"

    # Editing one metric's norm_max must take effect there and nowhere else.
    entry = eps.PROFICIENCY_BASELINES["pp1"]["mwr"]
    previous = entry["norm_max"]
    entry["norm_max"] = 200
    try:
        assert eps.metric_norm_max("pp1", "mwr") == 200
        assert eps.simulator_to_canonical(150.0, "pp1", "mwr") == 150.0, (
            "an exercise whose simulator was switched to 0..200 is still being rescaled"
        )
        assert eps.metric_norm_max("pb1", "mwr") == 40, "the change leaked to another exercise"
    finally:
        entry["norm_max"] = previous


def test_baseline_source_rewrite_survives_extra_settings():
    """Saving proficiency values must not depend on emet_id being the last key.

    The rewrite is anchored on emet_id. It used to demand a closing brace right
    after it, so adding norm_max to those lines silently turned every save into a
    no-op — the backup was written, the dialog reported success, and the file was
    unchanged. Any setting added later must not reintroduce that.
    """
    app = _load_app()

    line = (
        '        "mwr": {"mean": 8.87, "stddev": 1.17, "prof_raw": 10.04, '
        '"direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, '
        '"emet_id_RSAC_2026": 3928, "norm_max": 40},'
    )
    new_vals = {"mean": 9.5, "stddev": 1.75, "prof_raw": 11.25}
    out = app._rewrite_baseline_values(line, 3928, new_vals)

    assert out != line, (
        "the rewrite matched nothing — saving proficiency values is a silent no-op"
    )
    assert '"mean": 9.5' in out and '"stddev": 1.75' in out and '"prof_raw": 11.25' in out
    assert '"norm_max": 40' in out, "the rewrite destroyed norm_max"
    assert '"emet_id_RSAC_2026": 3928' in out, "the rewrite destroyed the line's identity"
    assert '"direction": "lower"' in out

    # A different emet_id must leave the line completely alone.
    assert app._rewrite_baseline_values(line, 9999, new_vals) == line, (
        "the rewrite is not anchored to the requested metric"
    )

    # And it must work against the real module text, for a real metric.
    import exercise_proficiency_scores as eps

    with open(app._baselines_module_path(), "r", encoding="utf-8") as f:
        content = f.read()
    eid = eps.PROFICIENCY_BASELINES["pp1"]["mwr"]["emet_id_RSAC_2026"]
    rewritten = app._rewrite_baseline_values(content, eid, new_vals)
    assert rewritten != content, (
        f"no line in the live module matched emet_id {eid} — the save path is broken"
    )
    assert rewritten.count('"norm_max"') == content.count('"norm_max"'), (
        "the rewrite changed how many norm_max settings exist"
    )


def test_legacy_and_canonical_mwr_columns_agree():
    """Simulator exports and app-written rows must yield the same canonical mwr.

    Simulator exports carry mwrp_score_pre_200 on the simulator's scale; attempts
    recorded by this app write mwr_score_200 already canonical. Both must parse to
    the same value, or history and new attempts stop being comparable.
    """
    app = _load_app()

    legacy = ("Aluno0001,2026-01-01 00:00:00,Pick & Place,620,"
              "mwrp_score_pre_raw,8.9,mwrp_score_pre_200,20")
    native = ("Aluno0001,2026-01-01 00:00:00,Pick & Place,620,"
              "mwr_score_raw,8.9,mwr_score_200,100")

    a = app.classify_clean_line(legacy)
    b = app.classify_clean_line(native)

    assert a is not None and b is not None
    assert a["mwr_score_200"] == 100.0, (
        f"simulator-scale mwr 20 should rescale to canonical 100, got {a['mwr_score_200']}"
    )
    assert a["mwr_score_200"] == b["mwr_score_200"], (
        "the legacy pre-column and the canonical column disagree: "
        f"{a['mwr_score_200']} vs {b['mwr_score_200']}"
    )
    assert a["mwr_score_raw"] == b["mwr_score_raw"]


def test_floor_and_ceiling_follow_norm_max():
    """Floor and ceiling must be derived from norm_max, not hardcoded per metric."""
    import exercise_proficiency_scores as eps

    for abb, metrics in eps.PROFICIENCY_BASELINES.items():
        codes = set(metrics)
        expected_ceiling = sum(eps.metric_norm_max(abb, c) for c in codes)
        expected_floor = sum(eps.metric_norm_max(abb, c) / 2 for c in codes)

        assert eps.OVERALL_SCORE_CEILING[abb] == expected_ceiling, (
            f"{abb}: ceiling {eps.OVERALL_SCORE_CEILING[abb]} != sum(norm_max) {expected_ceiling}"
        )
        assert eps.OVERALL_SCORE_PROFICIENCY_FLOOR[abb] == expected_floor, (
            f"{abb}: floor {eps.OVERALL_SCORE_PROFICIENCY_FLOOR[abb]} "
            f"!= sum(norm_max/2) {expected_floor}"
        )
        # The floor must be reachable and the ceiling must not be undershot.
        assert eps.OVERALL_SCORE_PROFICIENCY_FLOOR[abb] < eps.OVERALL_SCORE_CEILING[abb]
        # The validity limit must sit clear of the reference ceiling, which real
        # attempts can exceed because metric scores are uncapped above cutoff.
        assert eps.OVERALL_SCORE_VALIDITY_LIMIT[abb] > eps.OVERALL_SCORE_CEILING[abb], (
            f"{abb}: the validity limit is not above the reference ceiling, so genuine "
            f"high-scoring attempts will be discarded as bad reads"
        )

    # With mwr at 0..40 a 7-metric exercise keeps its historical 620/1240.
    assert eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"] == 620
    assert eps.OVERALL_SCORE_CEILING["pp1"] == 1240


def test_overall_score_follows_the_simulators_conditional_rule():
    """Overall Score is branch-dependent, not a plain sum.

    Per the simulator's documented behaviour: with nothing below cutoff it is the
    uncapped sum; with anything below cutoff every passing metric is flattened to
    its cutoff and only failing metrics keep their value. A plain sum was wrong for
    every attempt containing a failure.
    """
    _load_app()
    from attempt_csv import compute_200_scores, simulator_scale_overall
    import exercise_proficiency_scores as eps

    def branch(abb, metrics):
        vals, cuts = [], []
        for _rc, _rv, col, s in compute_200_scores(abb, metrics):
            code = col.replace("_score_200", "")
            vals.append(eps.canonical_to_simulator(s, abb, code))
            cuts.append(eps.metric_pass_min_score(abb, code))
        return vals, cuts

    # A strong attempt: nothing below cutoff -> uncapped sum, above the floor.
    good = {"ttc": 20.0, "eom": 100.0, "ico": 0, "iov": 0, "exf": 0, "mwr": 7.0, "drp": 0}
    vals, cuts = branch("pp1", good)
    assert all(v >= c for v, c in zip(vals, cuts)), "fixture is not an all-pass attempt"
    assert abs(simulator_scale_overall("pp1", good) - sum(vals)) < 1e-9, (
        "an all-pass attempt must use the uncapped sum"
    )
    assert simulator_scale_overall("pp1", good) >= eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"]

    # A weak attempt: at least one metric below cutoff -> clamped sum, below floor.
    bad = dict(good)
    bad["ttc"] = 400.0
    vals, cuts = branch("pp1", bad)
    assert any(v < c for v, c in zip(vals, cuts)), "fixture has no failing metric"

    overall = simulator_scale_overall("pp1", bad)
    expected = sum(min(v, c) for v, c in zip(vals, cuts))
    assert abs(overall - expected) < 1e-9, (
        f"an attempt with a failure must clamp passing metrics: {overall} != {expected}"
    )
    assert overall < sum(vals), "the clamp discarded no surplus"
    assert overall < eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"], (
        "a failing attempt must land below the proficiency floor, or the floor stops "
        "being an exact PASS test"
    )


def test_validity_limit_gates_the_margin_not_the_ceiling():
    """The margin must reject gross misreads without rejecting good attempts.

    Six real kr1 attempts score just above their reference ceiling, legitimately,
    because metric scores are uncapped above cutoff. Gating on the ceiling silently
    dropped them from every downstream statistic.
    """
    app = _load_app()
    import exercise_proficiency_scores as eps

    ceiling = eps.OVERALL_SCORE_CEILING["kr1"]

    # Just above the reference ceiling: a real attempt, must still yield a margin.
    rec = {"exerc_abb": "kr1", "overall_score": ceiling * 1.03}
    assert app.compute_attempt_proficiency_margin(rec) is not None, (
        "an attempt slightly above the reference ceiling is being discarded"
    )

    # A lost decimal point is ~100x off and must still be rejected.
    rec_bad = {"exerc_abb": "kr1", "overall_score": ceiling * 100}
    assert app.compute_attempt_proficiency_margin(rec_bad) is None, (
        "a decimal-shift misread is no longer being rejected"
    )

    limit = app.get_overall_score_validity_limit("kr1")
    assert limit is not None and limit > ceiling


def test_overall_norm_is_per_exercise_not_a_flat_1200():
    """overall_score must normalise against its own exercise's scale.

    A flat 1200 divisor made the 0..1 value mean different things on a 6-metric
    exercise than on an 8-metric one, and saturated everything above 1200 on the
    larger ones to exactly 1.0 — so NAED could not tell good from excellent there.
    """
    app = _load_app()
    import exercise_proficiency_scores as eps

    # The divisor must be the exercise's own reference ceiling.
    for abb in ("kr1", "pp1", "rtt"):
        assert app.overall_score_norm_divisor(abb) == eps.OVERALL_SCORE_CEILING[abb], (
            f"{abb} is not normalised against its own ceiling"
        )

    # Exercises with different metric counts must not share a divisor.
    assert app.overall_score_norm_divisor("kr1") != app.overall_score_norm_divisor("rtt"), (
        "a 6-metric and an 8-metric exercise still share one divisor"
    )

    # An unknown exercise must still produce a usable divisor.
    assert app.overall_score_norm_divisor("") == app.OVERALL_SCORE_MAX

    # Equivalent performance must normalise equally across exercises.
    a = app.compute_overall_norm(
        {"exerc_abb": "kr1", "overall_score": eps.OVERALL_SCORE_CEILING["kr1"] * 0.75}
    )
    b = app.compute_overall_norm(
        {"exerc_abb": "rtt", "overall_score": eps.OVERALL_SCORE_CEILING["rtt"] * 0.75}
    )
    assert a is not None and b is not None
    assert abs(a - b) < 1e-9, (
        f"the same relative performance normalises differently per exercise: {a} vs {b}"
    )

    # The old flat divisor saturated rtt; the per-exercise one must not.
    rtt_high = {"exerc_abb": "rtt", "overall_score": 1300.0}
    norm = app.compute_overall_norm(rtt_high)
    assert norm is not None and norm < 1.0, (
        "an rtt attempt above 1200 is still saturating to 1.0"
    )
    assert 1300.0 / app.OVERALL_SCORE_MAX > 1.0, "fixture no longer exercises the old bug"


def test_baselines_source_round_trips():
    """Rendering the proficiency table as source must reproduce it exactly.

    save_baselines() rewrites a file imported at startup. If the renderer loses a
    value or a type, the app boots on wrong PASS thresholds — so the generated
    source is parsed back and compared before anything is written.
    """
    _load_app()
    import exercise_proficiency_scores as eps

    normalized = eps.normalize_baselines(eps.PROFICIENCY_BASELINES)
    source = eps.format_baselines_source(eps.PROFICIENCY_BASELINES)

    # The same check save_baselines runs, on a full synthetic module body.
    eps._verify_baselines_source(source, normalized, "<test>")

    namespace: dict = {}
    body = source.split("\n", 1)[1].rsplit("\n", 1)[0]
    exec(compile(body, "<test>", "exec"), namespace)
    back = namespace["PROFICIENCY_BASELINES"]

    assert back == normalized, "the rendered source does not round-trip"
    assert len(back) == 60, f"expected 60 exercises, rendered {len(back)}"
    assert sum(len(v) for v in back.values()) == 400

    # Types must survive: emet_id and norm_max are ints, not floats.
    entry = back["pp1"]["mwr"]
    assert isinstance(entry["emet_id_RSAC_2026"], int)
    assert isinstance(entry["norm_max"], int)
    assert entry["norm_max"] == 40
    assert isinstance(entry["mean"], float)

    # A refusal must be a refusal: mismatched content cannot be written.
    try:
        eps._verify_baselines_source(source, {"pp1": {}}, "<test>")
    except RuntimeError:
        pass
    else:
        raise AssertionError("verification accepted a table it was not built from")


def test_baselines_defaults_snapshot_exists_and_matches():
    """The rollback snapshot must exist, or 'reset to default' silently does nothing."""
    _load_app()
    import exercise_proficiency_scores as eps

    assert eps.BASELINES_DEFAULTS, (
        f"no baseline snapshot at {eps.defaults_path()} — reverting is unavailable"
    )
    assert len(eps.BASELINES_DEFAULTS) == 60
    assert sum(len(v) for v in eps.BASELINES_DEFAULTS.values()) == 400

    # revert_to_defaults must hand out a copy, never the snapshot itself.
    copy = eps.revert_to_defaults()
    copy["pp1"]["mwr"]["norm_max"] = 999
    assert eps.BASELINES_DEFAULTS["pp1"]["mwr"]["norm_max"] != 999, (
        "revert_to_defaults leaked the snapshot object"
    )

    # write_defaults_file must refuse to overwrite the only copy of the originals.
    try:
        eps.write_defaults_file()
    except FileExistsError:
        pass
    else:
        raise AssertionError("write_defaults_file overwrote the existing snapshot")


def test_baselines_validation_catches_silent_breakage():
    """check_baselines_consistency must reject what fails silently at runtime."""
    _load_app()
    import copy as _copy
    import exercise_proficiency_scores as eps

    assert eps.check_baselines_consistency() == [], (
        "the shipped proficiency table does not pass its own validation"
    )

    def problems_with(mutate):
        data = _copy.deepcopy(eps.normalize_baselines(eps.PROFICIENCY_BASELINES))
        mutate(data)
        return eps.check_baselines_consistency(data)

    def bad_direction(d):
        d["pp1"]["ttc"]["direction"] = "Lower"

    def zero_norm_max(d):
        d["pp1"]["ttc"]["norm_max"] = 0

    def duplicate_emet(d):
        d["pp1"]["ttc"]["emet_id_RSAC_2026"] = d["pp1"]["eom"]["emet_id_RSAC_2026"]

    def unknown_metric(d):
        d["pp1"]["zzz"] = dict(d["pp1"]["ttc"])

    def collapsed_range(d):
        d["pp1"]["ttc"]["worst_multiplier"] = d["pp1"]["ttc"]["best_multiplier"]

    for name, mutate in (
        ("a mis-cased direction", bad_direction),
        ("norm_max of 0", zero_norm_max),
        ("a duplicated emet_id", duplicate_emet),
        ("an unknown metric code", unknown_metric),
        ("best == worst multiplier", collapsed_range),
    ):
        assert problems_with(mutate), f"{name} was not reported"

    # And save must refuse rather than write a broken table.
    broken = _copy.deepcopy(eps.normalize_baselines(eps.PROFICIENCY_BASELINES))
    broken["pp1"]["ttc"]["norm_max"] = 0
    try:
        eps.save_baselines(broken)
    except ValueError:
        pass
    else:
        raise AssertionError("save_baselines wrote a table with norm_max = 0")


def test_derived_tables_refresh_when_baselines_change():
    """Floor/ceiling are snapshots; editing norm_max must rebuild them.

    Without this the app keeps deciding PASS against the values the file had at
    startup, with nothing on screen indicating it.
    """
    app = _load_app()
    import exercise_proficiency_scores as eps

    entry = eps.PROFICIENCY_BASELINES["pp1"]["mwr"]
    before_floor = eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"]
    before_ceiling = eps.OVERALL_SCORE_CEILING["pp1"]
    previous = entry["norm_max"]

    entry["norm_max"] = 200
    try:
        eps.refresh_derived_tables()
        assert eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"] == before_floor + 80, (
            "the PASS floor did not follow the edited norm_max"
        )
        assert eps.OVERALL_SCORE_CEILING["pp1"] == before_ceiling + 160
        assert eps.OVERALL_SCORE_VALIDITY_LIMIT["pp1"] == (before_ceiling + 160) * 2

        # The app caches copies of those tables; they must be droppable.
        app.get_overall_score_proficiency_floor("pp1")
        app.invalidate_normative_caches()
        assert app.get_overall_score_proficiency_floor("pp1") == before_floor + 80, (
            "the app served a stale cached floor after the baselines changed"
        )
    finally:
        entry["norm_max"] = previous
        eps.refresh_derived_tables()
        app.invalidate_normative_caches()

    assert eps.OVERALL_SCORE_PROFICIENCY_FLOOR["pp1"] == before_floor
    assert app.get_overall_score_proficiency_floor("pp1") == before_floor


def test_computed_mwr_score_is_not_round_tripped():
    """The live path must not divide mwr by 5 and multiply it back.

    That round trip rounded to 2 decimals in the middle, so the published value
    could differ from the score actually calculated.
    """
    _load_app()
    from attempt_csv import compute_200_scores, simulator_scale_overall
    from exercise_proficiency_scores import PROFICIENCY_BASELINES, calc_score

    metrics = {"ttc": 74.3, "eom": 152.0, "ico": 0, "iov": 0, "exf": 0, "mwr": 8.9, "drp": 0}
    scored = {c.replace("_score_200", ""): s for _rc, _rv, c, s in compute_200_scores("pp1", metrics)}

    b = PROFICIENCY_BASELINES["pp1"]["mwr"]
    expected = calc_score(
        raw=8.9, mean=float(b["mean"]), sd=float(b["stddev"]),
        proficiency=float(b["prof_raw"]), direction=str(b["direction"]),
        best_multiplier=float(b.get("best_multiplier", -3)),
        worst_multiplier=float(b.get("worst_multiplier", 5)),
        metric_code="mwr",
    )

    assert "mwr" in scored, "mwr is no longer emitted under its own canonical name"
    assert scored["mwr"] == expected, (
        f"mwr score {scored['mwr']} != calc_score {expected} — a lossy rescale remains"
    )

    # The simulator-scale overall must stay below the ceiling, which is on that scale.
    overall = simulator_scale_overall("pp1", metrics)
    assert overall < sum(scored.values()), (
        "simulator-scale overall should be lower than the canonical sum when mwr is 0..40"
    )


def test_attempt_processor_is_producer_agnostic():
    """AttemptProcessor must stay free of Qt and of any data-acquisition concern.

    The public edition has one producer, manual entry. Keeping the pipeline
    neutral is what allows an automated producer to be added at a given site
    without reaching into the decision logic — which is how the two producers
    were kept consistent when this build still had both.
    """
    import inspect

    app = _load_app()
    src = inspect.getsource(app.AttemptProcessor)
    for forbidden in ("Signal", "QObject", "QMessageBox", "extract_from_screenshot",
                      "watch_folder"):
        assert forbidden not in src, (
            f"AttemptProcessor references {forbidden!r} — the shared pipeline is no "
            f"longer neutral with respect to how an attempt was produced"
        )


def test_attempt_serialisation_is_independent_of_its_source():
    """An optional screenshot reference must be a trailing field, nothing more.

    Attempt records written by earlier versions carry a `screenshot_file` pair at
    the end of the line. Serialisation must therefore be identical with and
    without it, apart from that suffix, or those records stop round-tripping and
    the attempts table silently loses columns.
    """
    _load_app()
    from attempt_csv import build_csv_line

    attempt = {
        "exercise_abbreviation": "pp1",
        "exercise_full_name": "Pick & Place",
        "overall_score_raw": 640.0,
        "timestamp": "2026-01-01 00:00:00",
        "metrics_canonical": {"ttc": 74.3, "eom": 152.0, "ico": 0, "iov": 0,
                              "exf": 0, "mwr": 8.9, "drp": 0},
    }
    plain = build_csv_line(attempt, subject="Subject01")
    with_shot = build_csv_line(attempt, subject="Subject01", screenshot_filename="shot.png")
    assert with_shot == plain + ",screenshot_file,shot.png", (
        "the screenshot reference is no longer a pure trailing field, so legacy "
        "attempt records will not round-trip"
    )


def test_entry_dialog_fields_cover_what_scoring_requires():
    """Every metric the dialog offers must be exactly what metrics_complete demands,
    or the tutor cannot ever satisfy it."""
    app = _load_app()
    for abb in ("pp1", "rtt", "tah", "is2"):
        codes = app._metrics_for_exercise(abb)
        assert codes, f"no enterable metrics for {abb}"
        assert app.AttemptProcessor.metrics_complete(abb, {c: 1.0 for c in codes}), (
            f"the dialog's field set for {abb} does not satisfy metrics_complete"
        )
        for code in codes:
            assert app._metric_caption(code) != code or code in ("mwc",), (
                f"metric {code!r} of {abb} has no on-screen caption, so the tutor would "
                f"see a bare code"
            )


def test_skill_ratings_derived_fields_hold():
    """skill_intrinsic and skill_overall must follow from the authored fields.

    The editor shows them read-only and recomputes them, so if the file ever stops
    satisfying the rule the editor would silently overwrite values someone typed
    deliberately. Checks the live catalogue and the baseline.
    """
    import exercise_defs as ed

    problems = ed.check_derived_consistency()
    assert not problems, "exercise_defs.py has inconsistent derived values: " + "; ".join(
        problems
    )

    defaults = ed.load_defaults()
    assert defaults, (
        f"baseline missing or unreadable at {ed.defaults_path()} — 'revert to default' "
        f"would be impossible"
    )
    assert set(defaults) == set(ed.EXERCISE_DEFS), (
        "the baseline and the live catalogue describe different exercise sets"
    )


def test_catalogue_source_round_trips():
    """Rewriting the catalogue must reproduce it exactly, and verify before writing.

    Saving edits `exercise_defs.py` itself, so a formatting bug here would corrupt a
    file that is imported at startup. Runs entirely on strings — nothing is written.
    """
    import exercise_defs as ed

    entries = {abb: dict(entry) for abb, entry in ed.EXERCISE_DEFS.items()}

    block = ed.format_catalogue_source(entries)
    namespace: dict = {}
    exec(compile(block, "<generated>", "exec"), namespace)
    assert namespace["EXERCISE_DEFS"] == entries, (
        "the generated catalogue block does not round-trip the current values"
    )

    # The pre-write verification must actually reject a mismatch.
    bad = {abb: dict(e) for abb, e in entries.items()}
    bad.pop(next(iter(bad)))
    try:
        ed._verify_catalogue_source(block, bad, "<generated>")
    except RuntimeError:
        pass
    else:
        raise AssertionError("_verify_catalogue_source accepted the wrong exercise set")

    # A name with quotes and a non-ASCII character must survive the round trip.
    tricky = {abb: dict(e) for abb, e in entries.items()}
    first = next(iter(tricky))
    tricky[first]["exerc_full"] = 'A "quoted" — nâme'
    ns2: dict = {}
    exec(compile(ed.format_catalogue_source(tricky), "<generated>", "exec"), ns2)
    assert ns2["EXERCISE_DEFS"][first]["exerc_full"] == 'A "quoted" — nâme', (
        "quoting or encoding is lost when the catalogue is written"
    )


def test_exercise_defs_is_shared_for_writes():
    """Saving must mutate the shared EXERCISE_DEFS, not rebind it.

    Both the app and the scoring modules hold this object by reference; rebinding
    it would leave one of them on a stale catalogue.
    """
    import exercise_defs as ed

    app = _load_app()
    from exercise_proficiency_scores import EXERCISE_DEFS as ocr_defs

    assert app.EXERCISE_DEFS is ed.EXERCISE_DEFS is ocr_defs, (
        "EXERCISE_DEFS is no longer a single shared object"
    )

    # revert_to_defaults must hand back a copy, never touch the live catalogue.
    before = {abb: dict(e) for abb, e in ed.EXERCISE_DEFS.items()}
    reverted = ed.revert_to_defaults()
    reverted[next(iter(reverted))]["bimd"] = 999
    assert {abb: dict(e) for abb, e in ed.EXERCISE_DEFS.items()} == before, (
        "revert_to_defaults leaked into the live catalogue"
    )


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
