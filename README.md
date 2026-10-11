# RSAC — Robotic Surgery Adaptive Curricula

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23299532.svg)](https://doi.org/10.5281/zenodo.23299532)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Desktop application for running an **adaptive curriculum** on a robotic surgery
simulator. After each attempt, RSAC scores the trainee's metrics against
exercise-specific proficiency baselines and recommends what they should attempt
next — progress, repeat, move sideways, or step back — together with the
reasoning behind the recommendation.

The recommendation engine is **NAED** (Next Attempt Exercise Decision), a
three-layer pipeline:

| Layer | Question it answers |
| --- | --- |
| **NAED-1** | Is there enough evidence to decide at all? Computes data sufficiency, stability, signal-to-noise and maturity, and gates the decision behind a confidence threshold. |
| **NAED-2** | In which direction should the trainee move? Classifies the recency-weighted multi-metric mastery trajectory into keep / upgrade / lateral / downgrade, and detects isolated per-metric bottlenecks. |
| **NAED-3** | Which exercise specifically? Navigates the curriculum graph, applying fallback chains when the preferred edge does not exist. |

Performance metrics are entered manually, or imported in bulk from the
simulator's own session-export CSV files.

> **Scope.** This is the portable edition described in the accompanying
> publication. It preserves the adaptive decision algorithm in full, but omits
> the site-specific data-acquisition layer used in the originating laboratory,
> where metrics were captured from the simulator screen automatically. That
> layer depended on the local network architecture, folder configuration and
> screen-capture setup of a single centre and could not be expected to work
> unchanged elsewhere.

---

## Requirements

**Python 3.10 or newer.** All remaining dependencies are Python packages listed
in `requirements.txt`; no system-level binaries are required.

## Installation

```bash
git clone <repository-url>
cd RSAC_Freeware
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate
pip install -r requirements.txt
```

Then copy the example configuration:

```bash
cp rsac_config.example.json rsac_config.json
```

## Starting RSAC

On Windows, **double-click `Start RSAC.bat`**. That is the only file you need;
everything else is the application itself.

From a terminal, on any platform:

```bash
python RSAC_Freeware_1_00.py
```

All three configuration fields may be left empty — the application will prompt
for folders as needed and remember the choices.

## Data

**No participant data is included in this repository.** The application reads
and writes only inside its own folder, creating these directories on first use:

| Folder | Contents |
| --- | --- |
| `csv_clean/` | Cleaned attempt records, one file per subject |
| `csv_simulator/` | Raw exports from the simulator |
| `analysis_history/` | Saved analysis output |

Subject records live in `subjects.json`, also created on first use. All of the
above are excluded from version control by `.gitignore`; keep them that way.

## Configuration

Three data tables are editable from the GUI under **Settings > Exercises**, and
each can be reverted to a pristine baseline:

| Table | File | Baseline |
| --- | --- | --- |
| Exercise catalogue and metrics | `exercise_defs.py` | `exercise_defs_default.json` |
| Curriculum graph (NAED-3) | `exercise_progression_defs.py` | `exercise_progression_defs_default.json` |
| Proficiency baselines | `exercise_proficiency_scores.py` | `exercise_proficiency_scores_default.json` |

The editors rewrite the live Python source in place between `BEGIN`/`END`
markers, so the file you read is always the configuration in force.

> **Important:** proficiency baselines must mirror the values configured in the
> simulator itself. If they diverge, RSAC will score attempts against a standard
> the simulator never applied. The application warns about this before opening
> the editor.

## Tests

```bash
python test_imports.py
```

No test framework required; `pytest` will also collect them if present. The
suite covers the cross-module import chain, the normative scoring tables, the
curriculum graph's integrity, NAED-3 resolution for every exercise/decision
pair, and round-tripping of all three configuration editors.

## Project layout

```
RSAC_Freeware_1_00.py           Main application (GUI, NAED pipeline, analysis)
exercise_defs.py                Exercise catalogue and per-exercise metrics
exercise_progression_defs.py    Curriculum graph consumed by NAED-3
exercise_proficiency_scores.py  Proficiency baselines and score normalisation
attempt_csv.py                  Attempt scoring and Clean CSV serialisation
app_paths.py                    Resolves where data and assets are read/written
curriculum_svg.py               Curriculum diagram rendering
test_imports.py                 Test suite
```

## Documentation

The algorithm is documented in full in the supplementary material accompanying
the publication:

- **Online Resource 1** — proficiency-referenced scoring, and the development of
  the adaptive decision framework.
- **Online Resource 2** — the 60 curriculum exercises, with motor-skill domain
  ratings, proficiency-score parameters and per-exercise metrics.
- **Online Resource 3** — the architecture, operators and decision rules of the
  NAED algorithm, including every threshold and formula implemented here.

Within the code, the pipeline is laid out in labelled sections that can be
searched for directly: `[SEC-06]` for NAED-1 data sufficiency, `[SEC-08]` for
NAED-2 mastery and decision logic, and `[SEC-11]` for NAED-3 exercise mapping.
A full section index sits at the top of `RSAC_Freeware_1_00.py`.

## License

See [LICENSE](LICENSE).

## Citation

If you use RSAC, please cite the archived release:

> Sarmento Junior, K. (2026). *RSAC: Robotic Surgery Adaptive Curricula* (Version 1.0.0) [Computer software]. Zenodo. https://doi.org/10.5281/zenodo.23299532

GitHub's **Cite this repository** button generates this in APA or BibTeX from
`CITATION.cff`.

<!-- TODO: add the manuscript reference once the article is published. -->
