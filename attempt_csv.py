"""Score one attempt and serialise it as a Clean CSV line.

Usage:
    from attempt_csv import build_csv_line, append_to_csv

    line = build_csv_line(attempt, subject="Subject01")
    append_to_csv(line, subject="Subject01")

`attempt` is the five-key dict produced by the manual-entry dialog. The
`screenshot_filename` argument of build_csv_line() is retained so that attempt
records written by earlier versions, which carried a screenshot reference,
still round-trip identically.

This module was previously `screenshot_ocr/csv_builder.py`. It never had
anything to do with OCR — it computes the _200 scores and formats the CSV line —
and the package it lived in has been removed along with the screen-capture
layer, so it now sits beside the scoring tables it depends on.
"""

from __future__ import annotations

import os
from typing import Any

from exercise_proficiency_scores import (
    PROFICIENCY_BASELINES,
    calc_score,
    canonical_to_simulator,
    metric_pass_min_score,
)

# Metrics that appear on screen but are NOT scored (no _200 calculation)
_UNSCORED_METRICS = {"mwc"}


def compute_200_scores(
    exercise_abb: str,
    metrics_canonical: dict[str, Any],
) -> list[tuple[str, float | int, str, float]]:
    """Compute _score_200 for each metric using proficiency baselines.

    Returns list of (raw_col_name, raw_value, score_200_col_name, score_200_value).
    Metrics not in PROFICIENCY_BASELINES are skipped.
    Unscored metrics (e.g., mwc) are skipped.

    Scores are CANONICAL (0..200, PASS at 100) for every metric. This function
    used to divide mwr by 5 and emit it as mwrp_score_pre_200, purely to imitate
    the simulator's 0..40 range - which the reader then multiplied by 5 again. The
    round trip lost precision to rounding and gained nothing, so mwr is now
    written under its own name on the same scale as everything else.
    """
    baselines = PROFICIENCY_BASELINES.get(exercise_abb, {})
    if not baselines:
        return []

    result: list[tuple[str, float | int, str, float]] = []

    for metric_code, raw_value in metrics_canonical.items():
        # Skip unscored metrics
        if metric_code in _UNSCORED_METRICS:
            continue

        # Skip if no baseline defined for this metric/exercise
        baseline = baselines.get(metric_code)
        if baseline is None:
            continue

        # Ensure raw_value is numeric
        try:
            raw_val = float(raw_value)
        except (TypeError, ValueError):
            continue

        # Calculate 200-score
        score_200 = calc_score(
            raw=raw_val,
            mean=float(baseline["mean"]),
            sd=float(baseline["stddev"]),
            proficiency=float(baseline["prof_raw"]),
            direction=str(baseline["direction"]),
            best_multiplier=float(baseline.get("best_multiplier", -3)),
            worst_multiplier=float(baseline.get("worst_multiplier", 5)),
            metric_code=metric_code,
        )

        raw_col = f"{metric_code}_score_raw"
        col_200 = f"{metric_code}_score_200"

        result.append((raw_col, raw_val, col_200, score_200))

    return result


def simulator_scale_overall(
    exercise_abb: str,
    metrics_canonical: dict[str, Any],
) -> float:
    """Reproduce the Overall Score the simulator reports for an attempt.

    The simulator applies one of two rules, depending on the whole attempt:

      - nothing below cutoff : the UNCAPPED sum, so performance better than the
                               reference keeps accruing credit above the cutoff
      - anything below cutoff: sum of min(score, cutoff) - every passing metric is
                               flattened to exactly its cutoff and only the failing
                               ones keep their real value, so all surplus is lost

    Scores are summed on the SIMULATOR's scale, where a metric normalised to 0..40
    has a cutoff of 20 rather than 100.

    Verified against 2596 exported attempts: median residual 0.00 on both branches.
    A plain sum was wrong for every attempt containing a failure.
    """
    scored = compute_200_scores(exercise_abb, metrics_canonical)

    values: list[float] = []
    cutoffs: list[float] = []
    for _raw_col, _raw_val, col_200, score_200 in scored:
        code = col_200.replace("_score_200", "")
        values.append(canonical_to_simulator(score_200, exercise_abb, code))
        cutoffs.append(metric_pass_min_score(exercise_abb, code))

    if all(v >= c for v, c in zip(values, cutoffs)):
        return sum(values)
    return sum(min(v, c) for v, c in zip(values, cutoffs))


def build_csv_line(
    attempt: dict[str, Any],
    subject: str,
    screenshot_filename: str = "",
) -> str:
    """Build a complete CSV line for one attempt.

    Format: subject,timestamp,exercise_full_name,overall_score,metric1_raw_col,val,metric1_200_col,val,...[,screenshot_file,<name>]

    Args:
        attempt: The attempt dict, as produced by the manual-entry dialog:
            exercise_abbreviation, exercise_full_name, overall_score_raw,
            timestamp, metrics_canonical.
        subject: Subject name (e.g., "Subject01")
        screenshot_filename: Optional image reference appended as a trailing
            label-value pair. Retained for records written by earlier versions.

    Returns:
        CSV line string (no trailing newline)
    """
    exercise_name = attempt["exercise_full_name"]
    exercise_abb = attempt["exercise_abbreviation"]
    overall_score = attempt.get("overall_score_raw", "")
    timestamp = attempt.get("timestamp", "")
    metrics_canonical = attempt.get("metrics_canonical", {})

    # Compute 200-scores
    scored_metrics = compute_200_scores(exercise_abb, metrics_canonical)

    # Build the line parts
    parts: list[str] = [
        subject,
        timestamp,
        exercise_name,
        _fmt(overall_score),
    ]

    # Append each metric: raw_col, raw_val, 200_col, 200_val
    for raw_col, raw_val, col_200, score_200 in scored_metrics:
        parts.append(raw_col)
        parts.append(_fmt(raw_val))
        parts.append(col_200)
        parts.append(_fmt(score_200))

    # Append screenshot filename as the last label-value pair
    if screenshot_filename:
        parts.append("screenshot_file")
        parts.append(screenshot_filename)

    return ",".join(parts)


def append_to_csv(
    csv_line: str,
    subject: str,
    output_dir: str | None = None,
    target_path: str | None = None,
) -> str:
    """Append a CSV line to the subject's CSV file.

    If the file doesn't exist, it is created (no header row — matches RSAC format).
    Returns the full path to the CSV file.

    The application always passes `target_path`. The `output_dir` fallback is for
    direct calls; it resolves to the app's own csv_clean folder, which used to be
    a `csv_output` folder beside this module when it lived in its own package.
    """
    if target_path:
        csv_path = target_path
        out_dir = os.path.dirname(os.path.abspath(csv_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
    else:
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "csv_clean")
        os.makedirs(output_dir, exist_ok=True)

        # Find existing CSV for this subject, or create new one
        csv_path = _find_or_create_csv(subject, output_dir)

    # Duplicate check: compare 4th and 6th fields against the last line
    if os.path.isfile(csv_path):
        try:
            with open(csv_path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
            if lines:
                last_fields = lines[-1].split(",")
                new_fields = csv_line.split(",")
                if (len(last_fields) > 5 and len(new_fields) > 5
                        and last_fields[3] == new_fields[3]
                        and last_fields[5] == new_fields[5]):
                    return csv_path  # Skip duplicate
        except Exception:
            pass

    with open(csv_path, "a", encoding="utf-8-sig") as f:
        f.write(csv_line + "\n")

    return csv_path


def _find_or_create_csv(subject: str, output_dir: str) -> str:
    """Find an existing CSV for this subject, or return a path for a new one."""
    # Look for existing files matching the subject name
    for fname in os.listdir(output_dir):
        if fname.lower().endswith(".csv") and subject.lower() in fname.lower():
            return os.path.join(output_dir, fname)

    # Create new file with timestamp-based name
    from datetime import datetime
    now = datetime.now().strftime("%d_%m_%Y-%H_%M_%S")
    fname = f"MimicClean_{subject}_{now}.csv"
    return os.path.join(output_dir, fname)


def _fmt(value: Any) -> str:
    """Format a value for CSV output — integers stay as ints, floats get reasonable precision."""
    if value is None or value == "":
        return ""
    if isinstance(value, float):
        if value == int(value):
            return str(int(value))
        return f"{value:.2f}"
    return str(value)
