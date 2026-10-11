import sys
import os
import re
import csv
import json
import math
import shutil

from datetime import datetime
from typing import Optional, Any

# Must run before the three configuration modules are imported: in a frozen
# build it seeds a writable folder with them and puts that folder first on
# sys.path, so the Settings > Exercises editors still have real source to
# rewrite. No-op in a source install. See app_paths for why this is necessary.
import app_paths

app_paths.bootstrap()

import exercise_defs  # noqa: E402
from exercise_defs import EXERCISE_DEFS  # noqa: E402
import exercise_progression_defs
from exercise_progression_defs import (
    CURRICULA,
    CONNECTION_TYPES,
    CONNECTION_TYPE_COLORS,
    CONNECTION_TYPE_LABELS,
    DEFAULT_CURRICULUM,
)

all_attempt_rows: list[dict[str, Any]] = []

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QDialog,
    QDialogButtonBox,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QLabel,
    QComboBox,
    QFileDialog,
    QLineEdit,
    QHeaderView,
    QCheckBox,
    QSplashScreen,
    QMenu,
    QScrollArea,
    QSizePolicy,
    QRadioButton,
    QButtonGroup,
    QFrame,
    QInputDialog,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QSplitter,
    QToolButton,
    QGraphicsDropShadowEffect,
    QStyledItemDelegate,
    QCompleter,
)
from PySide6.QtCore import (
    Qt, QTimer, QCoreApplication, QObject, Signal,
    QSize, QPropertyAnimation, QEasingCurve,
)
from PySide6.QtGui import QColor, QBrush, QFont, QPixmap

try:
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
except Exception:
    Figure = None
    FigureCanvas = None
    np = None

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import qtawesome as qta
    _HAS_QTA = True
except Exception:
    qta = None
    _HAS_QTA = False

try:
    from PySide6.QtSvgWidgets import QSvgWidget
    _HAS_QTSVG = True
except Exception:
    QSvgWidget = None
    _HAS_QTSVG = False

try:
    from scipy import stats as _scipy_stats
except Exception:
    _scipy_stats = None

try:
    import statsmodels.api as _sm
except Exception:
    _sm = None

try:
    from curriculum_svg import CurriculumDiagram
except Exception:
    CurriculumDiagram = None


# =============================================================================
#  FILE STRUCTURE -- TABLE OF CONTENTS
# =============================================================================
#
#  Search for a section tag (e.g. "[SEC-05]") to jump to that section.
#
#  [SEC-CFG]  Site Configuration (rsac_config.json)
#  [SEC-01]  Splash Screen
#  [SEC-SUBJ]  Subject Register & Welcome Dialog
#  [SEC-02]  Curriculum Definitions (EXERCISE_DEFS, CURRICULA)
#  [SEC-03]  CSV File Cleaning & I/O
#  [SEC-04]  Main Window (File Manager)
#  [SEC-MENU] Session Menu Window (sidebar)
#  [SEC-05]  Mathematical Utilities
#  [SEC-06]  NAED-1: Data Sufficiency Assessment
#  [SEC-07]  NAED-1 Details Window
#  [SEC-08]  NAED-2: Mastery & Decision Logic
#  [SEC-09]  NAED-2 Details Window
#  [SEC-10]  CSV Data Parsing
#  [SEC-11]  NAED-3: Exercise Mapping
#  [SEC-12]  NAED-3 Details Window
#  [SEC-13]  Recommendations Window
#  [SEC-LIVE-JSON]  Live Decision JSON Writer
#  [SEC-OM]  Outcome Measures
#  [SEC-PEER]  Peer Comparison
#  [SEC-14]  Data Show Window
#  [SEC-15]  Auxiliary Windows (Decision Details, Time Analysis, Progress Graph)
#  [SEC-16]  Graph Window
#  [SEC-17]  Override Decision Dialog (JSON-based)
#  [SEC-18]  NO-Override Handler (JSON-based)
#  [SEC-19]  Recommendations Patch (bind NO handler)
#  [SEC-20]  Entry Point
#


# =============================================================================
#  [SEC-CFG] SITE CONFIGURATION
# =============================================================================
#
# Everything that depends on how a particular lab is wired up lives in
# rsac_config.json beside this script, so the tool can be distributed without
# one site's machine names and share paths baked into the source. Any key the
# file omits falls back to CONFIG_DEFAULTS below.
#
#   simulator_user_exports_dir
#       Folder the simulator reads curriculum XML from, e.g. a UNC share such
#       as \\SIMULATOR-PC\Users\...\exports\User Exports. Leave empty to write
#       the proficiency XML only to the local Flex_VR_XML folder.
#   template_xml
#       Curriculum XML the proficiency export is derived from. Relative names
#       resolve inside Flex_VR_XML; absolute paths are used as given.

CONFIG_DEFAULTS: dict[str, Any] = {
    "simulator_user_exports_dir": "",
    "template_xml": "RSAC_2026_Aug_08_a.xml",
}


def _script_dir() -> str:
    """Folder RSAC reads and writes its own files in.

    In a source install this is the application folder, unchanged. In a frozen
    build it is a writable per-user folder, because the bundle itself is either
    temporary or not writable. See app_paths.
    """
    return app_paths.user_data_dir()


def _config_path() -> str:
    return os.path.join(_script_dir(), "rsac_config.json")


def load_config() -> dict[str, Any]:
    """Return the site config, falling back to CONFIG_DEFAULTS for missing keys."""
    cfg = dict(CONFIG_DEFAULTS)
    path = _config_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                stored = json.load(f)
            if isinstance(stored, dict):
                cfg.update({k: v for k, v in stored.items() if k in CONFIG_DEFAULTS})
        except Exception:
            pass
    return cfg


def ensure_config_file() -> str:
    """Write rsac_config.json with the defaults if it does not exist yet.

    Called when a window that needs these paths is opened rather than at import
    time, so simply running the app never creates files. Returns the config path.
    """
    path = _config_path()
    if not os.path.isfile(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(CONFIG_DEFAULTS, f, indent=2)
        except Exception:
            pass
    return path


def _config_str(key: str) -> str:
    """Read a string setting, falling back to its default if blank or missing."""
    value = str(load_config().get(key) or "").strip()
    if not value:
        value = str(CONFIG_DEFAULTS.get(key) or "").strip()
    return value


def save_config_value(key: str, value: Any) -> None:
    """Persist a single setting, leaving the rest of the file as it is.

    Silently does nothing if the key is unknown or the file cannot be written —
    remembering a path is a convenience and must never break the caller.
    """
    if key not in CONFIG_DEFAULTS:
        return
    cfg = load_config()
    cfg[key] = value
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


# =============================================================================
#  [SEC-01] SPLASH SCREEN
# =============================================================================

def show_splash_and_start_main(app):
    logo_path = app_paths.asset_path("img", "RASC_logo.jpg")

    win_holder = {}

    if os.path.exists(logo_path):
        pixmap = QPixmap(logo_path)

        try:
            screen = app.primaryScreen()
            geom = screen.availableGeometry() if screen else None
            if geom is not None and not pixmap.isNull():
                target_w = max(560, int(geom.width() * 0.60))
                target_h = max(360, int(geom.height() * 0.40))
                pixmap = pixmap.scaled(
                    target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
        except Exception:
            pass

        splash = QSplashScreen(pixmap)
        splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        splash.showMessage("Loading RSAC...", Qt.AlignBottom | Qt.AlignHCenter, QColor("#1b3664"))
        splash.show()
        app.processEvents()

        def _start_main():
            try:
                splash.close()
            except Exception:
                pass
            dlg = WelcomeDialog()
            main_win = MainWindow()
            menu_win = None
            if dlg.exec() == QDialog.Accepted:
                if dlg.selected_subject:
                    win_holder["selected_subject"] = dlg.selected_subject
                    main_win.apply_subject_session(dlg)
                    menu_win = SessionMenuWindow(dlg.selected_subject, main_win)
                    win_holder["menu_win"] = menu_win
                    menu_win.show()
                else:
                    main_win.show()
                win_holder["win"] = main_win

        QTimer.singleShot(5000, _start_main)

    else:
        dlg = WelcomeDialog()
        main_win = MainWindow()
        menu_win = None
        if dlg.exec() == QDialog.Accepted:
            if dlg.selected_subject:
                win_holder["selected_subject"] = dlg.selected_subject
                main_win.apply_subject_session(dlg)
                menu_win = SessionMenuWindow(dlg.selected_subject, main_win)
                win_holder["menu_win"] = menu_win
                menu_win.show()
            else:
                main_win.show()
            win_holder["win"] = main_win

    return win_holder


# =============================================================================
#  [SEC-SUBJ] SUBJECT REGISTER & WELCOME DIALOG
# =============================================================================

# Subjects are created by the tutor and persisted in subjects.json next to the
# script. Every subject is assigned ONE curriculum (see CURRICULA), which
# selects the pathway NAED-3 uses to make its recommendations.


def get_curriculum_for_subject(subject: str) -> str:
    """Return the curriculum key assigned to a subject (fallback: DEFAULT_CURRICULUM)."""
    try:
        rec = find_subject(subject)
    except Exception:
        rec = None
    if rec:
        cur = rec.get("curriculum")
        if cur in CURRICULA:
            return cur
    return DEFAULT_CURRICULUM


# Knowledge-graph SVG files, one per adaptive curriculum.
_CURRICULUM_SVG_FILENAMES = {
    "grad": "2026_Aug_a - KG - Adaptive Curricula - Grad Students - 28 exercises_b.svg",
    "resident_ext": "2026_Aug_a - KG - Adaptive Curricula - Extended - 60 exercises.svg",
}


def _curriculum_svg_path(curriculum: str) -> str | None:
    """Return the absolute path to the knowledge-graph SVG for `curriculum`,
    or None if no SVG exists yet for that curriculum."""
    filename = _CURRICULUM_SVG_FILENAMES.get(curriculum)
    if not filename:
        return None
    path = app_paths.asset_path("img", filename)
    return path if os.path.isfile(path) else None


# ---------------------------------------------------------------------------
#  Subject register (subjects.json)
# ---------------------------------------------------------------------------

# Options for the "Curriculum" prompt shown when creating a new subject:
# (display label, curriculum key). The curriculum choice selects which
# CURRICULA pathway (grad / resident_ext) NAED-3 uses to make decisions.
# The first entry is pre-selected, so it is kept in step with
# DEFAULT_CURRICULUM.
CURRICULUM_OPTIONS: list[tuple[str, str]] = [
    ("Grad Student", "grad"),
    ("Resident / Extended", "resident_ext"),
]


def _subjects_json_path() -> str:
    return os.path.join(_script_dir(), "subjects.json")


def load_subjects() -> list[dict[str, Any]]:
    """Load the subject register, or an empty list if it does not exist yet."""
    path = _subjects_json_path()
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except Exception:
            return []
        return records if isinstance(records, list) else []
    return []


def save_subjects(records: list[dict[str, Any]]) -> None:
    path = _subjects_json_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def find_subject(subject: str) -> dict[str, Any] | None:
    subject = (subject or "").strip()
    if not subject:
        return None
    for rec in load_subjects():
        if rec.get("subject") == subject:
            return rec
    return None


# ---------------------------------------------------------------------------
#  Welcome Dialog  (modal, shown after splash)
# ---------------------------------------------------------------------------

class WelcomeDialog(QDialog):
    """'Welcome to RSAC.' — pick an existing subject or create a new one.

    A new subject is given a name and a curriculum (see CURRICULUM_OPTIONS);
    both are persisted in subjects.json so the same pathway is used on every
    subsequent session.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to RSAC")
        self.setMinimumWidth(420)

        self.selected_subject: str | None = None
        self.is_new_subject: bool = False

        self._subjects: list[dict[str, Any]] = []

        outer = QVBoxLayout(self)
        self._build_subject_page(outer)
        self._refresh_subject_combo()

    def _build_subject_page(self, layout: QVBoxLayout):
        lbl = QLabel("Welcome to RSAC.\nPlease select subject:")
        lbl.setStyleSheet("font-size: 15px; font-weight: bold;")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self.subject_combo = QComboBox()
        layout.addWidget(self.subject_combo)

        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("OK")
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._on_ok)
        btn_row.addWidget(btn_cancel)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

    def _refresh_subject_combo(self):
        self._subjects = load_subjects()
        self.subject_combo.clear()
        self.subject_combo.addItem("-- New subject --")
        for r in self._subjects:
            initials = r.get("initials", "")
            label = f"{r['subject']} ({initials})" if initials else r["subject"]
            self.subject_combo.addItem(label)

    def _on_ok(self):
        choice = self.subject_combo.currentText()
        if choice == "-- New subject --":
            self._create_new_subject()
        else:
            # Extract subject name from "Name (Initials)" format
            subj_name = choice.rsplit("(", 1)[0].strip()
            rec = next((r for r in self._subjects if r.get("subject") == subj_name), None)
            if rec is None:
                QMessageBox.warning(self, "Not Found", "Could not find that subject's record.")
                return
            self.selected_subject = subj_name
            self.is_new_subject = False

            # Show curriculum & current exercise summary for returning subject
            self._show_returning_subject_info(subj_name, rec)

            self.accept()

    def _show_returning_subject_info(self, subject: str, rec: dict) -> None:
        """Show a message box summarising curriculum and current exercise for a
        returning subject."""
        import json as _json

        # --- Curriculum label ---
        cur_key = rec.get("curriculum")
        if cur_key and cur_key in CURRICULA:
            cur_label = CURRICULA[cur_key].get("label", cur_key)
        else:
            cur_label = CURRICULA.get(DEFAULT_CURRICULUM, {}).get("label", DEFAULT_CURRICULUM)

        # --- Current exercise from history JSON ---
        current_exercise = "(no history yet)"
        script_dir = _script_dir()
        hist_dir = os.path.join(script_dir, "analysis_history")
        if os.path.isdir(hist_dir):
            _pat = re.compile(
                r"^History_" + re.escape(subject) + r"_(\d+)-att\.json$", re.IGNORECASE
            )
            hist_path = None
            for fname in os.listdir(hist_dir):
                if _pat.match(fname):
                    hist_path = os.path.join(hist_dir, fname)
                    break
            if hist_path and os.path.isfile(hist_path):
                try:
                    with open(hist_path, "r", encoding="utf-8-sig") as f:
                        data = _json.load(f)
                    if data:
                        last = data[-1]
                        # The Reality Check reflects what actually happened next and
                        # takes priority over the NAED pipeline's recommendation —
                        # e.g. training may have ended in reality even if NAED-3
                        # suggested another exercise (static curricula, early exit, etc.).
                        # If the tutor overrode a multi-candidate NAED-3 recommendation,
                        # Reality_Check records the chosen exercise.
                        reality = last.get("Reality_Check") or {}
                        reality_next = (reality.get("next_exercise_abbreviation") or "").strip()
                        naed3 = last.get("NAED-3") or {}

                        def _abb_to_full(abb: str) -> str:
                            return EXERCISE_DEFS.get(abb, {}).get("exerc_full", abb) or abb

                        if reality_next.upper() == "END" or naed3.get("training_complete"):
                            current_exercise = "Training Complete"
                        elif reality_next and reality_next.upper() != "END":
                            current_exercise = _abb_to_full(reality_next)
                        else:
                            # Fall back to NAED-3 override or recommendation
                            chosen = (naed3.get("chosen_next_abb") or "").strip()
                            naed_next_full = naed3.get("next_exercise_full")
                            if chosen:
                                current_exercise = _abb_to_full(chosen)
                            elif naed_next_full:
                                current_exercise = naed_next_full
                            else:
                                # Fall back to the last exercise analysed
                                current_exercise = last.get("exercise_fullname", "(unknown)")
                except Exception:
                    current_exercise = "(could not read history)"

        QMessageBox.information(
            self,
            "Returning Subject",
            f"<b>{subject}</b><br><br>"
            f"Curriculum: <b>{cur_label}</b><br>"
            f"Current exercise: <b>{current_exercise}</b>",
        )

    def _create_new_subject(self):
        # Custom dialog: collect name + initials
        dlg = QDialog(self)
        dlg.setWindowTitle("New Subject")
        dlg.setMinimumWidth(380)
        dlg_layout = QVBoxLayout(dlg)
        dlg_layout.addWidget(QLabel("Subject Name:"))
        txt_name = QLineEdit()
        txt_name.setPlaceholderText("e.g., John Smith")
        dlg_layout.addWidget(txt_name)
        dlg_layout.addWidget(QLabel("Initials (optional):"))
        txt_initials = QLineEdit()
        txt_initials.setPlaceholderText("e.g., JMS")
        txt_initials.setMaxLength(10)
        dlg_layout.addWidget(txt_initials)
        dlg_btn_row = QHBoxLayout()
        dlg_btn_row.addStretch(1)
        dlg_btn_ok = QPushButton("OK")
        dlg_btn_cancel = QPushButton("Cancel")
        dlg_btn_ok.clicked.connect(dlg.accept)
        dlg_btn_cancel.clicked.connect(dlg.reject)
        dlg_btn_row.addWidget(dlg_btn_ok)
        dlg_btn_row.addWidget(dlg_btn_cancel)
        dlg_layout.addLayout(dlg_btn_row)

        if dlg.exec() != QDialog.Accepted:
            return

        name = txt_name.text().strip()
        initials = txt_initials.text().strip().upper()

        if not name:
            QMessageBox.warning(self, "Missing Name",
                                "Subject name cannot be empty. Please try again.")
            return
        if any(r.get("subject") == name for r in self._subjects):
            QMessageBox.warning(self, "Duplicate Name", f"A subject named '{name}' already exists.")
            return

        # Curriculum — VITAL: determines the adaptive decision-making pathway
        # (CURRICULA["grad"] / CURRICULA["resident_ext"]) NAED-3 follows.
        cur_dlg = QDialog(self)
        cur_dlg.setWindowTitle("Curriculum")
        cur_dlg.setMinimumWidth(380)
        cur_layout = QVBoxLayout(cur_dlg)
        cur_layout.addWidget(QLabel(f"Select the curriculum for <b>{name}</b>:"))
        cur_combo = QComboBox()
        for label, _cur in CURRICULUM_OPTIONS:
            cur_combo.addItem(label)
        cur_layout.addWidget(cur_combo)
        cur_btn_row = QHBoxLayout()
        cur_btn_row.addStretch(1)
        cur_btn_ok = QPushButton("OK")
        cur_btn_ok.clicked.connect(cur_dlg.accept)
        cur_btn_row.addWidget(cur_btn_ok)
        cur_layout.addLayout(cur_btn_row)

        if cur_dlg.exec() != QDialog.Accepted:
            return

        _, curriculum = CURRICULUM_OPTIONS[cur_combo.currentIndex()]

        rec = {
            "subject": name,
            "initials": initials,
            "date_created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "curriculum": curriculum,
        }
        self._subjects.append(rec)
        save_subjects(self._subjects)

        self.selected_subject = name
        self.is_new_subject = True
        self.accept()


# =============================================================================
#  [SEC-02] EXERCISE & METRIC DEFINITIONS
# =============================================================================

# Exercises

# EXERCISE_DEFS now lives in exercise_defs.py and is imported at the top of this file.
# It was moved out so that the scoring modules can share it without importing this
# module back (that cycle broke silently on the RSAC_7_00 -> RSAC_Freeware_1_00 rename).

# The progression graph (CURRICULA and the CONNECTION_TYPE_* tables) now lives in
# exercise_progression_defs.py and is imported at the top of this file. Same reason:
# it is site-specific configuration that a new centre must replace, and it was hard to
# find in here. Run exercise_progression_defs.check_progression_consistency() after
# editing it — a typo'd destination is otherwise silent.

# Progress Graph — exercise category background colors (v7.0 exerc_cat)
EXERCISE_CAT_COLORS = {
    "inm": "#ffffb0",   # Instrument Manipulation — light yellow
    "3au": "#d9f2b0",   # 3rd Arm Use — light green
    "cat": "#ffd699",   # Cautery / Energy — light orange
    "ned": "#b0ffff",   # Needle Driving — light cyan
    "sut": "#c8c8ff",   # Suturing — lavender
    "not": "#ffb0c0",   # Knot Tying — light pink
}

EXERCISE_CAT_LABELS = {
    "inm": "Instrument Manipulation",
    "3au": "3rd Arm Use",
    "cat": "Cautery / Energy",
    "ned": "Needle Driving",
    "sut": "Suturing",
    "not": "Knot Tying",
}

# Metrics

METRIC_LABEL_MAP = {
    "Time to Complete Exercise": "ttc",
    "Economy of Motion": "eom",
    "Instrument Collisions": "ico",
    "Instruments Out Of View": "iov",
    "Excessive Instrument Force": "exf",
    "Drops": "drp",
    "Wire Collisions": "wrc",
    "Wire Contact Duration": "wcd",
    "Tower Knockoffs": "tko",
    "Misapplied Energy Time": "met",
    "Blood Loss Volume": "blv",
    "Broken Vessels": "bve",
    "Missed Targets": "mtg",
    "Pierce Distance": "pid",
    "Knot Anomalies": "kta",
    "Correct Knots": "ckt",
    "Closure Accuracy": "cac",
    "Suture Pullouts": "spo",
    "Excessive Suture Force": "esf",
    "Incorrect Cut Length": "icl",
    "Incorrect Suture Cuts": "isc",
    "Instrument Switches": "isw",
    "Points": "pts",
}

PRE_METRIC_LABEL_MAP = {
    "Master Workspace Range": "mwrp",
}

# "Master Workspace Range" is the metric the Mimic software ships normalized to 40
# instead of 200, with the PASS threshold at 20 instead of 100. This app analyses
# everything on one canonical scale (0..200, PASS at 100), so such a score is
# rescaled on the way in.
#
# The normalized range is a PER-EXERCISE, PER-METRIC simulator setting, so the
# conversion factor is NOT a constant: it is derived from norm_max, declared in
# exercise_proficiency_scores.py, which must mirror your simulator's settings.
# That replaces the flat x5 that used to be applied here regardless of exercise —
# which silently inflated any exercise whose simulator setting had been changed
# to 0..200, multiplying an already-canonical score by 5 again.
#
# The raw score is left alone; only the normalized score is rescaled.

# "Pre" metrics are parsed with a "_pre_" infix (e.g. mwrp_score_pre_raw).
# This map re-publishes them under shorter UI-facing keys.

PRE_METRIC_ALIASES = {
    "mwrp": {"ui_key": "mwr", "multiplier_score_raw": 1},
}

# Metrics used by each exercise (abbreviations from METRIC_LABEL_MAP + PRE_METRIC_ALIASES ui_keys)
EXERCISE_METRICS: dict[str, list[str]] = {
    "pp1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "pb1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "pb2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "pb3": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "rtt": ["ttc", "eom", "ico", "iov", "drp", "tko", "wrc", "wcd"],
    "mb1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "mb2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "mb3": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "4ac": ["ttc", "eom", "ico", "iov", "drp", "icl", "isc", "isw"],
    "rr1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rr2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rw1": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "rw2": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "rw3": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "vop": ["pts"],
    "ct1": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "ct2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "ppc": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "mbc": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "es1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "met"],
    "es2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "met"],
    "ed2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "met", "blv", "bve"],
    "ed3": ["ttc", "eom", "ico", "iov", "exf", "mwr", "met", "blv", "bve"],
    "tr1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "tr2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "nt1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "ss0": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "ss1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "ss2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "ss3": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "ss4": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "bgd": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
    "row": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "wcv": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tcv": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "wch": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tch": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "sug": ["ttc", "eom", "ico", "iov", "esf", "cac", "mtg", "pid"],
    "tu1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tah": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tu2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tav": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "tu3": ["ttc", "eom", "ico", "iov", "exf", "mwr", "mtg"],
    "kr1": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "kr2": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "kr3": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "kr4": ["ttc", "eom", "ico", "iov", "exf", "mwr"],
    "is1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "isc"],
    "is2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "isc"],
    # --- v7.0 new exercises (confirmed from PROFICIENCY_BASELINES) ---
    "30d": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "ttr": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rc1": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rc2": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rc3": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "rc4": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp"],
    "sc1": ["pts"],
    "sc2": ["pts"],
    "ppd": ["ttc", "eom", "ico", "iov", "icl", "icu"],
    "ech": ["pts"],
    "rrt": ["ttc", "eom", "ico", "iov", "exf", "mwr", "drp", "mtg"],
}


# -------------------------------------------------
# Score column definitions (used by Analysis and Graph windows)
# -------------------------------------------------
SCORE_COLUMNS = [
    ("overall_score", "overall_score"),
    ("ttc_score_raw", "ttc_score_raw"),
    ("ttc_score_200", "ttc_score_200"),
    ("eom_score_raw", "eom_score_raw"),
    ("eom_score_200", "eom_score_200"),
    ("ico_score_raw", "ico_score_raw"),
    ("ico_score_200", "ico_score_200"),
    ("iov_score_raw", "iov_score_raw"),
    ("iov_score_200", "iov_score_200"),
    ("exf_score_raw", "exf_score_raw"),
    ("exf_score_200", "exf_score_200"),
    ("mwr_score_raw", "mwr_score_raw"),
    ("mwr_score_200", "mwr_score_200"),
    ("drp_score_raw", "drp_score_raw"),
    ("drp_score_200", "drp_score_200"),
    ("wrc_score_raw", "wrc_score_raw"),
    ("wrc_score_200", "wrc_score_200"),
    ("wcd_score_raw", "wcd_score_raw"),
    ("wcd_score_200", "wcd_score_200"),
    ("tko_score_raw", "tko_score_raw"),
    ("tko_score_200", "tko_score_200"),
    ("met_score_raw", "met_score_raw"),
    ("met_score_200", "met_score_200"),
    ("blv_score_raw", "blv_score_raw"),
    ("blv_score_200", "blv_score_200"),
    ("bve_score_raw", "bve_score_raw"),
    ("bve_score_200", "bve_score_200"),
    ("mtg_score_raw", "mtg_score_raw"),
    ("mtg_score_200", "mtg_score_200"),
    ("pid_score_raw", "pid_score_raw"),
    ("pid_score_200", "pid_score_200"),
    ("kta_score_raw", "kta_score_raw"),
    ("kta_score_200", "kta_score_200"),
    ("ckt_score_raw", "ckt_score_raw"),
    ("ckt_score_200", "ckt_score_200"),
    ("cac_score_raw", "cac_score_raw"),
    ("cac_score_200", "cac_score_200"),
    ("spo_score_raw", "spo_score_raw"),
    ("spo_score_200", "spo_score_200"),
    ("esf_score_raw", "esf_score_raw"),
    ("esf_score_200", "esf_score_200"),
    ("icl_score_raw", "icl_score_raw"),
    ("icl_score_200", "icl_score_200"),
    ("isc_score_raw", "isc_score_raw"),
    ("isc_score_200", "isc_score_200"),
    ("isw_score_raw", "isw_score_raw"),
    ("isw_score_200", "isw_score_200"),
    ("pts_score_raw", "pts_score_raw"),
    ("pts_score_200", "pts_score_200"),
]


# =============================================================================
#  [SEC-03] CSV FILE CLEANING & I/O
# =============================================================================

# Discards any row that is not an attempt record (see is_export_data_row)
# Discards rows containing "Incomplete"
# Discards rows containing "Master Contact Warning"
#
# Strips whitespace before commas
# Formats decimals to 2 decimal places
# Truncates the final field to 2 decimal places if it has more
# Remove fields related to: email, profession, specialty, curriculum
# Removes fields related to: passed, is critical
# Removes fields equal to "Complete"
# Lines are lexicographically sorted
#
# CRITICAL STEP:
# Consecutive rows sharing the same 3rd field (exercise name at this point) are merged, by appending the later row's metrics (field 4+) to the previous row.
# Swap second and third fields (subject, exercise, datetime → subject, datetime, exercise)
# 
# Normalizes exercise names via EXERCISE_NAME_REPLACEMENTS (e.g., "4. Suturing" → "Suturing")
# Normalizes metric labels: "Time to Complete Exercise" → ttc_score_raw
# Inserts corresponding *_score_200 columns before normalized scores
# Rows are sorted by Subject (alphabetical - first field) → Datetime (chronological - second field tiebreaker) → Exercise (alphabetical - third field tie-breaker)

EXPORT_PATTERN = re.compile(
    r"^MimicSessionExport_(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})\.csv$",
    re.IGNORECASE
)

# Clean filenames: MimicClean_<SubjectOrMultiple>_dd_mm_yyyy-HH_MM_SS.csv
CLEAN_PATTERN_WITH_SUBJECT = re.compile(
    r"^MimicClean_(.+?)_(\d{2})_(\d{2})_(\d{4})-(\d{2})_(\d{2})_(\d{2})\.csv$",
    re.IGNORECASE
)

# Backward compatible pattern: MimicClean_dd_mm_yyyy-HH_MM_SS.csv
CLEAN_PATTERN_LEGACY = re.compile(
    r"^MimicClean_(\d{2})_(\d{2})_(\d{4})-(\d{2})_(\d{2})_(\d{2})\.csv$",
    re.IGNORECASE
)


def is_single_subject_clean_filename(filename: str) -> bool:
    """True if `filename` is a clean CSV holding exactly one subject.

    Retrospective analysis replays one subject's progression, so it needs a
    single-subject file: not a 'Multiple' file, and not the legacy untagged
    format whose subject cannot be recovered from the name.

    The test used to be `filename.startswith("MimicClean_Aluno")`. At any centre
    using different subject codes the retrospective menu item therefore never
    appeared at all — a feature silently missing rather than failing.
    """
    match = CLEAN_PATTERN_WITH_SUBJECT.match(filename or "")
    if not match:
        return False
    return match.group(1).strip().lower() != "multiple"


# Cleaning helpers
SPACE_BEFORE_FIRST_COMMA = re.compile(r"\s+(?=,)")
DECIMAL_WITH_DOT = re.compile(r"\d+\.\d+")

# Status values the simulator writes in field 7 of a session export.
_EXPORT_ATTEMPT_STATUSES = {"complete", "incomplete"}

# Simulator service accounts. These are properties of the simulator software,
# not of any one centre: sessions run while setting up or testing the machine
# are logged under them and are not trainee attempts.
_EXPORT_NON_SUBJECT_ACCOUNTS = {"administrator", "admin", "guest", "default", "user"}


def is_export_data_row(raw: str) -> bool:
    """True if `raw` is a trainee attempt record in a MimicSessionExport CSV.

    A data row is identified by its own structure: at least 8 comma-separated
    fields, a non-empty subject in field 0 that is not a simulator service
    account, and a recognised status in field 7. This excludes the header line
    (whose field 7 is the literal "Status"), blank lines, and trailing junk.

    This replaces an earlier `raw.startswith("Aluno")` test. "Aluno" was the
    subject-naming convention of the centre where RSAC was developed, so an
    export from anywhere else matched no rows at all and the import completed
    reporting zero attempts and no error — the failure was entirely silent.

    That test was also, incidentally, what kept the simulator's own
    `Administrator` sessions out of the data, which is why the service-account
    exclusion below is needed to preserve the original behaviour.
    """
    fields = raw.split(",")
    if len(fields) < 8:
        return False
    subject = fields[0].strip()
    if not subject:
        return False
    if subject.lower() in _EXPORT_NON_SUBJECT_ACCOUNTS:
        return False
    return fields[7].strip().lower() in _EXPORT_ATTEMPT_STATUSES


TRUNCATE_LAST_FIELD_EXTRA_DECIMALS = re.compile(r"(\.\d{2})\d+")

# Exercise name normalization for simulator exports (applied during cleaning, after the exercise/date swap)
EXERCISE_NAME_REPLACEMENTS: dict[str, str] = {
    "2. Ring Tower Transfer": "Ring Tower Transfer",
    "3. Knot Tying": "Knot Tying",
    "4. Suturing": "Suturing",
    "5. 4th Arm Cutting": "4th Arm Cutting",
    "Tube Closure Horizontal": "Tube Closure - Horizontal",
    "Tube Closure Vertical": "Tube Closure - Vertical",
}

def normalize_exercise_name(name: str) -> str:
    name = (name or "").strip()
    return EXERCISE_NAME_REPLACEMENTS.get(name, name)


def collect_export_files(folder: str):
    if not folder or not os.path.isdir(folder):
        return []

    items = []
    for name in os.listdir(folder):
        if not name.startswith("MimicSessionExport_"):
            continue
        m = EXPORT_PATTERN.match(name)
        if not m:
            continue
        date_part, time_part = m.groups()
        dt = datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H-%M-%S")
        items.append({
            "datetime": dt,
            "date": dt.strftime("%d-%m-%Y"),
            "time": dt.strftime("%H:%M:%S"),
            "filename": name,
            "path": os.path.join(folder, name),
        })
    items.sort(key=lambda x: x["datetime"], reverse=True)
    return items


def collect_clean_files(folder: str):
    items = []
    if not folder or not os.path.isdir(folder):
        return items

    for name in os.listdir(folder):
        if not name.lower().startswith("mimicclean_"):
            continue

        dt = None
        date_disp = ""
        time_disp = ""

        m = CLEAN_PATTERN_WITH_SUBJECT.match(name)
        if m:
            _subject_tag, dd, mm, yyyy, HH, MM, SS = m.groups()
            try:
                dt = datetime.strptime(f"{dd}-{mm}-{yyyy} {HH}:{MM}:{SS}", "%d-%m-%Y %H:%M:%S")
                date_disp = dt.strftime("%d-%m-%Y")
                time_disp = dt.strftime("%H:%M:%S")
            except ValueError:
                dt = None
        else:
            m2 = CLEAN_PATTERN_LEGACY.match(name)
            if m2:
                dd, mm, yyyy, HH, MM, SS = m2.groups()
                try:
                    dt = datetime.strptime(f"{dd}-{mm}-{yyyy} {HH}:{MM}:{SS}", "%d-%m-%Y %H:%M:%S")
                    date_disp = dt.strftime("%d-%m-%Y")
                    time_disp = dt.strftime("%H:%M:%S")
                except ValueError:
                    dt = None

        subject_tag = ""
        if m:
            subject_tag = m.group(1)

        items.append({
            "datetime": dt,
            "date": date_disp,
            "time": time_disp,
            "filename": name,
            "path": os.path.join(folder, name),
            "subject": subject_tag,
        })

    items.sort(key=lambda x: (x["datetime"] is None, x["datetime"] or datetime.min), reverse=True)
    return items



def collect_history_json_files(history_dir: str) -> list[dict[str, str]]:
    """Collect History_*-att.json history files from ./analysis_history.

    These files are written both by live session decisions (source='live')
    and by retrospective analysis (source='retro').

    Returns list of dicts: {filename, path, subject, attempts, source, date, time}
    """
    import json as _json
    out: list[dict[str, str]] = []
    if not os.path.isdir(history_dir):
        return out

    _pat = re.compile(r"^History_(.+?)_(\d+)-att\.json$", re.IGNORECASE)
    for name in sorted(os.listdir(history_dir)):
        if not name.lower().endswith(".json"):
            continue
        m = _pat.match(name)
        if not m:
            continue
        subject = m.group(1)
        attempts = m.group(2)
        fp = os.path.join(history_dir, name)
        mtime = os.path.getmtime(fp)
        dt = datetime.fromtimestamp(mtime)
        source = "retro"  # default if unreadable
        try:
            with open(fp, "r", encoding="utf-8") as _jf:
                _data = _json.load(_jf)
            if isinstance(_data, list) and _data and isinstance(_data[0], dict):
                source = str(_data[0].get("source", "retro")).lower()
        except Exception:
            pass
        out.append({
            "filename": name,
            "path": fp,
            "subject": subject,
            "attempts": attempts,
            "source": source,
            "date": dt.strftime("%Y-%m-%d"),
            "time": dt.strftime("%H:%M:%S"),
        })
    out.sort(key=lambda d: d.get("filename", ""))
    return out


def stamp_for_clean_output(session_dt: datetime) -> str:
    return session_dt.strftime("%d_%m_%Y-%H_%M_%S")


def build_clean_output_filename(subject_tag: str, session_dt: datetime) -> str:
    # subject_tag is typically a single subject code, or 'Multiple'
    stamp = stamp_for_clean_output(session_dt)
    subject_tag = (subject_tag or "").strip() or "Unknown"
    return f"MimicClean_{subject_tag}_{stamp}.csv"


def build_clean_output_path(
    export_input_path: str,
    session_dt: datetime,
    output_folder: Optional[str] = None,
    subject_tag: Optional[str] = None,
) -> str:
    # If output_folder is provided, write into that folder (used by folder convention).
    folder = output_folder if output_folder else os.path.dirname(export_input_path)

    # Legacy naming (no subject tag) remains supported if subject_tag is None.
    if subject_tag is None:
        stamp = stamp_for_clean_output(session_dt)
        return os.path.join(folder, f"MimicClean_{stamp}.csv")

    filename = build_clean_output_filename(subject_tag, session_dt)
    return os.path.join(folder, filename)


# Clean CSV Step - Cleaning

def get_subjects_in_export(input_path: str) -> list[str]:
    """Read a MimicSessionExport CSV and return sorted unique subject names."""
    subjects: set[str] = set()
    with open(input_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            if not is_export_data_row(raw):
                continue
            if "Incomplete" in raw:
                continue
            if "Master Contact Warning" in raw:
                continue
            subj = raw.split(",")[0].strip()
            if subj:
                subjects.add(subj)
    return sorted(subjects)


def clean_mimic_csv(input_path: str, output_path: str, subject_filter: str | None = None) -> tuple[int, set[str]]:
    with open(input_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().splitlines()

    processed_lines = []
    subjects: set[str] = set()

    for raw in lines:
        if not is_export_data_row(raw):
            continue
        if "Incomplete" in raw:
            continue
        if "Master Contact Warning" in raw:
            continue

        # Optional per-subject filtering
        if subject_filter is not None:
            first_field = raw.split(",")[0].strip()
            if first_field != subject_filter:
                continue

        line = SPACE_BEFORE_FIRST_COMMA.sub("", raw)

        fields = line.split(",")

        # Keep only the first field + fields from index 5 onward
        new_fields = [fields[0]] + (fields[5:] if len(fields) > 5 else [])

        # Format any dot-decimals to 2 dp
        tmp = []
        for v in new_fields:
            if DECIMAL_WITH_DOT.search(v):
                try:
                    num = float(v)
                    v = f"{num:.2f}"
                except ValueError:
                    pass
            tmp.append(v)
        new_fields = tmp

        # Remove fields equal to "Complete"
        new_fields = [v for v in new_fields if v != "Complete"]

        # Remove the last two fields
        if len(new_fields) >= 3:
            new_fields = new_fields[:-2]

        # Ensure last field has at most 2 decimal places
        if new_fields:
            last = new_fields[-1]
            if re.search(r"\.\d{2,}", last):
                new_fields[-1] = TRUNCATE_LAST_FIELD_EXTRA_DECIMALS.sub(r"\1", last)

        subjects.add((new_fields[0] if new_fields else '').strip())
        processed_lines.append(",".join(new_fields))

    processed_lines.sort()

    # Merge consecutive lines if 3rd field is same
    final_lines = []
    for line in processed_lines:
        cur = line.split(",")

        if final_lines:
            prev = final_lines[-1].split(",")
            if len(cur) >= 3 and len(prev) >= 3 and cur[2] == prev[2]:
                to_add = cur[4:] if len(cur) > 4 else []
                final_lines[-1] = ",".join(prev + to_add)
                continue

        final_lines.append(line)

    # Swap fields 2 and 3 (exercise <-> date/time) ONLY after merging.
    # After swapping, sort by:
    #   1) subject (field 1)
    #   2) date_time (field 2, parsed as datetime)
    #   3) exercise (field 3) as a deterministic tie-breaker
    
    def _parse_dt_for_clean_sort(s: str) -> Optional[datetime]:
        s = (s or "").strip()
        if not s:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    # -------------------------------------------------
    # Metric label normalization (late-stage)
    # -------------------------------------------------

    def _apply_metric_label_insertion(parts: list[str]) -> list[str]:
        i = 0
        while i < len(parts):
            label = parts[i]

            abbr = METRIC_LABEL_MAP.get(label)
            if abbr:
                raw_key = f"{abbr}_score_raw"
                k200 = f"{abbr}_score_200"
                parts[i] = raw_key

                insert_pos = i + 2
                if insert_pos <= len(parts):
                    if insert_pos >= len(parts) or parts[insert_pos] != k200:
                        parts.insert(insert_pos, k200)
                        i = insert_pos + 1
                        continue
                i += 1
                continue

            pre_abbr = PRE_METRIC_LABEL_MAP.get(label)
            if pre_abbr:
                pre_raw_key = f"{pre_abbr}_score_pre_raw"
                pre_200_key = f"{pre_abbr}_score_pre_200"
                parts[i] = pre_raw_key

                insert_pos = i + 2
                if insert_pos <= len(parts):
                    if insert_pos >= len(parts) or parts[insert_pos] != pre_200_key:
                        parts.insert(insert_pos, pre_200_key)
                        i = insert_pos + 1
                        continue
                i += 1
                continue

            i += 1
        return parts
    swapped_rows: list[tuple[str, Optional[datetime], str, str]] = []
    for line in final_lines:
        parts = line.split(",")
        if len(parts) >= 3:
            # original: subject, exercise, date_time, ...
            # swapped:   subject, date_time, exercise, ...
            parts[1], parts[2] = parts[2], parts[1]

        # Apply metric label normalization/insertion after final structural edits
        parts = _apply_metric_label_insertion(parts)
        subject_name = parts[0].strip() if parts else ""
        dt_str = parts[1].strip() if len(parts) > 1 else ""
        ex_name = parts[2].strip() if len(parts) > 2 else ""
        ex_name = normalize_exercise_name(ex_name)
        if len(parts) > 2:
            parts[2] = ex_name
        dt_obj = _parse_dt_for_clean_sort(dt_str)
        swapped_rows.append((subject_name, dt_obj, ex_name, ",".join(parts)))

    swapped_rows.sort(key=lambda t: (t[0], t[1] is None, t[1] or datetime.min, t[2]))

    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        for _subj, _dt, _ex, line in swapped_rows:
            f.write(line + "\n")

    return len(swapped_rows), subjects


def extract_incomplete_attempts(input_path: str, subject_filter: str | None = None) -> dict[str, dict[str, dict[str, float]]]:
    """Count incomplete attempts (and sum their duration) per subject per exercise
    in a MimicSessionExport CSV.

    In the raw export every metric of one attempt is a separate line sharing the
    same timestamp, so a distinct (subject, exercise, timestamp) combination among
    'Incomplete' rows identifies one incomplete attempt. The duration of each
    attempt is read from its 'Time to Complete Exercise' metric row (raw value,
    in seconds).

    Returns {subject: {exercise: {"count": int, "time": float}}}.
    """
    seen: set[tuple[str, str, str]] = set()
    durations: dict[tuple[str, str, str], float] = {}
    with open(input_path, "r", encoding="utf-8-sig", errors="replace") as f:
        for raw in f:
            raw = raw.strip()
            if not is_export_data_row(raw):
                continue
            fields = raw.split(",")
            if fields[7].strip() != "Incomplete":
                continue
            subject = fields[0].strip()
            if subject_filter is not None and subject != subject_filter:
                continue
            exercise = normalize_exercise_name(fields[5])
            timestamp = fields[6].strip()
            key = (subject, exercise, timestamp)
            seen.add(key)
            if len(fields) > 10 and fields[9].strip() == "Time to Complete Exercise":
                try:
                    durations[key] = float(fields[10].strip())
                except ValueError:
                    pass

    counts: dict[str, dict[str, dict[str, float]]] = {}
    for key in seen:
        subject, exercise, _ts = key
        per_subj = counts.setdefault(subject, {})
        per_ex = per_subj.setdefault(exercise, {"count": 0, "time": 0.0})
        per_ex["count"] += 1
        per_ex["time"] += durations.get(key, 0.0)
    return counts


def write_incomplete_attempts_csv(
    subject: str,
    exercise_stats: dict[str, dict[str, float]],
    output_folder: str,
    session_dt: datetime,
) -> str | None:
    """Write IncompleteAttempts_<subject>_<stamp>.csv (one line per exercise).

    Format: subject,exercise,incomplete_count,total_time_seconds (no header,
    matching MimicClean style). Any previous IncompleteAttempts file for the
    subject is replaced. Returns the output path, or None if there are no
    incomplete attempts.
    """
    prefix = f"incompleteattempts_{subject.lower()}_"
    try:
        for name in os.listdir(output_folder):
            if name.lower().startswith(prefix) and name.lower().endswith(".csv"):
                os.remove(os.path.join(output_folder, name))
    except Exception:
        pass

    if not exercise_stats:
        return None

    stamp = stamp_for_clean_output(session_dt)
    out_path = os.path.join(output_folder, f"IncompleteAttempts_{subject}_{stamp}.csv")
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for exercise in sorted(exercise_stats):
            stats = exercise_stats[exercise]
            count = int(stats.get("count", 0))
            total_time = float(stats.get("time", 0.0))
            f.write(f"{subject},{exercise},{count},{total_time:.4f}\n")
    return out_path


def update_incomplete_attempts_csv(
    subject: str,
    exercise_full: str,
    ttc_seconds: float,
    output_folder: str,
) -> str:
    """Create or update the subject's IncompleteAttempts_ CSV for a single live
    incomplete attempt (see AttemptProcessor.log_incomplete).

    Unlike write_incomplete_attempts_csv (used by the retrospective batch
    import, which replaces the whole file from a fresh count), this
    increments a single exercise's line in place, preserving any other
    exercises already logged for the subject. Creates the file (and the
    exercise's line) if they don't exist yet.
    """
    prefix = f"incompleteattempts_{subject.lower()}_"
    inc_path = None
    try:
        for name in os.listdir(output_folder):
            if name.lower().startswith(prefix) and name.lower().endswith(".csv"):
                inc_path = os.path.join(output_folder, name)
                break
    except Exception:
        pass

    if inc_path is None:
        stamp = stamp_for_clean_output(datetime.now())
        inc_path = os.path.join(output_folder, f"IncompleteAttempts_{subject}_{stamp}.csv")

    lines: list[str] = []
    if os.path.isfile(inc_path):
        with open(inc_path, "r", encoding="utf-8-sig", errors="replace") as f:
            lines = f.read().splitlines()

    found = False
    for i, raw in enumerate(lines):
        parts = raw.split(",")
        if len(parts) >= 4 and parts[0].strip() == subject and parts[1].strip() == exercise_full:
            try:
                count = int(parts[2].strip()) + 1
            except ValueError:
                count = 1
            try:
                total_time = float(parts[3].strip()) + ttc_seconds
            except ValueError:
                total_time = ttc_seconds
            lines[i] = f"{subject},{exercise_full},{count},{total_time:.4f}"
            found = True
            break

    if not found:
        lines.append(f"{subject},{exercise_full},1,{ttc_seconds:.4f}")

    with open(inc_path, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

    return inc_path


def get_incomplete_stats_by_exercise(subject: str, folder: str) -> dict[str, dict[str, float]]:
    """Read the IncompleteAttempts_<subject>_*.csv file (if any) in *folder* and
    return {exerc_abb: {"count": int, "time": float}} for the given subject.
    """
    prefix = f"incompleteattempts_{subject.lower()}_"
    inc_path = None
    try:
        for name in os.listdir(folder):
            if name.lower().startswith(prefix) and name.lower().endswith(".csv"):
                inc_path = os.path.join(folder, name)
                break
    except Exception:
        return {}

    if not inc_path:
        return {}

    full_to_abb: dict[str, str] = {
        str(v.get("exerc_full")).strip(): k
        for k, v in EXERCISE_DEFS.items()
        if v.get("exerc_full") is not None and str(v.get("exerc_full")).strip()
    }

    stats: dict[str, dict[str, float]] = {}
    try:
        with open(inc_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for raw in f:
                parts = raw.strip().split(",")
                if len(parts) < 4 or parts[0].strip() != subject:
                    continue
                ex_name = ",".join(parts[1:-2]).strip()
                abb = ex_name if ex_name in EXERCISE_DEFS else full_to_abb.get(ex_name, "")
                if not abb:
                    continue
                entry = stats.setdefault(abb, {"count": 0, "time": 0.0})
                try:
                    entry["count"] += int(parts[-2].strip())
                except ValueError:
                    pass
                try:
                    entry["time"] += float(parts[-1].strip())
                except ValueError:
                    pass
    except Exception:
        return {}

    return stats


def get_incomplete_totals(subject: str, folder: str) -> tuple[int, float]:
    """Read the IncompleteAttempts_<subject>_*.csv file (if any) in *folder* and
    return (total_count, total_time_seconds) summed across all exercises.
    """
    prefix = f"incompleteattempts_{subject.lower()}_"
    inc_path = None
    try:
        for name in os.listdir(folder):
            if name.lower().startswith(prefix) and name.lower().endswith(".csv"):
                inc_path = os.path.join(folder, name)
                break
    except Exception:
        return 0, 0.0

    if not inc_path:
        return 0, 0.0

    total_count = 0
    total_time = 0.0
    try:
        with open(inc_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for raw in f:
                parts = raw.strip().split(",")
                if len(parts) < 4 or parts[0].strip() != subject:
                    continue
                try:
                    total_count += int(parts[-2].strip())
                except ValueError:
                    pass
                try:
                    total_time += float(parts[-1].strip())
                except ValueError:
                    pass
    except Exception:
        return 0, 0.0

    return total_count, total_time


class _SubjectSelectionDialog(QDialog):
    """Dialog with checkboxes to select which subjects to extract."""

    def __init__(self, subjects: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Subjects to Extract")
        self.setMinimumWidth(340)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select the subjects you want to extract:"))

        # "All subjects" checkbox
        self.cb_all = QCheckBox(f"All subjects ({len(subjects)})")
        self.cb_all.setChecked(True)
        self.cb_all.stateChanged.connect(self._on_all_toggled)
        layout.addWidget(self.cb_all)

        # Separator
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #888;")
        layout.addWidget(line)

        # Individual subject checkboxes, inside a scroll area so that a long
        # subject list cannot push the mode radios and OK/Cancel off-screen.
        self._subject_cbs: list[tuple[str, QCheckBox]] = []
        subj_container = QWidget()
        subj_layout = QVBoxLayout(subj_container)
        subj_layout.setContentsMargins(0, 0, 0, 0)
        subj_layout.setSpacing(2)
        for s in subjects:
            cb = QCheckBox(s)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_individual_toggled)
            subj_layout.addWidget(cb)
            self._subject_cbs.append((s, cb))
        subj_layout.addStretch(1)

        subj_scroll = QScrollArea()
        subj_scroll.setWidget(subj_container)
        subj_scroll.setWidgetResizable(True)
        subj_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        subj_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        subj_scroll.setFrameShape(QFrame.StyledPanel)
        subj_scroll.setMinimumHeight(120)
        subj_scroll.setMaximumHeight(320)
        layout.addWidget(subj_scroll, stretch=1)

        layout.addSpacing(10)

        # Output mode selection
        mode_line = QWidget()
        mode_line.setFixedHeight(1)
        mode_line.setStyleSheet("background-color: #888;")
        layout.addWidget(mode_line)
        layout.addWidget(QLabel("Files to create:"))
        self._radio_clean = QRadioButton("Clean CSV only")
        self._radio_incomplete = QRadioButton("Incomplete attempts CSV only")
        self._radio_both = QRadioButton("Both")
        self._radio_both.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self._radio_clean)
        mode_group.addButton(self._radio_incomplete)
        mode_group.addButton(self._radio_both)
        layout.addWidget(self._radio_clean)
        layout.addWidget(self._radio_incomplete)
        layout.addWidget(self._radio_both)

        layout.addSpacing(10)

        # OK / Cancel
        btn_row = QHBoxLayout()
        btn_ok = QPushButton("OK")
        btn_cancel = QPushButton("Cancel")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(btn_ok)
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self._updating = False

    def _on_all_toggled(self):
        if self._updating:
            return
        self._updating = True
        checked = self.cb_all.isChecked()
        for _, cb in self._subject_cbs:
            cb.setChecked(checked)
        self._updating = False

    def _on_individual_toggled(self):
        if self._updating:
            return
        self._updating = True
        all_checked = all(cb.isChecked() for _, cb in self._subject_cbs)
        none_checked = not any(cb.isChecked() for _, cb in self._subject_cbs)
        if all_checked:
            self.cb_all.setCheckState(Qt.Checked)
        elif none_checked:
            self.cb_all.setCheckState(Qt.Unchecked)
        else:
            self.cb_all.setCheckState(Qt.PartiallyChecked)
        self._updating = False

    def selected_subjects(self) -> list[str]:
        return [s for s, cb in self._subject_cbs if cb.isChecked()]

    def selected_mode(self) -> str:
        """Return 'clean', 'incomplete' or 'both'."""
        if self._radio_clean.isChecked():
            return "clean"
        if self._radio_incomplete.isChecked():
            return "incomplete"
        return "both"


def _write_incomplete_for_subject(
    ui: 'MainWindow',
    input_path: str,
    session_dt: datetime,
    subject: str,
) -> str | None:
    """Extract and write the IncompleteAttempts file for one subject. Returns path or None."""
    try:
        inc_counts = extract_incomplete_attempts(input_path, subject_filter=subject).get(subject, {})
        return write_incomplete_attempts_csv(subject, inc_counts, ui.clean_dir, session_dt)
    except Exception as e:
        QMessageBox.warning(ui, "Incomplete attempts", f"Could not extract incomplete attempts for {subject}:\n{e}")
        return None


def _clean_single_subject(
    ui: 'MainWindow',
    input_path: str,
    session_dt: datetime,
    subject: str,
    mode: str = "both",
) -> str | None:
    """Process one subject according to mode ('clean', 'incomplete' or 'both').

    Returns the created file path (clean file when mode includes cleaning,
    otherwise the incomplete file) or None on skip/error.
    """
    if mode == "incomplete":
        return _write_incomplete_for_subject(ui, input_path, session_dt, subject)

    clean_path = build_clean_output_path(
        input_path,
        session_dt,
        output_folder=ui.clean_dir,
        subject_tag=subject,
    )

    # Check if a clean file for this subject already exists
    try:
        prefix = f"mimicclean_{subject.lower()}_"
        existing_matches = [
            os.path.join(ui.clean_dir, name)
            for name in os.listdir(ui.clean_dir)
            if name.lower().startswith(prefix)
            and name.lower().endswith(".csv")
            and not name.lower().startswith("__tmp_")
        ]
    except Exception:
        existing_matches = []

    if existing_matches:
        resp = QMessageBox.question(
            ui,
            "Replace existing subject file?",
            f"A MimicClean file for {subject} already exists in csv_clean.\n\n"
            "If you continue, the previous file will be deleted and replaced.\n\n"
            "Proceed?",
            QMessageBox.Ok | QMessageBox.Cancel,
            QMessageBox.Cancel,
        )
        if resp != QMessageBox.Ok:
            return None
        for old in existing_matches:
            try:
                os.remove(old)
            except Exception:
                pass

    stamp = stamp_for_clean_output(session_dt)
    tmp_path = os.path.join(ui.clean_dir, f"__tmp_MimicClean_{subject}_{stamp}.csv")

    try:
        n_clean, _subjs = clean_mimic_csv(input_path, tmp_path, subject_filter=subject)
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        QMessageBox.critical(ui, "Cleaning failed", f"Error cleaning {subject}:\n{e}")
        return None

    if n_clean == 0:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return None

    try:
        os.replace(tmp_path, clean_path)
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        QMessageBox.critical(ui, "Rename failed", f"Could not finalize clean file for {subject}:\n{e}")
        return None

    # Extract incomplete-attempt counts to a separate IncompleteAttempts file
    if mode == "both":
        _write_incomplete_for_subject(ui, input_path, session_dt, subject)

    return clean_path


def run_clean_selected_export(ui: 'MainWindow') -> None:
    row = ui.export_table.currentRow()
    if row < 0:
        QMessageBox.warning(ui, "No selection", "Please select a MimicSessionExport file first.")
        return

    item = ui.export_files[row]
    input_path = item["path"]

    if not os.path.isfile(input_path):
        QMessageBox.critical(ui, "File not found", f"The file no longer exists:\n{input_path}")
        return

    # Discover subjects in the original CSV
    try:
        subjects = get_subjects_in_export(input_path)
    except Exception as e:
        QMessageBox.critical(ui, "Read error", f"Could not read subjects from file:\n{e}")
        return

    if not subjects:
        QMessageBox.information(ui, "No data", "No valid subject rows found in this file.")
        return

    # Show subject selection dialog
    dlg = _SubjectSelectionDialog(subjects, parent=ui)
    if dlg.exec() != QDialog.Accepted:
        return

    selected = dlg.selected_subjects()
    if not selected:
        QMessageBox.information(ui, "No selection", "No subjects were selected.")
        return

    mode = dlg.selected_mode()

    # Extract each subject to its own file(s)
    created: list[str] = []
    for subj in selected:
        result = _clean_single_subject(ui, input_path, item["datetime"], subj, mode=mode)
        if result:
            created.append(result)

    ui.refresh_lists()

    if created:
        names = "\n".join(os.path.basename(p) for p in created)
        QMessageBox.information(
            ui,
            "Done",
            f"Files created ({len(created)} of {len(selected)} selected):\n\n{names}",
        )
    else:
        QMessageBox.information(ui, "No files created", "No files were created.")


# =============================================================================
#  [SEC-04] MAIN WINDOW (FILE MANAGER)
# =============================================================================


class _CollapsibleSection(QWidget):
    """A toggle header (button) + content widget that can collapse/expand."""

    def __init__(self, title: str, content_widget: QWidget, expanded: bool = True,
                 color: str = "#e0e0e0", hover_color: str = "#d0d0d0",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self._title = title
        self._content = content_widget
        self._expanded = expanded

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toggle_btn = QPushButton()
        self._toggle_btn.setStyleSheet(
            f"QPushButton {{ text-align: left; font-weight: bold; padding: 6px; border: none; "
            f"background: {color}; color: white; }}"
            f"QPushButton:hover {{ background: {hover_color}; }}"
        )
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

        layout.addWidget(self._content)

        self._content.setVisible(self._expanded)
        self._update_label()
        self._update_size_policy()

    def _update_label(self) -> None:
        arrow = "\u25BC" if self._expanded else "\u25B6"
        self._toggle_btn.setText(f"  {arrow}  {self._title}")

    def _update_size_policy(self) -> None:
        parent_layout = self.parentWidget().layout() if self.parentWidget() else None
        if self._expanded:
            self.setMinimumHeight(0)
            self.setMaximumHeight(16777215)
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            if parent_layout:
                idx = parent_layout.indexOf(self)
                if idx >= 0:
                    parent_layout.setStretch(idx, 1)
        else:
            btn_h = self._toggle_btn.sizeHint().height() or 30
            self.setFixedHeight(btn_h)
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            if parent_layout:
                idx = parent_layout.indexOf(self)
                if idx >= 0:
                    parent_layout.setStretch(idx, 0)

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._content.setVisible(self._expanded)
        self._update_label()
        self._update_size_policy()


# ---------------------------------------------------------------------------
#  Proficiency Values Window
# ---------------------------------------------------------------------------

# Reverse map: abbreviation -> full metric name
_METRIC_ABB_TO_FULL = {v: k for k, v in METRIC_LABEL_MAP.items()}
_METRIC_ABB_TO_FULL["mwr"] = "Master Workspace Range"


class _NumericTableItem(QTableWidgetItem):
    """A table cell that sorts by numeric value rather than as text.

    Without this, sorting the # or Sim ID column puts 10 before 2.
    """

    def __lt__(self, other: QTableWidgetItem) -> bool:
        try:
            return float(self.text() or 0) < float(other.text() or 0)
        except (TypeError, ValueError):
            return super().__lt__(other)


class _CategoryDelegate(QStyledItemDelegate):
    """Drop-down editor for the exercise category column.

    A delegate rather than a QComboBox permanently in every cell, because a
    permanent combo:
      - swallows the mouse wheel, so scrolling the table over that column
        silently changes categories instead of scrolling;
      - does not move when the table is sorted, since cell widgets are positioned
        by row index and stay put while the items beneath them are reordered.

    The category code is kept in Qt.UserRole; the cell text is the human label.
    """

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        for code, label in EXERCISE_CAT_LABELS.items():
            combo.addItem(f"{label} ({code})", userData=code)
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:
        idx = editor.findData(index.data(Qt.UserRole))
        editor.setCurrentIndex(max(0, idx))
        editor.showPopup()

    def setModelData(self, editor: QComboBox, model, index) -> None:
        model.setData(index, editor.currentData(), Qt.UserRole)
        model.setData(index, editor.currentText(), Qt.DisplayRole)


class SkillRatingsWindow(QMainWindow):
    """Editor for the exercise catalogue (EXERCISE_DEFS) and its skill ratings.

    Saving rewrites the EXERCISE_DEFS block inside `exercise_defs.py`, so that file
    always holds the values in force. Reverting restores from the read-only baseline
    in `exercise_defs_default.json`.

    `skill_intrinsic` and `skill_overall` are derived and shown read-only: they are
    recomputed live from the six components and the stringency rating. Letting them
    be typed is how a catalogue ends up disagreeing with itself.
    """

    # (field key, header, editable) — "__abb" is the dict key, not a field.
    COLUMNS: list[tuple[str, str, bool]] = (
        [
            ("__abb", "Abb", False),
            ("exerc_number", "#", True),
            ("exerc_full", "Exercise", True),
            ("id", "Sim ID", True),
            ("exerc_cat", "Category", True),
        ]
        + [(k, k.upper(), True) for k in exercise_defs.SKILL_COMPONENT_KEYS]
        + [
            ("skill_stringency", "Stringency", True),
            ("skill_intrinsic", "Intrinsic", False),
            ("skill_overall", "Overall", False),
        ]
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings – Exercises – Skill Ratings")
        self.resize(1180, 620)

        self._loading = False

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        intro = QLabel(
            "Skill ratings describe how demanding each exercise is. "
            "<b>Intrinsic</b> is the sum of the six components and <b>Overall</b> adds "
            "Stringency, so both are calculated for you. "
            "Saving writes these values into <code>exercise_defs.py</code>; "
            "<b>Reset</b> restores them from <code>exercise_defs_default.json</code>."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([c[1] for c in self.COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.itemChanged.connect(self._on_item_changed)
        self._table.setItemDelegateForColumn(
            self._col_of("exerc_cat"), _CategoryDelegate(self._table)
        )
        layout.addWidget(self._table, stretch=1)

        # Sorting is driven from header clicks rather than setSortingEnabled(True),
        # so that editing a cell can never make its row jump out from under the
        # cursor mid-typing.
        self._sort_col = self._col_of("exerc_number")
        self._sort_order = Qt.AscendingOrder
        header = self._table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(self._sort_col, self._sort_order)
        header.sectionClicked.connect(self._on_header_clicked)

        # Tooltip the component headers with what the codes mean.
        for col, (key, _header, _editable) in enumerate(self.COLUMNS):
            label = exercise_defs.SKILL_COMPONENT_LABELS.get(key)
            if label:
                item = self._table.horizontalHeaderItem(col)
                if item is not None:
                    item.setToolTip(label)

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("Save")
        self._btn_save.clicked.connect(self._on_save)
        self._btn_reload = QPushButton("Discard Changes")
        self._btn_reload.clicked.connect(lambda: self._load_entries(None))
        self._btn_revert_row = QPushButton("Reset Selected Exercise")
        self._btn_revert_row.clicked.connect(self._on_revert_selected)
        self._btn_revert_all = QPushButton("Reset All to Defaults")
        self._btn_revert_all.clicked.connect(self._on_revert_all)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_reload)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_revert_row)
        btn_row.addWidget(self._btn_revert_all)
        layout.addLayout(btn_row)

        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet("color: #555555;")
        layout.addWidget(self._lbl_status)

        # Without a baseline there is nothing to revert to, so say so rather than
        # offering buttons that would silently do nothing.
        if not exercise_defs.EXERCISE_DEFS_DEFAULTS:
            tip = (
                f"Baseline file not found:\n{exercise_defs.defaults_path()}\n"
                f"Resetting to defaults is unavailable until it is restored."
            )
            for btn in (self._btn_revert_row, self._btn_revert_all):
                btn.setEnabled(False)
                btn.setToolTip(tip)

        self._load_entries(None)
        align_window_top(self)

    # -- population ---------------------------------------------------------

    def _load_entries(self, entries: dict[str, dict] | None) -> None:
        """Fill the table from `entries`, or from the live catalogue when None."""
        source = EXERCISE_DEFS if entries is None else entries
        self._loading = True
        try:
            order = sorted(
                source.items(),
                key=lambda kv: (kv[1].get("exerc_number") or 0, kv[0]),
            )
            self._table.setRowCount(len(order))
            for row, (abb, entry) in enumerate(order):
                for col, (key, _header, editable) in enumerate(self.COLUMNS):
                    if key == "exerc_cat":
                        self._table.setItem(row, col, self._make_cat_item(entry))
                        continue

                    value = abb if key == "__abb" else entry.get(key)
                    text = "" if value is None else str(value)
                    item = (
                        _NumericTableItem(text)
                        if key in exercise_defs.INT_KEYS
                        else QTableWidgetItem(text)
                    )
                    if key == "__abb":
                        item.setData(Qt.UserRole, abb)
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setForeground(QBrush(QColor("#555555")))
                        item.setBackground(QBrush(QColor("#f0f0f0")))
                    self._table.setItem(row, col, item)
        finally:
            self._loading = False

        self._table.resizeColumnsToContents()
        self._apply_sort()
        self._refresh_modified_marks()
        self._update_status()

    def _make_cat_item(self, entry: dict) -> QTableWidgetItem:
        """Category cell: human label as text, the code stored in Qt.UserRole."""
        code = entry.get("exerc_cat")
        label = EXERCISE_CAT_LABELS.get(code)
        item = QTableWidgetItem(f"{label} ({code})" if label else str(code or ""))
        item.setData(Qt.UserRole, code)
        item.setToolTip("Double-click to change the category")
        return item

    def _col_of(self, key: str) -> int:
        for col, (k, _h, _e) in enumerate(self.COLUMNS):
            if k == key:
                return col
        return -1

    def _abb_at(self, row: int) -> str:
        item = self._table.item(row, 0)
        return "" if item is None else str(item.data(Qt.UserRole) or "")

    # -- sorting ------------------------------------------------------------

    def _on_header_clicked(self, col: int) -> None:
        """Sort by the clicked column, toggling direction on a repeat click."""
        if col == self._sort_col:
            self._sort_order = (
                Qt.DescendingOrder
                if self._sort_order == Qt.AscendingOrder
                else Qt.AscendingOrder
            )
        else:
            self._sort_col = col
            self._sort_order = Qt.AscendingOrder
        self._apply_sort()

    def _apply_sort(self) -> None:
        if self._sort_col < 0:
            return
        self._table.horizontalHeader().setSortIndicator(self._sort_col, self._sort_order)
        self._loading = True
        try:
            self._table.sortItems(self._sort_col, self._sort_order)
        finally:
            self._loading = False

    # -- editing ------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        key = self.COLUMNS[item.column()][0]
        if key in exercise_defs.SKILL_COMPONENT_KEYS or key == "skill_stringency":
            self._recompute_row(item.row())
        self._refresh_modified_marks()
        self._update_status()

    def _recompute_row(self, row: int) -> None:
        """Refresh the two derived cells from what is currently typed in the row."""
        entry = self._row_values(row, coerce=False)
        exercise_defs.recompute_derived(entry)
        self._loading = True
        try:
            for key in exercise_defs.DERIVED_KEYS:
                col = self._col_of(key)
                item = self._table.item(row, col)
                if item is not None:
                    item.setText(str(entry.get(key)))
        finally:
            self._loading = False

    def _row_values(self, row: int, coerce: bool = True) -> dict:
        """The row as a catalogue entry. With coerce=False, bad ints become 0."""
        out: dict = {}
        for col, (key, header, _editable) in enumerate(self.COLUMNS):
            if key == "__abb":
                continue
            if key == "exerc_cat":
                item = self._table.item(row, col)
                out[key] = "" if item is None else str(item.data(Qt.UserRole) or "")
                continue
            item = self._table.item(row, col)
            text = "" if item is None else item.text().strip()
            if key in exercise_defs.INT_KEYS:
                try:
                    out[key] = int(float(text)) if text else 0
                except ValueError:
                    if coerce:
                        raise ValueError(
                            f"{self._abb_at(row)}: '{header}' must be a whole number, "
                            f"not {text!r}"
                        )
                    out[key] = 0
            else:
                out[key] = text
        return out

    def _all_entries(self, coerce: bool = True) -> dict[str, dict]:
        """The whole table as a catalogue, derived fields filled in."""
        out: dict[str, dict] = {}
        for row in range(self._table.rowCount()):
            abb = self._abb_at(row)
            if not abb:
                continue
            out[abb] = exercise_defs.recompute_derived(
                self._row_values(row, coerce=coerce)
            )
        return out

    def _changed_from_defaults(self) -> dict[str, dict]:
        """Per-exercise differences against the baseline, for the change marks."""
        return {
            abb: diff
            for abb, entry in self._all_entries(coerce=False).items()
            if (diff := exercise_defs.diff_from_defaults(abb, entry))
        }

    def _refresh_modified_marks(self) -> None:
        """Bold the abbreviation of any exercise that differs from the baseline."""
        changed = self._changed_from_defaults()
        self._loading = True
        try:
            for row in range(self._table.rowCount()):
                abb = self._abb_at(row)
                item = self._table.item(row, 0)
                if item is None:
                    continue
                is_changed = abb in changed
                font = item.font()
                font.setBold(is_changed)
                item.setFont(font)
                item.setText(f"{abb} *" if is_changed else abb)
                item.setToolTip(
                    "Differs from the default: " + ", ".join(sorted(changed[abb]))
                    if is_changed
                    else ""
                )
        finally:
            self._loading = False

    def _update_status(self) -> None:
        changed = self._changed_from_defaults()
        bits = []
        if exercise_defs.EXERCISE_DEFS_DEFAULTS:
            bits.append(
                f"{len(changed)} of {self._table.rowCount()} exercises differ from default"
            )
        else:
            bits.append("<b>no baseline file</b> — cannot reset to defaults")
        if self._all_entries(coerce=False) != {
            abb: {k: v for k, v in entry.items() if k in exercise_defs.CATALOGUE_KEY_ORDER}
            for abb, entry in EXERCISE_DEFS.items()
        }:
            bits.append("<b>unsaved changes</b>")
        self._lbl_status.setText(" &nbsp;|&nbsp; ".join(bits))

    # -- actions ------------------------------------------------------------

    def _on_save(self) -> None:
        try:
            entries = self._all_entries(coerce=True)
        except ValueError as e:
            QMessageBox.warning(self, "Skill Ratings", str(e))
            return

        problems = self._validate()
        if problems:
            QMessageBox.warning(
                self, "Skill Ratings", "Cannot save:\n\n" + "\n".join(problems)
            )
            return

        renamed = [
            abb
            for abb, entry in entries.items()
            if abb in EXERCISE_DEFS
            and entry.get("exerc_full") != EXERCISE_DEFS[abb].get("exerc_full")
        ]
        if renamed:
            names = ", ".join(
                f"{EXERCISE_DEFS[abb].get('exerc_full')!r} → "
                f"{entries[abb].get('exerc_full')!r}"
                for abb in sorted(renamed)
            )
            reply = QMessageBox.warning(
                self,
                "Exercise renamed",
                f"You have changed the full name of: {names}\n\n"
                f"Exercise names are how attempts in the MimicClean CSVs are matched "
                f"to the catalogue. Renaming one will orphan every attempt already "
                f"recorded under the old name.\n\nSave anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        try:
            path = exercise_defs.save_catalogue(entries)
        except (OSError, RuntimeError, ValueError) as e:
            QMessageBox.critical(
                self,
                "Skill Ratings",
                f"Could not save — nothing was written:\n\n{e}",
            )
            return

        changed = self._changed_from_defaults()
        self._load_entries(None)
        QMessageBox.information(
            self,
            "Skill Ratings",
            f"Catalogue written to:\n{path}\n\n"
            f"{len(changed)} exercise(s) now differ from the default baseline.\n\n"
            f"Re-open any Progress Graph or analysis window to see the change.",
        )

    def _validate(self) -> list[str]:
        """Catch the mistakes that would corrupt the catalogue rather than just look odd."""
        problems: list[str] = []

        numbers: dict[int, list[str]] = {}
        ids: dict[int, list[str]] = {}
        names: dict[str, list[str]] = {}
        for row in range(self._table.rowCount()):
            abb = self._abb_at(row)
            if not abb:
                continue
            entry = self._row_values(row, coerce=False)
            numbers.setdefault(int(entry.get("exerc_number") or 0), []).append(abb)
            ids.setdefault(int(entry.get("id") or 0), []).append(abb)
            names.setdefault(str(entry.get("exerc_full") or "").strip().lower(), []).append(abb)

        for value, abbs in sorted(numbers.items()):
            if len(abbs) > 1:
                problems.append(f"Order number {value} is used by {', '.join(abbs)}")
        for value, abbs in sorted(ids.items()):
            if len(abbs) > 1:
                problems.append(f"Sim ID {value} is used by {', '.join(abbs)}")
        for value, abbs in sorted(names.items()):
            if not value:
                problems.append(f"{', '.join(abbs)} has no exercise name")
            elif len(abbs) > 1:
                problems.append(f"Exercise name {value!r} is used by {', '.join(abbs)}")

        return problems

    def _revert(self, abbs: list[str] | None, note: str) -> None:
        """Pull baseline values into the table without writing anything.

        The reset only reaches `exercise_defs.py` when the user then saves, so a
        mis-click costs nothing.
        """
        try:
            reverted = exercise_defs.revert_to_defaults(abbs)
        except RuntimeError as e:
            QMessageBox.warning(self, "Skill Ratings", str(e))
            return
        # Keep the rest of the table as typed; only the reverted rows change.
        current = self._all_entries(coerce=False)
        for abb in reverted if abbs is None else abbs:
            if abb in reverted:
                current[abb] = reverted[abb]
        self._load_entries(current)
        self._lbl_status.setText(f"{note} <b>Not saved yet</b> — press Save to apply.")

    def _on_revert_selected(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        abbs = [a for a in (self._abb_at(r) for r in rows) if a]
        if not abbs:
            QMessageBox.information(
                self, "Skill Ratings", "Select the exercise you want to reset first."
            )
            return
        self._revert(abbs, f"Restored {', '.join(abbs)} from the default baseline.")

    def _on_revert_all(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset All",
            "Restore the default skill ratings for all exercises?\n\n"
            "This loads the baseline into the table; nothing is written until you Save.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._revert(None, "Restored all exercises from the default baseline.")


class _DestinationsDelegate(QStyledItemDelegate):
    """Text editor for a connection cell, completing on exercise abbreviations.

    Destinations are edited as a comma-separated list. A completer is offered because
    the alternative — typing abbreviations from memory — is how a curriculum ends up
    pointing at an exercise that does not exist, which NAED-3 cannot report.
    """

    def __init__(self, parent=None, choices: list[str] | None = None):
        super().__init__(parent)
        self._choices = choices or []

    def set_choices(self, choices: list[str]) -> None:
        self._choices = choices

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        completer = QCompleter(self._choices, editor)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        editor.setCompleter(completer)
        editor.setPlaceholderText("e.g. pb2, mb2   (blank = no option)")
        return editor


class ExerciseProgressionWindow(QMainWindow):
    """Editor for the exercise progression graph (CURRICULA) in exercise_progression_defs.py.

    Saving rewrites the CURRICULA block inside that file, so it always holds the graph in
    force. Reverting restores from the read-only baseline in
    exercise_progression_defs_default.json.

    Each row is one source exercise; the four columns are the connection types NAED-3
    follows. Destinations are comma-separated abbreviations, or END to mark the end of
    training. Clearing all four cells removes the exercise from the curriculum.

    Every cell is validated as it is typed, and Save is refused while anything is wrong.
    That strictness is deliberate: a destination that does not exist makes NAED-3 answer
    "no option available" and advise keeping the subject where they are — identical to a
    deliberate dead end, with nothing logged. A typo here is invisible in use.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exercise Progression — Connections")
        self.resize(1180, 640)

        self.COLUMNS: list[tuple[str, str, bool]] = [
            ("__abb", "Exercise", False),
            ("__full", "Name", False),
        ] + [
            (t, CONNECTION_TYPE_LABELS.get(t, t), True)
            for t in CONNECTION_TYPES
        ]

        self._loading = False
        # Working copy of the whole graph, so switching curriculum does not discard
        # unsaved edits to the other one.
        self._graph: dict[str, dict] = exercise_progression_defs.normalize_curricula(CURRICULA)
        self._cell_problems: dict[tuple[int, int], str] = {}

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        intro = QLabel(
            "Which exercise a subject moves to next, per curriculum. NAED-3 reads this: "
            "<b>Upgrade</b> on a normal pass, <b>HP Upgrade</b> on a high-performance pass, "
            "<b>Downgrade</b> on a fail, <b>Lateral</b> for an equivalent alternative.<br>"
            "Enter destinations as comma-separated abbreviations (a single destination is "
            "forced; several let the tutor choose). <b>END</b> marks training complete. "
            "Clear all four cells to remove an exercise from the curriculum.<br>"
            "Saving rewrites <code>exercise_progression_defs.py</code>."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Curriculum:"))
        self._combo_cur = QComboBox()
        for key in self._graph:
            self._combo_cur.addItem(f"{self._graph[key]['label']} ({key})", userData=key)
        self._combo_cur.currentIndexChanged.connect(self._on_curriculum_changed)
        sel_row.addWidget(self._combo_cur)
        sel_row.addSpacing(16)
        sel_row.addWidget(QLabel("Label:"))
        self._edit_label = QLineEdit()
        self._edit_label.setMinimumWidth(240)
        self._edit_label.editingFinished.connect(self._on_label_edited)
        sel_row.addWidget(self._edit_label)
        sel_row.addStretch(1)
        self._btn_add = QPushButton("Add Exercise…")
        self._btn_add.clicked.connect(self._on_add_exercise)
        sel_row.addWidget(self._btn_add)
        self._btn_check = QPushButton("Check Graph")
        self._btn_check.clicked.connect(self._on_check)
        sel_row.addWidget(self._btn_check)
        layout.addLayout(sel_row)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([c[1] for c in self.COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table, stretch=1)

        # Colour each connection header the same way the Progress Graph draws its edges,
        # so the table and the diagram read as the same thing.
        self._delegates: dict[int, _DestinationsDelegate] = {}
        for col, (key, _header, _editable) in enumerate(self.COLUMNS):
            colour = CONNECTION_TYPE_COLORS.get(key)
            item = self._table.horizontalHeaderItem(col)
            if colour and item is not None:
                item.setForeground(QBrush(QColor(colour)))
            if key in CONNECTION_TYPES:
                delegate = _DestinationsDelegate(self._table)
                self._table.setItemDelegateForColumn(col, delegate)
                self._delegates[col] = delegate

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("Save")
        self._btn_save.clicked.connect(self._on_save)
        self._btn_reload = QPushButton("Discard Changes")
        self._btn_reload.clicked.connect(self._on_discard)
        self._btn_revert_row = QPushButton("Reset Selected Exercise")
        self._btn_revert_row.clicked.connect(self._on_revert_selected)
        self._btn_revert_all = QPushButton("Reset All to Defaults")
        self._btn_revert_all.clicked.connect(self._on_revert_all)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_reload)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_revert_row)
        btn_row.addWidget(self._btn_revert_all)
        layout.addLayout(btn_row)

        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet("color: #555555;")
        layout.addWidget(self._lbl_status)

        if not exercise_progression_defs.CURRICULA_DEFAULTS:
            tip = (
                f"Baseline file not found:\n{exercise_progression_defs.defaults_path()}\n"
                f"Resetting to defaults is unavailable until it is restored."
            )
            for btn in (self._btn_revert_row, self._btn_revert_all):
                btn.setEnabled(False)
                btn.setToolTip(tip)

        self._populate()
        align_window_top(self)

    # -- helpers ------------------------------------------------------------

    def _current_key(self) -> str:
        return str(self._combo_cur.currentData() or "")

    def _col_of(self, key: str) -> int:
        for col, (k, _h, _e) in enumerate(self.COLUMNS):
            if k == key:
                return col
        return -1

    def _abb_at(self, row: int) -> str:
        item = self._table.item(row, 0)
        return "" if item is None else str(item.data(Qt.UserRole) or "")

    @staticmethod
    def _parse_destinations(text: str) -> list[str]:
        """Split a cell into destination tokens, tolerating commas and stray spaces."""
        out: list[str] = []
        for raw in re.split(r"[,;\s]+", (text or "").strip()):
            if not raw:
                continue
            out.append(
                exercise_progression_defs.END_SENTINEL
                if raw.upper() == exercise_progression_defs.END_SENTINEL
                else raw.lower()
            )
        return out

    # -- population ---------------------------------------------------------

    def _populate(self) -> None:
        """Fill the table from the working copy for the selected curriculum."""
        key = self._current_key()
        cur = self._graph.get(key) or {"label": key, "connections": {}}
        connections = cur.get("connections") or {}

        choices = sorted(
            connections,
            key=lambda a: ((EXERCISE_DEFS.get(a) or {}).get("exerc_number") or 0, a),
        ) + [exercise_progression_defs.END_SENTINEL]
        for delegate in self._delegates.values():
            delegate.set_choices(choices)

        order = sorted(
            connections,
            key=lambda a: ((EXERCISE_DEFS.get(a) or {}).get("exerc_number") or 0, a),
        )

        self._loading = True
        try:
            self._edit_label.setText(str(cur.get("label") or ""))
            self._table.setRowCount(len(order))
            for row, abb in enumerate(order):
                links = connections.get(abb) or {}
                for col, (ckey, _header, editable) in enumerate(self.COLUMNS):
                    if ckey == "__abb":
                        item = QTableWidgetItem(abb)
                        item.setData(Qt.UserRole, abb)
                    elif ckey == "__full":
                        item = QTableWidgetItem(
                            str((EXERCISE_DEFS.get(abb) or {}).get("exerc_full") or "")
                        )
                    else:
                        item = QTableWidgetItem(", ".join(links.get(ckey) or []))
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setForeground(QBrush(QColor("#555555")))
                        item.setBackground(QBrush(QColor("#f0f0f0")))
                    self._table.setItem(row, col, item)
        finally:
            self._loading = False

        self._table.resizeColumnsToContents()
        header = self._table.horizontalHeader()
        for col, (ckey, _h, _e) in enumerate(self.COLUMNS):
            if ckey in CONNECTION_TYPES:
                header.setSectionResizeMode(col, QHeaderView.Stretch)
        self._refresh_marks()
        self._revalidate()

    def _table_to_graph(self) -> None:
        """Write the table back into the working copy for the selected curriculum."""
        key = self._current_key()
        if not key:
            return
        connections: dict[str, dict] = {}
        for row in range(self._table.rowCount()):
            abb = self._abb_at(row)
            if not abb:
                continue
            links: dict[str, list[str]] = {}
            for col, (ckey, _h, _e) in enumerate(self.COLUMNS):
                if ckey not in CONNECTION_TYPES:
                    continue
                item = self._table.item(row, col)
                dests = self._parse_destinations("" if item is None else item.text())
                if dests:
                    links[ckey] = dests
            # An exercise with no outgoing connections at all is dropped, which is how
            # the UI offers removal without a separate delete button.
            if links:
                connections[abb] = links
        self._graph[key] = {
            "label": self._edit_label.text().strip() or key,
            "connections": connections,
        }

    # -- validation ---------------------------------------------------------

    def _revalidate(self) -> None:
        """Mark bad cells and refresh the status line.

        Per-cell checks only — whole-graph checks (unreachable destinations, missing
        END) run on Save and via Check Graph, because they are noisy mid-edit.
        """
        key = self._current_key()
        valid_sources = set(self._graph.get(key, {}).get("connections") or {})
        self._cell_problems = {}

        self._loading = True
        try:
            for row in range(self._table.rowCount()):
                abb = self._abb_at(row)
                for col, (ckey, header, _e) in enumerate(self.COLUMNS):
                    if ckey not in CONNECTION_TYPES:
                        continue
                    item = self._table.item(row, col)
                    if item is None:
                        continue
                    dests = self._parse_destinations(item.text())
                    problem = ""
                    end = exercise_progression_defs.END_SENTINEL
                    if len(set(dests)) != len(dests):
                        problem = "the same destination is listed twice"
                    elif abb in dests:
                        problem = f"{abb} points at itself"
                    elif end in dests and len(dests) > 1:
                        problem = f"{end} cannot be combined with other destinations"
                    else:
                        unknown = [d for d in dests if d != end and d not in EXERCISE_DEFS]
                        if unknown:
                            problem = (
                                f"unknown exercise: {', '.join(unknown)}"
                            )
                        else:
                            stranded = [
                                d for d in dests
                                if d != end and d not in valid_sources
                            ]
                            if stranded:
                                problem = (
                                    f"{', '.join(stranded)} is not in this curriculum, so a "
                                    f"subject sent there could never progress"
                                )
                    if problem:
                        self._cell_problems[(row, col)] = f"{abb} / {header}: {problem}"
                        item.setBackground(QBrush(QColor("#ffd6d6")))
                        item.setToolTip(problem)
                    else:
                        item.setBackground(QBrush(QColor("#ffffff")))
                        item.setToolTip("")
        finally:
            self._loading = False

        self._btn_save.setEnabled(not self._cell_problems)
        self._update_status()

    def _update_status(self) -> None:
        bits: list[str] = []
        if self._cell_problems:
            first = next(iter(sorted(self._cell_problems.items())))[1]
            bits.append(
                f"<b style='color:#b00000;'>{len(self._cell_problems)} invalid cell(s)</b> "
                f"— {first}"
            )
        changed = exercise_progression_defs.changed_from_defaults(self._graph)
        if exercise_progression_defs.CURRICULA_DEFAULTS:
            total = sum(len(v) for v in changed.values())
            bits.append(f"{total} exercise(s) differ from default")
        else:
            bits.append("<b>no baseline file</b> — cannot reset to defaults")
        if self._graph != exercise_progression_defs.normalize_curricula(CURRICULA):
            bits.append("<b>unsaved changes</b>")
        self._lbl_status.setText(" &nbsp;|&nbsp; ".join(bits))

    def _refresh_marks(self) -> None:
        """Bold the abbreviation of any exercise that differs from the baseline."""
        key = self._current_key()
        changed = set(
            exercise_progression_defs.changed_from_defaults(self._graph).get(key, [])
        )
        self._loading = True
        try:
            for row in range(self._table.rowCount()):
                abb = self._abb_at(row)
                item = self._table.item(row, 0)
                if item is None:
                    continue
                is_changed = abb in changed
                font = item.font()
                font.setBold(is_changed)
                item.setFont(font)
                item.setText(f"{abb} *" if is_changed else abb)
                item.setToolTip("Differs from the default baseline" if is_changed else "")
        finally:
            self._loading = False

    # -- events -------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        self._table_to_graph()
        self._refresh_marks()
        self._revalidate()

    def _on_label_edited(self) -> None:
        if self._loading:
            return
        self._table_to_graph()
        self._update_status()

    def _on_curriculum_changed(self) -> None:
        if self._loading:
            return
        self._populate()

    # -- actions ------------------------------------------------------------

    def _on_add_exercise(self) -> None:
        key = self._current_key()
        existing = set(self._graph.get(key, {}).get("connections") or {})
        available = sorted(
            (a for a in EXERCISE_DEFS if a not in existing),
            key=lambda a: ((EXERCISE_DEFS.get(a) or {}).get("exerc_number") or 0, a),
        )
        if not available:
            QMessageBox.information(
                self, "Exercise Progression",
                "Every exercise in the catalogue is already in this curriculum.",
            )
            return
        choices = [
            f"{a} — {(EXERCISE_DEFS.get(a) or {}).get('exerc_full', '')}" for a in available
        ]
        picked, ok = QInputDialog.getItem(
            self, "Add Exercise", "Add to this curriculum:", choices, 0, False
        )
        if not ok or not picked:
            return
        abb = picked.split(" — ")[0].strip()

        # Seeded with no connections; it becomes real once the user fills a cell in.
        # Until then it is a dead end, which _revalidate will flag on anything
        # pointing at it.
        cur = self._graph.setdefault(key, {"label": key, "connections": {}})
        cur["connections"][abb] = {}
        self._graph[key] = {
            "label": cur.get("label") or key,
            "connections": dict(cur["connections"]),
        }
        self._populate_preserving(abb)

    def _populate_preserving(self, focus_abb: str) -> None:
        """Repopulate, then select and scroll to `focus_abb`.

        `normalize_curricula` drops an exercise with no connections, so a freshly added
        row is inserted directly into the table instead of round-tripping through it.
        """
        key = self._current_key()
        connections = dict(self._graph.get(key, {}).get("connections") or {})
        connections.setdefault(focus_abb, {})
        order = sorted(
            connections,
            key=lambda a: ((EXERCISE_DEFS.get(a) or {}).get("exerc_number") or 0, a),
        )
        self._loading = True
        try:
            self._table.setRowCount(len(order))
            for row, abb in enumerate(order):
                links = connections.get(abb) or {}
                for col, (ckey, _h, editable) in enumerate(self.COLUMNS):
                    if ckey == "__abb":
                        item = QTableWidgetItem(abb)
                        item.setData(Qt.UserRole, abb)
                    elif ckey == "__full":
                        item = QTableWidgetItem(
                            str((EXERCISE_DEFS.get(abb) or {}).get("exerc_full") or "")
                        )
                    else:
                        item = QTableWidgetItem(", ".join(links.get(ckey) or []))
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setForeground(QBrush(QColor("#555555")))
                        item.setBackground(QBrush(QColor("#f0f0f0")))
                    self._table.setItem(row, col, item)
                if abb == focus_abb:
                    self._table.selectRow(row)
                    self._table.scrollToItem(self._table.item(row, 0))
        finally:
            self._loading = False
        self._refresh_marks()
        self._revalidate()

    def _on_check(self) -> None:
        """Report whole-graph problems, including ones Save would refuse."""
        self._table_to_graph()
        problems = exercise_progression_defs.check_progression_consistency(self._graph)
        asym = exercise_progression_defs.asymmetric_laterals(self._graph)

        html = ""
        if self._cell_problems:
            html += "<b>Invalid cells</b><ul>" + "".join(
                f"<li>{p}</li>" for _k, p in sorted(self._cell_problems.items())
            ) + "</ul>"
        if problems:
            html += "<b>Graph problems (Save is refused)</b><ul>" + "".join(
                f"<li>{p}</li>" for p in problems
            ) + "</ul>"
        if asym:
            html += (
                "<b>One-way laterals</b><br>"
                "<i>Not errors. NAED-3 follows laterals as written, but the peer-comparison "
                "equivalence classes treat them as two-way, so these behave differently in "
                "the two places.</i><ul>"
                + "".join(f"<li>{a}</li>" for a in asym)
                + "</ul>"
            )
        if not html:
            html = "<b>No problems found.</b><br>Every destination exists and can progress."

        box = QMessageBox(self)
        box.setWindowTitle("Exercise Progression — Check")
        box.setTextFormat(Qt.RichText)
        box.setText(html)
        box.exec()

    def _on_save(self) -> None:
        self._table_to_graph()
        if self._cell_problems:
            QMessageBox.warning(
                self,
                "Exercise Progression",
                "Cannot save while cells are invalid:\n\n"
                + "\n".join(p for _k, p in sorted(self._cell_problems.items())),
            )
            return
        try:
            path = exercise_progression_defs.save_curricula(self._graph)
        except (OSError, RuntimeError, ValueError) as e:
            QMessageBox.critical(
                self,
                "Exercise Progression",
                f"Could not save — nothing was written:\n\n{e}",
            )
            return

        self._graph = exercise_progression_defs.normalize_curricula(CURRICULA)
        changed = exercise_progression_defs.changed_from_defaults(self._graph)
        self._populate()
        QMessageBox.information(
            self,
            "Exercise Progression",
            f"Progression graph written to:\n{path}\n\n"
            f"{sum(len(v) for v in changed.values())} exercise(s) now differ from the "
            f"default baseline.\n\n"
            f"Re-open any Recommendations or Progress Graph window to see the change.",
        )

    def _on_discard(self) -> None:
        self._graph = exercise_progression_defs.normalize_curricula(CURRICULA)
        self._populate()

    def _revert(self, abbs: list[str] | None, note: str) -> None:
        """Pull baseline values into the table without writing anything."""
        baseline = exercise_progression_defs.revert_to_defaults()
        if not baseline:
            QMessageBox.warning(
                self,
                "Exercise Progression",
                f"No baseline file at:\n{exercise_progression_defs.defaults_path()}",
            )
            return
        key = self._current_key()
        if abbs is None:
            self._graph = baseline
        else:
            base_conns = (baseline.get(key) or {}).get("connections") or {}
            cur = self._graph.setdefault(key, {"label": key, "connections": {}})
            conns = dict(cur.get("connections") or {})
            for abb in abbs:
                if abb in base_conns:
                    conns[abb] = base_conns[abb]
                else:
                    conns.pop(abb, None)
            self._graph[key] = {"label": cur.get("label") or key, "connections": conns}
        self._populate()
        self._lbl_status.setText(f"{note} <b>Not saved yet</b> — press Save to apply.")

    def _on_revert_selected(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        abbs = [a for a in (self._abb_at(r) for r in rows) if a]
        if not abbs:
            QMessageBox.information(
                self, "Exercise Progression", "Select the exercise you want to reset first."
            )
            return
        self._revert(abbs, f"Restored {', '.join(abbs)} from the default baseline.")

    def _on_revert_all(self) -> None:
        reply = QMessageBox.question(
            self,
            "Reset All",
            "Restore the default progression graph for every curriculum?\n\n"
            "This loads the baseline into the table; nothing is written until you Save.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._revert(None, "Restored all curricula from the default baseline.")


class ProficiencyValuesWindow(QMainWindow):
    """Window showing proficiency threshold values for each exercise's metrics.

    When `fixed_exercise` is provided, the exercise selector is hidden and only
    that exercise is displayed. When `read_only` is True, the Edit Values button
    is hidden.
    """

    def __init__(self, parent=None, fixed_exercise: str | None = None, read_only: bool = False):
        super().__init__(parent)
        self.fixed_exercise = (fixed_exercise or "").strip()
        self.read_only = read_only
        self._edit_window: 'EditProficiencyWindow | None' = None

        if self.fixed_exercise:
            ex_full = EXERCISE_DEFS.get(self.fixed_exercise, {}).get("exerc_full", self.fixed_exercise)
            self.setWindowTitle(f"Proficiency Values — {self.fixed_exercise} ({ex_full})")
            self.resize(520, 320)
        else:
            self.setWindowTitle("Proficiency Values")
            self.resize(520, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Exercise selector (hidden in fixed-exercise mode)
        self._sel_container = QWidget()
        _sel_row = QHBoxLayout(self._sel_container)
        _sel_row.setContentsMargins(0, 0, 0, 0)
        _sel_row.addWidget(QLabel("Exercise:"))
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_exercise_changed)
        _sel_row.addWidget(self._combo, 1)
        layout.addWidget(self._sel_container)

        if self.fixed_exercise:
            self._sel_container.setVisible(False)

        # Table
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        # Edit button (hidden in read-only mode)
        btn_row = QHBoxLayout()
        self._btn_edit = QPushButton("Edit Values")
        self._btn_edit.clicked.connect(self._open_edit_window)
        btn_row.addWidget(self._btn_edit)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        if self.read_only:
            self._btn_edit.setVisible(False)

        self._populate_combo()

    def _populate_combo(self):
        from exercise_proficiency_scores import PROFICIENCY_BASELINES
        self._baselines = PROFICIENCY_BASELINES

        if self.fixed_exercise:
            if self.fixed_exercise in self._baselines:
                full = EXERCISE_DEFS.get(self.fixed_exercise, {}).get("exerc_full", "")
                label = f"{self.fixed_exercise} — {full}" if full else self.fixed_exercise
                self._combo.addItem(label, self.fixed_exercise)
                self._combo.setCurrentIndex(0)
                self._on_exercise_changed()
            else:
                self._combo.clear()
                self._show_no_baseline(self.fixed_exercise)
            return

        # Build sorted list: "abbreviation — Full Name"
        items: list[tuple[str, str]] = []
        for abb in sorted(self._baselines.keys()):
            full = EXERCISE_DEFS.get(abb, {}).get("exerc_full", "")
            label = f"{abb} — {full}" if full else abb
            items.append((abb, label))
        for abb, label in items:
            self._combo.addItem(label, abb)

    def _show_no_baseline(self, abb: str):
        self._table.clear()
        self._table.setColumnCount(1)
        self._table.setHorizontalHeaderLabels(["Proficiency Values"])
        self._table.setRowCount(1)
        self._table.setItem(0, 0, QTableWidgetItem(f"No proficiency baseline for '{abb}'"))
        self._table.resizeColumnsToContents()

    def _on_exercise_changed(self):
        abb = self._combo.currentData()
        if not abb:
            return
        metrics = self._baselines.get(abb, {})
        if not metrics:
            self._show_no_baseline(abb)
            return

        self._table.clear()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["Metric", "Proficiency", "Direction"])
        self._table.setRowCount(len(metrics))

        for row, (mc, vals) in enumerate(sorted(metrics.items())):
            full_name = _METRIC_ABB_TO_FULL.get(mc, mc)
            prof = vals.get("prof_raw", "")
            direction = vals.get("direction", "")
            self._table.setItem(row, 0, QTableWidgetItem(f"{mc} — {full_name}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{prof}"))
            self._table.setItem(row, 2, QTableWidgetItem(direction))

        self._table.resizeColumnsToContents()

    def _open_edit_window(self):
        if self._edit_window is not None and self._edit_window.isVisible():
            self._edit_window.raise_()
            self._edit_window.activateWindow()
            return
        if not _confirm_baseline_edit(self):
            return
        self._edit_window = EditProficiencyWindow(parent=self)
        self._edit_window.show()


# ---------------------------------------------------------------------------
#  Edit Proficiency Window
# ---------------------------------------------------------------------------

BASELINES_MODULE_RELPATH = "exercise_proficiency_scores.py"


def _flex_vr_xml_dir() -> str:
    return os.path.join(_script_dir(), "Flex_VR_XML")


def _simulator_exports_dir() -> str:
    """Configured simulator export folder, or "" if the site has not set one."""
    return str(load_config().get("simulator_user_exports_dir") or "").strip()


def _template_xml_path() -> str:
    """Absolute path of the curriculum XML the export is based on."""
    name = _config_str("template_xml")
    if os.path.isabs(name):
        return name
    return os.path.join(_flex_vr_xml_dir(), name)


def _next_xml_filename() -> str:
    """Generate RSAC_YYYY_MMM_DD_x.xml with serialized letter for today."""
    from datetime import date
    today = date.today()
    prefix = f"RSAC_{today.year}_{today.strftime('%b')}_{today.day:02d}"
    # Check every output folder in use for existing files with today's prefix
    existing: set[str] = set()
    for d in (_flex_vr_xml_dir(), _simulator_exports_dir()):
        if not d:
            continue
        try:
            for f in os.listdir(d):
                if f.startswith(prefix) and f.endswith(".xml"):
                    existing.add(f)
        except Exception:
            pass
    # Find next available letter
    for letter in "abcdefghijklmnopqrstuvwxyz":
        candidate = f"{prefix}_{letter}.xml"
        if candidate not in existing:
            return candidate
    return f"{prefix}_z.xml"


_BASELINE_EDIT_CONFIRM_WORD = "CHANGE"


def _baselines_module_path() -> str:
    return os.path.join(_script_dir(), BASELINES_MODULE_RELPATH)


def _rewrite_baseline_values(content: str, emet_id, new_vals: dict) -> str:
    """Replace mean/stddev/prof_raw on the baseline line carrying this emet_id.

    Anchored on emet_id because that is the only value unique to the line.

    The anchor deliberately does NOT assume emet_id is the last key in the entry.
    It used to require a closing brace immediately after it, so adding any further
    setting to those lines — norm_max, or anything later — made every replacement
    fail to match and the save silently became a no-op.
    """
    pattern = (
        r'("mean": )[^,]+(, "stddev": )[^,]+(, "prof_raw": )[^,]+'
        rf'(.*?"emet_id_RSAC_2026": {emet_id}\b)'
    )

    def _replacer(m):
        return (
            f'{m.group(1)}{new_vals["mean"]}'
            f'{m.group(2)}{new_vals["stddev"]}'
            f'{m.group(3)}{new_vals["prof_raw"]}'
            f'{m.group(4)}'
        )

    return re.sub(pattern, _replacer, content)


def _confirm_baseline_edit(parent: QWidget) -> bool:
    """Require an explicit typed confirmation before proficiency values are edited.

    Editing rewrites PROFICIENCY_BASELINES, which every PASS / proficiency
    decision in the app depends on, and overwrites the module that defines it.
    A timestamped backup is taken before that write, but the new thresholds
    still apply to all later analyses, so the action must be deliberate.
    """
    text, ok = QInputDialog.getText(
        parent,
        "Confirm Proficiency Edit",
        "Editing proficiency values changes the thresholds that define a PASS\n"
        "for every subject, in this session and in all future analyses.\n\n"
        f"{BASELINES_MODULE_RELPATH} will be rewritten on disk; a timestamped\n"
        "backup is created first.\n\n"
        f"Type {_BASELINE_EDIT_CONFIRM_WORD} to continue:",
    )
    if not ok:
        return False
    if text.strip() != _BASELINE_EDIT_CONFIRM_WORD:
        QMessageBox.warning(
            parent, "Not Confirmed",
            "Proficiency values were not changed.\n\n"
            f"Type {_BASELINE_EDIT_CONFIRM_WORD} exactly to confirm."
        )
        return False
    return True


def _warn_baselines_mirror_simulator(parent: QWidget) -> bool:
    """Warn, before the editor opens, that these values mirror the simulator's own.

    The proficiency table is not this app's policy — it is a *copy* of how the
    simulator is configured. The simulator scores attempts with the original; this
    app re-derives those scores with the copy. Editing here does not change the
    simulator, so the two can be made to disagree, and when they do every score and
    PASS decision this app produces is wrong while looking entirely normal. Nothing
    downstream can detect it, which is why the warning is up front rather than at
    save time.

    Returns False if the user declines, in which case the editor does not open.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Warning)
    box.setWindowTitle("Values Must Match the Simulator")
    box.setTextFormat(Qt.RichText)
    box.setText(
        "<b>These values must reflect the parameters set in the simulator.</b>"
    )
    box.setInformativeText(
        "The proficiency table is a copy of the simulator's own configuration. "
        "The simulator scores each attempt with the original; this app re-derives "
        "those scores with the copy.<br><br>"
        "<b>Editing here does not change the simulator.</b> If the two disagree, "
        "every score and PASS decision this app produces will differ from the "
        "simulator's — and nothing on screen will show that it is happening.<br><br>"
        "Change the simulator first, then mirror the change here. "
        "<b>Norm Max</b> especially must equal the simulator's normalised range for "
        "that metric.<br><br>"
        "Continue?"
    )
    box.setStandardButtons(QMessageBox.Cancel)
    proceed = box.addButton("Continue", QMessageBox.AcceptRole)
    box.setDefaultButton(QMessageBox.Cancel)
    box.exec()
    return box.clickedButton() is proceed


def _backup_baselines_module(src_path: str) -> str:
    """Copy the baselines module to a timestamped .bak beside it.

    Returns the backup path, or "" if the copy failed — in which case the
    caller must not overwrite the original.
    """
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{src_path}.{stamp}.bak"
    try:
        shutil.copy2(src_path, backup_path)
    except Exception:
        return ""
    return backup_path


def _recalc_metric(old_mean: float, old_stddev: float, new_prof_raw: float,
                   best_mult: int, worst_mult: int) -> dict[str, float]:
    """Recalculate mean, stddev, best_raw, worst_raw from new prof_raw.

    Keeps mean:stddev ratio; prof_raw = mean + 1*stddev for lower direction.
    """
    old_prof = old_mean + old_stddev  # prof_multiplier is always 1
    if old_prof == 0:
        # Edge case: both were zero, set new mean = new_prof_raw, stddev = 0
        new_mean = round(new_prof_raw, 2)
        new_stddev = 0.0
    else:
        scale = new_prof_raw / old_prof
        new_mean = round(old_mean * scale, 2)
        new_stddev = round(old_stddev * scale, 2)

    best_raw = round(new_mean + best_mult * new_stddev, 2)
    if best_raw < 0:
        best_raw = 0.0
    worst_raw = round(new_mean + worst_mult * new_stddev, 2)
    new_prof = round(new_mean + new_stddev, 2)

    return {
        "mean": new_mean,
        "stddev": new_stddev,
        "prof_raw": new_prof,
        "best_raw": best_raw,
        "worst_raw": worst_raw,
    }


def _generate_updated_xml(baselines: dict) -> str:
    """Read the original XML and replace mean/stddev/prof_raw/best_raw/worst_raw
    for each emet_id found in PROFICIENCY_BASELINES. Returns the XML string."""
    original = _template_xml_path()
    if not os.path.isfile(original):
        raise FileNotFoundError(
            f"Template curriculum XML not found:\n{original}\n\n"
            f"Set \"template_xml\" in {os.path.basename(_config_path())} to the "
            "curriculum XML exported from your simulator."
        )

    with open(original, "r", encoding="utf-8") as f:
        content = f.read()

    # Build emet_id -> new values lookup
    emet_lookup: dict[int, dict] = {}
    for _ex, metrics in baselines.items():
        for _mc, vals in metrics.items():
            eid = vals.get("emet_id_RSAC_2026")
            if eid is None:
                continue
            emet_lookup[int(eid)] = vals

    def _replace_metric_line(line: str) -> str:
        """If line is a CurriculumMetric with a known emet_id, update values."""
        if "CurriculumMetric" not in line or "emet_id=" not in line:
            return line
        m = re.search(r'emet_id="(\d+)"', line)
        if not m:
            return line
        eid = int(m.group(1))
        if eid not in emet_lookup:
            return line
        vals = emet_lookup[eid]
        mean = vals["mean"]
        stddev = vals["stddev"]
        prof_raw = vals["prof_raw"]
        best_mult = vals.get("best_multiplier", -3)
        worst_mult = vals.get("worst_multiplier", 5)
        best_raw = round(mean + best_mult * stddev, 2)
        if best_raw < 0:
            best_raw = 0.0
        worst_raw = round(mean + worst_mult * stddev, 2)

        # Format helpers — strip trailing zeros but keep at least one decimal context
        def _fmt(v: float) -> str:
            s = f"{v:.2f}"
            # Remove unnecessary trailing zeros: 67.50 -> 67.5, 0.00 -> 0
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            return s

        line = re.sub(r'mean="[^"]*"', f'mean="{_fmt(mean)}"', line)
        line = re.sub(r'stddev="[^"]*"', f'stddev="{_fmt(stddev)}"', line)
        line = re.sub(r'prof_raw="[^"]*"', f'prof_raw="{_fmt(prof_raw)}"', line)
        line = re.sub(r'best_raw="[^"]*"', f'best_raw="{_fmt(best_raw)}"', line)
        line = re.sub(r'worst_raw="[^"]*"', f'worst_raw="{_fmt(worst_raw)}"', line)
        return line

    lines = content.split("\n")
    new_lines = [_replace_metric_line(l) for l in lines]
    return "\n".join(new_lines)


class EditProficiencyWindow(QMainWindow):
    """Allows editing proficiency values, recalculating mean/stddev, and exporting XML."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Proficiency Values")
        self.resize(620, 500)

        # Materialize rsac_config.json so the export paths can be pointed at
        # this site's simulator without editing the source.
        ensure_config_file()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Exercise selector
        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Exercise:"))
        self._combo = QComboBox()
        self._combo.currentIndexChanged.connect(self._on_exercise_changed)
        sel_row.addWidget(self._combo, 1)
        layout.addLayout(sel_row)

        # Table with Edit buttons
        self._table = QTableWidget()
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.NoSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table)

        # Save & Export button
        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("Save && Export XML")
        self._btn_save.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        self._btn_save.clicked.connect(self._save_and_export)
        self._btn_save.setEnabled(False)
        btn_row.addWidget(self._btn_save)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self._pending_changes: dict[str, dict[str, dict]] = {}  # {exerc_abb: {metric: new_vals}}
        self._populate_combo()

    def _populate_combo(self):
        from exercise_proficiency_scores import PROFICIENCY_BASELINES
        self._baselines = PROFICIENCY_BASELINES
        items: list[tuple[str, str]] = []
        for abb in sorted(self._baselines.keys()):
            full = EXERCISE_DEFS.get(abb, {}).get("exerc_full", "")
            label = f"{abb} — {full}" if full else abb
            items.append((abb, label))
        for abb, label in items:
            self._combo.addItem(label, abb)

    def _on_exercise_changed(self):
        self._refresh_table()

    def _refresh_table(self):
        abb = self._combo.currentData()
        if not abb:
            return
        metrics = self._baselines.get(abb, {})

        self._table.clear()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["Metric", "Proficiency", "Direction", ""])
        self._table.setRowCount(len(metrics))

        for row, (mc, vals) in enumerate(sorted(metrics.items())):
            full_name = _METRIC_ABB_TO_FULL.get(mc, mc)
            prof = vals.get("prof_raw", 0)
            direction = vals.get("direction", "")
            self._table.setItem(row, 0, QTableWidgetItem(f"{mc} — {full_name}"))
            self._table.setItem(row, 1, QTableWidgetItem(f"{prof}"))
            self._table.setItem(row, 2, QTableWidgetItem(direction))

            btn = QPushButton("Edit")
            btn.setFixedWidth(60)
            btn.clicked.connect(lambda checked, a=abb, m=mc: self._edit_metric(a, m))
            self._table.setCellWidget(row, 3, btn)

        self._table.resizeColumnsToContents()
        self._table.setColumnWidth(3, 70)

    def _edit_metric(self, exerc_abb: str, metric: str):
        vals = self._baselines[exerc_abb][metric]
        current_prof = vals.get("prof_raw", 0)
        full_name = _METRIC_ABB_TO_FULL.get(metric, metric)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit {metric} — {full_name}")
        dlg.setMinimumWidth(360)
        dlg_layout = QVBoxLayout(dlg)

        dlg_layout.addWidget(QLabel(
            f"<b>{exerc_abb}</b> / <b>{metric}</b><br>"
            f"Current proficiency: <b>{current_prof}</b>"
        ))

        # Radio buttons for mode
        grp = QButtonGroup(dlg)
        rb_abs = QRadioButton("Set absolute value")
        rb_pct = QRadioButton("Change by percentage")
        rb_abs.setChecked(True)
        grp.addButton(rb_abs)
        grp.addButton(rb_pct)
        dlg_layout.addWidget(rb_abs)
        dlg_layout.addWidget(rb_pct)

        # Input field
        input_row = QHBoxLayout()
        input_row.addWidget(QLabel("Value:"))
        txt_val = QLineEdit()
        txt_val.setPlaceholderText("e.g. 75.5 or +10 or -15")
        input_row.addWidget(txt_val)
        dlg_layout.addLayout(input_row)

        hint = QLabel("<small>For percentage: use +10 for +10%, -15 for -15%</small>")
        hint.setStyleSheet("color: #666;")
        dlg_layout.addWidget(hint)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        dlg_layout.addWidget(btn_box)

        if dlg.exec() != QDialog.Accepted:
            return

        text = txt_val.text().strip()
        if not text:
            return

        try:
            if rb_pct.isChecked():
                pct = float(text)
                new_prof = round(current_prof * (1 + pct / 100), 2)
            else:
                new_prof = round(float(text), 2)
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
            return

        if new_prof < 0:
            QMessageBox.warning(self, "Invalid Value", "Proficiency cannot be negative.")
            return

        # Recalculate
        old_mean = vals["mean"]
        old_stddev = vals["stddev"]
        best_mult = vals.get("best_multiplier", -3)
        worst_mult = vals.get("worst_multiplier", 5)

        recalced = _recalc_metric(old_mean, old_stddev, new_prof, best_mult, worst_mult)

        # Update PROFICIENCY_BASELINES in memory
        vals["mean"] = recalced["mean"]
        vals["stddev"] = recalced["stddev"]
        vals["prof_raw"] = recalced["prof_raw"]

        # Track pending changes
        if exerc_abb not in self._pending_changes:
            self._pending_changes[exerc_abb] = {}
        self._pending_changes[exerc_abb][metric] = recalced

        self._btn_save.setEnabled(True)
        self._refresh_table()

    def _save_and_export(self):
        if not self._pending_changes:
            QMessageBox.information(self, "No Changes", "No metrics have been edited.")
            return

        # Generate XML
        try:
            xml_content = _generate_updated_xml(self._baselines)
        except Exception as exc:
            QMessageBox.critical(self, "XML Generation Error", str(exc))
            return

        filename = _next_xml_filename()

        # Save to ./Flex_VR_XML (relative to script)
        xml_dir = _flex_vr_xml_dir()
        os.makedirs(xml_dir, exist_ok=True)
        local_path = os.path.join(xml_dir, filename)

        try:
            with open(local_path, "w", encoding="utf-8") as f:
                f.write(xml_content)
        except Exception as exc:
            QMessageBox.critical(self, "Save Error", f"Could not save local copy:\n{exc}")
            return

        # Save to the simulator's export folder, if this site configured one
        sim_dir = _simulator_exports_dir()
        if sim_dir:
            sim_path = os.path.join(sim_dir, filename)
            try:
                with open(sim_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
            except Exception as exc:
                QMessageBox.warning(
                    self, "Simulator Save Warning",
                    f"Saved local copy OK:\n{local_path}\n\n"
                    f"But could NOT write to the simulator folder:\n{sim_dir}\n\n{exc}"
                )
                return
            sim_line = f"Simulator: {sim_path}<br>"
        else:
            sim_line = (
                "Simulator: not written — "
                f"\"simulator_user_exports_dir\" is not set in "
                f"{os.path.basename(_config_path())}<br>"
            )

        # Also update the .py source file with new values
        backup_path = self._update_baselines_source_file()
        if backup_path is None:
            return
        if backup_path:
            backup_line = f"Baselines backup: {backup_path}<br>"
        else:
            backup_line = ""

        changes_summary = []
        for ex, mets in sorted(self._pending_changes.items()):
            for mc, v in sorted(mets.items()):
                changes_summary.append(f"  {ex}/{mc}: prof_raw={v['prof_raw']}")

        self._pending_changes.clear()
        self._btn_save.setEnabled(False)

        QMessageBox.information(
            self, "Export Complete",
            f"XML saved successfully as <b>{filename}</b><br><br>"
            f"Local copy: {local_path}<br>"
            f"{sim_line}"
            f"{backup_line}<br>"
            f"Changes:<br>{'<br>'.join(changes_summary)}"
        )

    def _update_baselines_source_file(self) -> str | None:
        """Rewrite the baselines module with the new mean/stddev/prof_raw values.

        A timestamped backup is taken first; the original is left untouched if
        that fails. Returns the backup path on success, "" if there was nothing
        to update, or None if the rewrite was aborted (caller should stop).
        """
        src_path = _baselines_module_path()
        if not os.path.isfile(src_path):
            return ""

        try:
            with open(src_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as exc:
            QMessageBox.critical(
                self, "Baselines Not Updated",
                f"Could not read:\n{src_path}\n\n{exc}\n\n"
                "The XML was written but the proficiency values on disk are unchanged."
            )
            return None

        backup_path = _backup_baselines_module(src_path)
        if not backup_path:
            QMessageBox.critical(
                self, "Baselines Not Updated",
                f"Could not create a backup of:\n{src_path}\n\n"
                "Nothing was overwritten. Check the folder is writable and retry."
            )
            return None

        for exerc_abb, mets in self._pending_changes.items():
            for metric, new_vals in mets.items():
                # Use emet_id to uniquely identify the line in the source file
                eid = self._baselines[exerc_abb][metric].get("emet_id_RSAC_2026")
                if eid is None:
                    continue
                content = _rewrite_baseline_values(content, eid, new_vals)

        try:
            with open(src_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as exc:
            QMessageBox.critical(
                self, "Baselines Not Updated",
                f"Could not write:\n{src_path}\n\n{exc}\n\n"
                f"Restore from the backup if needed:\n{backup_path}"
            )
            return None

        return backup_path


class _DirectionDelegate(QStyledItemDelegate):
    """Drop-down for the direction column.

    Restricted to a list because the value is compared literally in `calc_score`:
    anything other than "lower" scores as "higher", so a typo silently inverts the
    metric instead of failing.
    """

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        from exercise_proficiency_scores import VALID_DIRECTIONS

        combo.addItems(list(VALID_DIRECTIONS))
        return combo

    def setEditorData(self, editor: QComboBox, index) -> None:
        idx = editor.findText(str(index.data(Qt.DisplayRole) or "").strip())
        editor.setCurrentIndex(max(0, idx))
        editor.showPopup()

    def setModelData(self, editor: QComboBox, model, index) -> None:
        model.setData(index, editor.currentText(), Qt.DisplayRole)


class ProficiencyBaselinesWindow(QMainWindow):
    """Editor for the proficiency table (PROFICIENCY_BASELINES).

    Saving rewrites the marked block in `exercise_proficiency_scores.py`, so that
    file always holds the values in force. Reverting restores from the read-only
    snapshot in `exercise_proficiency_scores_default.json`.

    One row per metric of the selected exercise. These values decide what a PASS is
    for every subject, in this session and in every later analysis, which is why the
    window validates as you type and refuses to save anything invalid:

      - `direction` is compared literally in `calc_score`, so a typo does not fail,
        it inverts the metric.
      - `norm_max` is the simulator's normalised range for that metric. It must
        match the simulator, or every score read from an export is mis-scaled. It
        also sets the PASS mark (half of it) and the exercise's floor and ceiling.
      - `Simulator ID` is shown read-only: it identifies the metric in the XML
        export, and changing it would silently retarget that export.
    """

    # (field key, header, editable) — "__code"/"__name" are display-only.
    COLUMNS: list[tuple[str, str, bool]] = [
        ("__code", "Code", False),
        ("__name", "Metric", False),
        ("mean", "Mean", True),
        ("stddev", "Std Dev", True),
        ("prof_raw", "Proficiency (raw)", True),
        ("direction", "Direction", True),
        ("best_multiplier", "Best × SD", True),
        ("worst_multiplier", "Worst × SD", True),
        ("norm_max", "Norm Max", True),
        ("emet_id_RSAC_2026", "Simulator ID", False),
    ]

    _FLOAT_COLS = frozenset({"mean", "stddev", "prof_raw"})
    _INT_COLS = frozenset({"best_multiplier", "worst_multiplier", "norm_max"})

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Proficiency Values — PROFICIENCY_BASELINES")
        self.resize(1120, 620)

        import exercise_proficiency_scores as eps

        self._eps = eps
        self._loading = False
        # Working copy, so nothing touches the live table until Save succeeds.
        self._baselines: dict = eps.normalize_baselines(eps.PROFICIENCY_BASELINES)
        self._cell_problems: dict[tuple[int, int], str] = {}

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        warning = QLabel(
            "⚠ <b>These values must reflect the parameters set in the simulator.</b> "
            "They are a copy of its configuration, not a setting of this app — "
            "editing them here does not change the simulator, and if the two "
            "disagree every score and PASS decision shown elsewhere is wrong with "
            "no visible sign of it."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet(
            "background: #fff3cd; color: #6b4f00; border: 1px solid #e0c060;"
            "border-radius: 4px; padding: 7px;"
        )
        layout.addWidget(warning)

        intro = QLabel(
            "The values that define a PASS. <b>Mean</b> and <b>Std Dev</b> are the "
            "reference cohort's; <b>Proficiency (raw)</b> is the threshold in the "
            "metric's own unit; <b>Direction</b> says whether lower or higher raw "
            "values are better; the multipliers set the best/worst ends of the "
            "scoring range.<br>"
            "<b>Norm Max</b> must equal the simulator's normalised range for that "
            "metric — it sets the PASS mark at half its value, and the exercise's "
            "score floor and ceiling.<br>"
            "Saving rewrites <code>exercise_proficiency_scores.py</code>."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        sel_row = QHBoxLayout()
        sel_row.addWidget(QLabel("Exercise:"))
        self._combo = QComboBox()
        for abb in self._baselines:
            full = (EXERCISE_DEFS.get(abb) or {}).get("exerc_full", "")
            self._combo.addItem(f"{abb} — {full}" if full else abb, userData=abb)
        self._combo.currentIndexChanged.connect(self._on_exercise_changed)
        sel_row.addWidget(self._combo, 1)
        sel_row.addSpacing(16)
        self._btn_check = QPushButton("Check Table")
        self._btn_check.clicked.connect(self._on_check)
        sel_row.addWidget(self._btn_check)
        layout.addLayout(sel_row)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels([c[1] for c in self.COLUMNS])
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table, stretch=1)

        col = self._col_of("direction")
        if col >= 0:
            self._direction_delegate = _DirectionDelegate(self._table)
            self._table.setItemDelegateForColumn(col, self._direction_delegate)

        btn_row = QHBoxLayout()
        self._btn_save = QPushButton("Save")
        self._btn_save.clicked.connect(self._on_save)
        self._btn_discard = QPushButton("Discard Changes")
        self._btn_discard.clicked.connect(self._on_discard)
        self._btn_revert_row = QPushButton("Reset Selected Metric")
        self._btn_revert_row.clicked.connect(self._on_revert_selected)
        self._btn_revert_ex = QPushButton("Reset This Exercise")
        self._btn_revert_ex.clicked.connect(self._on_revert_exercise)
        self._btn_revert_all = QPushButton("Reset All to Defaults")
        self._btn_revert_all.clicked.connect(self._on_revert_all)
        btn_row.addWidget(self._btn_save)
        btn_row.addWidget(self._btn_discard)
        btn_row.addStretch(1)
        btn_row.addWidget(self._btn_revert_row)
        btn_row.addWidget(self._btn_revert_ex)
        btn_row.addWidget(self._btn_revert_all)
        layout.addLayout(btn_row)

        self._lbl_status = QLabel("")
        self._lbl_status.setWordWrap(True)
        self._lbl_status.setStyleSheet("color: #555555;")
        layout.addWidget(self._lbl_status)

        if not eps.BASELINES_DEFAULTS:
            tip = (
                f"Baseline snapshot not found:\n{eps.defaults_path()}\n"
                f"Resetting to defaults is unavailable until it is restored."
            )
            for btn in (self._btn_revert_row, self._btn_revert_ex, self._btn_revert_all):
                btn.setEnabled(False)
                btn.setToolTip(tip)

        self._populate()
        align_window_top(self)

    # -- helpers ------------------------------------------------------------

    def _current_abb(self) -> str:
        return str(self._combo.currentData() or "")

    def _col_of(self, key: str) -> int:
        for col, (k, _h, _e) in enumerate(self.COLUMNS):
            if k == key:
                return col
        return -1

    def _code_at(self, row: int) -> str:
        item = self._table.item(row, 0)
        return "" if item is None else str(item.data(Qt.UserRole) or "")

    @staticmethod
    def _fmt(value) -> str:
        if isinstance(value, float):
            return f"{value:.2f}" if value == int(value) else repr(value)
        return "" if value is None else str(value)

    # -- population ---------------------------------------------------------

    def _populate(self) -> None:
        abb = self._current_abb()
        metrics = self._baselines.get(abb) or {}
        codes = list(metrics)

        self._loading = True
        try:
            self._table.setRowCount(len(codes))
            for row, code in enumerate(codes):
                entry = metrics.get(code) or {}
                for col, (key, _header, editable) in enumerate(self.COLUMNS):
                    if key == "__code":
                        item = QTableWidgetItem(code)
                        item.setData(Qt.UserRole, code)
                    elif key == "__name":
                        item = QTableWidgetItem(_METRIC_ABB_TO_FULL.get(code, code))
                    else:
                        item = QTableWidgetItem(self._fmt(entry.get(key)))
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        item.setForeground(QBrush(QColor("#555555")))
                        item.setBackground(QBrush(QColor("#f0f0f0")))
                    self._table.setItem(row, col, item)
        finally:
            self._loading = False

        self._table.resizeColumnsToContents()
        header = self._table.horizontalHeader()
        name_col = self._col_of("__name")
        if name_col >= 0:
            header.setSectionResizeMode(name_col, QHeaderView.Stretch)
        self._refresh_marks()
        self._revalidate()

    def _table_to_baselines(self) -> None:
        """Write the table back into the working copy for the selected exercise.

        Cells that do not parse are left at their previous value; `_revalidate`
        flags them and blocks Save, so a half-typed number never silently becomes
        something else.
        """
        abb = self._current_abb()
        if not abb:
            return
        metrics = self._baselines.get(abb) or {}
        for row in range(self._table.rowCount()):
            code = self._code_at(row)
            entry = metrics.get(code)
            if not code or entry is None:
                continue
            for col, (key, _h, editable) in enumerate(self.COLUMNS):
                if not editable:
                    continue
                item = self._table.item(row, col)
                if item is None:
                    continue
                text = item.text().strip()
                if key in self._FLOAT_COLS:
                    try:
                        entry[key] = float(text)
                    except ValueError:
                        pass
                elif key in self._INT_COLS:
                    try:
                        entry[key] = int(float(text))
                    except ValueError:
                        pass
                else:
                    entry[key] = text

    # -- validation ---------------------------------------------------------

    def _revalidate(self) -> None:
        """Mark bad cells and refresh the status line. Save is refused while any stand."""
        self._cell_problems = {}
        abb = self._current_abb()

        self._loading = True
        try:
            for row in range(self._table.rowCount()):
                code = self._code_at(row)
                for col, (key, header, editable) in enumerate(self.COLUMNS):
                    if not editable:
                        continue
                    item = self._table.item(row, col)
                    if item is None:
                        continue
                    text = item.text().strip()
                    problem = ""
                    if key in self._FLOAT_COLS or key in self._INT_COLS:
                        try:
                            value = float(text)
                        except ValueError:
                            problem = f"{text!r} is not a number"
                        else:
                            if math.isnan(value) or math.isinf(value):
                                problem = "must be a finite number"
                            elif key == "stddev" and value < 0:
                                problem = "cannot be negative"
                            elif key == "norm_max" and value <= 0:
                                problem = "must be greater than 0"
                            elif key in self._INT_COLS and value != int(value):
                                problem = "must be a whole number"
                    elif key == "direction":
                        if text not in self._eps.VALID_DIRECTIONS:
                            problem = (
                                f"must be one of "
                                f"{', '.join(self._eps.VALID_DIRECTIONS)}"
                            )

                    if not problem and key in ("best_multiplier", "worst_multiplier"):
                        other = (
                            "worst_multiplier" if key == "best_multiplier"
                            else "best_multiplier"
                        )
                        other_item = self._table.item(row, self._col_of(other))
                        try:
                            if other_item is not None and float(
                                other_item.text().strip()
                            ) == float(text):
                                problem = (
                                    "best and worst multipliers are equal, which "
                                    "collapses the scoring range"
                                )
                        except ValueError:
                            pass

                    if problem:
                        self._cell_problems[(row, col)] = f"{abb}/{code} {header}: {problem}"
                        item.setBackground(QBrush(QColor("#ffd6d6")))
                        item.setToolTip(problem)
                    else:
                        item.setBackground(QBrush(QColor("#ffffff")))
                        item.setToolTip("")
        finally:
            self._loading = False

        self._btn_save.setEnabled(not self._cell_problems)
        self._update_status()

    def _update_status(self) -> None:
        bits: list[str] = []
        if self._cell_problems:
            first = next(iter(sorted(self._cell_problems.items())))[1]
            bits.append(
                f"<b style='color:#b00000;'>{len(self._cell_problems)} invalid cell(s)</b> "
                f"— {first}"
            )

        abb = self._current_abb()
        metrics = self._baselines.get(abb) or {}
        if metrics:
            # Recomputed from the working copy, so the effect of editing a norm_max
            # is visible before saving.
            floor = sum(
                float(e.get("norm_max") or 0) / 2.0 for e in metrics.values()
            )
            ceiling = sum(float(e.get("norm_max") or 0) for e in metrics.values())
            bits.append(
                f"{len(metrics)} metric(s) — PASS floor <b>{floor:.0f}</b>, "
                f"reference ceiling <b>{ceiling:.0f}</b>"
            )

        changed = self._eps.changed_from_defaults(self._baselines)
        if self._eps.BASELINES_DEFAULTS:
            total = sum(len(v) for v in changed.values())
            bits.append(f"{total} metric(s) differ from default")
        else:
            bits.append("<b>no baseline snapshot</b> — cannot reset to defaults")

        if self._baselines != self._eps.normalize_baselines(
            self._eps.PROFICIENCY_BASELINES
        ):
            bits.append("<b>unsaved changes</b>")

        self._lbl_status.setText(" &nbsp;|&nbsp; ".join(bits))

    def _refresh_marks(self) -> None:
        """Bold the code of any metric that differs from the snapshot."""
        abb = self._current_abb()
        changed = set(self._eps.changed_from_defaults(self._baselines).get(abb, []))
        self._loading = True
        try:
            for row in range(self._table.rowCount()):
                code = self._code_at(row)
                item = self._table.item(row, 0)
                if item is None:
                    continue
                is_changed = code in changed
                font = item.font()
                font.setBold(is_changed)
                item.setFont(font)
                item.setText(f"{code} *" if is_changed else code)
                item.setToolTip(
                    "Differs from the default snapshot" if is_changed else ""
                )
        finally:
            self._loading = False

    # -- events -------------------------------------------------------------

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._loading:
            return
        self._table_to_baselines()
        self._refresh_marks()
        self._revalidate()

    def _on_exercise_changed(self) -> None:
        if self._loading:
            return
        self._populate()

    # -- actions ------------------------------------------------------------

    def _on_check(self) -> None:
        """Report whole-table problems, including the ones Save would refuse."""
        self._table_to_baselines()
        problems = self._eps.check_baselines_consistency(self._baselines)

        html = ""
        if self._cell_problems:
            html += "<b>Invalid cells</b><ul>" + "".join(
                f"<li>{p}</li>" for _k, p in sorted(self._cell_problems.items())
            ) + "</ul>"
        if problems:
            html += "<b>Table problems (Save is refused)</b><ul>" + "".join(
                f"<li>{p}</li>" for p in problems[:40]
            ) + "</ul>"
            if len(problems) > 40:
                html += f"<i>… and {len(problems) - 40} more.</i>"
        if not html:
            html = (
                "<b>No problems found.</b><br>Every metric has a usable scoring "
                "range, a valid direction and a positive norm_max."
            )

        box = QMessageBox(self)
        box.setWindowTitle("Proficiency Values — Check")
        box.setTextFormat(Qt.RichText)
        box.setText(html)
        box.exec()

    def _on_save(self) -> None:
        self._table_to_baselines()
        if self._cell_problems:
            QMessageBox.warning(
                self, "Proficiency Values",
                "Cannot save while cells are invalid:\n\n"
                + "\n".join(p for _k, p in sorted(self._cell_problems.items())),
            )
            return

        if self._baselines == self._eps.normalize_baselines(
            self._eps.PROFICIENCY_BASELINES
        ):
            QMessageBox.information(
                self, "Proficiency Values", "Nothing has changed."
            )
            return

        if not _confirm_baseline_edit(self):
            return

        src_path = _baselines_module_path()
        backup_path = (
            _backup_baselines_module(src_path) if os.path.isfile(src_path) else ""
        )
        if os.path.isfile(src_path) and not backup_path:
            QMessageBox.critical(
                self, "Proficiency Values",
                f"Could not create a backup of:\n{src_path}\n\n"
                "Nothing was written. Check the folder is writable and retry.",
            )
            return

        try:
            path = self._eps.save_baselines(self._baselines)
        except (OSError, RuntimeError, ValueError) as e:
            QMessageBox.critical(
                self, "Proficiency Values",
                f"Could not save — nothing was written:\n\n{e}",
            )
            return

        # The floor/ceiling tables this app caches are derived from the values just
        # rewritten; without this the session keeps deciding PASS against the old ones.
        invalidate_normative_caches()

        changed = self._eps.changed_from_defaults(self._baselines)
        self._baselines = self._eps.normalize_baselines(self._eps.PROFICIENCY_BASELINES)
        self._populate()

        QMessageBox.information(
            self, "Proficiency Values",
            f"Proficiency values written to:\n{path}\n\n"
            + (f"Backup: {backup_path}\n\n" if backup_path else "")
            + f"{sum(len(v) for v in changed.values())} metric(s) now differ from the "
            f"default snapshot.\n\n"
            f"Re-open any Analysis or Proficiency window to see the change.",
        )

    def _on_discard(self) -> None:
        self._baselines = self._eps.normalize_baselines(self._eps.PROFICIENCY_BASELINES)
        self._populate()

    def _revert(self, scope: str, codes: list[str] | None, note: str) -> None:
        """Pull snapshot values into the table without writing anything."""
        baseline = self._eps.revert_to_defaults()
        if not baseline:
            QMessageBox.warning(
                self, "Proficiency Values",
                f"No baseline snapshot at:\n{self._eps.defaults_path()}",
            )
            return

        if scope == "all":
            self._baselines = baseline
        else:
            abb = self._current_abb()
            base_metrics = baseline.get(abb) or {}
            live = self._baselines.setdefault(abb, {})
            targets = list(base_metrics) if codes is None else codes
            for code in targets:
                if code in base_metrics:
                    live[code] = dict(base_metrics[code])
                else:
                    live.pop(code, None)

        self._populate()
        self._lbl_status.setText(f"{note} <b>Not saved yet</b> — press Save to apply.")

    def _on_revert_selected(self) -> None:
        rows = sorted({i.row() for i in self._table.selectedIndexes()})
        codes = [c for c in (self._code_at(r) for r in rows) if c]
        if not codes:
            QMessageBox.information(
                self, "Proficiency Values",
                "Select the metric you want to reset first.",
            )
            return
        self._revert(
            "metrics", codes,
            f"Restored {', '.join(codes)} from the default snapshot.",
        )

    def _on_revert_exercise(self) -> None:
        abb = self._current_abb()
        self._revert(
            "exercise", None,
            f"Restored every metric of {abb} from the default snapshot.",
        )

    def _on_revert_all(self) -> None:
        reply = QMessageBox.question(
            self, "Reset All",
            "Restore the default proficiency values for every exercise?\n\n"
            "This loads the snapshot into the table; nothing is written until you Save.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._revert("all", None, "Restored all exercises from the default snapshot.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("RSAC – File Manager")
        # Open at the desired Admin Session position and a resizable size roughly
        # double the previous fixed size. Screen position 336,5 with client area
        # size 868x528 gives screen size ~868x528.
        self.resize(868, 528)
        self.move(336, 5)

        self.export_files = []
        self.clean_files = []

        self._datashow_windows: list[DataShowWindow] = []
        self._hidden_datashow_windows: dict[str, DataShowWindow] = {}
        self._live_session_windows: list['LiveSessionWindow'] = []
        self._proficiency_window: 'ProficiencyValuesWindow | None' = None
        self._skill_ratings_window: 'SkillRatingsWindow | None' = None
        self._exercise_progression_window: 'ExerciseProgressionWindow | None' = None
        self._proficiency_baselines_window: 'ProficiencyBaselinesWindow | None' = None

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        _table_ss = "QTableWidget::item:selected { background: transparent; color: inherit; }"

        # --- Section 1: Original CSV Files ---
        self.export_table = QTableWidget(0, 4)
        self.export_table.setHorizontalHeaderLabels(["Date", "Time", "Filename", "Clean CSV Created"])
        self.export_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.export_table.setSelectionMode(QTableWidget.SingleSelection)
        self.export_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.export_table.horizontalHeader().setStretchLastSection(True)
        self.export_table.doubleClicked.connect(self.clean_selected_export)
        self.export_table.setStyleSheet(_table_ss)
        self.export_table.setFocusPolicy(Qt.NoFocus)
        self.export_table.itemSelectionChanged.connect(lambda: self._bold_selected_row(self.export_table))

        sec1 = _CollapsibleSection("Original CSV Files  (double-click to create clean CSV)", self.export_table,
                                     expanded=False, color="#143E7A", hover_color="#1B4F99")
        main_layout.addWidget(sec1)

        # --- Section 2: MimicClean Files ---
        self.clean_table = QTableWidget(0, 3)
        self.clean_table.setHorizontalHeaderLabels(["Date", "Time", "Filename"])
        self.clean_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clean_table.setSelectionMode(QTableWidget.SingleSelection)
        self.clean_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clean_table.horizontalHeader().setStretchLastSection(True)
        self.clean_table.doubleClicked.connect(self.analyze_selected_clean)
        self.clean_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.clean_table.customContextMenuRequested.connect(self._clean_table_context_menu)
        self.clean_table.setStyleSheet(_table_ss)
        self.clean_table.setFocusPolicy(Qt.NoFocus)
        self.clean_table.setSortingEnabled(True)
        self.clean_table.itemSelectionChanged.connect(lambda: self._bold_selected_row(self.clean_table))

        sec2 = _CollapsibleSection("Clean CSV Files  (double-click to analyze)", self.clean_table,
                                     expanded=False, color="#008941", hover_color="#00A34E")
        main_layout.addWidget(sec2)

        # --- Section 3: History Files ---
        self.retro_files: list[dict[str, str]] = []
        self._retro_summary_windows: list['RetroSummaryWindow'] = []

        self.retro_table = QTableWidget(0, 5)
        self.retro_table.setHorizontalHeaderLabels(["Source", "Subject", "Attempts", "Date", "Filename"])
        self.retro_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.retro_table.setSelectionMode(QTableWidget.SingleSelection)
        self.retro_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.retro_table.horizontalHeader().setStretchLastSection(True)
        self.retro_table.doubleClicked.connect(self._open_retro_summary)
        self.retro_table.setStyleSheet(_table_ss)
        self.retro_table.setFocusPolicy(Qt.NoFocus)
        self.retro_table.itemSelectionChanged.connect(lambda: self._bold_selected_row(self.retro_table))

        sec4 = _CollapsibleSection("History Files  (double-click for summary)", self.retro_table,
                                     expanded=False, color="#CC6600", hover_color="#E07700")
        main_layout.addWidget(sec4)

        main_layout.addStretch()

        self._init_folders()
        self.refresh_lists()

    def close_all_session_windows(self) -> None:
        """Close every auxiliary window opened from this File Manager."""
        for attr in (
            "_datashow_windows",
            "_live_session_windows",
            "_retro_summary_windows",
        ):
            window_list = list(getattr(self, attr, []))
            for w in window_list:
                try:
                    w.close()
                except Exception:
                    pass
            getattr(self, attr, []).clear()

        for w in list(self._hidden_datashow_windows.values()):
            try:
                w.close()
            except Exception:
                pass
        self._hidden_datashow_windows.clear()

        for attr in (
            "_proficiency_window",
        ):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.close()
                except Exception:
                    pass
            setattr(self, attr, None)

    def apply_subject_session(self, dlg: 'WelcomeDialog') -> None:
        """Apply a (new or changed) subject selection from WelcomeDialog.

        Updates the window title and runs the same auto-open logic used at
        application startup: a brand-new subject goes straight to the Score
        Screen Capture window, while a returning one is shown any pending
        NAED decision notice.
        """
        subject = dlg.selected_subject
        if not subject:
            return

        self.setWindowTitle(f"RSAC – File Manager  [{subject}]")

        if dlg.is_new_subject:
            QTimer.singleShot(
                200, lambda s=subject: self.open_live_session_window(subject=s)
            )
        else:
            QTimer.singleShot(
                300, lambda s=subject: self.check_pending_decision_notice(s)
            )

    def _init_folders(self) -> None:
        # Folder convention (relative to this script):
        #   ./csv_simulator : raw simulator exports (MimicSessionExport_*.csv)
        #   ./csv_clean     : cleaned files created by this tool (MimicClean_*.csv)
        base_dir = _script_dir()
        self.simulator_dir = os.path.join(base_dir, "csv_simulator")
        self.clean_dir = os.path.join(base_dir, "csv_clean")
        self.history_dir = os.path.join(base_dir, "analysis_history")

        # Create folders if missing. Creating csv_simulator is harmless and makes the convention explicit.
        try:
            os.makedirs(self.simulator_dir, exist_ok=True)
            os.makedirs(self.clean_dir, exist_ok=True)
            os.makedirs(self.history_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Folder error",
                "Could not create required subfolders next to the script.\n\n"                f"Error: {e}"
            )
            sys.exit(1)

        # Optional UX: inform if simulator folder is empty
        try:
            has_exports = any(
                name.lower().startswith("mimicsessionexport_") and name.lower().endswith(".csv")
                for name in os.listdir(self.simulator_dir)
            )
        except Exception:
            has_exports = False

        if not has_exports:
            QMessageBox.information(
                self,
                "csv_simulator is empty",
                "Place your simulator export CSV files in the folder:\n\n"
                f"{self.simulator_dir}\n\n"
                "Then reopen the app."
            )

    def _bold_selected_row(self, table: QTableWidget) -> None:
        normal = QFont()
        bold = QFont()
        bold.setBold(True)
        for r in range(table.rowCount()):
            font = bold if r in {idx.row() for idx in table.selectionModel().selectedRows()} else normal
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item:
                    item.setFont(font)

    def refresh_lists(self):
        try:
            self.export_files = collect_export_files(self.simulator_dir)
            self.clean_files = collect_clean_files(self.clean_dir)
            self.retro_files = collect_history_json_files(self.history_dir)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list files:\n{e}")
            sys.exit(1)

        self.populate_export_table()
        self.populate_clean_table()
        self.populate_retro_table()

    def _clean_status_for_export(self, export_path: str) -> str:
        """Return 'YES - All Subjects', 'YES - Partially', or 'NO' for an export file."""
        try:
            all_subjects = get_subjects_in_export(export_path)
        except Exception:
            return "NO"
        if not all_subjects:
            return "NO"

        clean_names_lower = [cf.get("filename", "").lower() for cf in self.clean_files]
        found = 0
        for subj in all_subjects:
            prefix = f"mimicclean_{subj.lower()}_"
            if any(cn.startswith(prefix) for cn in clean_names_lower):
                found += 1

        if found == 0:
            return "NO"
        elif found >= len(all_subjects):
            return "YES - All Subjects"
        else:
            return "YES - Partially"

    def populate_export_table(self):
        green = QColor(0, 128, 0)
        orange = QColor(200, 140, 0)
        red = QColor(200, 0, 0)
        self.export_table.setRowCount(len(self.export_files))
        for row, item in enumerate(self.export_files):
            self.export_table.setItem(row, 0, QTableWidgetItem(item["date"]))
            self.export_table.setItem(row, 1, QTableWidgetItem(item["time"]))
            self.export_table.setItem(row, 2, QTableWidgetItem(item["filename"]))
            status = self._clean_status_for_export(item["path"])
            status_item = QTableWidgetItem(status)
            if status.startswith("YES - All"):
                status_item.setForeground(QBrush(green))
            elif status.startswith("YES - Partial"):
                status_item.setForeground(QBrush(orange))
            else:
                status_item.setForeground(QBrush(red))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.export_table.setItem(row, 3, status_item)
        self.export_table.resizeColumnsToContents()

    def populate_clean_table(self):
        self.clean_table.setSortingEnabled(False)
        self.clean_table.setRowCount(len(self.clean_files))
        for row, item in enumerate(self.clean_files):
            date_item = QTableWidgetItem(item["date"])
            date_item.setData(Qt.UserRole, row)
            self.clean_table.setItem(row, 0, date_item)
            self.clean_table.setItem(row, 1, QTableWidgetItem(item["time"]))
            self.clean_table.setItem(row, 2, QTableWidgetItem(item["filename"]))
        self.clean_table.resizeColumnsToContents()
        self.clean_table.setSortingEnabled(True)


    def populate_retro_table(self):
        self.retro_table.setRowCount(len(self.retro_files))
        for row, item in enumerate(self.retro_files):
            self.retro_table.setItem(row, 0, QTableWidgetItem(item.get("source", "")))
            self.retro_table.setItem(row, 1, QTableWidgetItem(item.get("subject", "")))
            self.retro_table.setItem(row, 2, QTableWidgetItem(item.get("attempts", "")))
            self.retro_table.setItem(row, 3, QTableWidgetItem(item.get("date", "")))
            self.retro_table.setItem(row, 4, QTableWidgetItem(item.get("filename", "")))
        self.retro_table.resizeColumnsToContents()

    def _open_retro_summary(self):
        row = self.retro_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No selection", "Please select a History file first.")
            return
        item = self.retro_files[row]
        retro_path = item.get("path", "")
        if not retro_path or not os.path.isfile(retro_path):
            QMessageBox.critical(self, "File not found", f"The file no longer exists:\n{retro_path}")
            return
        try:
            w = RetroSummaryWindow(retro_path, parent=self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open history summary:\n{e}")
            return
        self._retro_summary_windows.append(w)
        w.show()

    def _confirm_overwrite_if_exists(self, path: str) -> bool:
        if not os.path.exists(path):
            return True
        resp = QMessageBox.question(
            self,
            "Overwrite file?",
            f"File already exists:\n{path}\n\nOverwrite it?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return resp == QMessageBox.Yes

    def clean_selected_export(self):
        return run_clean_selected_export(self)



    def analyze_selected_clean(self):
        row = self.clean_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No selection", "Please select a MimicClean file first.")
            return

        idx = self.clean_table.item(row, 0).data(Qt.UserRole)
        item = self.clean_files[idx]
        clean_path = item["path"]

        if not os.path.isfile(clean_path):
            QMessageBox.critical(self, "File not found", f"The file no longer exists:\n{clean_path}")
            return

        self.open_datashow_window(clean_path)

    def open_live_session_window(self, subject: str = ""):
        w = LiveSessionWindow(main_window=self, subject=subject)
        self._live_session_windows.append(w)
        w.show()
        w.raise_()
        w.activateWindow()

    def check_pending_decision_notice(self, subject: str) -> None:
        """Warn the tutor if `subject` has an attempt awaiting Accept/Reject
        from a previous session (app was closed before a decision was made)."""
        if not subject:
            return
        try:
            pending = find_pending_decision(self.clean_dir, subject)
        except Exception:
            pending = None
        if not pending:
            return
        QMessageBox.warning(
            self,
            "Pending Decision",
            f"<b>{subject}</b> has a recommendation awaiting a decision from a "
            f"previous session:<br><br>"
            f"Exercise: <b>{pending['exercise_full']}</b> "
            f"(attempt #{pending['exercise_attempt_number']})<br><br>"
            "Open this subject's file in Data Show and click "
            "<b>Recommendations</b> to Accept or Override it before continuing.",
        )

    def _show_adaptive_algorithm(self, subject: str = ""):
        img_dir = app_paths.asset_path("img")
        curriculum = get_curriculum_for_subject(subject) if subject else ""
        if curriculum == "grad":
            img_name = "2026_Aug_a - KG - Adaptive Curricula - Grad Students - 28 exercises.jpeg"
        elif curriculum == "resident_ext":
            img_name = "2026_Aug_a - KG - Adaptive Curricula - Extended - 60 exercises.jpeg"
        else:
            img_name = "2026_Aug_a - KG - Adaptive Curricula - Grad Students - 28 exercises.jpeg"
        img_path = os.path.join(img_dir, img_name)
        if os.path.isfile(img_path):
            os.startfile(img_path)
        else:
            QMessageBox.warning(self, "File not found", f"Could not find:\n{img_path}")

    def _show_proficiency_values(self):
        if self._proficiency_window is not None and self._proficiency_window.isVisible():
            self._proficiency_window.raise_()
            self._proficiency_window.activateWindow()
            return
        self._proficiency_window = ProficiencyValuesWindow(parent=self)
        self._proficiency_window.show()

    def _show_skill_ratings(self):
        """Open the exercise catalogue / skill ratings editor (single instance)."""
        if self._skill_ratings_window is not None and self._skill_ratings_window.isVisible():
            self._skill_ratings_window.raise_()
            self._skill_ratings_window.activateWindow()
            return
        self._skill_ratings_window = SkillRatingsWindow(parent=self)
        self._skill_ratings_window.show()

    def _show_exercise_progression(self):
        """Open the exercise progression graph editor (single instance)."""
        if (
            self._exercise_progression_window is not None
            and self._exercise_progression_window.isVisible()
        ):
            self._exercise_progression_window.raise_()
            self._exercise_progression_window.activateWindow()
            return
        self._exercise_progression_window = ExerciseProgressionWindow(parent=self)
        self._exercise_progression_window.show()

    def _show_proficiency_baselines(self):
        """Open the proficiency values editor (single instance).

        Gated on the simulator warning: these values only mean anything while they
        match the simulator's own configuration, and that cannot be checked from
        here. An already-open window is raised without re-warning.
        """
        if (
            self._proficiency_baselines_window is not None
            and self._proficiency_baselines_window.isVisible()
        ):
            self._proficiency_baselines_window.raise_()
            self._proficiency_baselines_window.activateWindow()
            return
        if not _warn_baselines_mirror_simulator(self):
            return
        self._proficiency_baselines_window = ProficiencyBaselinesWindow(parent=self)
        self._proficiency_baselines_window.show()

    def _find_datashow_window(self, clean_path: str) -> 'DataShowWindow | None':
        """Find an open DataShowWindow for the given clean_path, normalizing paths for comparison."""
        norm = os.path.normcase(os.path.abspath(clean_path))
        for w in list(self._datashow_windows):
            try:
                if not w.isVisible():
                    continue
                w_path = getattr(w, "clean_path", None)
                if w_path and os.path.normcase(os.path.abspath(w_path)) == norm:
                    return w
            except Exception:
                continue
        return None

    def _open_or_refresh_datashow_for_clean(
        self,
        clean_path: str,
        subject: str,
        exercise_full_name: str,
    ) -> None:
        # Reuse an existing window for the same clean file if already open
        w = self._find_datashow_window(clean_path)
        if w is not None:
            w.reload_clean_file(subject=subject, exercise=exercise_full_name)
            w.raise_()
            w.activateWindow()
            return

        try:
            w = DataShowWindow(clean_path)
        except Exception as e:
            QMessageBox.critical(self, "Data Show failed", f"Could not open Data Show:\n{e}")
            return

        self._datashow_windows.append(w)
        w.show()
        w.reload_clean_file(subject=subject, exercise=exercise_full_name)

    def open_datashow_window(self, clean_path: str):
        # Reuse an existing window if one is already open for this file
        w = self._find_datashow_window(clean_path)
        if w is not None:
            w.reload_clean_file()
            w.raise_()
            w.activateWindow()
            return

        try:
            w = DataShowWindow(clean_path)
        except Exception as e:
            QMessageBox.critical(self, "Data Show failed", f"Could not open Data Show:\n{e}")
            return

        self._datashow_windows.append(w)
        w.show()

    def _get_or_open_datashow_for_subject(self, subject: str) -> 'DataShowWindow | None':
        """Find/open the DataShow window for the subject's latest MimicClean CSV."""
        if not subject:
            QMessageBox.warning(self, "No subject", "No subject is selected for this session.")
            return None

        matches = [
            item for item in self.clean_files
            if item.get("subject") == subject and os.path.isfile(item.get("path", ""))
        ]
        if not matches:
            QMessageBox.information(
                self, "No Clean CSV",
                f"No Clean CSV file found for <b>{subject}</b>.\n\n"
                "Import and clean a simulator export first.",
            )
            return None

        latest = max(matches, key=lambda x: x.get("datetime") or datetime.min)
        clean_path = latest["path"]

        w = self._find_datashow_window(clean_path)
        if w is not None:
            w.reload_clean_file(subject=subject)
            w.raise_()
            w.activateWindow()
            return w

        try:
            w = DataShowWindow(clean_path)
        except Exception as e:
            QMessageBox.critical(self, "Data Show failed", f"Could not open Data Show:\n{e}")
            return None

        self._datashow_windows.append(w)
        w.show()
        return w

    def open_clean_csv_for_subject(self, subject: str) -> None:
        """Open the most recent MimicClean CSV for `subject` in a DataShow window."""
        self._get_or_open_datashow_for_subject(subject)

    def _get_datashow_backend_for_subject(self, subject: str, silent: bool = False) -> 'DataShowWindow | None':
        """Return a DataShowWindow instance for `subject`'s latest MimicClean CSV,
        without showing the Data Show table. Reuses a visible Data Show window if
        the user already has one open for this subject; otherwise reuses (or
        creates) a hidden backend instance purely to compute Training Analysis /
        Progress Graph data.

        If `silent` is True, no message boxes are shown on failure (used by bulk
        operations like Arms Comparison, which iterate over many subjects).
        """
        if not subject:
            if not silent:
                QMessageBox.warning(self, "No subject", "No subject is selected for this session.")
            return None

        matches = [
            item for item in self.clean_files
            if item.get("subject") == subject and os.path.isfile(item.get("path", ""))
        ]
        if not matches:
            if not silent:
                QMessageBox.information(
                    self, "No Clean CSV",
                    f"No Clean CSV file found for <b>{subject}</b>.\n\n"
                    "Import and clean a simulator export first.",
                )
            return None

        latest = max(matches, key=lambda x: x.get("datetime") or datetime.min)
        clean_path = latest["path"]

        # Reuse a visible Data Show window if the user already has one open.
        w = self._find_datashow_window(clean_path)
        if w is not None:
            w.reload_clean_file(subject=subject)
            return w

        norm = os.path.normcase(os.path.abspath(clean_path))
        w = self._hidden_datashow_windows.get(norm)
        if w is not None:
            try:
                w.reload_clean_file(subject=subject)
                return w
            except Exception:
                self._hidden_datashow_windows.pop(norm, None)

        try:
            w = DataShowWindow(clean_path)
        except Exception as e:
            if not silent:
                QMessageBox.critical(self, "Data Show failed", f"Could not open Data Show:\n{e}")
            return None

        self._hidden_datashow_windows[norm] = w
        return w

    def open_training_analysis_for_subject(self, subject: str) -> None:
        """Jump straight to Training Analysis for `subject` without opening Data Show."""
        w = self._get_datashow_backend_for_subject(subject)
        if w is not None:
            w._open_ds_training_analysis()

    def open_progress_graph_for_subject(self, subject: str) -> None:
        """Jump straight to the Progress Graph for `subject` without opening Data Show."""
        w = self._get_datashow_backend_for_subject(subject)
        if w is not None:
            w._open_ds_progress_graph()

    def is_history_up_to_date(self, subject: str) -> bool:
        """Return True if `subject` has no attempts yet, or an existing retrospective
        History JSON already covers all of the subject's current attempts.
        """
        if not subject:
            return True

        matches = [
            item for item in self.clean_files
            if item.get("subject") == subject and os.path.isfile(item.get("path", ""))
        ]
        if not matches:
            return True

        latest = max(matches, key=lambda x: x.get("datetime") or datetime.min)
        try:
            rows = classify_clean_file(latest["path"])
        except Exception:
            return True
        total_attempts = sum(1 for r in rows if r.get("subject") == subject)
        if total_attempts == 0:
            return True

        hist_dir = self.history_dir
        if not os.path.isdir(hist_dir):
            return False

        _pat = re.compile(
            r"^History_" + re.escape(subject) + r"_(\d+)-att\.json$", re.IGNORECASE
        )
        try:
            for fname in os.listdir(hist_dir):
                m = _pat.match(fname)
                if m:
                    return int(m.group(1)) >= total_attempts
        except Exception:
            return False

        return False

    def generate_retro_history_for_subject(self, subject: str) -> None:
        """Run the retrospective NAED History creation/update flow for `subject`."""
        w = self._get_datashow_backend_for_subject(subject)
        if w is not None:
            w._generate_retro_history_json()

    def _clean_table_context_menu(self, pos):
        row = self.clean_table.rowAt(pos.y())
        if row < 0:
            return
        idx = self.clean_table.item(row, 0).data(Qt.UserRole)
        item = self.clean_files[idx]
        fname = item.get("filename", "")

        if not is_single_subject_clean_filename(fname):
            return

        menu = QMenu(self)
        action = menu.addAction("Generate Retrospective Analysis History File")
        chosen = menu.exec(self.clean_table.viewport().mapToGlobal(pos))
        if chosen == action:
            self._run_retrospective_analysis(item)

    def _run_retrospective_analysis(self, file_item: dict):
        clean_path = file_item.get("path", "")
        if not clean_path or not os.path.isfile(clean_path):
            QMessageBox.critical(self, "File not found", f"File not found:\n{clean_path}")
            return
        try:
            out_path = _generate_retrospective_history(clean_path)
            self.refresh_lists()
            QMessageBox.information(
                self, "Retrospective Analysis Complete",
                f"History file generated:\n{out_path}",
            )
        except Exception as e:
            QMessageBox.critical(self, "Retrospective Analysis Failed", str(e))


# =============================================================================
#  [SEC-04B] Live Session (attempt -> append MimicClean -> open DataShow -> NAED)
# =============================================================================

# An "attempt dict" is the unit of input to the live loop. It has five keys:
#
#     exercise_abbreviation : str          e.g. "pb1"
#     exercise_full_name    : str          e.g. "Peg Board 1"
#     overall_score_raw     : float | str  the number, or the string "Incomplete"
#     timestamp             : str          "YYYY-MM-DD HH:MM:SS"
#     metrics_canonical     : dict         {metric_code: raw_value}
#
# Screenshot OCR produces one of these; so does the manual entry dialog. Nothing
# downstream of AttemptProcessor knows or cares which producer it came from.


class AttemptProcessor:
    """Attempt orchestration, independent of where the attempt came from.

    Holds everything the live loop does with an attempt that is *not* specific to
    screenshots: the curriculum check, incomplete-attempt routing, metric
    validation, scoring and the CSV append.

    Deliberately free of Qt and of any file-watching so that the screenshot
    producer and the manual-entry producer share exactly one code path. Callers
    keep their own side effects (moving images, showing dialogs) around these
    calls, because the ordering of those differs per producer.
    """

    def __init__(self, subject: str, clean_path: str) -> None:
        self.subject = subject
        self.clean_path = clean_path

    # -- curriculum check ---------------------------------------------------

    def expected_exercise(self) -> str:
        """The exercise this subject is supposed to be doing next.

        Read from the last Reality_Check in the subject's history JSON, so it
        reflects the decision the tutor actually accepted. 'pp1' when there is no
        history yet.
        """
        import json as _json

        script_dir = _script_dir()
        hist_dir = os.path.join(script_dir, "analysis_history")
        if not os.path.isdir(hist_dir):
            return "pp1"

        _pat = re.compile(
            r"^History_" + re.escape(self.subject) + r"_(\d+)-att\.json$", re.IGNORECASE
        )
        for fname in os.listdir(hist_dir):
            if not _pat.match(fname):
                continue
            try:
                with open(os.path.join(hist_dir, fname), "r", encoding="utf-8-sig") as f:
                    data = _json.load(f)
                if data:
                    last_entry = data[-1]
                    rc = last_entry.get("Reality_Check") or {}
                    next_abb = (rc.get("next_exercise_abbreviation") or "").strip()
                    if next_abb:
                        return next_abb
            except Exception:
                continue
        return "pp1"

    def check_exercise(self, result: dict[str, Any]) -> tuple[bool, str, str]:
        """Compare the attempt's exercise against the expected one.

        Returns (matches, attempt_exercise_full, expected_exercise_full). A
        mismatch is not an error — the tutor is allowed to confirm it — so the
        caller decides what to do.
        """
        attempt_abb = str(result.get("exercise_abbreviation") or "")
        expected_abb = self.expected_exercise()
        if not attempt_abb or not expected_abb or attempt_abb == expected_abb:
            return True, "", ""
        attempt_full = str(result.get("exercise_full_name") or attempt_abb)
        expected_full = str(
            EXERCISE_DEFS.get(expected_abb, {}).get("exerc_full", expected_abb)
        )
        return False, attempt_full, expected_full

    # -- classification -----------------------------------------------------

    @staticmethod
    def is_incomplete(result: dict[str, Any]) -> bool:
        """True when the attempt was abandoned rather than scored.

        The simulator prints "Incomplete" in the Attempt Summary bar instead of a
        score; the manual dialog offers the same option.
        """
        raw = result.get("overall_score_raw")
        return isinstance(raw, str) and raw.strip().lower() == "incomplete"

    @staticmethod
    def metrics_complete(exerc_abb: str, metrics_canonical: dict) -> bool:
        """True if every metric the exercise is scored on is present.

        For screenshots this catches a tooltip or cursor covering a metric card.
        For manual entry it catches a skipped field.
        """
        try:
            from exercise_proficiency_scores import PROFICIENCY_BASELINES
        except Exception as e:
            _warn_normative_tables_unavailable("PROFICIENCY_BASELINES", e)
            return True
        expected = PROFICIENCY_BASELINES.get(exerc_abb, {})
        if not expected:
            # Unknown exercise — cannot validate, so allow it through.
            return True
        for metric_key in expected:
            if metric_key not in metrics_canonical:
                return False
        return True

    # -- writes -------------------------------------------------------------

    def log_incomplete(self, result: dict[str, Any]) -> str:
        """Record an abandoned attempt in the subject's IncompleteAttempts_ CSV."""
        exercise_full = str(result.get("exercise_full_name") or "")
        metrics_can = result.get("metrics_canonical") or {}
        try:
            ttc_seconds = float(metrics_can.get("ttc"))
        except (TypeError, ValueError):
            ttc_seconds = 0.0

        output_folder = os.path.dirname(os.path.abspath(self.clean_path))
        return update_incomplete_attempts_csv(
            subject=self.subject,
            exercise_full=exercise_full,
            ttc_seconds=ttc_seconds,
            output_folder=output_folder,
        )

    def append(self, result: dict[str, Any], screenshot_filename: str = "") -> str:
        """Score the attempt and append it to the Clean CSV. Returns the path."""
        from attempt_csv import build_csv_line, append_to_csv

        line = build_csv_line(
            result, subject=self.subject, screenshot_filename=screenshot_filename
        )
        return append_to_csv(line, subject=self.subject, target_path=self.clean_path)


# =============================================================================
#  [SEC-MENU] SESSION MENU WINDOW (sidebar)
# =============================================================================

def _qicon(name: str, color: str = "white"):
    """Return a qtawesome icon, or None if qtawesome is unavailable."""
    if not _HAS_QTA:
        return None
    try:
        return qta.icon(name, color=color)
    except Exception:
        return None


def _add_card_shadow(widget: QWidget, blur: int = 12, y_offset: int = 2, alpha: int = 60) -> None:
    """Attach a soft drop shadow to a widget, giving it a floating 'card' look."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y_offset)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


# Screen position of the Session Menu sidebar, measured with AutoHotkey Spy.
# Every other window aligns its top edge to the same line, so the app reads as one
# workspace rather than a scatter of windows.
SESSION_MENU_POS = (29, 4)

# Left edge for content windows: clear of the Session Menu column.
CONTENT_WINDOW_X = 336


def align_window_top(win: QWidget, x: int | None = None) -> None:
    """Place `win` with its top edge level with the Session Menu's.

    Qt centres a window on its parent, which for a tall window and a parent sitting
    near the top of the screen puts the title bar *above* the desktop — unreachable,
    so the window cannot be moved or closed by mouse. Any window taller than its
    parent therefore has to be positioned explicitly.

    Also clamps the size to the available desktop, so a window can never open taller
    or wider than the space below and right of that top-left corner.
    """
    screen = win.screen() if hasattr(win, "screen") else None
    if screen is None:
        screen = QApplication.primaryScreen()
    if screen is None:
        return
    geom = screen.availableGeometry()

    y = geom.y() + SESSION_MENU_POS[1]
    width = min(win.width(), geom.width())
    height = min(win.height(), geom.bottom() - y + 1)
    if (width, height) != (win.width(), win.height()):
        win.resize(width, height)

    if x is None:
        x = geom.x() + CONTENT_WINDOW_X
    x = max(geom.x(), min(x, geom.right() - width + 1))
    win.move(x, y)


class _MenuSection(QWidget):
    """A card-style category header that expands/collapses its sub-buttons with
    a smooth slide animation. Used to group related Session Menu actions.

    Sections nest: `add_subsection` puts another _MenuSection inside this one's
    content, styled as a sub-header so it reads as a sibling of the action buttons
    it sits among. A nested section expanding grows its ancestors too, which is
    what `_propagate_resize` is for.
    """

    def __init__(
        self,
        title: str,
        icon_name: str,
        parent: QWidget | None = None,
        level: int = 0,
    ):
        super().__init__(parent)
        self._title = title
        self._expanded = False
        self._level = level

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(6)

        self.header_btn = QPushButton(f"  {title}")
        self.header_btn.setCursor(Qt.PointingHandCursor)
        self.header_btn.setMinimumHeight(40 if level == 0 else 32)
        icon = _qicon(icon_name, color="white")
        if icon is not None:
            self.header_btn.setIcon(icon)
            self.header_btn.setIconSize(QSize(16 if level == 0 else 14, 16 if level == 0 else 14))
        if level == 0:
            self.header_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #007f3d;
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 8px 14px;
                    font-weight: 700;
                    font-size: 13px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #005c2d;
                }
                QPushButton:pressed {
                    background-color: #004620;
                }
                """
            )
            _add_card_shadow(self.header_btn)
        else:
            # Sub-header: same blue as the action buttons it sits beside, so the
            # only thing marking it out is the disclosure arrow.
            self.header_btn.setStyleSheet(
                """
                QPushButton {
                    background-color: #0066b3;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 6px 12px;
                    font-weight: 600;
                    font-size: 12px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #1b3664;
                }
                QPushButton:pressed {
                    background-color: #004a82;
                }
                """
            )
        self.header_btn.clicked.connect(self._toggle)
        outer.addWidget(self.header_btn)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(14 if level == 0 else 12, 2, 0, 2)
        self.content_layout.setSpacing(6)
        self.content.setMaximumHeight(0)
        outer.addWidget(self.content)

        self._anim = QPropertyAnimation(self.content, b"maximumHeight")
        self._anim.setDuration(200)
        self._anim.setEasingCurve(QEasingCurve.InOutQuad)
        self._anim.valueChanged.connect(self._propagate_resize)

        self._update_header_text()

    def add_subsection(self, title: str, icon_name: str) -> "_MenuSection":
        """Nest another collapsible section inside this one."""
        sub = _MenuSection(title, icon_name, level=self._level + 1)
        self.content_layout.addWidget(sub)
        return sub

    def add_action_button(self, text: str, icon_name: str, callback) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(32)
        icon = _qicon(icon_name, color="white")
        if icon is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(14, 14))
        btn.setStyleSheet(
            """
            QPushButton {
                background-color: #0066b3;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 12px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #1b3664;
            }
            QPushButton:pressed {
                background-color: #004a82;
            }
            """
        )
        btn.clicked.connect(callback)
        self.content_layout.addWidget(btn)
        return btn

    def _update_header_text(self) -> None:
        arrow = "▾" if self._expanded else "▸"
        self.header_btn.setText(f"  {self._title}   {arrow}")

    def _toggle(self) -> None:
        self._expanded = not self._expanded
        self._update_header_text()
        target = self.content_layout.sizeHint().height() if self._expanded else 0
        self._anim.stop()
        self._anim.setStartValue(self.content.maximumHeight())
        self._anim.setEndValue(target)
        self._anim.finished.connect(self._notify_resize)
        self._anim.start()

    def _ancestor_sections(self) -> list["_MenuSection"]:
        out: list["_MenuSection"] = []
        parent = self.parentWidget()
        while parent is not None:
            if isinstance(parent, _MenuSection):
                out.append(parent)
            parent = parent.parentWidget()
        return out

    def _sync_expanded_height(self) -> None:
        """Re-clamp an open section to the height its content needs right now.

        An open section's maximumHeight was fixed when it was opened. If a nested
        section then expands inside it, that stale clamp would cut the child off.
        """
        if self._expanded:
            self.content.setMaximumHeight(self.content_layout.sizeHint().height())

    def _propagate_resize(self) -> None:
        for section in self._ancestor_sections():
            section._sync_expanded_height()

    def _notify_resize(self) -> None:
        try:
            self._anim.finished.disconnect(self._notify_resize)
        except Exception:
            pass
        self._propagate_resize()
        win = self.window()
        if win is not None:
            win.adjustSize()

    def set_section_visible(self, visible: bool) -> None:
        self.setVisible(visible)
        if not visible and self._expanded:
            self._expanded = False
            self._update_header_text()
            self.content.setMaximumHeight(0)


class SessionMenuWindow(QMainWindow):
    """Card-style sidebar menu shown after subject selection.

    Groups related actions into collapsible sections (Training Sessions,
    Performance, Admin) with icons and drop-shadow "cards" for a cleaner,
    more modern look.
    """

    def __init__(self, subject: str, main_window: MainWindow):
        super().__init__()
        self.subject = subject
        self.main_window = main_window

        self.setWindowTitle(f"RSAC – Session Menu  [{subject}]")
        self.setMinimumWidth(300)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        self._lbl_header = QLabel("RSAC")
        self._lbl_header.setAlignment(Qt.AlignCenter)
        self._lbl_header.setStyleSheet(
            "font-size: 24px; font-weight: bold; color: #1b3664; background: transparent;"
        )
        layout.addWidget(self._lbl_header)

        self._subject_card = QWidget()
        subject_card_layout = QVBoxLayout(self._subject_card)
        subject_card_layout.setContentsMargins(12, 8, 12, 8)
        self._subject_card.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.65); border-radius: 10px;"
        )
        _add_card_shadow(self._subject_card, blur=10, y_offset=1, alpha=40)
        self._lbl_subject = QLabel(f"<b>Subject:</b> {subject}")
        self._lbl_subject.setStyleSheet(
            "font-size: 14px; color: #1b3664; background: transparent;"
        )
        subject_card_layout.addWidget(self._lbl_subject)
        layout.addWidget(self._subject_card)
        layout.addSpacing(4)

        self._buttons: dict[str, QPushButton] = {}
        self._sections: dict[str, _MenuSection] = {}

        # --- Training Sessions ---
        training = _MenuSection("Training Sessions", "fa5s.dumbbell")
        self._buttons["Training per Exercise"] = training.add_action_button(
            "Training per Exercise", "fa5s.list-ol", self._on_exercises
        )
        self._buttons["Progress Graph"] = training.add_action_button(
            "Progress Graph", "fa5s.chart-line", self._on_progress_graph
        )
        self._buttons["NAED History"] = training.add_action_button(
            "NAED History", "fa5s.history", self._on_history
        )
        self._buttons["Create / Update NAED History"] = training.add_action_button(
            "Create / Update NAED History", "fa5s.sync", self._on_update_history
        )
        self._buttons["Adaptive Algorithm"] = training.add_action_button(
            "Adaptive Algorithm", "fa5s.brain", self._on_adaptive_algorithm
        )
        self._buttons["Live Session"] = training.add_action_button(
            "Live Session", "fa5s.play-circle", self._on_live_session
        )
        layout.addWidget(training)
        self._sections["Training Sessions"] = training

        # --- Performance ---
        performance = _MenuSection("Performance", "fa5s.tachometer-alt")
        self._buttons["Training Analysis"] = performance.add_action_button(
            "Training Analysis", "fa5s.chart-bar", self._on_training_analysis
        )
        self._buttons["Peer Comparison"] = performance.add_action_button(
            "Peer Comparison", "fa5s.users", self._on_peer_comparison
        )
        layout.addWidget(performance)
        self._sections["Performance"] = performance

        # --- Settings ---
        # Home for everything a site configures rather than uses per subject.
        settings = _MenuSection("Settings", "fa5s.cog")

        exercises_cfg = settings.add_subsection("Exercises", "fa5s.dumbbell")
        self._buttons["Skill Ratings"] = exercises_cfg.add_action_button(
            "Skill Ratings", "fa5s.sliders-h", self._on_skill_ratings
        )
        self._buttons["Exercise Progression"] = exercises_cfg.add_action_button(
            "Exercise Progression", "fa5s.project-diagram", self._on_exercise_progression
        )
        self._buttons["Proficiency Values"] = exercises_cfg.add_action_button(
            "Proficiency Values", "fa5s.bullseye", self._on_proficiency_baselines
        )
        self._sections["Exercises"] = exercises_cfg

        # The viewer, kept separate: it also drives the simulator XML export, which
        # the editor above deliberately does not do.
        self._buttons["Proficiency XML Export"] = settings.add_action_button(
            "Proficiency XML Export", "fa5s.star", self._on_proficiency
        )
        self._buttons["File Manager"] = settings.add_action_button(
            "File Manager", "fa5s.folder-open", self._on_file_manager
        )
        layout.addWidget(settings)
        self._sections["Settings"] = settings

        layout.addStretch()

        self._buttons["Change Subject"] = self._add_top_button(
            "Change Subject", "fa5s.exchange-alt", layout, self._on_change_subject,
            color="#1b3664", hover="#0f2242", pressed="#0a1831",
        )

        self._apply_button_visibility()
        self._apply_styles()

        self.adjustSize()
        # Height is ignored because the window auto-sizes based on expanded/collapsed
        # sections. Every other window aligns its top to this same y (SESSION_MENU_POS).
        self.move(*SESSION_MENU_POS)

    def _add_top_button(
        self, text: str, icon_name: str, layout: QVBoxLayout, callback,
        color: str = "#0066b3", hover: str = "#1b3664", pressed: str = "#004a82",
    ) -> QPushButton:
        btn = QPushButton(f"  {text}")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(40)
        icon = _qicon(icon_name, color="white")
        if icon is not None:
            btn.setIcon(icon)
            btn.setIconSize(QSize(16, 16))
        btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
                font-size: 13px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {hover};
            }}
            QPushButton:pressed {{
                background-color: {pressed};
            }}
            """
        )
        _add_card_shadow(btn)
        btn.clicked.connect(callback)
        layout.addWidget(btn)
        return btn

    def _apply_button_visibility(self) -> None:
        """Hide the actions that are not applicable to the current subject."""
        up_to_date = self.main_window.is_history_up_to_date(self.subject)
        self._buttons["Create / Update NAED History"].setVisible(not up_to_date)
        self.adjustSize()

    def _apply_styles(self) -> None:
        """Apply a green/blue RSAC color scheme to the menu background."""
        self.centralWidget().setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8fbff, stop:1 #d9ecff);
                border: none;
            }
            QLabel {
                color: #1b3664;
                background: transparent;
            }
            """
        )

    def _on_exercises(self):
        self.main_window.open_clean_csv_for_subject(self.subject)

    def _on_training_analysis(self):
        self.main_window.open_training_analysis_for_subject(self.subject)

    def _on_peer_comparison(self):
        """Open the Peer Comparison window for the subject's training time."""
        def _fmt(sec: float | None) -> str:
            if sec is None:
                return "N/A"
            try:
                total = int(round(float(sec)))
            except Exception:
                return "N/A"
            h, rem = divmod(total, 3600)
            m, s = divmod(rem, 60)
            return f"{h:02d}:{m:02d}:{s:02d}"

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = compute_peer_time_comparison(self.main_window, self.subject)
        finally:
            QApplication.restoreOverrideCursor()

        if result is None:
            QMessageBox.information(
                self, "Peer Comparison",
                f"Could not determine a peer comparison for {self.subject}.\n"
                "Make sure the subject has a curriculum and at least one proficiency checkpoint."
            )
            return

        if result.get("error"):
            QMessageBox.information(
                self, "Peer Comparison",
                f"Checkpoint for {self.subject}: {result['checkpoint_exercise']}\n"
                f"Your time: {_fmt(result['subject_time'])}\n\n"
                f"{result['error']}"
            )
            return

        dlg = PeerComparisonWindow(
            result, parent=self, main_window=self.main_window,
            subject=self.subject,
        )
        dlg.show()

    def _on_progress_graph(self):
        self.main_window.open_progress_graph_for_subject(self.subject)

    def _on_history(self):
        hist_dir = self.main_window.history_dir
        _pat = re.compile(
            r"^History_" + re.escape(self.subject) + r"_(\d+)-att\.json$", re.IGNORECASE
        )
        hist_path = None
        try:
            for fname in os.listdir(hist_dir):
                if _pat.match(fname):
                    hist_path = os.path.join(hist_dir, fname)
                    break
        except Exception:
            hist_path = None

        if not hist_path:
            QMessageBox.information(
                self, "No history", f"No history file found for {self.subject}."
            )
            return

        try:
            w = RetroSummaryWindow(hist_path, parent=self.main_window)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open history summary:\n{e}")
            return
        self.main_window._retro_summary_windows.append(w)
        w.show()

    def _on_live_session(self):
        self.main_window.open_live_session_window(subject=self.subject)

    def _on_update_history(self):
        self.main_window.generate_retro_history_for_subject(self.subject)
        self._apply_button_visibility()

    def _on_adaptive_algorithm(self):
        self.main_window._show_adaptive_algorithm(subject=self.subject)

    def _on_proficiency(self):
        self.main_window._show_proficiency_values()

    def _on_proficiency_baselines(self):
        self.main_window._show_proficiency_baselines()

    def _on_skill_ratings(self):
        self.main_window._show_skill_ratings()

    def _on_exercise_progression(self):
        self.main_window._show_exercise_progression()

    def _on_file_manager(self):
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()

    def _on_change_subject(self):
        dlg = WelcomeDialog()
        if dlg.exec() != QDialog.Accepted:
            return
        if not dlg.selected_subject:
            return

        self.main_window.close_all_session_windows()
        self.main_window.close()

        self.subject = dlg.selected_subject
        self.setWindowTitle(f"RSAC – Session Menu  [{self.subject}]")
        self._lbl_subject.setText(f"<b>Subject:</b> {self.subject}")
        self._apply_button_visibility()
        self.main_window.apply_subject_session(dlg)


class Toast(QDialog):
    """A short-lived, colored notification shown in the bottom-right corner."""

    _active: set["Toast"] = set()

    def __init__(
        self,
        message: str,
        parent: QWidget | None = None,
        duration_ms: int = 3000,
        success: bool = True,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)

        # Keep the toast alive while it is visible; otherwise the Python wrapper
        # can be garbage-collected before Qt has a chance to show it.
        Toast._active.add(self)
        self.destroyed.connect(lambda: Toast._active.discard(self))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        bg_color = "#2ca02c" if success else "#d62728"
        frame = QFrame(self)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
            QLabel {{
                color: white;
                font-size: 13px;
            }}
        """)

        inner = QHBoxLayout(frame)
        inner.setContentsMargins(12, 8, 12, 8)

        self.label = QLabel(message)
        self.label.setWordWrap(True)
        inner.addWidget(self.label)

        layout.addWidget(frame)

        self.adjustSize()
        width = min(self.width(), 400)
        self.resize(width, self.height())
        self._position(parent)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)
        self._timer.start(duration_ms)

    def _position(self, parent: QWidget | None) -> None:
        if parent is not None:
            geo = parent.geometry()
            x = geo.right() - self.width() - 20
            y = geo.bottom() - self.height() - 20
        else:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 20
            y = screen.bottom() - self.height() - 20
        self.move(max(0, x), max(0, y))

    @classmethod
    def show_toast(
        cls,
        message: str,
        parent: QWidget | None = None,
        duration_ms: int = 3000,
        success: bool = True,
    ) -> "Toast":
        """Create and display a toast.  Named 'show_toast' to avoid shadowing
        QWidget.show(), which would make the toast's own show() call fail."""
        toast = cls(message, parent, duration_ms, success)
        toast.show()
        return toast


def _metric_caption(code: str) -> str:
    """The on-screen caption for a metric code, e.g. 'ttc' -> 'Time to Complete Exercise'.

    Also resolves the "pre" metrics, whose captions live in PRE_METRIC_LABEL_MAP
    under their storage key rather than their UI key ('mwr' is published from
    'mwrp'). Falls back to the bare code so an unmapped metric is still enterable.
    """
    for label, mapped in METRIC_LABEL_MAP.items():
        if mapped == code:
            return label

    for pre_key, cfg in PRE_METRIC_ALIASES.items():
        if cfg.get("ui_key") != code:
            continue
        for label, mapped in PRE_METRIC_LABEL_MAP.items():
            if mapped == pre_key:
                return label

    for label, mapped in PRE_METRIC_LABEL_MAP.items():
        if mapped == code:
            return label

    return code


def _metrics_for_exercise(exerc_abb: str) -> list[str]:
    """The metric codes an exercise is scored on.

    PROFICIENCY_BASELINES is the single source of truth here — it is what
    AttemptProcessor.metrics_complete validates against and what compute_200_scores
    can actually score. EXERCISE_METRICS is only a fallback for display.
    """
    try:
        from exercise_proficiency_scores import PROFICIENCY_BASELINES
    except Exception as e:
        _warn_normative_tables_unavailable("PROFICIENCY_BASELINES", e)
        return list(EXERCISE_METRICS.get(exerc_abb, []))
    codes = list((PROFICIENCY_BASELINES.get(exerc_abb) or {}).keys())
    return codes or list(EXERCISE_METRICS.get(exerc_abb, []))


class AttemptEntryDialog(QDialog):
    """Manual entry of one attempt, as an alternative to screenshot OCR.

    Produces the same five-key attempt dict that extract_from_screenshot returns,
    so AttemptProcessor and the whole NAED chain treat it identically.

    The right-hand columns are the transcription guard: every raw value is scored
    live against the exercise's baselines and shown with its PASS/FAIL, and the
    summed Overall Score is checked against the exercise's proficiency floor and
    validity ceiling. A mistyped number is visible before it is committed.
    """

    def __init__(self, subject: str, expected_abb: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Add Attempt")
        self.setMinimumWidth(620)
        self.subject = subject
        self._rows: dict[str, dict[str, QWidget]] = {}
        self._result: dict[str, Any] | None = None

        outer = QVBoxLayout(self)

        header = QLabel(f"Subject: <b>{subject}</b>")
        outer.addWidget(header)

        # Exercise + timestamp
        top = QGridLayout()
        top.addWidget(QLabel("Exercise:"), 0, 0)
        self.cbo_exercise = QComboBox()
        for abb, info in sorted(
            EXERCISE_DEFS.items(), key=lambda kv: kv[1].get("exerc_number", 0)
        ):
            self.cbo_exercise.addItem(f"{info.get('exerc_full', abb)} ({abb})", userData=abb)
        if expected_abb:
            idx = self.cbo_exercise.findData(expected_abb)
            if idx >= 0:
                self.cbo_exercise.setCurrentIndex(idx)
        top.addWidget(self.cbo_exercise, 0, 1)

        self.lbl_expected = QLabel("")
        if expected_abb:
            expected_full = EXERCISE_DEFS.get(expected_abb, {}).get("exerc_full", expected_abb)
            self.lbl_expected.setText(f"Curriculum expects: <b>{expected_full}</b>")
            self.lbl_expected.setStyleSheet("color: #666666;")
        top.addWidget(self.lbl_expected, 0, 2)

        top.addWidget(QLabel("Date / time:"), 1, 0)
        self.txt_timestamp = QLineEdit(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        top.addWidget(self.txt_timestamp, 1, 1)

        self.chk_incomplete = QCheckBox("Attempt was Incomplete (not scored)")
        top.addWidget(self.chk_incomplete, 1, 2)
        outer.addLayout(top)

        # Metric grid, rebuilt whenever the exercise changes
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._grid_host)
        scroll.setMinimumHeight(260)
        outer.addWidget(scroll, stretch=1)

        self.lbl_summary = QLabel("")
        self.lbl_summary.setWordWrap(True)
        outer.addWidget(self.lbl_summary)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._btn_ok = buttons.button(QDialogButtonBox.Ok)
        self._btn_ok.setText("Add Attempt")
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self.cbo_exercise.currentIndexChanged.connect(self._rebuild_fields)
        self.chk_incomplete.toggled.connect(self._recompute)
        self._rebuild_fields()

    # -- construction -------------------------------------------------------

    def current_abb(self) -> str:
        return str(self.cbo_exercise.currentData() or "")

    def _rebuild_fields(self) -> None:
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._rows.clear()

        headers = ["Metric", "Raw value", "Score /200", "Result"]
        for c, text in enumerate(headers):
            lbl = QLabel(f"<b>{text}</b>")
            self._grid.addWidget(lbl, 0, c)

        codes = _metrics_for_exercise(self.current_abb())
        if not codes:
            self._grid.addWidget(
                QLabel("No baselines for this exercise — it cannot be scored."), 1, 0, 1, 4
            )
            self._recompute()
            return

        for r, code in enumerate(codes, start=1):
            caption = QLabel(f"{_metric_caption(code)}  ({code})")
            edit = QLineEdit()
            edit.setPlaceholderText("as shown on screen")
            edit.textChanged.connect(self._recompute)
            score = QLabel("—")
            verdict = QLabel("")
            self._grid.addWidget(caption, r, 0)
            self._grid.addWidget(edit, r, 1)
            self._grid.addWidget(score, r, 2)
            self._grid.addWidget(verdict, r, 3)
            self._rows[code] = {"edit": edit, "score": score, "verdict": verdict}

        self._recompute()

    # -- live scoring -------------------------------------------------------

    def metrics_canonical(self) -> dict[str, float]:
        """Raw values the tutor has actually filled in."""
        out: dict[str, float] = {}
        for code, widgets in self._rows.items():
            text = widgets["edit"].text().strip()
            if not text:
                continue
            try:
                out[code] = float(text.replace(",", "."))
            except ValueError:
                continue
        return out

    def _recompute(self) -> None:
        """Score what has been entered so far and update the echo columns."""
        # Fields stay enabled when Incomplete is ticked: log_incomplete still
        # records time-to-complete, so 'ttc' remains worth entering.
        incomplete = self.chk_incomplete.isChecked()
        if incomplete:
            for widgets in self._rows.values():
                widgets["score"].setText("—")
                widgets["verdict"].setText("")
            self.lbl_summary.setText(
                "Marked <b>Incomplete</b>. Only the attempt count and time-to-complete "
                "are recorded; nothing is added to the Clean CSV."
            )
            self._btn_ok.setEnabled(True)
            return

        abb = self.current_abb()
        metrics = self.metrics_canonical()

        try:
            from attempt_csv import compute_200_scores, simulator_scale_overall
        except Exception as e:
            self.lbl_summary.setText(f"Cannot score: {type(e).__name__}: {e}")
            self._btn_ok.setEnabled(False)
            return

        scored = compute_200_scores(abb, metrics)
        # compute_200_scores now returns canonical scores (0..200, PASS at 100) for
        # every metric, so the PASS check compares them directly. The Overall Score
        # is shown on the SIMULATOR's scale so it can be checked against the score
        # screen, which is why it is summed separately rather than from these values.
        by_code: dict[str, float] = {}
        for _raw_col, _raw_val, col_200, score_200 in scored:
            by_code[col_200.replace("_score_200", "")] = score_200
        overall = simulator_scale_overall(abb, metrics)

        for code, widgets in self._rows.items():
            if code in by_code:
                widgets["score"].setText(f"{by_code[code]:.2f}")
                passed = by_code[code] >= MASTERY_THRESHOLD
                widgets["verdict"].setText("PASS" if passed else "FAIL")
                widgets["verdict"].setStyleSheet(
                    "color: green; font-weight: bold;" if passed else "color: red; font-weight: bold;"
                )
            else:
                widgets["score"].setText("—")
                widgets["verdict"].setText("")
                widgets["verdict"].setStyleSheet("")

        missing = [c for c in self._rows if c not in metrics]
        parts: list[str] = [f"Overall Score (computed): <b>{overall:.2f}</b>"]

        floor = get_overall_score_proficiency_floor(abb)
        ceiling = get_overall_score_ceiling(abb)
        if floor is not None:
            parts.append(f"proficiency floor {floor:.0f}")
        if ceiling is not None:
            parts.append(f"ceiling {ceiling:.0f}")
        summary = " &nbsp;|&nbsp; ".join(parts)

        if missing:
            summary += (
                "<br><span style='color:#B00000;'>Missing: "
                + ", ".join(sorted(missing))
                + "</span>"
            )
        elif ceiling is not None and overall > ceiling:
            summary += (
                "<br><span style='color:#B00000;'>Overall Score exceeds the ceiling — "
                "check for a mistyped value.</span>"
            )
        else:
            summary += (
                "<br><span style='color:#444444;'>Compare this with the Overall Score "
                "shown on the simulator before adding.</span>"
            )

        self.lbl_summary.setText(summary)
        self._btn_ok.setEnabled(not missing)

    # -- output -------------------------------------------------------------

    def _on_ok(self) -> None:
        abb = self.current_abb()
        timestamp = self.txt_timestamp.text().strip()
        if not timestamp:
            QMessageBox.warning(self, "Add Attempt", "Please enter the attempt date and time.")
            return

        full = str(EXERCISE_DEFS.get(abb, {}).get("exerc_full", abb))

        if self.chk_incomplete.isChecked():
            metrics = self.metrics_canonical()
            self._result = {
                "exercise_abbreviation": abb,
                "exercise_full_name": full,
                "overall_score_raw": "Incomplete",
                "timestamp": timestamp,
                "metrics_canonical": metrics,
            }
            self.accept()
            return

        metrics = self.metrics_canonical()
        missing = [c for c in self._rows if c not in metrics]
        if missing:
            QMessageBox.warning(
                self,
                "Add Attempt",
                "These metrics are missing or not numeric:\n\n"
                + "\n".join(f"{_metric_caption(c)} ({c})" for c in sorted(missing)),
            )
            return

        try:
            from attempt_csv import simulator_scale_overall
        except Exception as e:
            QMessageBox.critical(self, "Add Attempt", f"Cannot score the attempt: {e}")
            return

        # Stored on the simulator's scale so it stays comparable with the Overall
        # Score the simulator itself reports for the same attempt.
        overall = simulator_scale_overall(abb, metrics)

        self._result = {
            "exercise_abbreviation": abb,
            "exercise_full_name": full,
            "overall_score_raw": round(overall, 2),
            "timestamp": timestamp,
            "metrics_canonical": metrics,
        }
        self.accept()

    def attempt(self) -> dict[str, Any] | None:
        """The attempt dict, or None if the dialog was cancelled."""
        return self._result


class LiveSessionWindow(QDialog):
    """The live adaptive loop: one attempt in, NAED decision out.

    Attempts are produced by manual entry (AttemptEntryDialog), which works at
    any site. They pass through AttemptProcessor and then _on_appended, which
    enforces the decision point: no further attempts until the tutor answers a
    NAED-1 ACT.

    AttemptProcessor is deliberately kept free of any knowledge of where an
    attempt came from, so an automated producer can be added here without
    touching the decision logic.
    """

    def __init__(self, main_window: MainWindow, subject: str = ""):
        super().__init__(None)
        self.setWindowTitle("RSAC – Live Session")
        self.setMinimumWidth(560)

        self.main_window = main_window
        self.subject = subject.strip()
        self._mode = "new"  # "new" or "append"

        self._active_clean_path: str = ""
        self._act_pending = False

        ensure_config_file()

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 10)

        # CSV target row (automatic decision, no user choice)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("CSV target:"))
        self.lbl_mode = QLabel("")
        self.lbl_mode.setWordWrap(True)
        row2.addWidget(self.lbl_mode, stretch=1)
        layout.addLayout(row2)

        # New/Append controls
        row3 = QHBoxLayout()
        self.lbl_subject = QLabel("Subject:")
        self.txt_subject = QLineEdit()
        self.txt_subject.setPlaceholderText("e.g., Subject01")
        row3.addWidget(self.lbl_subject)
        row3.addWidget(self.txt_subject, stretch=1)

        self.lbl_existing = QLabel("Existing file:")
        self.cbo_existing = QComboBox()
        self.btn_refresh_existing = QPushButton("Refresh")
        self.btn_refresh_existing.clicked.connect(self._refresh_existing_list)
        row3.addWidget(self.lbl_existing)
        row3.addWidget(self.cbo_existing, stretch=2)
        row3.addWidget(self.btn_refresh_existing)
        layout.addLayout(row3)

        # -- Manual entry ----------------------------------------------------
        manual_row = QHBoxLayout()
        self.btn_add_manual = QPushButton("Add Attempt…")
        self.btn_add_manual.setDefault(True)
        self.btn_add_manual.clicked.connect(self.add_attempt_manually)
        manual_row.addWidget(self.btn_add_manual)
        hint = QLabel("Type the metrics shown on the simulator's results screen.")
        hint.setStyleSheet("color: #666666;")
        manual_row.addWidget(hint, stretch=1)
        layout.addLayout(manual_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        self._auto_select_mode()

    def _refresh_existing_list(self):
        self.cbo_existing.clear()
        for item in self.main_window.clean_files:
            name = item.get("filename", "")
            path = item.get("path", "")
            if name and path:
                self.cbo_existing.addItem(name, userData=path)

    def _auto_select_mode(self):
        """Automatically choose between new CSV or append to existing CSV."""
        if not self.subject:
            self._mode = "new"
            self.lbl_mode.setText("New clean CSV")
            self.lbl_subject.setVisible(True)
            self.txt_subject.setVisible(True)
            self.txt_subject.setText("")
            self.lbl_existing.setVisible(False)
            self.cbo_existing.setVisible(False)
            self.btn_refresh_existing.setVisible(False)
            return

        existing_path = _find_latest_clean_file_for_subject(
            self.main_window.clean_dir, self.subject
        )
        if existing_path and os.path.isfile(existing_path):
            self._mode = "append"
            self._active_clean_path = existing_path
            self.lbl_mode.setText(
                f"Appending to existing clean CSV: {os.path.basename(existing_path)}"
            )
            self.lbl_subject.setVisible(False)
            self.txt_subject.setVisible(False)
            self.lbl_existing.setVisible(False)
            self.cbo_existing.setVisible(False)
            self.btn_refresh_existing.setVisible(False)
        else:
            self._mode = "new"
            self.lbl_mode.setText("New clean CSV")
            self.lbl_subject.setVisible(True)
            self.txt_subject.setVisible(True)
            self.txt_subject.setText(self.subject)
            self.lbl_existing.setVisible(False)
            self.cbo_existing.setVisible(False)
            self.btn_refresh_existing.setVisible(False)

    def _parse_subject_from_clean_filename(self, filename: str) -> str:
        m = CLEAN_PATTERN_WITH_SUBJECT.match(filename or "")
        if m:
            return (m.group(1) or "").strip()
        return ""

    def _resolve_target_clean_path_and_subject(self) -> tuple[str, str]:
        """Where this session's attempts go, and whose they are.

        Deliberately independent of the watched folder — manual entry needs this
        too, and it must work with no simulator configured at all.
        """
        if self._mode == "new":
            subject = self.txt_subject.text().strip()
            if not subject:
                raise ValueError("Please enter a subject name.")

            clean_dir = self.main_window.clean_dir
            os.makedirs(clean_dir, exist_ok=True)
            fname = build_clean_output_filename(subject, datetime.now())
            clean_path = os.path.join(clean_dir, fname)
            return clean_path, subject

        clean_path = self._active_clean_path
        if not clean_path or not os.path.isfile(clean_path):
            raise ValueError("Selected MimicClean CSV does not exist.")

        filename = os.path.basename(clean_path)
        subject = self._parse_subject_from_clean_filename(filename) or "Unknown"
        return clean_path, subject

    # -- manual entry producer ----------------------------------------------

    def add_attempt_manually(self):
        """Enter one attempt by hand and run it through the same live loop.

        This is the portable producer: it needs no simulator, no watched folder
        and no Tesseract.
        """
        if self._act_pending:
            QMessageBox.information(
                self,
                "Decision pending",
                "Please answer the open Recommendations prompt before adding "
                "another attempt.",
            )
            return

        try:
            clean_path, subject = self._resolve_target_clean_path_and_subject()
        except Exception as e:
            QMessageBox.warning(self, "Add Attempt", str(e))
            return

        processor = AttemptProcessor(subject=subject, clean_path=clean_path)

        dlg = AttemptEntryDialog(
            subject=subject, expected_abb=processor.expected_exercise(), parent=self
        )
        if dlg.exec() != QDialog.Accepted:
            return
        result = dlg.attempt()
        if not result:
            return

        matches, attempt_full, expected_full = processor.check_exercise(result)
        if not matches:
            reply = QMessageBox.question(
                self,
                "Exercise Mismatch",
                f"This attempt is not the exercise this subject is expected to be "
                f"doing according to the history file.\n\n"
                f"Entered exercise: {attempt_full}\n"
                f"Expected exercise: {expected_full}\n\n"
                f"Record it anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._set_status("Attempt discarded (exercise mismatch).")
                return

        exercise_full = str(result.get("exercise_full_name") or "")

        if processor.is_incomplete(result):
            try:
                inc_path = processor.log_incomplete(result)
            except Exception as e:
                QMessageBox.critical(self, "Add Attempt", f"Could not record it: {e}")
                return
            self._active_clean_path = clean_path
            self._set_status(
                f"Incomplete attempt ({exercise_full}) logged to {os.path.basename(inc_path)}."
            )
            try:
                self.main_window.refresh_lists()
            except Exception:
                pass
            return

        exerc_abb = str(result.get("exercise_abbreviation") or "")
        metrics_can = result.get("metrics_canonical") or {}
        if not processor.metrics_complete(exerc_abb, metrics_can):
            QMessageBox.warning(
                self,
                "Add Attempt",
                "Some metrics this exercise is scored on are missing, so the "
                "attempt cannot be scored. Please fill in every metric.",
            )
            return

        try:
            out_path = processor.append(result)
        except Exception as e:
            QMessageBox.critical(self, "Add Attempt", f"Could not write the attempt: {e}")
            return

        self._active_clean_path = out_path
        self._set_status(f"Appended to {os.path.basename(out_path)}")
        self._on_appended(out_path, subject, exercise_full)

    def _set_status(self, msg: str):
        self.lbl_status.setText(msg)

    def _on_appended(self, clean_path: str, subject: str, exercise_full_name: str):
        try:
            self.main_window.refresh_lists()
        except Exception:
            pass

        self.main_window._open_or_refresh_datashow_for_clean(
            clean_path=clean_path,
            subject=subject,
            exercise_full_name=exercise_full_name,
        )

        # NAED-1 == ACT is the enforced decision point: surface Recommendations
        # and refuse further attempts until the tutor answers. The producer is
        # blocked by disabling its button, which clears in _on_act_resolved.
        ds_win = self.main_window._find_datashow_window(clean_path)
        if ds_win is not None:
            naed1 = getattr(ds_win, "_last_naed1_details", None) or {}
            if naed1.get("decision") == "ACT":
                self._act_pending = True
                self.btn_add_manual.setEnabled(False)
                self._set_status("NAED-1: ACT — waiting for Recommendations decision...")
                ds_win.show_recommendations()
                # Connect the Recommendations window's decision_made to unblock
                if ds_win._recommendations_windows:
                    rec_win = ds_win._recommendations_windows[-1]
                    rec_win.decision_made.connect(self._on_act_resolved)
                else:
                    # Recommendations could not be opened — do not deadlock the
                    # session on a window that is not there.
                    self._on_act_resolved()

    def _on_act_resolved(self):
        """Called when the tutor clicks YES or NO in the Recommendations window."""
        self._act_pending = False
        self.btn_add_manual.setEnabled(True)
        self._set_status("Decision recorded.")


def _generate_retrospective_history(clean_path: str) -> str:
    """Generate a retrospective analysis history file from a single-subject clean file.

    For each exercise, starting from 3 attempts, runs NAED-1/2/3 incrementally.
    Writes a history entry for each analysis point.  Stops an exercise when the
    decision is something other than KEEP.
    """
    all_rows = classify_clean_file(clean_path)
    enrich_rows_with_exercise_defs(all_rows, EXERCISE_DEFS)

    if not all_rows:
        raise RuntimeError("No valid rows found in the clean file.")

    subject = (all_rows[0].get("subject") or "").strip()
    if not subject:
        raise RuntimeError("Could not determine subject from clean file.")

    # --- output path ---
    script_dir = _script_dir()
    hist_dir = os.path.join(script_dir, "analysis_history")
    os.makedirs(hist_dir, exist_ok=True)

    base_name = os.path.basename(clean_path)
    rest = base_name[len("MimicClean_"):] if base_name.startswith("MimicClean_") else base_name
    out_name = "History_" + rest
    out_path = os.path.join(hist_dir, out_name)

    # --- group rows by exercise (preserve file order) ---
    from collections import OrderedDict
    exercises: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for rec in all_rows:
        ex = (rec.get("exercise") or "").strip()
        if ex:
            exercises.setdefault(ex, []).append(rec)

    # --- helpers ---
    def _sanitize(x: Any) -> str:
        s = "" if x is None else str(x)
        s = s.replace("\r", " ").replace("\n", " ").replace("\t", " ")
        s = s.replace("\u2265", ">=").replace("\u2264", "<=")
        s = s.replace(",", " ")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _get_any(d: dict, *keys: str) -> Any:
        det = d.get("details", [])
        if isinstance(det, list):
            for key in keys:
                for it in det:
                    if isinstance(it, (tuple, list)) and len(it) >= 2 and str(it[0]).strip() == key:
                        return it[1]
        for key in keys:
            if key in d:
                return d.get(key)
        return None

    # --- iterate exercises and build history entries ---
    # Each entry is (exercise_name, n_attempts, [4 history lines])
    # so we can insert each block right after the nth attempt line.
    base_ts = datetime.now()
    ts_offset = 0
    history_entries: list[tuple[str, int, list[str]]] = []

    for exercise_name, exercise_rows in exercises.items():
        candidate_score200_keys = [k for k, _ in SCORE_COLUMNS if k.endswith("_score_200")]
        score200_keys = [
            k for k in candidate_score200_keys
            if any((r.get(k) not in (None, "")) for r in exercise_rows)
        ]

        for rec in exercise_rows:
            if "score_200_pass_total" not in rec:
                rec["score_200_pass_total"] = compute_score200_pass_total(rec, score200_keys)

        for n_attempts in range(3, len(exercise_rows) + 1):
            subset = exercise_rows[:n_attempts]

            naed1 = compute_naed1_metrics_and_decision(
                exercise_rows=subset,
                score200_keys=score200_keys,
                subject=subject,
                current_exercise=exercise_name,
                all_rows=all_rows,
            )

            if naed1.get("decision") != "ACT":
                continue

            naed2 = compute_naed2_decision(
                all_attempt_rows=subset,
                naed1_metrics=naed1,
            )

            naed2_dec = (naed2.get("decision") or "").strip()

            naed3: dict[str, Any] = {}
            if naed2_dec in ("UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL"):
                exerc_abb = (subset[0].get("exerc_abb") or "").strip()
                try:
                    naed3 = compute_naed3_recommendation(exerc_abb, naed2_dec, subject=subject)
                except Exception:
                    naed3 = {}

            from datetime import timedelta as _td
            ts_str = (base_ts + _td(seconds=ts_offset)).strftime("%Y-%m-%d %H:%M:%S")
            ts_offset += 1
            subj_s = _sanitize(subject)
            ex_s = _sanitize(exercise_name)

            def _kv_line(tag: str, items: list[tuple[str, Any]]) -> str:
                parts: list[str] = ["History", subj_s, ex_s, ts_str, tag]
                for k, v in items:
                    parts.append(_sanitize(k))
                    parts.append(_sanitize(v))
                return ",".join(parts)

            naed1_items = [
                ("window_n", _get_any(naed1, "window_n")),
                ("total_n", _get_any(naed1, "total_n")),
                ("reason", _get_any(naed1, "reason", "rationale")),
                ("confidence", _get_any(naed1, "confidence")),
                ("decision", _get_any(naed1, "decision")),
            ]
            naed1_items = [(k, v) for k, v in naed1_items if v is not None and str(v).strip() != ""]

            order2 = [
                "n", "Rm_last", "slope_m", "mastery_bottleneck", "bottleneck_Rk",
                "mean_other_Rk", "level_now", "level_now_norm", "pass_rate_all",
                "pass_rate_weighted", "consec_pass_all", "trailing_streak",
                "directionality_plain", "directionality_weighted", "volatility_weighted",
                "spread", "stability", "outlier_downweighting",
            ]
            naed2_items: list[tuple[str, Any]] = []
            for k in order2:
                v = _get_any(naed2, k)
                if v is not None and str(v).strip() != "":
                    naed2_items.append((k, v))

            fb_keys = [
                "mastery_bottleneck", "bottleneck_Rk", "mean_other_Rk", "mean_pass_total",
                "worst_metric", "worst_metric_pass_frac", "avg_other_metric_pass_frac",
                "feedback_trigger",
            ]
            for k in fb_keys:
                v = _get_any(naed2, k)
                if v is not None and str(v).strip() != "":
                    naed2_items.append((k, v))

            rat = _get_any(naed2, "Rationale", "rationale")
            log = _get_any(naed2, "Logical Rationale", "logical_rationale")
            dec2 = _get_any(naed2, "Decision", "decision")
            obs2 = _get_any(naed2, "Observation", "observation")
            if rat is not None and str(rat).strip() != "":
                naed2_items.append(("Rationale", rat))
            if log is not None and str(log).strip() != "":
                naed2_items.append(("Logical Rationale", log))
            if obs2 is not None and str(obs2).strip() != "":
                naed2_items.append(("Observation", obs2))
            if dec2 is not None and str(dec2).strip() != "":
                naed2_items.append(("Decision", dec2))

            naed3_items = [
                ("status", _get_any(naed3, "status")),
                ("message", _get_any(naed3, "message")),
                ("connection_used", _get_any(naed3, "connection_used")),
                ("next_exercise_abb", _get_any(naed3, "next_exercise_abb")),
                ("next_exercise_full", _get_any(naed3, "next_exercise_full")),
            ]
            naed3_items = [(k, v) for k, v in naed3_items if v is not None and str(v).strip() != ""]

            line_naed1 = _kv_line("NAED-1", naed1_items)
            line_naed2 = _kv_line("NAED-2", naed2_items)
            line_naed3 = _kv_line("NAED-3", naed3_items)
            line_user = ",".join(["History", subj_s, ex_s, ts_str, "user_decision", "retrospective"])

            history_entries.append((exercise_name, n_attempts, [line_naed1, line_naed2, line_naed3, line_user]))

            if naed2_dec != "KEEP":
                break

    # --- build file: attempt lines + history entries after each nth attempt ---
    with open(clean_path, "r", encoding="utf-8-sig", errors="replace") as f:
        raw_lines = f.read().splitlines()

    lines: list[str] = []
    for ln in raw_lines:
        if ln.strip():
            lines.append(ln.rstrip("\n"))

    if history_entries:
        import csv as _csv

        def _is_datetime_quick(s: str) -> bool:
            return bool(re.match(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}", (s or "").strip()))

        def _exercise_from_line(line: str) -> str:
            try:
                fields = next(_csv.reader([line]))
            except Exception:
                fields = [p.strip() for p in line.split(",")]
            if len(fields) >= 3:
                f1 = (fields[1] or "").strip()
                f2 = (fields[2] or "").strip()
                return f2 if _is_datetime_quick(f1) else f1
            return ""

        # Insert in reverse order so earlier insertions don't shift later indices
        for ex_name, n_at, hist_lines in reversed(history_entries):
            # Find the nth attempt line for this exercise (counting only attempt lines)
            count = 0
            target_idx = -1
            for i, ln in enumerate(lines):
                if ln.startswith("History"):
                    continue
                if ln.startswith(subject):
                    ex_i = _exercise_from_line(ln)
                    if ex_i.strip() == ex_name.strip():
                        count += 1
                        if count == n_at:
                            target_idx = i
                            break
            if target_idx >= 0:
                insert_at = target_idx + 1
                for off, hl in enumerate(hist_lines):
                    lines.insert(insert_at + off, hl)

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")

    return out_path


# =============================================================================
#  [SEC-05] MATHEMATICAL UTILITIES
# =============================================================================


def clamp(x: float, lo: float, hi: float) -> float:
    return lo if x < lo else hi if x > hi else x


def compute_score200_pass_total(
    rec: dict[str, Any],
    score200_keys: list[str],
) -> int:
    count = 0
    for k in score200_keys:
        try:
            if float(rec.get(k)) >= 100:
                count += 1
        except (TypeError, ValueError):
            pass
    return count


def overall_score_norm_divisor(exerc_abb: str) -> float:
    """Divisor that puts an exercise's overall_score on a 0..1 scale.

    The exercise's own reference ceiling, because the achievable overall_score is
    the sum over its metrics and exercises do not all have the same number of them
    (kr1 has 6, rtt has 8). A single flat divisor made the normalised value mean
    different things on different exercises and saturated every rtt attempt above
    1200 to exactly 1.0.

    Falls back to OVERALL_SCORE_MAX when the exercise is unknown.
    """
    ceiling = get_overall_score_ceiling(exerc_abb)
    if ceiling and ceiling > 0:
        return float(ceiling)
    return OVERALL_SCORE_MAX


def compute_overall_norm(rec: dict[str, Any]) -> Optional[float]:
    """An attempt's overall_score as 0..1 within its own exercise.

    Still clamped at 1.0: metric scores are uncapped above cutoff, so an
    exceptional attempt can exceed the reference ceiling, but everything
    downstream treats this series as 0..1. That now affects ~0.2% of attempts
    instead of every high-scoring attempt on the larger exercises.
    """
    v = rec.get("overall_score")
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    divisor = overall_score_norm_divisor((rec.get("exerc_abb") or "").strip())
    return clamp(x / divisor, 0.0, 1.0)


def compute_deltas(vals: list[float]) -> list[float]:
    if len(vals) < 2:
        return []
    return [vals[i] - vals[i - 1] for i in range(1, len(vals))]


def compute_spread(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return float(max(vals) - min(vals))


def compute_std(vals: list[float]) -> float:
    n = len(vals)
    if n <= 1:
        return 0.0
    mu = sum(vals) / n
    var = sum((v - mu) ** 2 for v in vals) / n
    return float(math.sqrt(var))



def compute_median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return float(s[mid])
    return float((s[mid - 1] + s[mid]) / 2.0)


def compute_mad(vals: list[float]) -> float:
    # Median Absolute Deviation (MAD). Returns 0 if vals empty.
    if not vals:
        return 0.0
    med = compute_median(vals)
    devs = [abs(v - med) for v in vals]
    return float(compute_median(devs))


def compute_robust_weights(vals: list[float], z0: float = 3.5) -> list[float]:
    # Tukey-style soft downweighting based on robust z-scores.
    # z = 0.6745 * (x - median) / MAD
    # weight = 1 / (1 + (|z|/z0)^2)
    # If MAD == 0, all weights = 1.
    if not vals:
        return []
    med = compute_median(vals)
    mad = compute_mad(vals)
    if mad <= 0:
        return [1.0 for _ in vals]

    out = []
    for v in vals:
        z = 0.6745 * (v - med) / mad
        az = abs(z)
        w = 1.0 / (1.0 + (az / z0) ** 2)
        out.append(float(clamp(w, 0.05, 1.0)))
    return out


def compute_exp_weights(n: int, half_life: float) -> list[float]:
    # Exponential recency weights, normalized later.
    # Most recent point gets weight 1.0, previous gets 0.5^(1/half_life), etc.
    if n <= 0:
        return []
    if half_life <= 0:
        return [1.0 for _ in range(n)]
    lam = math.log(2.0) / float(half_life)
    # i=0 is oldest, i=n-1 is newest
    return [float(math.exp(-lam * (n - 1 - i))) for i in range(n)]


def weighted_mean(vals: list[float], weights: list[float]) -> float:
    if not vals or not weights or len(vals) != len(weights):
        return 0.0
    wsum = sum(weights)
    if wsum <= 0:
        return 0.0
    return float(sum(v * w for v, w in zip(vals, weights)) / wsum)


def weighted_slope(vals: list[float], weights: list[float]) -> float:
    # Weighted least-squares slope vs attempt index (1..N).
    n = len(vals)
    if n <= 1 or not weights or len(weights) != n:
        return 0.0

    xs = list(range(1, n + 1))
    wsum = sum(weights)
    if wsum <= 0:
        return 0.0

    xbar = sum(w * x for w, x in zip(weights, xs)) / wsum
    ybar = sum(w * y for w, y in zip(weights, vals)) / wsum

    denom = sum(w * (x - xbar) ** 2 for w, x in zip(weights, xs))
    if denom <= 0:
        return 0.0

    numer = sum(w * (x - xbar) * (y - ybar) for w, x, y in zip(weights, xs, vals))
    return float(numer / denom)


def weighted_std(vals: list[float], weights: list[float]) -> float:
    # Weighted population std
    n = len(vals)
    if n <= 1 or not weights or len(weights) != n:
        return 0.0
    wsum = sum(weights)
    if wsum <= 0:
        return 0.0
    mu = weighted_mean(vals, weights)
    var = sum(w * (v - mu) ** 2 for v, w in zip(vals, weights)) / wsum
    return float(math.sqrt(max(0.0, var)))


def trailing_true_streak(flags: list[bool]) -> int:
    # Number of consecutive True values at the end of the sequence.
    streak = 0
    for f in reversed(flags):
        if f:
            streak += 1
        else:
            break
    return streak


def compute_directionality(vals: list[float]) -> float:
    # least-squares slope vs attempt index (1..N)
    n = len(vals)
    if n <= 1:
        return 0.0
    xs = list(range(1, n + 1))
    xbar = sum(xs) / n
    ybar = sum(vals) / n
    denom = sum((x - xbar) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    numer = sum((x - xbar) * (y - ybar) for x, y in zip(xs, vals))
    return float(numer / denom)


def compute_max_consec_true(flags: list[bool]) -> int:
    if not flags:
        return 0
    best = 0
    cur = 0
    for f in flags:
        if f:
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best


def compute_pass_rate(pass_flags: list[bool]) -> float:
    if not pass_flags:
        return 0.0
    return float(sum(1 for f in pass_flags if f) / len(pass_flags))


# =============================================================================
#  [SEC-06] NAED-1: DATA SUFFICIENCY ASSESSMENT
# =============================================================================

NAED1_MIN_N = 3
NAED1_FORCE_N = 6            # from 6 attempts on -> forced ACT
NAED1_WINDOW_MAX = 5         # for gating math, only consider 3..5 attempts
NAED1_NEED_MORE_N = 2
P_TARGET = 13               # maturity reference point (tune later)
NAED1_CONFIDENCE_THRESHOLD = 0.60

# Fallback divisor only, for an exercise whose reference ceiling is unknown.
# The real divisor is per-exercise: see overall_score_norm_divisor().
OVERALL_SCORE_MAX = 1200.0

def compute_similarity(prev_ex: str, cur_ex: str) -> float:
    # v7.0: similarity using exerc_cat metadata (exerc_series/exerc_family removed)
    # - same category => 0.7
    # - else => 0.0
    # Accepts abbreviations or full exercise names (rows usually store full names).
    if not prev_ex or not cur_ex:
        return 0.0

    def _lookup(ex: str) -> dict:
        ex = (ex or "").strip()
        d = EXERCISE_DEFS.get(ex)
        if isinstance(d, dict):
            return d
        ex_low = ex.lower()
        for info in EXERCISE_DEFS.values():
            if isinstance(info, dict) and (info.get("exerc_full") or "").strip().lower() == ex_low:
                return info
        return {}

    p_cat = (_lookup(prev_ex).get("exerc_cat") or "").strip()
    c_cat = (_lookup(cur_ex).get("exerc_cat") or "").strip()

    if p_cat and c_cat and p_cat == c_cat:
        return 0.7
    return 0.0


def compute_maturity_from_history(
    all_rows: list[dict[str, Any]],
    subject: str,
    score200_keys: list[str],
) -> float:
    # Maturity = clamp(total_proficiencies / P_TARGET, 0, 1)
    # proficiency: pass_attempts >= 3 AND max_consecutive_pass >= 2 (per exercise)
    if not subject:
        return 0.0

    by_ex: dict[str, list[dict[str, Any]]] = {}
    for r in all_rows:
        if r.get("subject") != subject:
            continue
        ex = (r.get("exercise") or "").strip()
        if not ex:
            continue
        by_ex.setdefault(ex, []).append(r)

    prof_count = 0
    for ex, rs in by_ex.items():
        rs.sort(key=lambda rr: (rr.get("date_time") is None, rr.get("date_time") or datetime.min))

        flags = []
        for rec in rs:
            pass_total = rec.get("score_200_pass_total")
            if not isinstance(pass_total, int):
                pass_total = compute_score200_pass_total(rec, score200_keys)
                rec["score_200_pass_total"] = pass_total
            flags.append(pass_total == len(score200_keys))

        pass_attempts = sum(1 for f in flags if f)
        max_consec = compute_max_consec_true(flags)

        if pass_attempts >= 3 and max_consec >= 2:
            prof_count += 1

    return clamp(prof_count / float(P_TARGET), 0.0, 1.0)


def find_previous_exercise_for_subject(
    all_rows: list[dict[str, Any]],
    subject: str,
    cur_exercise: str,
    cur_window_start_dt: Optional[datetime],
) -> str:
    if not subject or cur_window_start_dt is None:
        return ""

    prior = []
    for r in all_rows:
        if r.get("subject") != subject:
            continue
        ex = (r.get("exercise") or "").strip()
        dt = r.get("date_time")
        if not ex or dt is None:
            continue
        if dt < cur_window_start_dt and ex != cur_exercise:
            prior.append((dt, ex))

    if not prior:
        return ""

    prior.sort(key=lambda t: t[0], reverse=True)
    return prior[0][1]


def compute_naed1_metrics_and_decision(
    exercise_rows: list[dict[str, Any]],
    score200_keys: list[str],
    subject: str,
    current_exercise: str,
    all_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    # Goal:
    # - <3 attempts: WAIT (too soon)
    # - 3..5 attempts: compute confidence and decide WAIT/ACT
    # - >=6 attempts: MUST (force a decision); still compute metrics on last 5 for transparency

    total_n = len(exercise_rows)
    max_pass_total = len(score200_keys)

    if total_n < NAED1_MIN_N:
        return {
            "total_n": total_n,
            "window_n": total_n,
            "decision": "WAIT",
            "confidence": 0.0,
            "reason": f"Too few attempts (need {NAED1_MIN_N - total_n} more)",
            "metrics": {},
        }

    # choose window for the math: 3..5 attempts only
    if total_n <= NAED1_WINDOW_MAX:
        window_rows = exercise_rows[:]  # use all (3..5)
    else:
        window_rows = exercise_rows[-NAED1_WINDOW_MAX:]  # show last 5 for transparency

    window_n = len(window_rows)

    # pass-based metrics (per attempt)
    pass_flags: list[bool] = []
    pass_totals: list[int] = []
    for rec in window_rows:
        pt = rec.get("score_200_pass_total")
        if not isinstance(pt, int):
            pt = compute_score200_pass_total(rec, score200_keys)
            rec["score_200_pass_total"] = pt
        pass_totals.append(int(pt))
        pass_flags.append(int(pt) == max_pass_total)

    # overall-based metrics for directionality/deltas/volatility/spread/snr
    overall_norm_vals: list[float] = []
    for rec in window_rows:
        on = compute_overall_norm(rec)
        if on is not None:
            overall_norm_vals.append(float(on))
        else:
            # keep length consistent: treat missing as last value if possible, else 0
            if overall_norm_vals:
                overall_norm_vals.append(overall_norm_vals[-1])
            else:
                overall_norm_vals.append(0.0)

    deltas = compute_deltas(overall_norm_vals)
    directionality = compute_directionality(overall_norm_vals)
    volatility = compute_std(deltas)               # noise in change of overall_norm
    spread = compute_spread(overall_norm_vals)     # 0..1

    pass_rate = compute_pass_rate(pass_flags)
    consec_pass = compute_max_consec_true(pass_flags)

    # stability: high if volatility is small relative to spread, and spread not extreme
    eps = 1e-6
    if spread <= 0.0:
        vol_term = clamp(volatility / 0.10, 0.0, 1.0)  # arbitrary small scale when spread is ~0
    else:
        vol_term = clamp(volatility / (spread + eps), 0.0, 1.0)

    stability_from_vol = 1.0 - vol_term
    stability_from_spread = 1.0 - clamp(spread, 0.0, 1.0)
    stability = clamp(0.5 * stability_from_vol + 0.5 * stability_from_spread, 0.0, 1.0)

    signal_to_noise = abs(directionality) / (volatility + eps)
    snr_score = signal_to_noise / (signal_to_noise + 1.0)  # 0..1 saturating

    maturity = compute_maturity_from_history(all_rows, subject, score200_keys)

    win_start_dt = window_rows[0].get("date_time") if window_rows else None
    prev_ex = find_previous_exercise_for_subject(all_rows, subject, current_exercise, win_start_dt)
    similarity = compute_similarity(prev_ex, current_exercise)

    # data adequacy for 3..5: 3=>0.6, 4=>0.8, 5=>1.0
    data_score = clamp(window_n / 5.0, 0.0, 1.0)

    confidence = (
        0.20 * data_score +
        0.25 * stability +
        0.25 * snr_score +
        0.20 * maturity +
        0.10 * similarity
    )
    confidence = clamp(confidence, 0.0, 1.0)

    # overrides for ACT inside 3..5 regime
    override_act = False
    override_reason = ""

    if pass_flags and pass_flags[-1]:
        override_act = True
        override_reason = "Last attempt is PASS (all score_200 metrics passed)"

    if (not override_act) and (pass_rate >= (2.0 / 3.0)) and (consec_pass >= 2):
        override_act = True
        override_reason = "High pass_rate with consecutive passes"

    if (not override_act) and (pass_rate == 0.0) and (stability >= 0.70) and (directionality <= 0.0):
        override_act = True
        override_reason = "Stable stagnation on overall_score (likely stuck)"

    # Mastery-based override: if Rm_last is high enough, allow ACT even with marginal confidence
    naed1_mastery = compute_mastery_softmin_ewma(
        attempts=window_rows,
        metric_keys=score200_keys,
    )
    naed1_Rm_last = naed1_mastery["Rm_last"]
    if (not override_act) and (naed1_Rm_last >= RM_CORRIDOR_MID) and (stability >= 0.40):
        override_act = True
        override_reason = f"Rm_last ({naed1_Rm_last:.3f}) >= {RM_CORRIDOR_MID} with adequate stability"

    # final decision
    forced = False
    if total_n >= NAED1_FORCE_N:
        # Forced ACT after enough attempts (do not return a separate 'MUST' state)
        forced = True
        decision = "ACT"
        reason = f"{total_n} attempts reached (forced decision)"
        confidence = 1.0
    else:
        if override_act:
            decision = "ACT"
            reason = override_reason
        else:
            if confidence < NAED1_CONFIDENCE_THRESHOLD:
                decision = "WAIT"
                reason = f"Low confidence (need {NAED1_NEED_MORE_N} more attempts)"
            else:
                decision = "ACT"
                reason = "Confidence >= threshold"
    naed1_metrics = {
        "total_attempts_in_exercise": total_n,
        "window_n_used_for_metrics": window_n,
        "overall_norm_series": overall_norm_vals,
        "deltas_overall_norm": deltas,
        "directionality_overall_norm": directionality,
        "volatility_overall_norm": volatility,
        "spread_overall_norm": spread,
        "pass_totals_score200": pass_totals,
        "pass_rate": pass_rate,
        "consec_pass": consec_pass,
        "maturity": maturity,
        "prev_exercise": prev_ex,
        "similarity": similarity,
        "stability": stability,
        "signal_to_noise": signal_to_noise,
        "snr_score": snr_score,
        "data_score": data_score,
        "Rm_last_window": naed1_Rm_last,
        "confidence": confidence,
        "decision": decision,
        "reason": reason,
    }

    return {
        "total_n": total_n,
        "window_n": window_n,
        "decision": decision,
        "confidence": confidence,
        "reason": reason,
        "metrics": naed1_metrics,
    }


# =============================================================================
#  [SEC-07] NAED-1 DETAILS WINDOW
# =============================================================================

class NAED1DetailsWindow(QMainWindow):
    def __init__(self, title: str, details: dict[str, Any]):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(800, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)

        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        layout.addWidget(self.table)

        ui_metrics = details.get("metrics") or {}
        decision = details.get("decision", "")
        confidence = details.get("confidence", 0.0)
        reason = details.get("reason", "")

        rows_out: list[tuple[str, str]] = []

        # show most relevant metrics in readable order
        key_order = [
            "total_attempts_in_exercise",
            "window_n_used_for_metrics",
            "pass_totals_score200",
            "pass_rate",
            "consec_pass",
            "overall_norm_series",
            "deltas_overall_norm",
            "directionality_overall_norm",
            "volatility_overall_norm",
            "spread_overall_norm",
            "stability",
            "signal_to_noise",
            "snr_score",
            "maturity",
            "prev_exercise",
            "similarity",
            "data_score",
            "Rm_last_window",
        ]

        skip_keys = {"decision", "confidence", "reason"}

        for k in key_order:
            if k in ui_metrics and k not in skip_keys:
                rows_out.append((k, str(ui_metrics.get(k))))

        # append any remaining keys not listed
        for k in sorted(ui_metrics.keys()):
            if k not in set(key_order) and k not in skip_keys:
                rows_out.append((k, str(ui_metrics.get(k))))

        # final rows (shown at the end, emphasized)
        rows_out.append(("decision", str(ui_metrics.get("decision"))))
        rows_out.append(("confidence", f"{float(ui_metrics.get('confidence', 0.0)):.4f}"))
        rows_out.append(("reason", str(ui_metrics.get("reason"))))

        self.table.setRowCount(len(rows_out))
        bold_from = max(0, len(rows_out) - 3)

        for i, (k, v) in enumerate(rows_out):
            item_k = QTableWidgetItem(k)
            item_v = QTableWidgetItem(v)

            if i >= bold_from:
                f = item_k.font()
                f.setBold(True)
                item_k.setFont(f)
                item_v.setFont(f)

            self.table.setItem(i, 0, item_k)
            self.table.setItem(i, 1, item_v)


# =============================================================================
#  [SEC-08] NAED-2: MASTERY & DECISION LOGIC
# =============================================================================

# --- Soft-min mastery constants (unified v2 scale) -------------------------
#
# There is ONE definition of Rm in this app, used by NAED-1, NAED-2 and the
# Outcome-Measures corridor lanes alike. It is the v2 scale calibrated in
# prototype_mastery_v2.py, which diagnosed three compounding defects in the
# original (q=8, p in [0,1], fixed 0.80 prior) formulation:
#
#   A  The EWMA started from a fixed prior, which anchored fast learners below
#      the lane they earned and held struggling subjects artificially up. With
#      half-life 5, 43.5% of the prior still survived at attempt 6. Seeding
#      from the first observed m[0] is the standard bias-corrected EWMA and
#      removes the cold-start bias entirely.
#   B  A lagging EWMA could label an attempt that passed EVERY metric as
#      "Struggling". Handled at the labelling layer (OM_LANE_CORROBORATION).
#   C  With q = 8 the soft-min was effectively a hard min, so one zeroed metric
#      annihilated the attempt (m -> 0) however strong the others were, while p
#      was capped at 1.0 so excellence earned nothing. The penalty was
#      unbounded but the reward was capped. Softening q and giving p a floor
#      plus a little headroom restores the balance.
#
# Note score_200 = 0 is often a clamp artifact (any performance worse than the
# mean + 5*sd "worst" anchor collapses to exactly 0.00), which is why the floor
# is applied at the aggregation layer rather than in the scoring engine.
#
MASTERY_SOFTMIN_Q = 4.0        # C1: smooth-AND power (was 8.0 = near-hard-min)
MASTERY_P_FLOOR = 0.15         # C2: heavy penalty for a zeroed metric, not a wipeout
MASTERY_P_HEADROOM = 1.25      # C2: let excellence partially offset weakness
MASTERY_BIAS_FREE_INIT = True  # A: seed the EWMA from m[0], not from a prior
MASTERY_EPS = 1e-6             # floor for per-metric attainment to avoid 0**(-q) blow-up
MASTERY_THRESHOLD = 100.0      # per-metric pass threshold on *_score_200 scale
MASTERY_RM_INIT = 0.80         # cold-start prior; inert while MASTERY_BIAS_FREE_INIT is True

# Per-metric attainment p for the Rk bottleneck signal is deliberately NOT
# floored or given headroom: RK_BOTTLENECK_THRESH / RK_OTHERS_THRESH below are
# calibrated against a plain 0..1 attainment, and the v2 floor/headroom exist
# to fix an *aggregation* pathology (defect C), which does not apply to a
# single metric read on its own.
MASTERY_RK_P_MIN = 0.0
MASTERY_RK_P_MAX = 1.0

# Corridor thresholds for Rm_last (tunable)
RM_READY = 0.92                # ready / too-easy upper trigger
RM_CORRIDOR_MID = 0.85         # corridor mid (upgrade region)
RM_CORRIDOR_LOW = 0.80         # corridor lower bound (KEEP region)
RM_STRUGGLING = 0.70           # struggling boundary (lateral-move region below this)
RM_SEVERE = 0.60               # severely struggling / too-hard boundary (downgrade region; v7.0)
# Feedback detection thresholds (Rk-based)
RK_BOTTLENECK_THRESH = 0.60    # per-metric EWMA below this => lagging
RK_OTHERS_THRESH = 0.85        # median/mean of non-bottleneck metrics above this => others fine
RM_FEEDBACK_FLOOR = 0.65       # minimum Rm_last to attach a bottleneck observation to KEEP
FAIL_RATIO_THRESH = 1.7        # failure-ratio bottleneck: metric fail_frac >= 1.7x each other
SKILL_CLUSTERS = [("eom_score_200", "mwr_score_200")]  # metrics measuring similar skills
# NAED-2 proficiency override, sub-rule 3a (Fast Proficiency): if proficiency is
# first reached at or before this attempt number, the exercise was clearly too
# easy and the subject is sent straight to HP_UPGRADE. The lower bound is 3,
# since proficiency itself requires >= 3 PASS, so this admits attempts 3..N.
FAST_PROFICIENCY_MAX_ATTEMPTS = 5


def compute_mastery_softmin_ewma(
    attempts: list[dict[str, Any]],
    metric_keys: list[str],
    half_life: float = 5.0,
    q: float = MASTERY_SOFTMIN_Q,
    eps: float = MASTERY_EPS,
    threshold: float = MASTERY_THRESHOLD,
    rm_init: float = MASTERY_RM_INIT,
    p_floor: float = MASTERY_P_FLOOR,
    p_headroom: float = MASTERY_P_HEADROOM,
    bias_free_init: bool | None = None,
) -> dict[str, Any]:
    """Compute per-attempt soft-min mastery m[t] and EWMA Rm over chronological attempts.

    THE single definition of Rm in this app. NAED-1, NAED-2 and the
    Outcome-Measures corridor lanes all read it from here, so a lane label and a
    decision band can never be computed on different scales.

    Formula (v2 scale — see the constants block above):
        p[t,k] = clamp(score_200 / threshold, p_floor, p_headroom)
        m[t]   = min( ( (1/K) * Sigma p[t,k]^(-q) )^(-1/q), 1 )   (soft-min)
        R_1    = m[1]                                   (bias-free start, fix A)
        R_t    = lambda * R_{t-1} + (1 - lambda) * m[t]  (EWMA)
        lambda = 2^(-1/H)

    Returns dict with:
      Rm_last   – final recency-weighted mastery EWMA (float)
      Rm_list   – the full R_t trajectory, one value per attempt
      m_list    – list of per-attempt soft-min mastery values
      Rk_last   – dict of per-metric EWMA values {metric_key: float}
      bottleneck – metric key with lowest Rk_last (or "")
      slope_m   – linear slope of m_list over attempt indices
    """
    if not metric_keys:
        return {"Rm_last": 0.0, "Rm_list": [], "m_list": [], "Rk_last": {},
                "bottleneck": "", "slope_m": 0.0}

    if bias_free_init is None:
        bias_free_init = MASTERY_BIAS_FREE_INIT

    lam = 2.0 ** (-1.0 / half_life) if half_life > 0 else 0.0  # decay factor

    Rm = rm_init
    Rk: dict[str, float] = {k: rm_init for k in metric_keys}
    m_list: list[float] = []
    Rm_list: list[float] = []

    K = len(metric_keys)

    for idx, att in enumerate(attempts):
        # Per-metric normalized attainment. Two clamps on purpose: the
        # aggregation uses the v2 floor/headroom, while Rk keeps a plain 0..1
        # attainment because RK_* are calibrated against that.
        p: dict[str, float] = {}
        p_rk: dict[str, float] = {}
        for k in metric_keys:
            s = att.get(k)
            try:
                sv = float(s)
            except (TypeError, ValueError):
                sv = 0.0  # missing metric treated as 0 (very poor)
            ratio = sv / threshold
            p[k] = clamp(ratio, p_floor, p_headroom)
            p_rk[k] = clamp(ratio, MASTERY_RK_P_MIN, MASTERY_RK_P_MAX)

        # Soft-min (smooth AND) aggregator, capped at 1 because p_headroom > 1
        inv_mean = 0.0
        for k in metric_keys:
            p_safe = max(p[k], eps)
            inv_mean += p_safe ** (-q)
        inv_mean /= float(K)
        m = min(inv_mean ** (-1.0 / q), 1.0)
        m_list.append(m)

        # EWMA updates
        if bias_free_init and idx == 0:
            Rm = m
        else:
            Rm = lam * Rm + (1.0 - lam) * m
        Rm_list.append(Rm)
        for k in metric_keys:
            Rk[k] = lam * Rk[k] + (1.0 - lam) * p_rk[k]

    # Bottleneck = metric with lowest Rk
    bottleneck = min(Rk, key=lambda kk: Rk[kk]) if Rk else ""

    # Slope of m_list for plateau detection
    slope_m = compute_directionality(m_list) if len(m_list) > 1 else 0.0

    return {
        "Rm_last": float(Rm),
        "Rm_list": Rm_list,
        "m_list": m_list,
        "Rk_last": dict(Rk),
        "bottleneck": bottleneck,
        "slope_m": float(slope_m),
    }


# NAED-2: Decide next action category for the subject on the current exercise.
# 1) Use ALL attempts, emphasize recency via exponential weights (no fixed last-N window).
# 2) Compute directionality/volatility on overall_score (normalized 0..1) with recency weights.
# 3) Robustly downweight outlier attempts (MAD-based) for trend metrics.
# 4) Use soft-min mastery EWMA (Rm_last) as primary progression signal.
# 5) Use weighted pass rate (binary) + trailing pass streak as secondary signals.
# 6) "Feedback detection" is checked first and forces KEEP (+ observation), not an override.
# 7) If exercise proficiency is achieved, KEEP is disallowed (progression is recommended).

def compute_naed2_decision(
    all_attempt_rows: list[dict[str, Any]],
    naed1_metrics: dict[str, Any],
) -> dict[str, Any]:

    n = len(all_attempt_rows)
    if n == 0:
        return {"decision": "KEEP", "rationale": "No attempts available.", "details": []}

    # Infer valid *_score_200 keys for THIS exercise selection (match Analysis Window PASS rule),
    
    score200_keys = sorted({
        k
        for r in all_attempt_rows
        for k in r.keys()
        if k.endswith("_score_200")
        and any((rr.get(k) not in (None, "")) for rr in all_attempt_rows)
    })
    max_pass_total = len(score200_keys)

    # Every row here belongs to the same exercise, so one divisor serves the whole
    # selection. Per-exercise, not a flat 1200 — see overall_score_norm_divisor.
    naed2_divisor = overall_score_norm_divisor(
        next((str(r.get("exerc_abb") or "").strip() for r in all_attempt_rows
              if str(r.get("exerc_abb") or "").strip()), "")
    )

    # Extract signals
    pass_totals: list[int] = []
    pass_flags: list[bool] = []
    overall_vals: list[float] = []
    overall_norm: list[float] = []

    for rec in all_attempt_rows:
        # Recompute per-selection pass total (do NOT reuse cached totals from other selections).
        pt = compute_score200_pass_total(rec, score200_keys) if score200_keys else 0
        pass_totals.append(int(pt))
        pass_flags.append(bool(score200_keys) and int(pt) == max_pass_total)

        ov = rec.get("overall_score")
        try:
            ovf = float(ov)
        except (TypeError, ValueError):
            ovf = float("nan")
        overall_vals.append(ovf)
        overall_norm.append(
            float(clamp((ovf / naed2_divisor) if not math.isnan(ovf) else 0.0, 0.0, 1.0))
        )

    # Level "now" = mean overall_score (kept for display; light weight in decision logic)
    valid_overall = [v for v in overall_vals if not math.isnan(v)]
    level_now = float(sum(valid_overall) / len(valid_overall)) if valid_overall else 0.0
    level_now_norm = float(clamp(level_now / naed2_divisor, 0.0, 1.0))

    # Pass metrics (ALL)
    pass_rate_all = compute_pass_rate(pass_flags)
    consec_pass_all = compute_max_consec_true(pass_flags)
    trailing_streak = trailing_true_streak(pass_flags)

    # Trend/shape over ALL attempts (overall_norm 0..1)
    deltas = compute_deltas(overall_norm)
    directionality_plain = compute_directionality(overall_norm)
    spread = compute_spread(overall_norm)

    # Exponential recency (no fixed N): half-life in attempts
    half_life = 5.0
    w_recency = compute_exp_weights(n, half_life)

    # Robust outlier downweighting (MAD-based) for trend metrics
    w_robust = compute_robust_weights(overall_norm, z0=3.5)
    w_trend = [wr * wb for wr, wb in zip(w_recency, w_robust)]

    directionality = weighted_slope(overall_norm, w_trend)

    # Volatility = weighted std of deltas (align weights to deltas)
    if deltas and len(w_trend) == n:
        w_deltas = w_trend[1:]
        volatility = weighted_std(deltas, w_deltas) if len(w_deltas) == len(deltas) else compute_std(deltas)
    else:
        volatility = 0.0

    # Weighted pass rate (binary) using recency weights
    pass_rate_weighted = weighted_mean([1.0 if f else 0.0 for f in pass_flags], w_recency)

    # Stability: high if volatility small relative to spread
    if spread > 0:
        vol_term = volatility / (spread + 1e-6)
    else:
        vol_term = 0.0
    stability = 1.0 - clamp(vol_term, 0.0, 1.0)
    spread_term = 1.0 - clamp(spread / 1.0, 0.0, 1.0)  # spread is already in 0..1
    stability = clamp(0.5 * stability + 0.5 * spread_term, 0.0, 1.0)

    # ----------------------------
    # Soft-min mastery EWMA (continuous multi-metric signal)
    # ----------------------------
    mastery_result = compute_mastery_softmin_ewma(
        attempts=all_attempt_rows,
        metric_keys=score200_keys,
        half_life=half_life,
    )
    Rm_last = mastery_result["Rm_last"]
    m_list = mastery_result["m_list"]
    Rk_last = mastery_result["Rk_last"]
    mastery_bottleneck = mastery_result["bottleneck"]
    slope_m = mastery_result["slope_m"]

    # ----------------------------
    # Feedback detection (per-metric) — now uses Rk_last (EWMA) as primary,
    # with legacy per_metric_pass_frac kept for display.
    # ----------------------------
    per_metric_pass_frac: dict[str, float] = {}
    for k in score200_keys:
        ok = 0
        tot = 0
        for rec in all_attempt_rows:
            v = rec.get(k)
            try:
                if float(v) >= 100:
                    ok += 1
            except (TypeError, ValueError):
                pass
            tot += 1
        per_metric_pass_frac[k] = float(ok / tot) if tot else 0.0

    # Legacy worst-metric (binary pass frac) — kept for display
    worst_metric = min(per_metric_pass_frac, key=lambda kk: per_metric_pass_frac[kk]) if per_metric_pass_frac else ""
    worst_metric_pass_frac = per_metric_pass_frac.get(worst_metric, 0.0)

    other_fracs = [v for kk, v in per_metric_pass_frac.items() if kk != worst_metric]
    avg_other_metric_pass_frac = float(sum(other_fracs) / len(other_fracs)) if other_fracs else 0.0

    mean_pass_total = float(sum(pass_totals) / n) if n else 0.0

    # Rk-based feedback detection (continuous bottleneck)
    bottleneck_Rk = Rk_last.get(mastery_bottleneck, 0.0) if mastery_bottleneck else 0.0
    other_Rk_vals = [v for kk, v in Rk_last.items() if kk != mastery_bottleneck]
    mean_other_Rk = float(sum(other_Rk_vals) / len(other_Rk_vals)) if other_Rk_vals else 0.0

    # Path A — Rk-based bottleneck (original)
    _path_a = (bottleneck_Rk <= RK_BOTTLENECK_THRESH and mean_other_Rk >= RK_OTHERS_THRESH)

    # Path B — Failure-ratio bottleneck (per-metric pass_frac based)
    # A metric (or known skill cluster) is a bottleneck if its fail_frac
    # is >= FAIL_RATIO_THRESH × every other metric's fail_frac individually.
    _fail_fracs = {k: 1.0 - v for k, v in per_metric_pass_frac.items()}
    _path_b = False
    _path_b_label = ""

    # Check each individual metric
    for _bk, _bf in _fail_fracs.items():
        _others = [v for kk, v in _fail_fracs.items() if kk != _bk]
        if _others and _bf > 0 and all(_bf >= FAIL_RATIO_THRESH * ov for ov in _others):
            _path_b = True
            _path_b_label = _bk
            break

    # Check known skill clusters (eom/mwr)
    if not _path_b:
        for _cluster in SKILL_CLUSTERS:
            _cluster_keys = [k for k in _cluster if k in _fail_fracs]
            if len(_cluster_keys) < 2:
                continue
            _cluster_ff = sum(_fail_fracs[k] for k in _cluster_keys) / len(_cluster_keys)
            _others = [v for kk, v in _fail_fracs.items() if kk not in _cluster_keys]
            if _others and _cluster_ff > 0 and all(_cluster_ff >= FAIL_RATIO_THRESH * ov for ov in _others):
                _path_b = True
                _path_b_label = "+".join(_cluster_keys)
                break

    feedback_trigger = (
        n >= 5 and
        Rm_last >= RM_FEEDBACK_FLOOR and
        (_path_a or _path_b) and
        directionality <= 0.025
    )

    # ----------------------------
    # Proficiency (same rule as Analyze window)
    # ----------------------------
    pass_attempts = sum(1 for f in pass_flags if f)
    proficiency = (pass_attempts >= 3 and consec_pass_all >= 2)

    # =====================================================================
    #  NAED-2 DECISION LOGIC
    # =====================================================================
    #
    #  This section determines the recommended action category for the
    #  subject on the current exercise.  It proceeds in two phases:
    #
    #  PHASE 1 — PRIMARY DECISION RULES (evaluated top-to-bottom; first
    #            match wins).  These are the core rules derived from the
    #            multi-metric mastery signal Rm_last and supporting
    #            indicators (directionality, volatility, stability).
    #
    #      Rule                    Rm_last band          Key conditions
    #      ───────────────   ──────────────────    ───────────────
    #      KEEP (+observation)     ≥ 0.80                isolated bottleneck Rk
    #      HP_UPGRADE              ≥ 0.92                dir ≥ 0.02, vol ≤ 0.20
    #      UPGRADE                 0.85 – 0.92           dir ≥ 0.02
    #      DOWNGRADE               < 0.60                dir ≤ 0.008, n ≥ 5
    #      LATERAL                 0.60 – 0.70           dir ≤ 0.008, n ≥ 5
    #      LATERAL                 0.70 – 0.80           |dir| ≤ 0.010, stable, n ≥ 5
    #      KEEP (explicit)         0.80 – 0.85           dir > 0
    #      KEEP (fallback)         any                   catch-all default
    #
    #      v7.0: lateral moves are favored over downgrades — DOWNGRADE is
    #      reserved for severe struggling (Rm < RM_SEVERE = 0.60); the
    #      0.60–0.70 band now recommends a lateral move instead.
    #
    #  PHASE 2 — OVERRIDE RULES (applied after Phase 1 in ascending
    #            priority; the last override to fire wins).  These enforce
    #            hard boundary constraints that take precedence over the
    #            primary rules.
    #
    #      Priority   Name                     Effect
    #      ────────   ──────────────────────   ───────────────────────────
    #      1 (low)    Struggling Override       Force LATERAL/DOWNGRADE
    #      2          Near Proficiency Override  Force KEEP
    #      3 (high)   Proficiency Override       Force UPGRADE or HP_UPGRADE
    #
    # =====================================================================

    decision = "KEEP"
    rationale = "No decision thresholds met; keep practicing current exercise."
    logical_rationale = "Fallback: no specific decision rule matched; KEEP."
    observation = ""

    # -----------------------------------------------------------------
    #  PHASE 1 — PRIMARY DECISION RULES
    # -----------------------------------------------------------------

    # Rule 1: KEEP (+ observation)
    # Triggered when a single metric or skill cluster is persistently
    # lagging (isolated bottleneck).  Two detection paths (OR):
    #   Path A — Rk-based: bottleneck_Rk ≤ 0.60 AND mean_other_Rk ≥ 0.85
    #   Path B — Failure-ratio: metric/cluster fail_frac ≥ 1.7× each other
    # Checked first because it applies across Rm ≥ 0.65 regardless of trend.
    # v7.0: no longer a separate "KEEP_WITH_FEEDBACK" decision — every KEEP is
    # accompanied by feedback in the new protocol. This rule now just forces
    # KEEP and attaches an observation naming the lagging metric/cluster.
    if feedback_trigger:
        decision = "KEEP"
        _bottleneck_label = mastery_bottleneck if _path_a else _path_b_label
        observation = f"Subject is persistently failing on metric {_bottleneck_label}"
        if _path_a:
            rationale = (f"Bottleneck metric ({mastery_bottleneck}) Rk={bottleneck_Rk:.3f} is persistently low "
                         f"while others are fine (mean={mean_other_Rk:.3f}); keep and provide targeted feedback.")
            logical_rationale = (f"n ≥ 5 AND Rm_last ≥ {RM_FEEDBACK_FLOOR} AND "
                                 f"bottleneck_Rk ≤ {RK_BOTTLENECK_THRESH} AND mean_other_Rk ≥ {RK_OTHERS_THRESH}")
        else:
            rationale = (f"Failure-ratio bottleneck ({_path_b_label}) detected: metric/cluster fails "
                         f"disproportionately more than others; keep and provide targeted feedback.")
            logical_rationale = (f"n ≥ 5 AND Rm_last ≥ {RM_FEEDBACK_FLOOR} AND "
                                 f"fail_ratio({_path_b_label}) ≥ {FAIL_RATIO_THRESH}× each other metric")

    else:
        # Rule 2: HP_UPGRADE (skip 2 levels)
        # Very high mastery with a strong, stable upward trend.
        # Blocked until exercise proficiency is achieved (≥3 passes + ≥2 consecutive).
        if (
            proficiency and
            Rm_last >= RM_READY and
            directionality >= 0.02 and
            volatility <= 0.20
        ):
            decision = "HP_UPGRADE"
            rationale = "Multi-metric mastery ≥ 0.92 with strong positive trend and low volatility."
            logical_rationale = (f"proficiency AND Rm_last ≥ {RM_READY} AND directionality ≥ 0.02 AND volatility ≤ 0.20")

        # Rule 3: UPGRADE (advance 1 level)
        # Upper corridor mastery with a clear positive trend.
        # Blocked until exercise proficiency is achieved (≥3 passes + ≥2 consecutive).
        # (Implicitly < 0.92 because Rule 2 is checked first.)
        elif (
            proficiency and
            Rm_last >= RM_CORRIDOR_MID and
            directionality >= 0.02
        ):
            decision = "UPGRADE"
            rationale = "Multi-metric mastery in upper corridor with strong positive trend."
            logical_rationale = (f"proficiency AND Rm_last ≥ {RM_CORRIDOR_MID} AND directionality ≥ 0.02")

        # Rule 4: DOWNGRADE
        # v7.0: reserved for SEVERE struggling (Rm < 0.60) and not clearly
        # improving. The exercise is genuinely too difficult for the subject.
        elif (
            Rm_last < RM_SEVERE and
            directionality <= 0.008 and
            n >= 5
        ):
            decision = "DOWNGRADE"
            rationale = "Multi-metric mastery severely below struggling threshold and not improving; exercise is too hard."
            logical_rationale = (f"Rm_last < {RM_SEVERE} AND directionality ≤ 0.008 AND n ≥ 5")

        # Rule 4b: LATERAL (lateral move — struggling band)
        # v7.0: 0.60–0.70 without improvement previously DOWNGRADED; now a
        # lateral move to a similar-difficulty exercise is preferred.
        elif (
            RM_SEVERE <= Rm_last < RM_STRUGGLING and
            directionality <= 0.008 and
            n >= 5
        ):
            decision = "LATERAL"
            rationale = "Multi-metric mastery in struggling band and not improving; a lateral move may unlock progress."
            logical_rationale = (f"{RM_SEVERE} ≤ Rm_last < {RM_STRUGGLING} AND directionality ≤ 0.008 AND n ≥ 5")

        # Rule 5: LATERAL (lateral move — stagnation band)
        # Between struggling and corridor floor with flat, stable performance.
        # A different exercise at the same level may unlock progress.
        # v7.0: relaxed (|dir| ≤ 0.010, n ≥ 5) so lateral triggers sooner.
        elif (
            RM_STRUGGLING <= Rm_last < RM_CORRIDOR_LOW and
            abs(directionality) <= 0.010 and
            stability >= 0.55 and
            n >= 5
        ):
            decision = "LATERAL"
            rationale = "Multi-metric mastery between struggling and corridor floor with stagnation; consider a lateral move."
            logical_rationale = (f"{RM_STRUGGLING} ≤ Rm_last < {RM_CORRIDOR_LOW} AND |directionality| ≤ 0.010 "
                                 f"AND stability ≥ 0.55 AND n ≥ 5")

        # Rule 6: KEEP (explicit — learning corridor with positive trend)
        # Subject is in the 0.80–0.85 band and showing improvement.
        elif (
            RM_CORRIDOR_LOW <= Rm_last < RM_CORRIDOR_MID and
            directionality > 0
        ):
            decision = "KEEP"
            rationale = "Multi-metric mastery in learning corridor (0.80–0.85) with positive trend; keep practicing."
            logical_rationale = (f"{RM_CORRIDOR_LOW} ≤ Rm_last < {RM_CORRIDOR_MID} AND directionality > 0")

        # Rule 7: KEEP (fallback)
        # No primary rule matched.  Default to keeping the current exercise.
        else:
            decision = "KEEP"
            rationale = "No decision thresholds met; keep practicing current exercise."
            logical_rationale = "Fallback: no specific decision rule matched; KEEP."

    # -----------------------------------------------------------------
    #  PHASE 2 — OVERRIDE RULES
    #
    #  Applied sequentially after Phase 1.  Each override may replace the
    #  decision made by a previous rule.  They are ordered from lowest to
    #  highest priority so that the most important override has the final
    #  word.
    # -----------------------------------------------------------------

    # Override 1 (lowest priority): STRUGGLING OVERRIDE
    # Purpose: catch subjects who are consistently failing even if the
    #          primary rules assigned KEEP (e.g., Rm is in fallback zone).
    # Condition: no PASS in the last 5 attempts AND at most 2 total PASS.
    # Effect (v7.0): LATERAL if Rm ≥ 0.60 (RM_SEVERE), DOWNGRADE only below.
    # Does NOT override: HP_UPGRADE, UPGRADE, or a KEEP that already carries
    # an observation (Rule 1 already fired).
    _last_5_pass = pass_flags[-5:] if len(pass_flags) >= 5 else []
    _no_pass_last_5 = (len(_last_5_pass) == 5 and not any(_last_5_pass))
    if (_no_pass_last_5 and pass_attempts <= 2
            and decision not in ("HP_UPGRADE", "UPGRADE")
            and not observation):
        if Rm_last >= RM_SEVERE:
            decision = "LATERAL"
            rationale = "Struggling override: no PASS in last 5 attempts with ≤ 2 total PASS; lateral move recommended."
            logical_rationale = (
                f"Struggling override: no PASS in last 5 AND pass_attempts ≤ 2 "
                f"AND Rm_last ≥ {RM_SEVERE}")
        else:
            decision = "DOWNGRADE"
            rationale = "Struggling override: no PASS in last 5 attempts with ≤ 2 total PASS; downgrade recommended."
            logical_rationale = (
                f"Struggling override: no PASS in last 5 AND pass_attempts ≤ 2 "
                f"AND Rm_last < {RM_SEVERE}")

    # Override 2: NEAR PROFICIENCY OVERRIDE
    # Purpose: protect a subject who is showing competence (recent PASS)
    #          from being prematurely downgraded or laterally moved.
    # Condition: at least 2 total PASS AND the most recent attempt is PASS.
    # Effect:   force KEEP.
    # Does NOT override: KEEP (already appropriate).
    _last_attempt_pass = pass_flags[-1] if pass_flags else False
    if (pass_attempts >= 2 and _last_attempt_pass
            and decision != "KEEP"):
        decision = "KEEP"
        rationale = "Near proficiency override: subject has ≥ 2 total PASS and last attempt was PASS; keep practicing."
        logical_rationale = "Near proficiency override: pass_attempts ≥ 2 AND last_attempt = PASS"

    # Override 3 (highest priority): PROFICIENCY OVERRIDE
    # Purpose: once a subject demonstrates proficiency (≥ 3 PASS with at
    #          least 2 consecutive), progression is mandatory regardless
    #          of what the primary rules or lower overrides decided.
    # n_at_proficiency: the attempt number at which proficiency was FIRST
    #   reached (walk pass_flags to find this).  Any attempts beyond that
    #   point are redundant and ignored for the fast-proficiency check.
    # Sub-rule 3a — Fast Proficiency: if n_at_proficiency ≤
    #               FAST_PROFICIENCY_MAX_ATTEMPTS, the exercise was clearly
    #               too easy → HP_UPGRADE.
    # Sub-rule 3b — Standard Proficiency: otherwise → UPGRADE (unless the
    #               primary rules already assigned HP_UPGRADE, which we keep).
    if proficiency:
        _cum_pass = 0
        _max_consec = 0
        _cur_consec = 0
        _n_at_prof = n  # fallback: total attempts
        for _i, _pf in enumerate(pass_flags, start=1):
            if _pf:
                _cum_pass += 1
                _cur_consec += 1
                if _cur_consec > _max_consec:
                    _max_consec = _cur_consec
            else:
                _cur_consec = 0
            if _cum_pass >= 3 and _max_consec >= 2:
                _n_at_prof = _i
                break

        if _n_at_prof <= FAST_PROFICIENCY_MAX_ATTEMPTS:
            decision = "HP_UPGRADE"
            rationale = (f"Proficiency override: proficiency first reached at attempt {_n_at_prof} "
                         f"(≤ {FAST_PROFICIENCY_MAX_ATTEMPTS}); fast proficiency progression.")
            logical_rationale = (f"Proficiency override (pass_attempts ≥ 3 AND consec_pass_all ≥ 2) "
                                 f"AND n_at_proficiency={_n_at_prof} ≤ {FAST_PROFICIENCY_MAX_ATTEMPTS}")
        elif decision != "HP_UPGRADE":
            decision = "UPGRADE"
            rationale = (f"Proficiency override: proficiency first reached at attempt {_n_at_prof}; "
                         f"recommend progression to the next level.")
            logical_rationale = (f"Proficiency override (pass_attempts ≥ 3 AND consec_pass_all ≥ 2) "
                                 f"AND n_at_proficiency={_n_at_prof} > {FAST_PROFICIENCY_MAX_ATTEMPTS}")

    # Build details (for NAED-2 Details window)
    details: list[tuple[str, Any]] = [
        ("Decision", decision),
        ("Observation", observation),
        ("Rationale", rationale),
        ("Logical Rationale", logical_rationale),
        ("Inputs", ""),
        ("n", n),
        ("Rm_last", f"{Rm_last:.4f}"),
        ("slope_m", f"{slope_m:.4f}"),
        ("mastery_bottleneck", mastery_bottleneck),
        ("bottleneck_Rk", f"{bottleneck_Rk:.4f}"),
        ("mean_other_Rk", f"{mean_other_Rk:.3f}"),
        ("level_now", f"{level_now:.2f} (0..{naed2_divisor:.0f})"),
        ("level_now_norm", f"{level_now_norm:.3f} (0..1)"),
        ("pass_rate_all", f"{pass_rate_all:.3f}"),
        ("pass_rate_weighted", f"{pass_rate_weighted:.3f} (half-life={half_life:.1f})"),
        ("consec_pass_all", consec_pass_all),
        ("trailing_streak", trailing_streak),
        ("directionality_plain", f"{directionality_plain:.4f}"),
        ("directionality_weighted", f"{directionality:.4f}"),
        ("volatility_weighted", f"{volatility:.4f}"),
        ("spread", f"{spread:.4f}"),
        ("stability", f"{stability:.3f}"),
        ("outlier_downweighting", "MAD-based (Tukey-style)"),
        ("Feedback detection", ""),
        ("mean_pass_total", f"{mean_pass_total:.2f}"),
        ("worst_metric (legacy)", worst_metric),
        ("worst_metric_pass_frac (legacy)", f"{worst_metric_pass_frac:.3f}"),
        ("avg_other_metric_pass_frac (legacy)", f"{avg_other_metric_pass_frac:.3f}"),
        ("feedback_trigger", "TRUE" if feedback_trigger else "FALSE"),
    ]

    return {
        "decision": decision,
        "observation": observation,
        "rationale": rationale,

        "logical_rationale": logical_rationale,

        # Core inputs/signals (kept at top-level so NAED-2 Details can display them)
        "n": n,
        "level_now": level_now,
        "level_now_norm": level_now_norm,
        # The scale level_now sits on, so displays do not have to assume one.
        "overall_norm_divisor": naed2_divisor,
        "pass_rate_all": pass_rate_all,
        "consec_pass_all": consec_pass_all,
        "pass_attempts": pass_attempts,
        "pass_rate_weighted": pass_rate_weighted,
        "trailing_streak": trailing_streak,
        "directionality_plain": directionality_plain,
        "directionality": directionality,
        "volatility": volatility,
        "spread": spread,
        "stability": stability,

        # Soft-min mastery signals
        "Rm_last": Rm_last,
        "m_list": m_list,
        "slope_m": slope_m,
        "Rk_last": Rk_last,
        "mastery_bottleneck": mastery_bottleneck,
        "bottleneck_Rk": bottleneck_Rk,
        "mean_other_Rk": mean_other_Rk,

        # Feedback detection diagnostics
        "mean_pass_total": mean_pass_total,
        "worst_metric": worst_metric,
        "worst_metric_pass_frac": worst_metric_pass_frac,
        "avg_other_metric_pass_frac": avg_other_metric_pass_frac,
        "feedback_trigger": feedback_trigger,

        # Per-metric pass fractions (legacy binary)
        "metric_pass_fracs": per_metric_pass_frac,

        # Full ordered trace (still used for debugging / future UI)
        "details": details,
        "per_metric_pass_frac": per_metric_pass_frac,
    }


# =============================================================================
#  [SEC-09] NAED-2 DETAILS WINDOW
# =============================================================================

class NAED2DetailsWindow(QMainWindow):
    def __init__(self, title: str, naed2: dict[str, Any], clean_path: str = "", subject: str = "", exercise: str = ""):
        super().__init__()
        self.clean_path = clean_path
        self.subject = subject
        self.exercise = exercise
        self.naed1 = {}
        self.naed2 = naed2
        self.naed3 = {}
        self.setWindowTitle(title)
        self.resize(820, 620)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # ----------------------------
        # NAED-2 Details (UI-only formatting)
        # ----------------------------
        def _detail_lookup(key: str):
            # Prefer top-level keys; fall back to the ordered 'details' trace if present.
            if key in naed2:
                return naed2.get(key)
            det = naed2.get("details", [])
            if isinstance(det, list):
                for it in det:
                    if isinstance(it, (tuple, list)) and len(it) >= 2 and it[0] == key:
                        return it[1]
            return None

        def _float_prefix(x) -> float:
            # Extract a leading float from strings like "0.233 (half-life=5.0)".
            if isinstance(x, (int, float)):
                return float(x)
            if x is None:
                return 0.0
            s = str(x).strip()
            m = re.match(r"^[+-]?\d+(?:\.\d+)?", s)
            try:
                return float(m.group(0)) if m else 0.0
            except Exception:
                return 0.0

        text = ""

        # Keep the title (as-is)
        text += "<h2 style='text-align:center;'>NAED-2 Details</h2>" + "<br>"

        # Two-column content area:
        # Left: Inputs + Per-metric pass fractions
        # Right: Keep with Feedback Outcome + Vital operators
        text += "<table width='100%' cellspacing='0' cellpadding='0' style='table-layout:fixed;'><tr>"

        # ----------------------------
        # LEFT COLUMN
        # ----------------------------
        text += "<td width='50%' valign='top' style='padding-right:12px;'>"

        # Inputs (ordered, as requested)
        n = int(naed2.get("n", 0) or 0)
        pass_rate_all = float(naed2.get("pass_rate_all", 0.0) or 0.0)

        # UI-only: prefer provided pass_attempts; if absent, estimate from pass_rate_all * n
        pass_attempts = int(naed2.get("pass_attempts", 0) or 0)
        if pass_attempts <= 0 and n > 0:
            pass_attempts = int(round(pass_rate_all * n))

        pass_rate_weighted_val = float(naed2.get("pass_rate_weighted", 0.0) or 0.0)
        if pass_rate_weighted_val == 0.0:
            pass_rate_weighted_val = _float_prefix(_detail_lookup("pass_rate_weighted"))

        consec_pass_all = int(naed2.get("consec_pass_all", 0) or 0)
        level_now = float(naed2.get("level_now", 0.0) or 0.0)
        level_now_norm = float(naed2.get("level_now_norm", 0.0) or 0.0)

        # Mastery signals
        Rm_last_val = float(naed2.get("Rm_last", 0.0) or 0.0)
        slope_m_val = float(naed2.get("slope_m", 0.0) or 0.0)
        bottleneck_key = str(naed2.get("mastery_bottleneck", "") or "")
        bottleneck_Rk_val = float(naed2.get("bottleneck_Rk", 0.0) or 0.0)
        mean_other_Rk_val = float(naed2.get("mean_other_Rk", 0.0) or 0.0)

        text += "<h3>Mastery (soft-min EWMA)</h3>"
        text += "<ul>"
        text += f"<li><b>Rm_last = {Rm_last_val:.4f}</b></li>"
        text += f"<li>slope_m = {slope_m_val:.4f}</li>"
        text += f"<li>bottleneck = {bottleneck_key}</li>"
        text += f"<li>bottleneck_Rk = {bottleneck_Rk_val:.4f}</li>"
        text += f"<li>mean_other_Rk = {mean_other_Rk_val:.3f}</li>"
        text += "</ul>"

        text += "<h3>Inputs</h3>"
        text += "<ul>"
        text += f"<li>n = {n}</li>"
        text += f"<li>pass_attempts = {pass_attempts}</li>"
        text += f"<li>consec_pass_all = {consec_pass_all}</li>"
        text += f"<li>pass_rate_all = {pass_rate_all:.3f}</li>"
        text += f"<li>pass_rate_weighted = {pass_rate_weighted_val:.3f}</li>"
        _divisor = float(naed2.get("overall_norm_divisor", 0.0) or 0.0) or OVERALL_SCORE_MAX
        text += f"<li>level_now = {level_now:.2f} (0..{_divisor:.0f})</li>"
        text += f"<li>level_now_norm = {level_now_norm:.3f} (0..1)</li>"
        text += "</ul>"

        # Per-metric Rk EWMA values + legacy pass fractions
        rk_last = naed2.get("Rk_last", {}) or {}
        mpf = naed2.get("metric_pass_fracs", {}) or {}
        if isinstance(rk_last, dict) and rk_last:
            text += "<h3>Per-metric Rk (EWMA) &amp; pass frac</h3>"
            text += "<ul>"
            for k in sorted(rk_last.keys()):
                rk_v = float(rk_last.get(k, 0.0))
                pf_v = float(mpf.get(k, 0.0)) if isinstance(mpf, dict) else 0.0
                marker = " ⚠" if k == bottleneck_key else ""
                text += f"<li>{k}: Rk={rk_v:.3f}, pass_frac={pf_v:.3f}{marker}</li>"
            text += "</ul>"
        elif isinstance(mpf, dict) and mpf:
            text += "<h3>Per-metric pass fractions</h3>"
            text += "<ul>"
            for k in sorted(mpf.keys()):
                try:
                    frac = float(mpf[k])
                except Exception:
                    frac = 0.0
                text += f"<li>{k}: {frac:.3f}</li>"
            text += "</ul>"

        text += "</td>"  # end left column

        # ----------------------------
        # RIGHT COLUMN
        # ----------------------------
        text += "<td width='50%' valign='top' style='padding-left:12px;'>"

        # Keep with Feedback Outcome (Rk-based + legacy)
        text += "<h3>Keep with Feedback Outcome</h3>"
        text += "<ul>"
        text += f"<li>bottleneck = {bottleneck_key}</li>"
        text += f"<li>bottleneck_Rk = {bottleneck_Rk_val:.4f} (thresh ≤ {RK_BOTTLENECK_THRESH})</li>"
        text += f"<li>mean_other_Rk = {mean_other_Rk_val:.3f} (thresh ≥ {RK_OTHERS_THRESH})</li>"
        text += f"<li>mean_pass_total = {naed2.get('mean_pass_total', 0.0):.2f}</li>"
        text += f"<li>worst_metric (legacy) = {naed2.get('worst_metric', '')}</li>"
        text += f"<li>worst_metric_pass_frac (legacy) = {naed2.get('worst_metric_pass_frac', 0.0):.3f}</li>"
        text += f"<li>feedback_trigger = {str(bool(naed2.get('feedback_trigger', False))).upper()}</li>"
        text += "</ul>"

        # Vital operators (display-only)
        spread_val = _float_prefix(naed2.get("spread", 0.0))
        directionality_val = _float_prefix(naed2.get("directionality", 0.0))
        volatility_val = _float_prefix(naed2.get("volatility", 0.0))
        stability_val = _float_prefix(naed2.get("stability", _detail_lookup("stability")))

        text += "<h3>Vital operators</h3>"
        text += "<ul>"
        text += f"<li>spread = {spread_val:.4f}</li>"
        text += f"<li>directionality = {directionality_val:.4f}</li>"
        text += f"<li>volatility = {volatility_val:.4f}</li>"
        text += f"<li>stability = {stability_val:.3f}</li>"
        text += "</ul>"

        text += "</td>"  # end right column
        text += "</tr></table>"  # end two-column table

        # ----------------------------
        # Bottom section (single column): Decision + rationales
        # Add blank lines between Decision and Conceptual Rationale, and between Conceptual and Logical.
        # ----------------------------
        text += "<p>"
        decision_val = str(naed2.get("decision", ""))
        decision_colors = {
            "KEEP": "#0070C0",
            "UPGRADE": "#3A7C22",
            "HP_UPGRADE": "#77206D",
            "DOWNGRADE": "#EE0000",
            "LATERAL": "#E97132",
        }
        if decision_val in decision_colors:
            decision_html = f'<span style="color:{decision_colors[decision_val]};">{decision_val}</span>'
        else:
            decision_html = decision_val

        text += "<b>Decision:</b> " + decision_html + "<br><br>"
        observation_val = str(naed2.get("observation", "") or "")
        if observation_val:
            text += "<b>Observation:</b> <span style='color:#B00000;'>" + observation_val + "</span><br><br>"
        text += "<b>Conceptual Rationale:</b> " + str(naed2.get("rationale", "")) + "<br><br>"
        text += "<b>Logical Rationale:</b> " + str(naed2.get("logical_rationale", "")) + "</p>"

        from PySide6.QtWidgets import QTextEdit

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setHtml(text)  # preserves all formatting
        txt.setTextInteractionFlags(
            Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard
        )

        layout.addWidget(txt)

        # ----------------------------
        # Acceptance prompt (UI) + history logging
        # ----------------------------
        accept_row = QHBoxLayout()
        accept_row.addStretch(1)
        accept_row.addWidget(QLabel("Do you accept the recommendation?"))

        self.btn_accept_yes = QPushButton("YES")
        self.btn_accept_no = QPushButton("NO")
        self.btn_accept_yes.clicked.connect(self._on_accept_yes)
        self.btn_accept_no.clicked.connect(self._on_accept_no)

        accept_row.addWidget(self.btn_accept_yes)
        accept_row.addWidget(self.btn_accept_no)
        layout.addLayout(accept_row)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)
    # ----------------------------
    # Acceptance handlers
    # ----------------------------
    def _on_accept_no(self):
        # Per requirement: do nothing for now.
        return

    def _on_accept_yes(self):
        try:
            out_path = self._write_analysis_history()
        except Exception as e:
            QMessageBox.critical(self, "History write failed", f"Could not write analysis history:\n{e}")
            return

        # Disable to prevent double-click duplicates in the same window session
        try:
            self.btn_accept_yes.setEnabled(False)
            self.btn_accept_no.setEnabled(False)
        except Exception:
            pass

        Toast.show_toast(f"Decision recorded:\n{out_path}", parent=self, duration_ms=3000, success=True)


# =============================================================================
#  [SEC-10] CSV DATA PARSING
# =============================================================================

def _to_float_or_none(s: str) -> Optional[float]:
    s = (s or "").strip()
    if s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_dt_or_none(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if s == "":
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _fmt_dt(dt: Optional[datetime]) -> str:
    if dt is None:
        return ""
    return dt.strftime("%d-%m-%Y %H:%M:%S")


_FULL_TO_ABB_CACHE: dict[str, str] | None = None


def _exercise_abb_for_scale(exercise: str) -> str:
    """Resolve an exercise abbreviation from whatever the CSV's exercise column holds.

    Needed because the normalized range (norm_max) is a per-exercise setting, so a
    score cannot be rescaled without knowing which exercise it belongs to. The
    column may already hold the abbreviation, or the full name.
    """
    global _FULL_TO_ABB_CACHE
    ex = (exercise or "").strip()
    if not ex:
        return ""
    if ex in EXERCISE_DEFS:
        return ex
    if _FULL_TO_ABB_CACHE is None:
        _FULL_TO_ABB_CACHE = {
            str(v.get("exerc_full")).strip(): k
            for k, v in EXERCISE_DEFS.items()
            if isinstance(v, dict) and str(v.get("exerc_full") or "").strip()
        }
    return _FULL_TO_ABB_CACHE.get(ex, "")


def _simulator_to_canonical(score: float, exerc_abb: str, metric_code: str) -> float:
    """Rescale a simulator-produced score onto the canonical 0..200 range.

    Falls back to the unchanged value if the normative tables cannot be loaded, so
    a broken import degrades rather than crashing the parse — but it warns, because
    silently leaving a 0..40 score unscaled would misreport every PASS.
    """
    try:
        from exercise_proficiency_scores import simulator_to_canonical
    except Exception as e:
        _warn_normative_tables_unavailable("norm_max (metric score scaling)", e)
        return float(score)
    return simulator_to_canonical(score, exerc_abb, metric_code)


def classify_clean_line(line: str) -> Optional[dict[str, Any]]:
    if not line.strip():
        return None

    fields = line.split(",")

    # We only require the first 4 positional fields for basic identification.
    if len(fields) < 4:
        return None

    def f(n: int) -> str:
        return fields[n - 1].strip()

    def _value_after(label: str) -> Optional[float]:
        # Returns the numeric value that appears immediately after a label field.
        # If the label is not present, or there is no following field, returns None.
        for i, v in enumerate(fields):
            if v.strip() == label:
                if i + 1 >= len(fields):
                    return None
                return _to_float_or_none(fields[i + 1].strip())
        return None

    # Some MimicClean_Multiple exports appear to swap the (exercise, date_time) column order
    # compared to MimicClean_student exports. Detect and correct this purely for UI/display.
    dt2 = _parse_dt_or_none(f(2)) if len(fields) >= 2 else None
    dt3 = _parse_dt_or_none(f(3)) if len(fields) >= 3 else None
    date_time = dt2 if dt2 is not None else dt3
    exercise = f(3) if dt2 is not None else (f(2) if len(fields) >= 2 else "")

    metric_fields = [
        "ttc_score_raw", "ttc_score_200",
        "eom_score_raw", "eom_score_200",
        "ico_score_raw", "ico_score_200",
        "iov_score_raw", "iov_score_200",
        "exf_score_raw", "exf_score_200",
        "mwrp_score_pre_raw", "mwrp_score_pre_200",
        # Attempts recorded by this app write mwr under its own name, already on
        # the canonical scale. Simulator exports use the mwrp_score_pre_* pair
        # above instead, on the simulator's scale. Both forms are accepted.
        "mwr_score_raw", "mwr_score_200",
        "drp_score_raw", "drp_score_200",
        "wrc_score_raw", "wrc_score_200",
        "wcd_score_raw", "wcd_score_200",
        "tko_score_raw", "tko_score_200",
        "met_score_raw", "met_score_200",
        "blv_score_raw", "blv_score_200",
        "bve_score_raw", "bve_score_200",
        "mtg_score_raw", "mtg_score_200",
        "pid_score_raw", "pid_score_200",
        "kta_score_raw", "kta_score_200",
        "ckt_score_raw", "ckt_score_200",
        "cac_score_raw", "cac_score_200",
        "spo_score_raw", "spo_score_200",
        "esf_score_raw", "esf_score_200",
        "icl_score_raw", "icl_score_200",
        "isc_score_raw", "isc_score_200",
        "isw_score_raw", "isw_score_200",
        "pts_score_raw", "pts_score_200",
    ]

    out: dict[str, Any] = {
        "subject": f(1),
        "date_time": date_time,
        "exercise": exercise,
        "overall_score": _to_float_or_none(f(4)) if len(fields) >= 4 else None,
    }

    for key in metric_fields:
        out[key] = _value_after(key)

    # Screenshot filename (appended by the screenshot producer as a label-value pair)
    def _string_after(label: str) -> Optional[str]:
        for i, v in enumerate(fields):
            if v.strip() == label:
                if i + 1 >= len(fields):
                    return None
                val = fields[i + 1].strip()
                return val if val else None
        return None

    out["screenshot_file"] = _string_after("screenshot_file")

    # -------------------------------------------------
    # Derived compatibility fields for the DataShow UI
    # -------------------------------------------------
    # Re-publish "pre" metrics under their UI-facing alias keys (see PRE_METRIC_ALIASES).
    #
    # These columns carry the simulator's own normalized value, so they are rescaled
    # onto the canonical 0..200 range using that exercise/metric's norm_max. A row
    # that already provides the canonical column directly (written by this app) is
    # left untouched.
    exerc_abb = _exercise_abb_for_scale(exercise)
    for pre_key, cfg in PRE_METRIC_ALIASES.items():
        ui = cfg["ui_key"]
        raw = out.get(f"{pre_key}_score_pre_raw")
        if isinstance(raw, (int, float)):
            out[f"{ui}_score_raw"] = raw * cfg["multiplier_score_raw"]
        s200 = out.get(f"{pre_key}_score_pre_200")
        if isinstance(s200, (int, float)):
            out[f"{ui}_score_200"] = _simulator_to_canonical(s200, exerc_abb, ui)

    return out

def classify_clean_file(clean_path: str) -> list[dict[str, Any]]:
    with open(clean_path, "r", encoding="utf-8-sig", errors="replace") as f:
        lines = f.read().splitlines()

    rows: list[dict[str, Any]] = []
    for line in lines:
        rec = classify_clean_line(line)
        if rec is not None:
            rows.append(rec)
    return rows


def enrich_rows_with_exercise_defs(
    rows: list[dict[str, Any]],
    exercise_defs: dict[str, dict[str, int | str | None]],
) -> None:
    """Enrich each parsed attempt row with exercise metadata.

    - Uses exerc_abb (abbreviation) as the canonical identifier.
    - Supports inputs where rec["exercise"] may be either the abbreviation (preferred) or the full exercise name.
    - Also populates legacy keys (abbreviation/series/family) defensively for any older UI code paths.
    """

    full_to_abb: dict[str, str] = {
        str(v.get("exerc_full")).strip(): k
        for k, v in exercise_defs.items()
        if v.get("exerc_full") is not None and str(v.get("exerc_full")).strip()
    }

    for rec in rows:
        ex_raw = (rec.get("exercise") or "").strip()

        exerc_abb = ex_raw if ex_raw in exercise_defs else full_to_abb.get(ex_raw, "")
        meta = exercise_defs.get(exerc_abb) if exerc_abb else None

        rec["exerc_abb"] = exerc_abb

        if meta:
            rec["exerc_number"] = meta.get("exerc_number")
            rec["exerc_full"] = meta.get("exerc_full") or ""
            rec["exerc_cat"] = meta.get("exerc_cat") or ""
        else:
            rec["exerc_number"] = None
            rec["exerc_full"] = ""
            rec["exerc_cat"] = ""

        # Legacy compatibility (older UI code paths)
        rec["abbreviation"] = rec["exerc_abb"]






# =============================================================================
#  [SEC-11] NAED-3: EXERCISE MAPPING
# =============================================================================

def compute_naed3_recommendation(
    current_exercise_abb: str,
    naed2_decision: str,
    subject: str = "",
    curriculum: str = "",
) -> dict[str, Any]:
    """NAED-3: Convert the NAED-2 action category into next exercise candidates.

    v7.0: the mapping source of truth is CURRICULA[<subject's curriculum>]
    ["connections"], keyed by current exercise abbreviation. Each connection
    type maps to a LIST of candidate destinations:
      - one candidate  -> forced progression (requires_choice = False)
      - several        -> the user picks one (requires_choice = True)

    Decision -> connection type: UPGRADE -> upgrade,
    HP_UPGRADE -> hp_upgrade (fallback upgrade), DOWNGRADE -> downgrade
    (fallback lateral), LATERAL -> lateral.

    Backward-compatible output: next_exercise_abb/next_exercise_full hold the
    FIRST candidate; the full list is in "candidates".
    """
    # NOTE: throughout the UI/CSV, the field "exercise" is typically stored as the
    # *full* exercise name (e.g., "Peg Board 1"). Connections, however, are keyed
    # by the 3-letter abbreviation (e.g., "pb1").
    cur_in = (current_exercise_abb or "").strip()

    cur_key = curriculum if curriculum in CURRICULA else get_curriculum_for_subject(subject)
    cur_label = CURRICULA.get(cur_key, {}).get("label", cur_key)
    connections = CURRICULA.get(cur_key, {}).get("connections", {})

    def _exercise_to_abb(ex: str) -> str:
        ex = (ex or "").strip()
        if not ex:
            return ""
        # If it's already a known abbreviation, keep it.
        if ex in connections or ex in EXERCISE_DEFS:
            return ex
        # Try exact full-name match (most common).
        for abb, info in EXERCISE_DEFS.items():
            if not isinstance(info, dict):
                continue
            if (info.get("exerc_full") or "").strip() == ex:
                return str(abb)
        # Fallback: case-insensitive full-name match.
        ex_low = ex.lower()
        for abb, info in EXERCISE_DEFS.items():
            if not isinstance(info, dict):
                continue
            if (info.get("exerc_full") or "").strip().lower() == ex_low:
                return str(abb)
        return ""

    cur = _exercise_to_abb(cur_in)
    dec = (naed2_decision or "").strip()

    def _resolve_full_name(ex_abb: str) -> str:
        ex_abb = (ex_abb or "").strip()
        if not ex_abb:
            return ""
        exd = EXERCISE_DEFS.get(ex_abb, {})
        full = (exd.get("exerc_full") or "").strip()
        return full or ex_abb

    def _result(status: str, message: str, cands: list[str], used: str,
                training_complete: bool = False) -> dict[str, Any]:
        first = cands[0] if cands else ""
        return {
            "current_exercise_abb": cur,
            "naed2_decision": dec,
            "status": status,
            "message": message,
            "curriculum": cur_key,
            "curriculum_label": cur_label,
            "connection_used": used,
            "candidates": [
                {"abb": c, "full": ("Training Complete" if c == "END" else _resolve_full_name(c))}
                for c in cands
            ],
            "requires_choice": len(cands) > 1,
            "next_exercise_abb": first,
            "next_exercise_full": ("Training Complete" if first == "END" else (_resolve_full_name(first) if first else "")),
            "training_complete": training_complete,
        }

    conn = connections.get(cur)
    if not isinstance(conn, dict):
        return _result(
            "NO_MAPPING",
            (
                f"No connection entry found for the current exercise in curriculum "
                f"'{cur_label}'. (input={cur_in!r}, resolved_abb={cur!r})"
            ),
            [], "",
        )

    def _cands(conn_type: str) -> list[str]:
        vals = conn.get(conn_type) or []
        if isinstance(vals, str):  # tolerate accidental single-string values
            vals = [vals]
        return [str(v).strip() for v in vals if str(v).strip()]

    up = _cands("upgrade")
    hp = _cands("hp_upgrade")
    down = _cands("downgrade")
    lat = _cands("lateral")

    cands: list[str] = []
    used = ""
    status = "OK"
    message = ""

    if dec == "UPGRADE":
        # A1/A2
        if up:
            cands = up
            used = "upgrade"
        else:
            status = "NO_OPTION"
            message = "No upgrade exercise option available. I suggest to KEEP in the current exercise."

    elif dec == "HP_UPGRADE":
        # B1/B2
        if hp:
            cands = hp
            used = "hp_upgrade"
        elif up:
            cands = up
            used = "upgrade"
            message = "No hp_upgrade available; using upgrade as fallback."
        else:
            status = "NO_OPTION"
            message = "No upgrade exercise option available (hp_upgrade / upgrade are empty). I suggest to KEEP in the current exercise."

    elif dec == "DOWNGRADE":
        # C1/C2/C3
        if down:
            cands = down
            used = "downgrade"
        elif lat:
            cands = lat
            used = "lateral"
            message = "No downgrade available; using lateral as fallback."
        else:
            status = "NO_DOWNGRADE"
            message = "No downgrade or lateral exercise option available. I suggest to KEEP in the current exercise."

    elif dec == "LATERAL":
        # D1/D2
        if lat:
            cands = lat
            used = "lateral"
        else:
            status = "NO_LATERAL"
            # Suggest downgrade option if available
            if down:
                opts = ", ".join(f"{d} ({_resolve_full_name(d)})" for d in down)
                message = f"No lateral exercise option available. Please consider DOWNGRADE to {opts} or KEEP in the current exercise"
            else:
                message = "No lateral exercise option available. Please consider KEEP in the current exercise"

    else:
        status = "NOT_APPLICABLE"
        message = "NAED-3 is not applicable for this NAED-2 decision."

    # END sentinel: training is complete
    if cands == ["END"]:
        return _result(
            "CURRICULUM_COMPLETED", "TRAINING COMPLETE", ["END"], used,
            training_complete=True,
        )

    return _result(status, message, cands, used)


# =============================================================================
#  [SEC-12] NAED-3 DETAILS WINDOW
# =============================================================================

class NAED3DetailsWindow(QMainWindow):
    def __init__(self, title: str, naed3: dict[str, Any]):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(720, 420)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Render as simple rich text
        msg = (naed3.get("message") or "").strip()
        status = (naed3.get("status") or "").strip()
        cur = (naed3.get("current_exercise_abb") or "").strip()
        dec = (naed3.get("naed2_decision") or "").strip()
        nxt = (naed3.get("next_exercise_abb") or "").strip()
        nxt_full = (naed3.get("next_exercise_full") or "").strip()
        used = (naed3.get("connection_used") or "").strip()
        cur_label = (naed3.get("curriculum_label") or naed3.get("curriculum") or "").strip()
        candidates = naed3.get("candidates") or []

        html = ""
        html += "<h2 style='text-align:center;'>NAED-3 Details</h2>"
        html += "<hr>"
        if cur_label:
            html += "<p><b>Curriculum:</b> " + cur_label + "</p>"
        html += "<p><b>Current exercise:</b> " + (cur or "") + "</p>"
        html += "<p><b>NAED-2 decision:</b> " + (dec or "") + "</p>"

        if status == "CURRICULUM_COMPLETED":
            html += "<p style='font-size:18px; text-align:center;'><b>CURRICULUM COMPLETED</b></p>"
        elif len(candidates) > 1:
            html += "<p><b>Connection used:</b> " + (used or "") + "</p>"
            html += "<p><b>Candidate next exercises (user must choose one):</b></p><ul>"
            for c in candidates:
                c_abb = (c.get("abb") or "").strip() if isinstance(c, dict) else str(c)
                c_full = (c.get("full") or "").strip() if isinstance(c, dict) else ""
                html += "<li>" + c_abb + ((" — " + c_full) if c_full else "") + "</li>"
            html += "</ul>"
            if msg:
                html += "<p style='font-size:14px;'><b>Note:</b> " + msg + "</p>"
        elif nxt:
            html += "<p><b>Recommended next exercise:</b> " + nxt + "</p>"
            if nxt_full:
                html += "<p><b>Exercise full name:</b> " + nxt_full + "</p>"
            if used:
                html += "<p><b>Connection used:</b> " + used + "</p>"
        else:
            # No next option -> show message (if any)
            if msg:
                html += "<p style='font-size:14px;'><b>Note:</b> " + msg + "</p>"
            else:
                html += "<p style='font-size:14px;'><b>Note:</b> No recommendation available.</p>"

        from PySide6.QtWidgets import QTextEdit

        browser = QTextEdit()
        browser.setHtml(html)
        browser.setReadOnly(True)
        layout.addWidget(browser)


# ---------------------------------------------------------------------------
#  Pending Decision Detection
# ---------------------------------------------------------------------------
#
# If the app is closed while an attempt has reached NAED-1 == ACT but the
# tutor never clicked YES/NO on the Recommendations prompt, no history entry
# gets written for that attempt. These helpers reconstruct that "pending"
# state on demand (e.g., when a subject's session is resumed) by comparing
# the subject's clean CSV data against their history JSON.

def _history_decision_exists(subject: str, exercise_abbreviation: str, exercise_attempt_number: int) -> bool:
    """Check the subject's history JSON for a recorded decision matching this
    exercise + attempt number."""
    import json as _json

    if not subject:
        return False

    script_dir = _script_dir()
    hist_dir = os.path.join(script_dir, "analysis_history")
    if not os.path.isdir(hist_dir):
        return False

    _pat = re.compile(
        r"^History_" + re.escape(subject) + r"_(\d+)-att\.json$", re.IGNORECASE
    )
    for fname in os.listdir(hist_dir):
        if not _pat.match(fname):
            continue
        try:
            with open(os.path.join(hist_dir, fname), "r", encoding="utf-8-sig") as f:
                data = _json.load(f)
            for entry in data:
                if (
                    entry.get("exercise_abbreviation") == exercise_abbreviation
                    and entry.get("exercise_attempt_number") == exercise_attempt_number
                ):
                    return True
        except Exception:
            continue
    return False


def _find_latest_clean_file_for_subject(clean_dir: str, subject: str) -> str | None:
    """Return the path to the most recently modified MimicClean CSV for this subject."""
    for item in collect_clean_files(clean_dir):  # already sorted newest-first
        m = CLEAN_PATTERN_WITH_SUBJECT.match(item.get("filename", ""))
        if m and (m.group(1) or "").strip() == subject:
            return item.get("path")
    return None


def find_pending_decision(clean_dir: str, subject: str) -> dict[str, Any] | None:
    """Reconstruct whether `subject` has an attempt that reached NAED-1 == ACT
    but has no corresponding decision recorded in the history JSON.

    Returns a dict with subject/exercise_full/exercise_abb/
    exercise_attempt_number/clean_path, or None if nothing is pending.
    """
    clean_path = _find_latest_clean_file_for_subject(clean_dir, subject)
    if not clean_path or not os.path.isfile(clean_path):
        return None

    try:
        rows = classify_clean_file(clean_path)
    except Exception:
        return None

    enrich_rows_with_exercise_defs(rows, EXERCISE_DEFS)

    subj_rows = [r for r in rows if r.get("subject") == subject]
    if not subj_rows:
        return None
    subj_rows.sort(key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min))

    last_exercise = subj_rows[-1].get("exercise", "")
    if not last_exercise:
        return None

    ex_rows = [r for r in subj_rows if r.get("exercise") == last_exercise]
    ex_rows.sort(key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min))
    if not ex_rows:
        return None

    exerc_abb = ex_rows[-1].get("exerc_abb", "")
    allowed_metrics = EXERCISE_METRICS.get(exerc_abb, [])
    score200_keys = [f"{m}_score_200" for m in allowed_metrics]

    try:
        naed1 = compute_naed1_metrics_and_decision(
            exercise_rows=ex_rows,
            score200_keys=score200_keys,
            subject=subject,
            current_exercise=last_exercise,
            all_rows=rows,
        )
    except Exception:
        return None

    if (naed1.get("decision") or "").strip().upper() != "ACT":
        return None

    exercise_attempt_number = len(ex_rows)
    if _history_decision_exists(subject, exerc_abb, exercise_attempt_number):
        return None

    return {
        "subject": subject,
        "exercise_full": last_exercise,
        "exercise_abb": exerc_abb,
        "exercise_attempt_number": exercise_attempt_number,
        "clean_path": clean_path,
    }


# =============================================================================
#  [SEC-13] RECOMMENDATIONS WINDOW
# =============================================================================

class NextExercisePickerDialog(QDialog):
    """Modal dialog to choose the next exercise when NAED-3 returns multiple candidates."""

    def __init__(self, candidates: list[dict[str, str]], connection_used: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Next Exercise")
        self.setMinimumWidth(420)
        self.selected_abb: str = ""

        layout = QVBoxLayout(self)
        conn_label = CONNECTION_TYPE_LABELS.get(connection_used, connection_used)
        lbl = QLabel(
            f"The <b>{conn_label}</b> connection offers more than one destination.<br>"
            "Please choose the next exercise:"
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

        self._list = QListWidget()
        for c in candidates:
            abb = (c.get("abb") or "").strip() if isinstance(c, dict) else str(c)
            full = (c.get("full") or "").strip() if isinstance(c, dict) else ""
            item = QListWidgetItem(f"{full} ({abb})" if full else abb)
            item.setData(Qt.UserRole, abb)
            self._list.addItem(item)
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
        self._list.itemDoubleClicked.connect(lambda _it: self._on_ok())
        layout.addWidget(self._list)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self):
        item = self._list.currentItem()
        if item is None:
            QMessageBox.warning(self, "No selection", "Please select an exercise.")
            return
        self.selected_abb = str(item.data(Qt.UserRole) or "")
        self.accept()


class KeepAutoAcceptDialog(QDialog):
    """Modal countdown that auto-accepts a KEEP recommendation on timeout."""

    def __init__(self, parent: QWidget | None = None, seconds: int = 10):
        super().__init__(parent)
        self.setWindowTitle("Recommendation")
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        self._remaining = seconds

        layout = QVBoxLayout(self)
        self._label = QLabel(self._message())
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)

        btn_layout = QHBoxLayout()
        self._btn_ok = QPushButton("OK")
        self._btn_cancel = QPushButton("Cancel")
        self._btn_ok.clicked.connect(self.accept)
        self._btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_cancel)
        layout.addLayout(btn_layout)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    def _message(self) -> str:
        return f"Recommendation is KEEP.\nAutomatically accepting it in {self._remaining} seconds."

    def _tick(self):
        self._remaining -= 1
        if self._remaining <= 0:
            self._timer.stop()
            self.accept()
        else:
            self._label.setText(self._message())

    def closeEvent(self, event):
        self._timer.stop()
        super().closeEvent(event)


class RecommendationsWindow(QMainWindow):
    decision_made = Signal()  # emitted when the tutor clicks YES or NO

    def __init__(
        self,
        title: str,
        naed1: dict[str, Any] | None = None,
        naed2: dict[str, Any] | None = None,
        naed3: dict[str, Any] | None = None,
        clean_path: str = "",
        subject: str = "",
        exercise: str = "",
        exercise_abbreviation: str = "",
        total_attempt_number: int = 0,
        exercise_attempt_number: int = 0,
    ):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(900, 720)

        self.clean_path = clean_path
        self.subject = subject
        self.exercise = exercise
        self.exercise_abbreviation = exercise_abbreviation
        self.total_attempt_number = total_attempt_number
        self.exercise_attempt_number = exercise_attempt_number
        self.naed1 = naed1 or {}
        self.naed2 = naed2 or {}
        self.naed3 = naed3 or {}
        self.chosen_next_abb: str = ""  # set by the picker when NAED-3 offers multiple candidates

        from PySide6.QtWidgets import QTextEdit

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)

        html = self._build_html()
        txt.setHtml(html)
        layout.addWidget(txt)

        # ----------------------------
        # Acceptance prompt (from NAED-2) + history logging
        # ----------------------------
        self._training_complete = bool((self.naed3 or {}).get("training_complete"))

        accept_row = QHBoxLayout()
        accept_row.addStretch(1)

        already_decided = self._decision_already_taken()

        if already_decided:
            lbl = QLabel("Decision has already been taken.")
            lbl.setStyleSheet("color: #888888; font-style: italic; font-size: 13px;")
            accept_row.addWidget(lbl)
        elif self._training_complete:
            lbl = QLabel("\U0001f3c6  TRAINING COMPLETE  \U0001f3c6")
            lbl.setStyleSheet("color: #2ca02c; font-size: 16px; font-weight: bold;")
            accept_row.addWidget(lbl)
        else:
            accept_row.addWidget(QLabel("Do you accept the recommendation?"))

        self.btn_accept_yes = QPushButton("YES")
        self.btn_accept_no = QPushButton("NO")
        self.btn_accept_yes.clicked.connect(self._on_accept_yes)
        self.btn_accept_no.clicked.connect(self._on_accept_no)

        if already_decided:
            self.btn_accept_yes.setVisible(False)
            self.btn_accept_no.setVisible(False)
        elif self._training_complete:
            self.btn_accept_yes.setText("Acknowledge")
            self.btn_accept_no.setVisible(False)

        accept_row.addWidget(self.btn_accept_yes)
        accept_row.addWidget(self.btn_accept_no)
        layout.addLayout(accept_row)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)

    def _decision_already_taken(self) -> bool:
        """Check if a decision for this exercise + attempt already exists in the history JSON."""
        return _history_decision_exists(self.subject, self.exercise_abbreviation, self.exercise_attempt_number)

    def _build_html(self) -> str:
        def _esc(x: Any) -> str:
            s = "" if x is None else str(x)
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

        def _fmt_decision_naed1(dec: str) -> str:
            d = (dec or "").strip().upper()
            if d == "WAIT":
                return f"<span style='color:red;'><b>{_esc(dec)}</b></span>"
            if d == "ACT":
                return f"<span style='color:green;'><b>{_esc(dec)}</b></span>"
            return f"<b>{_esc(dec)}</b>" if dec else ""

        def _fmt_decision_naed2(dec: str) -> str:
            d = (dec or "").strip().upper()
            # Legacy aliases (pre-7.0 history files): NEIGHBOR, LATERAL_MOVE,
            # UPGRADE_HPP, UPGRADE_NP.
            if d in ("LATERAL", "NEIGHBOR", "LATERAL_MOVE", "LATERAL_MOVE / NEIGHBOR"):
                return f"<span style='color:orange;'><b>{_esc(dec)}</b></span>"
            if d == "DOWNGRADE":
                return f"<span style='color:red;'><b>{_esc(dec)}</b></span>"
            if d in ("HP_UPGRADE", "UPGRADE_HPP"):
                return f"<span style='color:blue;'><b>{_esc(dec)}</b></span>"
            if d in ("UPGRADE", "UPGRADE_NP"):
                return f"<span style='color:green;'><b>{_esc(dec)}</b></span>"
            return f"<b>{_esc(dec)}</b>" if dec else ""

        def _render_simple_table(title: str, rows: list[tuple[str, str]]) -> str:
            out = [f"<h3>{_esc(title)}</h3>", "<table border='1' cellpadding='6' cellspacing='0' width='100%'>"]
            out.append("<tr><th align='left' width='34%'>Field</th><th align='left'>Value</th></tr>")
            for k, v_html in rows:
                out.append(f"<tr><td><b>{_esc(k)}</b></td><td>{v_html}</td></tr>")
            out.append("</table>")
            return "".join(out)

        def _get_any(d: dict[str, Any], *keys: str) -> Any:
            # Prefer 'details' trace (the user prefers the "lower half"), then top-level
            det = d.get("details", [])
            if isinstance(det, list):
                for key in keys:
                    for it in det:
                        if isinstance(it, (tuple, list)) and len(it) >= 2 and str(it[0]).strip() == key:
                            return it[1]
            for key in keys:
                if key in d:
                    return d.get(key)
            # case-insensitive fallback
            low_map = {str(k).strip().lower(): k for k in d.keys()}
            for key in keys:
                kk = low_map.get(str(key).strip().lower())
                if kk is not None:
                    return d.get(kk)
            if isinstance(det, list):
                det_low = {str(it[0]).strip().lower(): it[1] for it in det if isinstance(it, (tuple, list)) and len(it) >= 2}
                for key in keys:
                    if str(key).strip().lower() in det_low:
                        return det_low[str(key).strip().lower()]
            return None

        parts: list[str] = []
        parts.append("<h2 style='text-align:center; font-size:22px; font-weight:bold;'>Next Attempt Exercise Decision (NAED)</h2>")
        parts.append("<hr>")

        # ----------------------------
        # NAED-1 (summary)
        # ----------------------------
        if self.naed1:
            naed1 = self.naed1
            rows1 = []
            # Requested inverted order
            rows1.append(("window_n", _esc(_get_any(naed1, "window_n"))))
            rows1.append(("total_n", _esc(_get_any(naed1, "total_n"))))
            rows1.append(("reason", _esc(_get_any(naed1, "reason", "rationale"))))
            rows1.append(("confidence", _esc(_get_any(naed1, "confidence"))))
            rows1.append(("decision", _fmt_decision_naed1(str(_get_any(naed1, "decision") or ""))))
            parts.append(_render_simple_table("NAED-1", rows1))
        else:
            parts.append("<h3>NAED-1</h3><p><i>No data.</i></p>")

        parts.append("<br>")

        # ----------------------------
        # NAED-2 (details, single column, no duplicates)
        # ----------------------------
        if self.naed2:
            naed2 = self.naed2

            # Build "Feedback detection" block (Rk-based + legacy)
            fb_keys = [
                "mastery_bottleneck",
                "bottleneck_Rk",
                "mean_other_Rk",
                "mean_pass_total",
                "worst_metric",
                "worst_metric_pass_frac",
                "avg_other_metric_pass_frac",
                "feedback_trigger",
            ]
            fb_items = []
            for k in fb_keys:
                v = _get_any(naed2, k)
                if v is not None and str(v).strip() != "":
                    fb_items.append(f"<li><b>{_esc(k)}</b>: {_esc(v)}</li>")
            fb_html = "<ul>" + "".join(fb_items) + "</ul>" if fb_items else "<i>No feedback detection details.</i>"

            # Main ordered fields
            order = [
                "n",
                "Rm_last",
                "slope_m",
                "mastery_bottleneck",
                "bottleneck_Rk",
                "mean_other_Rk",
                "level_now",
                "level_now_norm",
                "pass_rate_all",
                "pass_rate_weighted",
                "consec_pass_all",
                "trailing_streak",
                "directionality_plain",
                "directionality_weighted",
                "volatility_weighted",
                "spread",
                "stability",
                "outlier_downweighting",
            ]
            rows2: list[tuple[str, str]] = []
            for k in order:
                v = _get_any(naed2, k)
                if v is None:
                    continue
                rows2.append((k, _esc(v)))

            # Feedback detection group
            rows2.append(("Feedback detection", fb_html))

            # Rationale + logical rationale + decision (with color)
            rationale = _get_any(naed2, "Rationale", "rationale", "reason")
            logical_rationale = _get_any(naed2, "Logical Rationale", "logical_rationale", "logical rationale")
            decision = _get_any(naed2, "Decision", "decision")

            if rationale is not None:
                rows2.append(("Rationale", _esc(rationale)))
            if logical_rationale is not None:
                rows2.append(("Logical Rationale", _esc(logical_rationale)))

            observation = _get_any(naed2, "Observation", "observation")
            if observation is not None and str(observation).strip() != "":
                rows2.append(("Observation", f"<span style='color:#B00000;'>{_esc(observation)}</span>"))

            if decision is not None:
                rows2.append(("Decision", _fmt_decision_naed2(str(decision))))

            parts.append(_render_simple_table("NAED-2", rows2))
        else:
            parts.append("<h3>NAED-2</h3><p><i>No data.</i></p>")

        parts.append("<br>")

        # ----------------------------
        # NAED-3 (ordered)
        # ----------------------------
        if self.naed3:
            naed3 = self.naed3
            rows3 = []
            rows3.append(("status", _esc(_get_any(naed3, "status"))))
            rows3.append(("message", _esc(_get_any(naed3, "message"))))
            cur_lbl = _get_any(naed3, "curriculum_label", "curriculum")
            if cur_lbl:
                rows3.append(("curriculum", _esc(cur_lbl)))
            rows3.append(("connection_used", _esc(_get_any(naed3, "connection_used"))))
            candidates = _get_any(naed3, "candidates") or []
            if isinstance(candidates, list) and len(candidates) > 1:
                cand_html = "<br>".join(
                    _esc(f"{(c.get('full') or '').strip()} ({(c.get('abb') or '').strip()})")
                    if isinstance(c, dict) else _esc(str(c))
                    for c in candidates
                )
                rows3.append(("candidate next exercises", f"<b>{cand_html}</b>"))
                rows3.append(("note", "<i>Multiple options — you will choose one upon accepting.</i>"))
            else:
                rows3.append(("next_exercise_abb", _esc(_get_any(naed3, "next_exercise_abb"))))
                nxt_full = _get_any(naed3, "next_exercise_full")
                rows3.append(("next_exercise_full", f"<b>{_esc(nxt_full)}</b>" if nxt_full else ""))
            parts.append(_render_simple_table("NAED-3", rows3))
        else:
            parts.append("<h3>NAED-3</h3><p><i>No data.</i></p>")

        return "".join(parts)


    def _on_accept_no(self):
        # Per requirement: NO does not write history; it simply closes or does nothing.
        # Keeping it as a no-op avoids accidental logging.
        return

    def _on_accept_yes(self):
        # v7.0: when NAED-3 offers multiple candidate destinations, the tutor
        # must pick one before the decision is recorded.
        naed3 = self.naed3 or {}
        if (
            not self._training_complete
            and naed3.get("requires_choice")
            and (naed3.get("candidates") or [])
        ):
            picker = NextExercisePickerDialog(
                naed3.get("candidates") or [],
                connection_used=(naed3.get("connection_used") or ""),
                parent=self,
            )
            if picker.exec() != QDialog.Accepted or not picker.selected_abb:
                return  # cancelled -> no decision recorded
            self.chosen_next_abb = picker.selected_abb

        try:
            reality_check = self._build_reality_check_yes()
            out_path = _save_live_decision_json(self, reality_check)
        except Exception as e:
            QMessageBox.critical(self, "History write failed", f"Could not write analysis history:\n{e}")
            return

        # Disable to prevent double-click duplicates in the same window session
        try:
            self.btn_accept_yes.setEnabled(False)
            self.btn_accept_no.setEnabled(False)
        except Exception:
            pass

        if self._training_complete:
            msg = f"Training complete. Recorded:\n{out_path}"
        else:
            msg = f"Recommendation recorded:\n{out_path}"
        try:
            Toast.show_toast(msg, parent=None, duration_ms=3000, success=True)
        except Exception:
            pass
        self.decision_made.emit()
        QTimer.singleShot(0, self.close)

    def _build_reality_check_yes(self) -> dict[str, Any]:
        """Build Reality_Check for YES: mirrors NAED-3 if available, else KEEP.

        v7.0: if the tutor picked one of several candidates, that choice wins.
        """
        naed3 = self.naed3 or {}
        naed2_dec = (self.naed2.get("decision") or "").strip() if self.naed2 else ""
        if naed2_dec == "KEEP" or not naed3:
            return {
                "next_exercise_abbreviation": self.exercise_abbreviation,
                "reality_connection_used": "KEEP",
                "reality_naed_match": True,
            }
        next_abb = (
            self.chosen_next_abb
            or naed3.get("next_exercise_abb")
            or self.exercise_abbreviation
        )
        return {
            "next_exercise_abbreviation": next_abb,
            "reality_connection_used": naed3.get("connection_used") or "",
            "reality_naed_match": True,
        }


# =============================================================================
#  [SEC-LIVE-JSON] LIVE DECISION JSON WRITER
# =============================================================================

def _round_val(v, n=4):
    if isinstance(v, float):
        return round(v, n)
    return v


def _build_live_naed_objects(win) -> tuple[dict, dict | None, dict | None]:
    """Build NAED-1/2/3 JSON objects from a RecommendationsWindow's raw dicts.

    Uses the same structure as the retrospective JSON builder.
    """
    naed1 = win.naed1 or {}
    naed1_obj = {
        "window_n": naed1.get("window_n"),
        "total_n": naed1.get("total_n"),
        "reason": naed1.get("reason"),
        "confidence": _round_val(naed1.get("confidence")),
        "decision": naed1.get("decision"),
    }

    naed2 = win.naed2 or {}
    naed2_decision = (naed2.get("decision") or "").strip()
    if naed1.get("decision") == "ACT" and naed2:
        naed2_obj: dict[str, Any] | None = {
            "exercise_attempts": naed2.get("n"),
            "Rm_last": _round_val(naed2.get("Rm_last")),
            "slope_m": _round_val(naed2.get("slope_m")),
            "mastery_bottleneck": naed2.get("mastery_bottleneck"),
            "bottleneck_Rk": _round_val(naed2.get("bottleneck_Rk")),
            "mean_other_Rk": _round_val(naed2.get("mean_other_Rk")),
            "level_now": _round_val(naed2.get("level_now"), 2),
            "level_now_norm": _round_val(naed2.get("level_now_norm")),
            "pass_rate_all": _round_val(naed2.get("pass_rate_all")),
            "pass_rate_weighted": _round_val(naed2.get("pass_rate_weighted")),
            "consec_pass_all": naed2.get("consec_pass_all"),
            "trailing_streak": naed2.get("trailing_streak"),
            "directionality_plain": _round_val(naed2.get("directionality_plain")),
            "directionality_weighted": _round_val(naed2.get("directionality")),
            "volatility_weighted": _round_val(naed2.get("volatility")),
            "spread": _round_val(naed2.get("spread")),
            "stability": _round_val(naed2.get("stability")),
            "outlier_downweighting": "MAD-based (Tukey-style)",
            "Feedback_detection": {
                "mastery_bottleneck": naed2.get("mastery_bottleneck"),
                "bottleneck_Rk": _round_val(naed2.get("bottleneck_Rk")),
                "mean_other_Rk": _round_val(naed2.get("mean_other_Rk")),
                "mean_pass_total": _round_val(naed2.get("mean_pass_total"), 2),
                "worst_metric": naed2.get("worst_metric"),
                "worst_metric_pass_frac": _round_val(naed2.get("worst_metric_pass_frac")),
                "avg_other_metric_pass_frac": _round_val(naed2.get("avg_other_metric_pass_frac")),
                "feedback_trigger": naed2.get("feedback_trigger"),
            },
            "Rationale": naed2.get("rationale"),
            "Logical_Rationale": naed2.get("logical_rationale"),
            "Observation": naed2.get("observation") or None,
            "Decision": naed2_decision,
        }
    else:
        naed2_obj = None

    naed3 = win.naed3 or {}
    if naed2_decision in ("UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL") and naed3:
        naed3_obj: dict[str, Any] | None = {
            "status": naed3.get("status"),
            "message": naed3.get("message"),
            "curriculum": naed3.get("curriculum"),
            "connection_used": naed3.get("connection_used"),
            "candidates": naed3.get("candidates"),
            "requires_choice": naed3.get("requires_choice", False),
            "chosen_next_abb": getattr(win, "chosen_next_abb", "") or None,
            "next_exercise_abb": naed3.get("next_exercise_abb"),
            "next_exercise_full": naed3.get("next_exercise_full"),
            "training_complete": naed3.get("training_complete", False),
        }
    else:
        naed3_obj = None

    return naed1_obj, naed2_obj, naed3_obj


def _save_live_decision_json(win, reality_check: dict[str, Any]) -> str:
    """Build a live JSON entry from a RecommendationsWindow and append to the history JSON.

    Creates a new file if none exists, or appends to the existing one.
    Returns the path of the written file.
    """
    import json as _json

    if not win.subject:
        raise RuntimeError("Subject is not available in this window.")

    naed1_obj, naed2_obj, naed3_obj = _build_live_naed_objects(win)

    exerc_full = EXERCISE_DEFS.get(win.exercise_abbreviation, {}).get("exerc_full", win.exercise)

    entry: dict[str, Any] = {
        "analysis_type": "live",
        "source": "live",
        "subject": win.subject,
        "total_attempt_number": win.total_attempt_number,
        "exercise_fullname": exerc_full,
        "exercise_abbreviation": win.exercise_abbreviation,
        "exercise_attempt_number": win.exercise_attempt_number,
        "NAED-1": naed1_obj,
        "NAED-2": naed2_obj,
        "NAED-3": naed3_obj,
        "Reality_Check": reality_check,
    }

    # --- Resolve output path ---
    script_dir = _script_dir()
    hist_dir = os.path.join(script_dir, "analysis_history")
    os.makedirs(hist_dir, exist_ok=True)

    # Look for existing History_<Subject>_*-att.json
    _pat = re.compile(
        r"^History_" + re.escape(win.subject) + r"_(\d+)-att\.json$", re.IGNORECASE
    )
    existing_path: str | None = None
    for fname in os.listdir(hist_dir):
        if _pat.match(fname):
            existing_path = os.path.join(hist_dir, fname)
            break  # use first match (there should be at most one per subject)

    if existing_path and os.path.isfile(existing_path):
        out_path = existing_path
        with open(out_path, "r", encoding="utf-8-sig") as f:
            data: list[dict[str, Any]] = _json.load(f)
    else:
        n = win.total_attempt_number or 0
        out_name = f"History_{win.subject}_{n}-att.json"
        out_path = os.path.join(hist_dir, out_name)
        data = []

    data.append(entry)

    with open(out_path, "w", encoding="utf-8") as f:
        _json.dump(data, f, indent=2, default=str, ensure_ascii=False)

    return out_path


# =============================================================================
#  [SEC-OM] OUTCOME MEASURES
# =============================================================================
#
# Pure computation functions for per-subject outcome analysis.
# These are independent of the NAED pipeline and can be called from any window.
#

# --- Corridor-lane labelling ------------------------------------------------
#
# Rm itself is computed by compute_mastery_softmin_ewma (see [SEC-08]) — there
# is exactly one definition of it, shared with the NAED decision bands. What
# remains here is purely the *labelling* of that value.
#
# The lane edges are deliberately the same numbers as the NAED decision
# thresholds, and are now expressed as references to them so the two can never
# drift apart silently. Note the lanes have no equivalent of RM_SEVERE: every
# Rm below RM_STRUGGLING collapses into OM_MASTERY_DEFAULT_LABEL, so one lane
# spans what NAED-2 splits into its lateral-move and downgrade regions.
OM_MASTERY_LABELS = [
    (RM_READY, "Strong mastery"),
    (RM_CORRIDOR_MID, "Corridor-high"),
    (RM_CORRIDOR_LOW, "Corridor-stable"),
    (RM_STRUGGLING, "Struggling"),
]
OM_MASTERY_DEFAULT_LABEL = "Excessively difficult"

# Fix B (see the mastery constants block): a lagging EWMA labelled attempts
# that themselves passed EVERY metric as "Struggling" — 28.2% of all low-lane
# entries system-wide were full-PASS attempts. An attempt that passed
# everything cannot be evidence of struggling, whatever the trailing average
# says. This is a labelling concern only, which is why it lives here and not in
# the Rm computation.
OM_LANE_CORROBORATION = True   # B: a full-PASS attempt cannot be a low lane
OM_LANE_FALLBACK_LABEL = "Corridor-stable"  # B: lane assigned on corroboration
OM_LOW_LANE_LABELS = ("Struggling", OM_MASTERY_DEFAULT_LABEL)  # the two lowest lanes


def label_mastery(Rm: float) -> str:
    """Map a mastery EWMA value to a human-readable label."""
    for threshold, label in OM_MASTERY_LABELS:
        if Rm >= threshold:
            return label
    return OM_MASTERY_DEFAULT_LABEL


_OVERALL_FLOOR_CACHE: dict[str, int] | None = None

_NORMATIVE_WARNINGS_SEEN: set[str] = set()


def _warn_normative_tables_unavailable(table: str, exc: BaseException) -> None:
    """Report, once per table, that a normative table could not be loaded.

    Swallowing this silently is what hid the broken import after the
    RSAC_7_00 -> RSAC_Freeware_1_00 rename: Proficiency Margin returned None for
    every attempt and no error was ever shown. See FREEWARE_HANDOFF.md 5.7.
    """
    if table in _NORMATIVE_WARNINGS_SEEN:
        return
    _NORMATIVE_WARNINGS_SEEN.add(table)
    print(
        f"WARNING: {table} could not be loaded from "
        f"exercise_proficiency_scores.py ({type(exc).__name__}: {exc}). "
        f"Metrics that depend on it (e.g. Proficiency Margin) will be unavailable.",
        file=sys.stderr,
    )


def get_overall_score_proficiency_floor(exerc_abb: str) -> float | None:
    """Return the exercise's overall score proficiency floor — the lowest
    overall score an attempt can have while still being a PASS.

    Single source of truth is OVERALL_SCORE_PROFICIENCY_FLOOR in
    exercise_proficiency_scores.py. Returns None if unknown.
    """
    global _OVERALL_FLOOR_CACHE
    if _OVERALL_FLOOR_CACHE is None:
        try:
            from exercise_proficiency_scores import (
                OVERALL_SCORE_PROFICIENCY_FLOOR,
            )
            _OVERALL_FLOOR_CACHE = dict(OVERALL_SCORE_PROFICIENCY_FLOOR)
        except Exception as e:
            _warn_normative_tables_unavailable("OVERALL_SCORE_PROFICIENCY_FLOOR", e)
            _OVERALL_FLOOR_CACHE = {}
    v = _OVERALL_FLOOR_CACHE.get(exerc_abb)
    return float(v) if isinstance(v, (int, float)) else None


_OVERALL_CEILING_CACHE: dict[str, int] | None = None
_OVERALL_VALIDITY_CACHE: dict[str, float] | None = None


def invalidate_normative_caches() -> None:
    """Drop the cached normative tables so the next read reflects edited baselines.

    These are copies taken on first use. Editing a norm_max or a metric set changes
    every one of them, and without this the app keeps deciding PASS against the
    values the file had at startup — with no visible sign that it is doing so.
    """
    global _OVERALL_FLOOR_CACHE, _OVERALL_CEILING_CACHE, _OVERALL_VALIDITY_CACHE
    _OVERALL_FLOOR_CACHE = None
    _OVERALL_CEILING_CACHE = None
    _OVERALL_VALIDITY_CACHE = None


def get_overall_score_validity_limit(exerc_abb: str) -> float | None:
    """Return the overall score above which an attempt is treated as a bad read.

    Distinct from the reference ceiling: metric scores are not capped at norm_max,
    so real attempts can exceed that. See OVERALL_SCORE_VALIDITY_FACTOR.
    """
    global _OVERALL_VALIDITY_CACHE
    if _OVERALL_VALIDITY_CACHE is None:
        try:
            from exercise_proficiency_scores import (
                OVERALL_SCORE_VALIDITY_LIMIT,
            )
            _OVERALL_VALIDITY_CACHE = dict(OVERALL_SCORE_VALIDITY_LIMIT)
        except Exception as e:
            _warn_normative_tables_unavailable("OVERALL_SCORE_VALIDITY_LIMIT", e)
            _OVERALL_VALIDITY_CACHE = {}
    v = _OVERALL_VALIDITY_CACHE.get(exerc_abb)
    return float(v) if isinstance(v, (int, float)) else None


def get_overall_score_ceiling(exerc_abb: str) -> float | None:
    """Return the exercise's reference ceiling — the overall score of an attempt
    at norm_max on every metric.

    This is a yardstick, NOT a maximum: the simulator does not cap a metric at its
    norm_max, so attempts can legitimately score above it. Use
    get_overall_score_validity_limit() to reject bad reads.

    Returns None if unknown.
    """
    global _OVERALL_CEILING_CACHE
    if _OVERALL_CEILING_CACHE is None:
        try:
            from exercise_proficiency_scores import (
                OVERALL_SCORE_CEILING,
            )
            _OVERALL_CEILING_CACHE = dict(OVERALL_SCORE_CEILING)
        except Exception as e:
            _warn_normative_tables_unavailable("OVERALL_SCORE_CEILING", e)
            _OVERALL_CEILING_CACHE = {}
    v = _OVERALL_CEILING_CACHE.get(exerc_abb)
    return float(v) if isinstance(v, (int, float)) else None


def compute_attempt_proficiency_margin(rec: dict[str, Any]) -> float | None:
    """Proficiency Margin of a SINGLE attempt, in percent:

        margin % = (overall_score - floor) / floor * 100

    The floor is the lowest overall score a PASS attempt can have (see
    get_overall_score_proficiency_floor), so 0% means the attempt was exactly at
    the minimum passing standard and higher values mean more headroom.

    Returns None if the attempt has no valid overall_score, if the exercise's
    floor is unknown, or if overall_score exceeds the exercise's validity limit
    (so far above any real attempt that it must be a bad read).

    The gate deliberately uses the validity limit and not the reference ceiling.
    Metric scores are uncapped above their cutoff, so gating on the ceiling threw
    away genuine high-scoring attempts.
    """
    v = rec.get("overall_score")
    if not isinstance(v, (int, float)):
        return None
    overall = float(v)

    exerc_abb = rec.get("exerc_abb", "") or ""

    limit = get_overall_score_validity_limit(exerc_abb)
    if limit is not None and overall > limit:
        return None

    floor = get_overall_score_proficiency_floor(exerc_abb)
    if not floor:
        return None

    return (overall - floor) / floor * 100.0


def collect_pass_attempt_margins(
    rows: list[dict],
    pass_flags: list[bool],
    n: int = 3,
) -> list[float]:
    """Proficiency Margins of ALL PASS attempts in *rows*, one value each.

    Returns an empty list if the exercise has fewer than *n* PASS attempts (the
    same gate used by compute_performance_margin), so that exercises which never
    reached a meaningful pass history do not contribute.
    """
    pass_rows = [r for r, p in zip(rows, pass_flags) if p]
    if len(pass_rows) < n:
        return []

    margins: list[float] = []
    for r in pass_rows:
        pm = compute_attempt_proficiency_margin(r)
        if pm is not None:
            margins.append(pm)
    return margins


def compute_performance_margin(
    rows: list[dict],
    pass_flags: list[bool],
    n: int = 3,
) -> float | None:
    """Proficiency Margin of an exercise: the mean per-attempt Proficiency
    Margin across ALL of its PASS attempts (see
    compute_attempt_proficiency_margin).

    Returns None if fewer than *n* PASS attempts exist or if no attempt yields a
    valid margin.
    """
    margins = collect_pass_attempt_margins(rows, pass_flags, n)
    if not margins:
        return None
    return sum(margins) / len(margins)


def compute_mastery_trajectory(
    attempts: list[dict[str, Any]],
    metric_keys: list[str],
    half_life: float = 5.0,
    **kwargs: Any,
) -> list[float]:
    """The R_t^(m) trajectory over chronological attempts, one value per attempt.

    Thin wrapper over compute_mastery_softmin_ewma — the corridor lanes and the
    NAED decision bands therefore read the SAME Rm, computed once, on the same
    scale. Any keyword accepted by that function may be forwarded.
    """
    if not metric_keys or not attempts:
        return []

    return compute_mastery_softmin_ewma(
        attempts=attempts,
        metric_keys=metric_keys,
        half_life=half_life,
        **kwargs,
    )["Rm_list"]


def build_mastery_table(
    attempts: list[dict[str, Any]],
    score200_keys: list[str],
    min_attempts: int = 3,
    half_life: float = 5.0,
    rm_init: float = MASTERY_RM_INIT,
) -> list[dict[str, Any]]:
    """Build a mastery trajectory table for one exercise.

    Returns a list of dicts starting from attempt *min_attempts*:
        {"attempt": int, "Rm": float, "label": str, "passed": bool,
         "corroborated": bool}

    Fix B (OM_LANE_CORROBORATION): an attempt that passed every metric is never
    labelled with a low lane. Rm is a trailing average, so without this guard a
    flawless attempt inherits the penalty of an earlier failure — 28.2% of all
    low-lane entries system-wide were attempts that passed everything.
    "corroborated" flags the entries whose label was raised by this rule.
    """
    Rm_list = compute_mastery_trajectory(attempts, score200_keys, half_life=half_life, rm_init=rm_init)

    n_keys = len(score200_keys)
    table: list[dict[str, Any]] = []
    for i in range(min_attempts - 1, len(Rm_list)):
        Rm = Rm_list[i]
        label = label_mastery(Rm)
        passed = (
            n_keys > 0
            and compute_score200_pass_total(attempts[i], score200_keys) == n_keys
        )
        corroborated = False
        if OM_LANE_CORROBORATION and passed and label in OM_LOW_LANE_LABELS:
            label = OM_LANE_FALLBACK_LABEL
            corroborated = True
        table.append({
            "attempt": i + 1,
            "Rm": Rm,
            "label": label,
            "passed": passed,
            "corroborated": corroborated,
        })
    return table


def aggregate_mastery_labels(
    tables: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    """Pool mastery tables from all exercises and compute label percentages.

    Returns:
        {"total": int, "counts": {label: int}, "percentages": {label: float}}
    """
    all_labels = [lbl for _, lbl in OM_MASTERY_LABELS] + [OM_MASTERY_DEFAULT_LABEL]
    counts: dict[str, int] = {lbl: 0 for lbl in all_labels}

    for table in tables:
        for entry in table:
            lbl = entry.get("label", OM_MASTERY_DEFAULT_LABEL)
            counts[lbl] = counts.get(lbl, 0) + 1

    total = sum(counts.values())
    percentages: dict[str, float] = {}
    for lbl in all_labels:
        percentages[lbl] = (counts[lbl] / total * 100) if total > 0 else 0.0

    return {"total": total, "counts": counts, "percentages": percentages}


def compute_om_summary(
    classified_rows: list[dict[str, Any]],
    subject: str,
    incomplete_count: int = 0,
    incomplete_time: float = 0.0,
) -> dict[str, Any]:
    """Compute all Outcome Measures for a single subject.

    *incomplete_count*/*incomplete_time* are the subject's totals from the
    IncompleteAttempts_<subject>_*.csv file (see get_incomplete_totals), used
    to compute the "including incomplete" variants below. Incomplete attempts
    have no PASS/FAIL score, so they are treated as non-PASS.

    Returns a dict with:
        total_time                     - sum of ttc_score_raw across complete attempts
        total_time_incl_incomplete     - total_time + incomplete_time
        total_time_pass                - sum of ttc_score_raw across PASS attempts
        total_time_fail                - sum of ttc_score_raw across non-PASS complete attempts
        total_time_fail_incl_incomplete- total_time_fail + incomplete_time
        pct_time_pass                  - total_time_pass / total_time_incl_incomplete * 100 (or None)
        total_attempts                 - total number of complete attempts
        total_attempts_incl_incomplete - total_attempts + incomplete_count
        total_passes                   - number of PASS attempts
        total_fails                    - number of non-PASS complete attempts
        total_fails_incl_incomplete    - total_fails + incomplete_count
        exercises_passed    - number of exercises reaching proficiency (>=3 pass, >=2 consecutive)
        avg_perf_margin     - mean Proficiency Margin pooled over ALL PASS attempts
                              of every qualifying exercise, i.e. attempt-weighted (or None)
        mastery_tables      - dict {exercise_abb: list[dict]} per-exercise mastery tables
        mastery_aggregation - aggregated label percentages across all exercises
    """
    rows = [r for r in classified_rows if r.get("subject") == subject]
    if not rows:
        return {
            "total_time": 0.0,
            "total_time_incl_incomplete": incomplete_time,
            "total_time_pass": 0.0,
            "total_time_fail": 0.0,
            "total_time_fail_incl_incomplete": incomplete_time,
            "pct_time_pass": None,
            "total_attempts": 0,
            "total_attempts_incl_incomplete": incomplete_count,
            "total_passes": 0,
            "total_fails": 0,
            "total_fails_incl_incomplete": incomplete_count,
            "exercises_passed": 0,
            "avg_perf_margin": None,
            "mastery_tables": {},
            "mastery_aggregation": aggregate_mastery_labels([]),
        }

    # Group by exercise abbreviation
    by_exercise: dict[str, list[dict]] = {}
    for r in rows:
        ex = r.get("exerc_abb", "")
        if ex:
            by_exercise.setdefault(ex, []).append(r)

    # Sort each exercise group chronologically
    for ex in by_exercise:
        by_exercise[ex].sort(
            key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min)
        )

    total_time = 0.0
    total_time_pass = 0.0
    total_time_fail = 0.0
    total_attempts = 0
    total_fails = 0
    exercises_passed = 0
    perf_margins: list[float] = []
    mastery_tables: dict[str, list[dict]] = {}

    for ex, ex_rows in by_exercise.items():
        metrics = EXERCISE_METRICS.get(ex, [])
        score200_keys = [f"{m}_score_200" for m in metrics]

        # Total attempts
        total_attempts += len(ex_rows)

        # Pass flags
        pass_flags: list[bool] = []
        for r in ex_rows:
            pt = compute_score200_pass_total(r, score200_keys)
            pass_flags.append(pt == len(score200_keys) if score200_keys else False)

        # Total time, split by PASS / non-PASS
        for r, passed in zip(ex_rows, pass_flags):
            t = r.get("ttc_score_raw")
            if isinstance(t, (int, float)):
                secs = float(t)
                total_time += secs
                if passed:
                    total_time_pass += secs
                else:
                    total_time_fail += secs

        # Total fails
        total_fails += sum(1 for f in pass_flags if not f)

        # Exercise proficiency (>=3 pass, >=2 consecutive)
        pass_count = sum(1 for f in pass_flags if f)
        max_consec = 0
        cur = 0
        for f in pass_flags:
            if f:
                cur += 1
                if cur > max_consec:
                    max_consec = cur
            else:
                cur = 0
        if pass_count >= 3 and max_consec >= 2:
            exercises_passed += 1

        # Proficiency Margin — pool EVERY PASS attempt, so the subject average
        # is attempt-weighted rather than exercise-weighted
        perf_margins.extend(collect_pass_attempt_margins(ex_rows, pass_flags))

        # Mastery trajectory table
        mastery_tables[ex] = build_mastery_table(ex_rows, score200_keys,
                                                       half_life=5.0)

    avg_perf_margin = (sum(perf_margins) / len(perf_margins)) if perf_margins else None

    total_time_all = total_time + incomplete_time
    pct_time_pass = (total_time_pass / total_time_all * 100.0) if total_time_all > 0 else None

    return {
        "total_time": total_time,
        "total_time_incl_incomplete": total_time_all,
        "total_time_pass": total_time_pass,
        "total_time_fail": total_time_fail,
        "total_time_fail_incl_incomplete": total_time_fail + incomplete_time,
        "pct_time_pass": pct_time_pass,
        "total_attempts": total_attempts,
        "total_attempts_incl_incomplete": total_attempts + incomplete_count,
        "total_passes": total_attempts - total_fails,
        "total_fails": total_fails,
        "total_fails_incl_incomplete": total_fails + incomplete_count,
        "exercises_passed": exercises_passed,
        "avg_perf_margin": avg_perf_margin,
        "mastery_tables": mastery_tables,
        "mastery_aggregation": aggregate_mastery_labels(list(mastery_tables.values())),
    }


# =============================================================================
#  [SEC-PEER] PEER COMPARISON (training time to equivalent checkpoint)
# =============================================================================

def _build_equivalence_map(curriculum: str) -> dict[str, set[str]]:
    """Build exercise equivalence classes from the LATERAL connections in CURRICULA.

    Each connected component of the undirected LATERAL graph becomes one
    equivalence class.  Every exercise in the curriculum is mapped to the full
    set of exercises equivalent to it (including itself).
    """
    connections = CURRICULA.get(curriculum, {}).get("connections", {})
    all_exercises = set(connections.keys())
    parent = {ex: ex for ex in all_exercises}

    def _find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: str, y: str) -> None:
        rx, ry = _find(x), _find(y)
        if rx != ry:
            parent[rx] = ry

    for ex, links in connections.items():
        for lat in links.get("lateral", []):
            if lat in all_exercises:
                _union(ex, lat)

    classes: dict[str, set[str]] = {}
    for ex in all_exercises:
        classes.setdefault(_find(ex), set()).add(ex)

    equiv_map: dict[str, set[str]] = {}
    for cls in classes.values():
        for ex in cls:
            equiv_map[ex] = cls
    return equiv_map


def _compute_curriculum_ranks(curriculum: str) -> dict[str, int]:
    """Return the curriculum rank for each exercise: longest distance from a start exercise.

    LATERAL connections are ignored; only upgrade / hp_upgrade edges are used.
    Higher rank = further along the curriculum.
    """
    connections = CURRICULA.get(curriculum, {}).get("connections", {})
    all_ex = set(connections.keys())
    if not all_ex:
        return {}

    incoming: dict[str, set[str]] = {ex: set() for ex in all_ex}
    graph: dict[str, set[str]] = {ex: set() for ex in all_ex}
    for ex, links in connections.items():
        for target in links.get("upgrade", []) + links.get("hp_upgrade", []):
            if target in all_ex and target != ex:
                graph[ex].add(target)
                incoming[target].add(ex)

    in_degree = {ex: len(incoming[ex]) for ex in all_ex}
    queue = [ex for ex in all_ex if in_degree[ex] == 0]
    ranks = {ex: 0 for ex in all_ex}
    processed = 0
    while queue:
        ex = queue.pop(0)
        processed += 1
        for target in graph[ex]:
            if ranks[target] < ranks[ex] + 1:
                ranks[target] = ranks[ex] + 1
            in_degree[target] -= 1
            if in_degree[target] == 0:
                queue.append(target)

    if processed < len(all_ex):
        # Cycle detected; fall back to memoized DFS
        memo: dict[str, int] = {}

        def _rank(ex: str) -> int:
            if ex in memo:
                return memo[ex]
            best = 0
            for src in incoming[ex]:
                best = max(best, _rank(src) + 1)
            memo[ex] = best
            return best

        ranks = {ex: _rank(ex) for ex in all_ex}

    return ranks


def _exercise_proficiency_index(ex_rows: list[dict]) -> int:
    """Return the index of the first attempt that makes the exercise proficient.

    Proficiency is defined as >=3 PASS attempts and >=2 consecutive PASS attempts.
    Returns -1 if proficiency has not been achieved.
    """
    if not ex_rows:
        return -1
    ex = ex_rows[0].get("exerc_abb", "")
    metrics = EXERCISE_METRICS.get(ex, [])
    score200_keys = [f"{m}_score_200" for m in metrics]
    pass_flags: list[bool] = []
    for r in ex_rows:
        pt = compute_score200_pass_total(r, score200_keys)
        pass_flags.append(pt == len(score200_keys) if score200_keys else False)

    pass_count = 0
    max_consec = 0
    cur = 0
    for i, f in enumerate(pass_flags):
        if f:
            pass_count += 1
            cur += 1
            if cur > max_consec:
                max_consec = cur
            if pass_count >= 3 and max_consec >= 2:
                return i
        else:
            cur = 0
    return -1


def _cumulative_time_at_checkpoint(
    rows: list[dict],
    subject: str,
    cutoff_dt: datetime,
    incomplete_by_ex: dict[str, float],
    checkpoint_rank: int,
    ranks: dict[str, int],
) -> float:
    """Sum complete-attempt time up to cutoff_dt plus incomplete time up to checkpoint rank.

    Incomplete time is counted for every exercise whose curriculum rank is less
    than or equal to the checkpoint rank.  This is the best approximation
    available because the aggregate IncompleteAttempts CSV does not store a
    timestamp per incomplete attempt.
    """
    complete_time = 0.0
    for r in rows:
        if r.get("subject") != subject:
            continue
        dt = r.get("date_time")
        if dt is None or not isinstance(dt, datetime):
            continue
        if dt <= cutoff_dt:
            t = r.get("ttc_score_raw")
            if isinstance(t, (int, float)):
                complete_time += float(t)

    incomplete_time = 0.0
    for ex, inc_time in incomplete_by_ex.items():
        if ranks.get(ex, 0) <= checkpoint_rank:
            incomplete_time += float(inc_time)

    return complete_time + incomplete_time


def _cumulative_pass_and_margin_at_checkpoint(
    rows: list[dict],
    subject: str,
    cutoff_dt: datetime,
    incomplete_stats_by_ex: dict[str, dict[str, float]],
    checkpoint_rank: int,
    ranks: dict[str, int],
) -> dict[str, Any]:
    """Compute PASS percentage and average Proficiency Margin up to a checkpoint.

    Mirrors _cumulative_time_at_checkpoint: complete attempts are counted if
    their date_time is on/before cutoff_dt (regardless of exercise, matching
    the training-time convention), while incomplete attempts are counted for
    every exercise whose curriculum rank is <= checkpoint_rank (incomplete
    attempts have no per-attempt timestamp).

    Returns a dict with:
        pass_attempts, total_attempts, pass_pct (None if no attempts)
        avg_margin - average Performance Margin across exercises where it is
        defined (>=3 PASS attempts up to cutoff_dt), or None if no exercise
        qualifies
    """
    complete_upto = [
        r for r in rows
        if r.get("subject") == subject
        and isinstance(r.get("date_time"), datetime)
        and r["date_time"] <= cutoff_dt
    ]

    by_exercise: dict[str, list[dict]] = {}
    for r in complete_upto:
        ex = r.get("exerc_abb", "")
        if ex:
            by_exercise.setdefault(ex, []).append(r)
    for ex in by_exercise:
        by_exercise[ex].sort(
            key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min)
        )

    pass_attempts = 0
    margins: list[float] = []
    for ex, ex_rows in by_exercise.items():
        metrics = EXERCISE_METRICS.get(ex, [])
        score200_keys = [f"{m}_score_200" for m in metrics]
        pass_flags: list[bool] = []
        for r in ex_rows:
            pt = compute_score200_pass_total(r, score200_keys)
            pass_flags.append(pt == len(score200_keys) if score200_keys else False)
        pass_attempts += sum(1 for f in pass_flags if f)
        margins.extend(collect_pass_attempt_margins(ex_rows, pass_flags))

    incomplete_count = 0
    for ex, stats in incomplete_stats_by_ex.items():
        if ranks.get(ex, 0) <= checkpoint_rank:
            incomplete_count += int(stats.get("count", 0) or 0)

    total_attempts = len(complete_upto) + incomplete_count
    pass_pct = (pass_attempts / total_attempts * 100.0) if total_attempts > 0 else None
    avg_margin = (sum(margins) / len(margins)) if margins else None

    return {
        "pass_attempts": pass_attempts,
        "total_attempts": total_attempts,
        "pass_pct": pass_pct,
        "avg_margin": avg_margin,
    }


def _exercise_class_stats(
    rows: list[dict],
    subject: str,
    class_members: set[str] | frozenset[str],
    incomplete_stats_by_ex: dict[str, dict[str, float]],
) -> dict[str, Any] | None:
    """Pool all-time attempts across an equivalence class for one subject.

    Returns None if the subject has not achieved proficiency (>=3 PASS,
    >=2 consecutive) in at least one member of class_members. Otherwise
    returns a dict with: time, pass_attempts, total_attempts, pass_pct,
    avg_margin, members_used (the class members the subject actually
    attempted).
    """
    subj_rows = [
        r for r in rows
        if r.get("subject") == subject and r.get("exerc_abb") in class_members
    ]
    if not subj_rows:
        return None

    by_exercise: dict[str, list[dict]] = {}
    for r in subj_rows:
        ex = r.get("exerc_abb", "")
        by_exercise.setdefault(ex, []).append(r)
    for ex in by_exercise:
        by_exercise[ex].sort(
            key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min)
        )

    proficient = False
    time_total = 0.0
    pass_attempts = 0
    total_attempts = 0
    margins: list[float] = []
    for ex, ex_rows in by_exercise.items():
        metrics = EXERCISE_METRICS.get(ex, [])
        score200_keys = [f"{m}_score_200" for m in metrics]
        pass_flags: list[bool] = []
        for r in ex_rows:
            pt = compute_score200_pass_total(r, score200_keys)
            pass_flags.append(pt == len(score200_keys) if score200_keys else False)
            t = r.get("ttc_score_raw")
            if isinstance(t, (int, float)):
                time_total += float(t)
        total_attempts += len(ex_rows)
        pass_attempts += sum(1 for f in pass_flags if f)
        if _exercise_proficiency_index(ex_rows) >= 0:
            proficient = True
        margins.extend(collect_pass_attempt_margins(ex_rows, pass_flags))

    if not proficient:
        return None

    for ex in class_members:
        stats = incomplete_stats_by_ex.get(ex)
        if stats:
            time_total += float(stats.get("time", 0.0) or 0.0)
            total_attempts += int(stats.get("count", 0) or 0)

    pass_pct = (pass_attempts / total_attempts * 100.0) if total_attempts > 0 else None
    avg_margin = (sum(margins) / len(margins)) if margins else None

    return {
        "time": time_total,
        "pass_attempts": pass_attempts,
        "total_attempts": total_attempts,
        "pass_pct": pass_pct,
        "avg_margin": avg_margin,
        "members_used": sorted(by_exercise.keys()),
    }


def _compute_percentile_stats(
    peer_values: list[float],
    target_value: float,
    higher_is_better: bool,
) -> dict[str, Any]:
    """Generic peer-percentile statistics for a single metric.

    "Better than target" means value > target_value if higher_is_better,
    else value < target_value (this mirrors the convention already used for
    training time, where lower = faster = better).

    Returns percentile_rank (% of peers better than target),
    performance_percentile (100 - percentile_rank, higher = better),
    performance_standardized_score (z from performance_percentile),
    z_score / z_score_reversed (conventional z-score, reversed so that
    positive = better), peer_mean, peer_std.
    """
    n_peers = len(peer_values)
    if n_peers == 0:
        return {
            "percentile_rank": None,
            "performance_percentile": None,
            "performance_standardized_score": None,
            "z_score": None,
            "z_score_reversed": None,
            "peer_mean": None,
            "peer_std": None,
        }

    if higher_is_better:
        n_better = sum(1 for v in peer_values if v > target_value)
    else:
        n_better = sum(1 for v in peer_values if v < target_value)
    n_equal = sum(1 for v in peer_values if v == target_value)
    percentile_rank = (n_better + n_equal / 2.0) / n_peers * 100.0
    performance_percentile = 100.0 - percentile_rank

    performance_standardized_score: float | None = None
    if _scipy_stats is not None:
        try:
            clipped_pct = max(0.0001, min(99.9999, performance_percentile))
            performance_standardized_score = float(_scipy_stats.norm.ppf(clipped_pct / 100.0))
        except Exception:
            pass

    peer_mean = float(np.mean(peer_values)) if np is not None else None
    peer_std = float(np.std(peer_values, ddof=1)) if np is not None and len(peer_values) > 1 else None
    z_score: float | None = None
    z_score_reversed: float | None = None
    if peer_mean is not None and peer_std is not None and peer_std > 0:
        z_score = (target_value - peer_mean) / peer_std
        z_score_reversed = z_score if higher_is_better else -z_score

    return {
        "percentile_rank": percentile_rank,
        "performance_percentile": performance_percentile,
        "performance_standardized_score": performance_standardized_score,
        "z_score": z_score,
        "z_score_reversed": z_score_reversed,
        "peer_mean": peer_mean,
        "peer_std": peer_std,
    }


def _find_last_proficiency_checkpoint(
    rows: list[dict],
    subject: str,
    ranks: dict[str, int],
) -> tuple[str, datetime] | None:
    """Return the highest-curriculum proficiency checkpoint for the subject.

    If multiple exercises share the highest curriculum rank, the one with the
    latest proficiency datetime is chosen.  Returns (exerc_abb,
    proficiency_datetime) or None if no proficiency has been achieved.
    """
    rows = [r for r in rows if r.get("subject") == subject]
    if not rows:
        return None

    by_exercise: dict[str, list[dict]] = {}
    for r in rows:
        ex = r.get("exerc_abb", "")
        if ex:
            by_exercise.setdefault(ex, []).append(r)

    for ex in by_exercise:
        by_exercise[ex].sort(
            key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min)
        )

    checkpoints: list[tuple[str, int, datetime]] = []
    for ex, ex_rows in by_exercise.items():
        prof_index = _exercise_proficiency_index(ex_rows)
        if prof_index < 0:
            continue
        prof_dt = ex_rows[prof_index].get("date_time")
        if prof_dt is None or not isinstance(prof_dt, datetime):
            continue
        rank = ranks.get(ex, 0)
        checkpoints.append((ex, rank, prof_dt))

    if not checkpoints:
        return None
    checkpoints.sort(key=lambda x: (-x[1], -x[2].timestamp()))
    return checkpoints[0][0], checkpoints[0][2]


def _find_equivalent_checkpoint(rows: list[dict], subject: str, equiv_class: set[str]) -> tuple[str, datetime] | None:
    """Return the latest proficiency checkpoint of subject that falls inside equiv_class.

    Returns (exerc_abb, proficiency_datetime) or None.
    """
    rows = [r for r in rows if r.get("subject") == subject]
    if not rows or not equiv_class:
        return None

    by_exercise: dict[str, list[dict]] = {}
    for r in rows:
        ex = r.get("exerc_abb", "")
        if ex in equiv_class:
            by_exercise.setdefault(ex, []).append(r)

    for ex in by_exercise:
        by_exercise[ex].sort(
            key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min)
        )

    checkpoints: list[tuple[str, datetime]] = []
    for ex, ex_rows in by_exercise.items():
        prof_index = _exercise_proficiency_index(ex_rows)
        if prof_index < 0:
            continue
        prof_dt = ex_rows[prof_index].get("date_time")
        if prof_dt is None or not isinstance(prof_dt, datetime):
            continue
        checkpoints.append((ex, prof_dt))

    if not checkpoints:
        return None
    checkpoints.sort(key=lambda x: x[1])
    return checkpoints[-1]


def _peer_matches_cohort(peer: str, curriculum: str) -> bool:
    """Return True if *peer* trains the same curriculum as the target subject."""
    return get_curriculum_for_subject(peer) == curriculum


def _ranks_for_subject(
    subject: str,
    curriculum: str,
    rows: list[dict] | None = None,
) -> dict[str, int]:
    """Return the curriculum rank map for *subject*.

    Ranks are only ever used within a single subject's own scale (to decide
    which incomplete attempts count towards their cumulative time).
    """
    return _compute_curriculum_ranks(curriculum)


def compute_peer_time_comparison(
    main_window: 'MainWindow',
    subject: str,
) -> dict[str, Any] | None:
    """Compare a subject's training time to reach their latest proficiency checkpoint against peers.

    Peers are the other subjects assigned the same curriculum.  For each peer,
    the comparable checkpoint is the same exercise if proficient, or any
    exercise in the same LATERAL-equivalence class.  Cumulative training time
    up to the proficiency moment is used for comparison.

    Also computes, using the same checkpoint and the same cumulative-up-to-
    checkpoint convention:
        - PASS attempts as a percentage of total attempts (including
          incomplete attempts)
        - Average Proficiency Margin across exercises attempted up to the
          checkpoint

    Returns a dict with:
        - subject, curriculum, checkpoint_exercise, checkpoint_time, subject_time
        - n_peers, peer_times, peer_details
        - percentile_rank (raw, lower = faster)
        - performance_percentile (100 - percentile_rank, higher = better)
        - performance_standardized_score (z-score from performance_percentile)
        - z_score (conventional z-score, reversed so lower time = positive)
        - peer_mean, peer_std
        - subject_pass_pct, peer_pass_pcts, pass_* (percentile stats, higher = better)
        - subject_avg_margin, peer_avg_margins, margin_* (percentile stats, higher = better)
    Returns None if the subject has no curriculum or no proficiency checkpoint.
    """
    curriculum = get_curriculum_for_subject(subject)
    if not curriculum:
        return None

    w = main_window._get_datashow_backend_for_subject(subject, silent=True)
    if w is None:
        return None
    try:
        target_rows = w.classified_rows
        target_folder = os.path.dirname(os.path.abspath(w.clean_path))
    except Exception:
        return None

    # Rank scale depends on the arm: CURRICULA graph for Adaptive, Static.txt
    # order for Static.
    ranks = _ranks_for_subject(subject, curriculum, target_rows)
    if not ranks:
        return None

    target_checkpoint = _find_last_proficiency_checkpoint(target_rows, subject, ranks)
    if target_checkpoint is None:
        return None
    target_ex, target_dt = target_checkpoint
    target_rank = ranks.get(target_ex, 0)
    target_incomplete = get_incomplete_stats_by_exercise(subject, target_folder)
    target_incomplete_by_ex = {ex: stats.get("time", 0.0) for ex, stats in target_incomplete.items()}
    target_time = _cumulative_time_at_checkpoint(
        target_rows, subject, target_dt, target_incomplete_by_ex, target_rank, ranks
    )
    target_pass_margin = _cumulative_pass_and_margin_at_checkpoint(
        target_rows, subject, target_dt, target_incomplete, target_rank, ranks
    )
    target_pass_pct = target_pass_margin["pass_pct"]
    target_avg_margin = target_pass_margin["avg_margin"]

    equiv_map = _build_equivalence_map(curriculum)
    equiv_class = equiv_map.get(target_ex, {target_ex})

    # Collect peers on the same curriculum
    peer_records: list[dict] = []
    seen_peers: set[str] = set()
    try:
        records = load_subjects()
    except Exception:
        records = []
    for rec in records:
        peer = rec.get("subject", "").strip()
        if not peer or peer == subject or peer in seen_peers:
            continue
        if not _peer_matches_cohort(peer, curriculum):
            continue
        seen_peers.add(peer)
        peer_records.append(rec)

    peer_times: list[float] = []
    peer_details: list[dict[str, Any]] = []
    peer_cache: list[dict[str, Any]] = []
    for rec in peer_records:
        peer = rec.get("subject", "").strip()
        peer_w = main_window._get_datashow_backend_for_subject(peer, silent=True)
        if peer_w is None:
            continue
        try:
            peer_rows = peer_w.classified_rows
            peer_folder = os.path.dirname(os.path.abspath(peer_w.clean_path))
        except Exception:
            continue
        try:
            peer_incomplete = get_incomplete_stats_by_exercise(peer, peer_folder)
        except Exception:
            peer_incomplete = {}
        peer_cache.append({"peer": peer, "rows": peer_rows, "incomplete": peer_incomplete})

        try:
            peer_checkpoint = _find_equivalent_checkpoint(peer_rows, peer, equiv_class)
        except Exception:
            peer_checkpoint = None
        if peer_checkpoint is None:
            continue
        peer_ex, peer_dt = peer_checkpoint
        peer_ranks = _ranks_for_subject(peer, curriculum, peer_rows)
        peer_rank = peer_ranks.get(peer_ex, 0)
        peer_incomplete_by_ex = {ex: stats.get("time", 0.0) for ex, stats in peer_incomplete.items()}
        peer_time = _cumulative_time_at_checkpoint(
            peer_rows, peer, peer_dt, peer_incomplete_by_ex, peer_rank, peer_ranks
        )
        peer_pass_margin = _cumulative_pass_and_margin_at_checkpoint(
            peer_rows, peer, peer_dt, peer_incomplete, peer_rank, peer_ranks
        )
        peer_times.append(peer_time)
        peer_details.append({
            "subject": peer,
            "exercise": peer_ex,
            "rank": peer_rank,
            "time": peer_time,
            "pass_pct": peer_pass_margin["pass_pct"],
            "avg_margin": peer_pass_margin["avg_margin"],
        })

    # --- By-exercise breakdown (all equivalence classes where the subject
    # has reached proficiency; independent of the top checkpoint above) ---
    by_exercise: list[dict[str, Any]] = []
    seen_classes: set[frozenset] = set()
    class_list: list[frozenset] = []
    for _ex, _cls in equiv_map.items():
        fs = frozenset(_cls)
        if fs not in seen_classes:
            seen_classes.add(fs)
            class_list.append(fs)

    for cls in class_list:
        subj_stats = _exercise_class_stats(target_rows, subject, cls, target_incomplete)
        if subj_stats is None:
            continue
        members_used = sorted(subj_stats["members_used"], key=lambda e: (ranks.get(e, 0), e))
        label = members_used[0] if len(members_used) == 1 else f"{members_used[0]}/{members_used[1]}"
        sort_rank = ranks.get(members_used[0], 0)

        peer_times_c: list[float] = []
        peer_pass_c: list[float] = []
        peer_margin_c: list[float] = []
        for pc in peer_cache:
            pstats = _exercise_class_stats(pc["rows"], pc["peer"], cls, pc["incomplete"])
            if pstats is None:
                continue
            peer_times_c.append(pstats["time"])
            if pstats["pass_pct"] is not None:
                peer_pass_c.append(pstats["pass_pct"])
            if pstats["avg_margin"] is not None:
                peer_margin_c.append(pstats["avg_margin"])

        if len(peer_times_c) < 1:
            continue

        time_stats_c = _compute_percentile_stats(peer_times_c, subj_stats["time"], higher_is_better=False)
        pass_stats_c = (
            _compute_percentile_stats(peer_pass_c, subj_stats["pass_pct"], higher_is_better=True)
            if subj_stats["pass_pct"] is not None and peer_pass_c
            else None
        )
        margin_stats_c = (
            _compute_percentile_stats(peer_margin_c, subj_stats["avg_margin"], higher_is_better=True)
            if subj_stats["avg_margin"] is not None and peer_margin_c
            else None
        )

        by_exercise.append({
            "label": label,
            "rank": sort_rank,
            "n_peers": len(peer_times_c),
            "subject_time": subj_stats["time"],
            "time_performance_percentile": time_stats_c["performance_percentile"],
            "subject_pass_pct": subj_stats["pass_pct"],
            "pass_performance_percentile": pass_stats_c["performance_percentile"] if pass_stats_c else None,
            "subject_avg_margin": subj_stats["avg_margin"],
            "margin_performance_percentile": margin_stats_c["performance_percentile"] if margin_stats_c else None,
        })

    by_exercise.sort(key=lambda d: d["rank"])

    if not peer_times:
        return {
            "subject": subject,
            "curriculum": curriculum,
            "checkpoint_exercise": target_ex,
            "checkpoint_rank": target_rank,
            "checkpoint_time": target_dt,
            "subject_time": target_time,
            "subject_pass_pct": target_pass_pct,
            "subject_avg_margin": target_avg_margin,
            "n_peers": 0,
            "by_exercise": by_exercise,
            "error": "No peers with a comparable proficiency checkpoint were found.",
        }

    n_peers = len(peer_times)
    time_stats = _compute_percentile_stats(peer_times, target_time, higher_is_better=False)

    peer_pass_pcts = [d["pass_pct"] for d in peer_details if d.get("pass_pct") is not None]
    pass_stats = (
        _compute_percentile_stats(peer_pass_pcts, target_pass_pct, higher_is_better=True)
        if target_pass_pct is not None and peer_pass_pcts
        else _compute_percentile_stats([], 0.0, higher_is_better=True)
    )

    peer_avg_margins = [d["avg_margin"] for d in peer_details if d.get("avg_margin") is not None]
    margin_stats = (
        _compute_percentile_stats(peer_avg_margins, target_avg_margin, higher_is_better=True)
        if target_avg_margin is not None and peer_avg_margins
        else _compute_percentile_stats([], 0.0, higher_is_better=True)
    )

    return {
        "subject": subject,
        "curriculum": curriculum,
        "checkpoint_exercise": target_ex,
        "checkpoint_rank": target_rank,
        "checkpoint_time": target_dt,
        "subject_time": target_time,
        "n_peers": n_peers,
        "peer_times": peer_times,
        "peer_details": peer_details,
        "percentile_rank": time_stats["percentile_rank"],
        "performance_percentile": time_stats["performance_percentile"],
        "performance_standardized_score": time_stats["performance_standardized_score"],
        "z_score": time_stats["z_score"],
        "z_score_reversed": time_stats["z_score_reversed"],
        "peer_mean": time_stats["peer_mean"],
        "peer_std": time_stats["peer_std"],
        # --- PASS attempts % (of total attempts incl. incomplete) ---
        "subject_pass_pct": target_pass_pct,
        "n_peers_pass_pct": len(peer_pass_pcts),
        "peer_pass_pcts": peer_pass_pcts,
        "pass_percentile_rank": pass_stats["percentile_rank"],
        "pass_performance_percentile": pass_stats["performance_percentile"],
        "pass_performance_standardized_score": pass_stats["performance_standardized_score"],
        "pass_z_score": pass_stats["z_score"],
        "pass_z_score_reversed": pass_stats["z_score_reversed"],
        "pass_peer_mean": pass_stats["peer_mean"],
        "pass_peer_std": pass_stats["peer_std"],
        # --- Average Proficiency Margin ---
        "subject_avg_margin": target_avg_margin,
        "n_peers_avg_margin": len(peer_avg_margins),
        "peer_avg_margins": peer_avg_margins,
        "margin_percentile_rank": margin_stats["percentile_rank"],
        "margin_performance_percentile": margin_stats["performance_percentile"],
        "margin_performance_standardized_score": margin_stats["performance_standardized_score"],
        "margin_z_score": margin_stats["z_score"],
        "margin_z_score_reversed": margin_stats["z_score_reversed"],
        "margin_peer_mean": margin_stats["peer_mean"],
        "margin_peer_std": margin_stats["peer_std"],
        # --- By-exercise breakdown ---
        "by_exercise": by_exercise,
    }


class PeerComparisonWindow(QDialog):
    """Display a peer comparison result with a summary panel and a chart."""

    def __init__(
        self,
        result: dict[str, Any],
        parent: QWidget | None = None,
        main_window: 'MainWindow | None' = None,
        subject: str = "",
    ):
        super().__init__(parent)
        self.setWindowTitle("Peer Comparison")
        self.setMinimumSize(1180, 560)
        self._result = result
        self._main_window = main_window
        self._subject = subject or str(result.get("subject", ""))

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._host: QWidget | None = None
        self._rebuild()
        # Open at the same screen position as the File Manager window.
        self.move(336, 5)

    def _rebuild(self) -> None:
        """(Re)build the whole body."""
        if self._host is not None:
            self._outer.removeWidget(self._host)
            self._host.deleteLater()
            self._host = None
        self._host = QWidget()
        self._outer.addWidget(self._host)
        self._build_ui(self._host)

    def _build_ui(self, host: QWidget) -> None:
        layout = QHBoxLayout(host)
        layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # --- Left summary panel ---
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.setSpacing(4)
        left_layout.setContentsMargins(12, 12, 12, 12)

        result = self._result
        pct = float(result.get("performance_percentile", 0.0))
        pass_pct_val = result.get("pass_performance_percentile")
        margin_pct_val = result.get("margin_performance_percentile")

        def _line(text: str, bold: bool = True) -> QLabel:
            if bold:
                text = f"<b>{text}</b>"
            lbl = QLabel(text)
            lbl.setStyleSheet("font-size: 13px; color: #333333;")
            lbl.setWordWrap(True)
            left_layout.addWidget(lbl)
            return lbl

        def _kv(label: str, value: Any) -> QLabel:
            lbl = QLabel(f"<b>{label}:</b> {value}")
            lbl.setStyleSheet("font-size: 13px; color: #333333;")
            lbl.setWordWrap(True)
            left_layout.addWidget(lbl)
            return lbl

        checkpoint = str(result.get("checkpoint_exercise", ""))
        rank = result.get("checkpoint_rank")
        if rank is not None:
            checkpoint += f" (rank {rank})"

        _kv("Subject", result.get("subject", ""))
        cur_key = result.get("curriculum", "")
        _kv("Curriculum", CURRICULA.get(cur_key, {}).get("label", cur_key))
        _kv("Checkpoint", checkpoint)
        _kv("Peers compared", result.get("n_peers", 0))

        left_layout.addSpacing(10)
        _line("Training Time")
        _line(f"Subject's time: {self._fmt(result.get('subject_time'))}", bold=False)
        _line(f"Peers Mean Time: {self._fmt(result.get('peer_mean'))}", bold=False)
        _line(f"Performance Percentile: {pct:.1f}%", bold=False)
        summary = QLabel(
            f"The subject's time is better than {pct:.1f}% of their peers at this point."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("font-size: 13px; color: #333333;")
        left_layout.addWidget(summary)

        left_layout.addSpacing(10)
        _line("PASS Attempts %")
        _line(f"Subject's PASS %: {self._fmt_pct(result.get('subject_pass_pct'))}", bold=False)
        _line(f"Peers Mean PASS %: {self._fmt_pct(result.get('pass_peer_mean'))}", bold=False)
        if pass_pct_val is not None:
            _line(f"Performance Percentile: {pass_pct_val:.1f}%", bold=False)
        else:
            _line("Performance Percentile: N/A", bold=False)
        if pass_pct_val is not None:
            pass_summary = QLabel(
                f"The subject's PASS rate is better than {pass_pct_val:.1f}% of their peers at this point."
            )
            pass_summary.setWordWrap(True)
            pass_summary.setStyleSheet("font-size: 13px; color: #333333;")
            left_layout.addWidget(pass_summary)

        left_layout.addSpacing(10)
        _line("Average Proficiency Margin")
        _line(f"Subject's Margin: {self._fmt_pct(result.get('subject_avg_margin'))}", bold=False)
        _line(f"Peers Mean Margin: {self._fmt_pct(result.get('margin_peer_mean'))}", bold=False)
        if margin_pct_val is not None:
            _line(f"Performance Percentile: {margin_pct_val:.1f}%", bold=False)
        else:
            _line("Performance Percentile: N/A", bold=False)
        if margin_pct_val is not None:
            margin_summary = QLabel(
                f"The subject's Proficiency Margin is better than {margin_pct_val:.1f}% of their peers at this point."
            )
            margin_summary.setWordWrap(True)
            margin_summary.setStyleSheet("font-size: 13px; color: #333333;")
            left_layout.addWidget(margin_summary)

        left_layout.addSpacing(10)
        _line("* higher = better", bold=False)

        left_layout.addStretch(1)

        # --- Right chart panel ---
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 10, 10, 10)

        view_combo = QComboBox()
        view_combo.addItem("Overview")
        view_combo.addItem("Training Time by Exercise")
        view_combo.addItem("PASS Attempts % by Exercise")
        view_combo.addItem("Avg. Proficiency Margin by Exercise")
        right_layout.addWidget(view_combo)

        chart_stack = QStackedWidget()

        overview_page = QWidget()
        overview_layout = QHBoxLayout(overview_page)
        overview_layout.setContentsMargins(0, 0, 0, 0)
        time_chart = self._create_chart("Training Time", pct, show_ylabel=True)
        overview_layout.addWidget(time_chart, 1)
        pass_chart = self._create_chart(
            "PASS Attempts %", pass_pct_val if pass_pct_val is not None else 50.0, show_ylabel=False
        )
        overview_layout.addWidget(pass_chart, 1)
        margin_chart = self._create_chart(
            "Avg. Proficiency Margin", margin_pct_val if margin_pct_val is not None else 50.0, show_ylabel=False
        )
        overview_layout.addWidget(margin_chart, 1)
        chart_stack.addWidget(overview_page)

        chart_stack.addWidget(self._create_by_exercise_chart("time_performance_percentile"))
        chart_stack.addWidget(self._create_by_exercise_chart("pass_performance_percentile"))
        chart_stack.addWidget(self._create_by_exercise_chart("margin_performance_percentile"))

        view_combo.currentIndexChanged.connect(chart_stack.setCurrentIndex)
        right_layout.addWidget(chart_stack, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([320, 780])
        layout.addWidget(splitter)

    def _create_chart(self, title: str, pct: float, show_ylabel: bool = True) -> QWidget:
        fig = Figure(figsize=(3.6, 4.2), dpi=100, tight_layout=True)
        ax = fig.add_subplot(111)

        pct = float(pct)

        # Diverging vertical bar from the 50% baseline
        if pct >= 50.0:
            color = "#2ca02c"  # green
            bottom = 50.0
            height = pct - 50.0
        else:
            color = "#d62728"  # red
            bottom = pct
            height = 50.0 - pct

        ax.bar(
            0,
            height,
            width=0.35,
            bottom=bottom,
            color=color,
            edgecolor="black",
            linewidth=1.2,
            zorder=3,
        )

        # 50% baseline (x-axis)
        ax.axhline(50.0, color="#333333", linewidth=2, zorder=2)

        # Styling
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xticks([])
        if show_ylabel:
            ax.set_ylabel("Performance Percentile", fontsize=12)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        # Value label
        offset = 4.0 if pct >= 50.0 else -4.0
        va = "bottom" if pct >= 50.0 else "top"
        ax.text(
            0,
            pct + offset,
            f"{pct:.1f}%",
            ha="center",
            va=va,
            fontsize=12,
            fontweight="bold",
        )

        return FigureCanvas(fig)

    def _create_by_exercise_chart(self, pct_key: str) -> QWidget:
        entries = [e for e in self._result.get("by_exercise", []) if e.get(pct_key) is not None]

        if not entries:
            lbl = QLabel("No comparable exercise-level data available.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("font-size: 13px; color: #666666;")
            return lbl

        n = len(entries)
        bar_width_in = 0.55
        fig_width = max(5.0, bar_width_in * n + 1.0)
        fig = Figure(figsize=(fig_width, 4.2), dpi=100, tight_layout=True)
        ax = fig.add_subplot(111)

        for i, e in enumerate(entries):
            pct = float(e[pct_key])
            if pct >= 50.0:
                color = "#2ca02c"
                bottom = 50.0
                height = pct - 50.0
            else:
                color = "#d62728"
                bottom = pct
                height = 50.0 - pct
            ax.bar(i, height, width=0.5, bottom=bottom, color=color, edgecolor="black", linewidth=1.0, zorder=3)
            offset = 3.0 if pct >= 50.0 else -3.0
            va = "bottom" if pct >= 50.0 else "top"
            ax.text(i, pct + offset, f"{pct:.0f}%", ha="center", va=va, fontsize=9, fontweight="bold")

        ax.axhline(50.0, color="#333333", linewidth=1.5, zorder=2)
        ax.set_ylim(0, 100)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.set_xlim(-0.6, n - 0.4)
        ax.set_xticks(list(range(n)))
        ax.set_xticklabels([e["label"] for e in entries], fontsize=9)
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", bottom=False, top=True, labeltop=True, labelbottom=False)
        ax.set_ylabel("Performance Percentile", fontsize=11)
        ax.yaxis.grid(True, linestyle="--", alpha=0.5)
        ax.set_axisbelow(True)

        canvas = FigureCanvas(fig)
        canvas.setMinimumWidth(int(fig_width * 100))

        scroll = QScrollArea()
        scroll.setWidget(canvas)
        scroll.setWidgetResizable(False)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    @staticmethod
    def _fmt(seconds: float | None) -> str:
        if seconds is None:
            return "N/A"
        try:
            total = int(round(float(seconds)))
        except Exception:
            return "N/A"
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    @staticmethod
    def _fmt_pct(value: float | None) -> str:
        if value is None:
            return "N/A"
        try:
            return f"{float(value):.2f}%"
        except Exception:
            return "N/A"


# =============================================================================
#  [SEC-14] DATA SHOW WINDOW
# =============================================================================

class DataShowWindow(QMainWindow):

    def __init__(self, clean_path: str):
        super().__init__()

        self.clean_path = clean_path
        self.clean_filename = os.path.basename(clean_path)

        self.setWindowTitle(f"Data Show: {self.clean_filename}")
        # Open at the exact screen position and size measured with AutoHotkey Spy.
        self.resize(1253, 630)
        self.move(338, 6)
        self.setStyleSheet(
            "QMainWindow { border-top: 3px solid #008941; }"
            "QComboBox { padding: 3px; }"
            "QPushButton { background: #008941; color: white; padding: 6px 14px; border: none; border-radius: 3px; }"
            "QPushButton:hover { background: #00A34E; }"
            "QPushButton:disabled { background: #cccccc; color: #888888; }"
        )

        self.classified_rows = classify_clean_file(clean_path)
        enrich_rows_with_exercise_defs(self.classified_rows, EXERCISE_DEFS)

        self.current_rows: list[dict[str, Any]] = []
        self.current_valid_score200_keys: list[str] = []
        self.current_subject: str = ""
        self.current_exercise: str = ""
        self.current_exerc_abb: str = ""

        self._graph_windows: list[GraphWindow] = []
        self._naed1_details_windows: list[NAED1DetailsWindow] = []
        self._naed2_details_windows: list[NAED2DetailsWindow] = []
        self._naed3_details_windows: list[NAED3DetailsWindow] = []
        self._recommendations_windows: list['RecommendationsWindow'] = []
        self._ds_progress_graph_windows: list = []
        self._ds_training_analysis_windows: list = []
        self._ds_proficiency_windows: list[ProficiencyValuesWindow] = []

        self._last_naed1_details: dict[str, Any] = {}
        self._last_naed2_details: dict[str, Any] = {}

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        heading = QLabel(f"<b>File:</b> {self.clean_filename}")
        heading.setTextFormat(Qt.RichText)
        main_layout.addWidget(heading)

        # Subject + Exercise
        pick_layout = QHBoxLayout()
        pick_layout.setContentsMargins(0, 0, 0, 0)
        pick_layout.setSpacing(8)

        pick_layout.addWidget(QLabel("Subject:"))
        self.subject_combo = QComboBox()
        self.subject_combo.currentIndexChanged.connect(self.on_subject_changed)
        pick_layout.addWidget(self.subject_combo, stretch=1)

        pick_layout.addWidget(QLabel("Exercise:"))
        self.exercise_combo = QComboBox()
        self.exercise_combo.currentIndexChanged.connect(self.on_exercise_changed)
        pick_layout.addWidget(self.exercise_combo, stretch=2)

        self.btn_proficiency_values = QPushButton("Proficiency Values")
        self.btn_proficiency_values.clicked.connect(self._show_proficiency_values)
        self.btn_proficiency_values.setEnabled(False)
        pick_layout.addWidget(self.btn_proficiency_values)

        main_layout.addLayout(pick_layout)

        # Table
        headers = ["Attempt Number", "PASS", "Date - Time"] + [label for _, label in SCORE_COLUMNS] + ["\U0001f4f7"]
        self._screenshot_col = len(headers) - 1
        self.attempts_table = QTableWidget(0, len(headers))
        self.attempts_table.setHorizontalHeaderLabels(headers)
        self.attempts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.attempts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.attempts_table.setSelectionMode(QTableWidget.SingleSelection)

        self.attempts_table.setColumnHidden(0, True)  # hide Attempt Number (rows are numbered)

        header = self.attempts_table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        # Compact selectors row
        self._score_col_index = {key: 3 + idx for idx, (key, _lbl) in enumerate(SCORE_COLUMNS)}
        self._auto_hidden_cols: set[int] = set()
        selectors = QHBoxLayout()
        selectors.setContentsMargins(0, 0, 0, 0)
        selectors.setSpacing(16)

        selectors.addWidget(QLabel("View:"))

        self.chk_hide_dt = QCheckBox("Hide Date and Time")
        self.chk_hide_dt.setChecked(True)
        self.chk_hide_dt.toggled.connect(self._apply_column_visibility)
        selectors.addWidget(self.chk_hide_dt)

        self.chk_hide_raw = QCheckBox("Hide Raw Scores")
        self.chk_hide_raw.setChecked(True)
        self.chk_hide_raw.toggled.connect(self._apply_column_visibility)
        selectors.addWidget(self.chk_hide_raw)

        self.lbl_incomplete_attempts = QLabel("Number of incomplete attempts: N/A")
        selectors.addWidget(self.lbl_incomplete_attempts)

        selectors.addStretch(1)
        main_layout.addLayout(selectors)

        main_layout.addWidget(self.attempts_table)

        # Summary + Buttons row
        summary = QHBoxLayout()
        summary.setContentsMargins(0, 0, 0, 0)
        summary.setSpacing(24)

        self.lbl_pass_attempts = QLabel("Pass Attempts: 0")
        self.lbl_consecutive_pass = QLabel("Consecutive Pass Attempts: 0")
        self.lbl_exercise_proficiency = QLabel("Exercise Proficiency: NO")

        self.lbl_perf_margin = QLabel("")
        self.lbl_perf_margin.setVisible(False)

        self.lbl_next_reco = QLabel("NAED-1: WAIT")
        self.lbl_confidence = QLabel("Confidence: 0.00")

        summary.addWidget(self.lbl_pass_attempts)
        summary.addWidget(self.lbl_consecutive_pass)
        summary.addWidget(self.lbl_exercise_proficiency)
        summary.addWidget(self.lbl_perf_margin)
        summary.addWidget(self.lbl_next_reco)
        summary.addWidget(self.lbl_confidence)
        summary.addStretch(1)

        self.btn_recommendations = QPushButton("Recommendations")
        self.btn_recommendations.clicked.connect(self.show_recommendations)
        self.btn_recommendations.setEnabled(False)
        self.btn_recommendations.setVisible(False)
        summary.addWidget(self.btn_recommendations)

        self.btn_graphs = QPushButton("Show Graphs")
        self.btn_graphs.clicked.connect(self.show_graphs)
        self.btn_graphs.setEnabled(False)
        summary.addWidget(self.btn_graphs)

        main_layout.addLayout(summary)

        self.populate_subjects()

        # Auto-select first subject (which cascades to first exercise)
        if self.subject_combo.count() > 1:
            self.subject_combo.setCurrentIndex(1)

    def reload_clean_file(self, subject: str | None = None, exercise: str | None = None) -> None:
        """Reload the underlying MimicClean CSV from disk and optionally select a subject/exercise."""
        self.classified_rows = classify_clean_file(self.clean_path)
        enrich_rows_with_exercise_defs(self.classified_rows, EXERCISE_DEFS)
        self.populate_subjects()

        if subject:
            self._select_combo_text(self.subject_combo, subject)
        if exercise:
            self._select_combo_text(self.exercise_combo, exercise)

    @staticmethod
    def _select_combo_text(combo: QComboBox, text: str) -> None:
        if not text:
            return
        idx = combo.findText(text, Qt.MatchFixedString)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _open_screenshot(self, path: str) -> None:
        """Open a screenshot image in the system's default viewer."""
        try:
            os.startfile(path)
        except Exception as e:
            QMessageBox.warning(self, "Cannot open image", f"Failed to open:\n{path}\n\n{e}")

    def _apply_column_visibility(self):
        # Reset visibility for all columns we may toggle so previous selections do not "stick"
        self.attempts_table.setColumnHidden(2, False)
        for key, _lbl in SCORE_COLUMNS:
            col = self._score_col_index.get(key)
            if col is not None:
                self.attempts_table.setColumnHidden(col, False)

        # Apply user toggles
        self.attempts_table.setColumnHidden(2, self.chk_hide_dt.isChecked())

        hide_raw = self.chk_hide_raw.isChecked()
        if hide_raw:
            for key, _lbl in SCORE_COLUMNS:
                if key.endswith("_score_raw"):
                    col = self._score_col_index.get(key)
                    if col is not None:
                        self.attempts_table.setColumnHidden(col, True)

        # Apply auto-hidden columns (metrics absent in current selection)
        for col in getattr(self, "_auto_hidden_cols", set()):
            self.attempts_table.setColumnHidden(col, True)


    @staticmethod
    def _compute_pass_stats(pass_flags: list[bool]) -> tuple[int, int]:
        pass_attempts = sum(1 for x in pass_flags if x)
        if pass_attempts == 0:
            return 0, 0

        max_streak = 1
        current = 0
        for x in pass_flags:
            if x:
                current += 1
                if current > max_streak:
                    max_streak = current
            else:
                current = 0
        return pass_attempts, max_streak

    @staticmethod
    def _compute_performance_margin(
        rows: list[dict],
        pass_flags: list[bool],
        n: int = 3,
    ) -> float | None:
        """Thin wrapper — delegates to standalone compute_performance_margin (SEC-OM)."""
        return compute_performance_margin(rows, pass_flags, n)

    def _set_summary_labels(self, pass_attempts: int, max_consecutive: int):
        self.lbl_pass_attempts.setText(f"Pass Attempts: {pass_attempts}")
        self.lbl_consecutive_pass.setText(f"Consecutive Pass Attempts: {max_consecutive}")

        proficient = (pass_attempts >= 3 and max_consecutive >= 2)
        self.lbl_exercise_proficiency.setText(
            f"Exercise Proficiency: {'YES' if proficient else 'NO'}"
        )
        self.lbl_exercise_proficiency.setStyleSheet(
            "color: green;" if proficient else "color: red;"
        )

    def _reset_reco_ui(self):
        self._last_naed1_details = {}
        self._last_naed2_details = {}
        self.lbl_next_reco.setText("NAED-1: WAIT")
        self.lbl_next_reco.setStyleSheet("color: red;")
        self.lbl_confidence.setText("Confidence: 0.00")
        self.lbl_confidence.setStyleSheet("")
        self.btn_recommendations.setEnabled(False)
        self.btn_recommendations.setVisible(False)


    def populate_subjects(self):
        subjects = sorted({r.get("subject", "") for r in self.classified_rows if r.get("subject")})

        self.subject_combo.blockSignals(True)
        self.subject_combo.clear()
        self.subject_combo.addItem("-- Select --")
        for s in subjects:
            self.subject_combo.addItem(s)
        self.subject_combo.blockSignals(False)

        self.exercise_combo.blockSignals(True)
        self.exercise_combo.clear()
        self.exercise_combo.addItem("-- Select --")
        self.exercise_combo.blockSignals(False)

        self.attempts_table.setRowCount(0)
        self._set_summary_labels(0, 0)
        self._apply_column_visibility()

        self.current_rows = []
        self.current_subject = ""
        self.current_exercise = ""
        self.current_exerc_abb = ""
        self.btn_graphs.setEnabled(False)
        self.btn_proficiency_values.setEnabled(False)
        self._reset_reco_ui()

    def on_subject_changed(self):
        subject = self.subject_combo.currentText()
        if subject == "-- Select --":
            self.exercise_combo.setEnabled(False)
            self.exercise_combo.blockSignals(True)
            self.exercise_combo.clear()
            self.exercise_combo.addItem("-- Select --")
            self.exercise_combo.blockSignals(False)
            self.attempts_table.setRowCount(0)
            self._set_summary_labels(0, 0)
            self.current_rows = []
            self.current_subject = ""
            self.current_exercise = ""
            self.current_exerc_abb = ""
            self.btn_graphs.setEnabled(False)
            self.btn_proficiency_values.setEnabled(False)
            self._reset_reco_ui()
            return

        # Collect this subject's exercises together with every attempt timestamp,
        # so each exercise can be ordered by when it was FIRST attempted.
        _stamps_by_ex: dict[str, list[datetime]] = {}
        for r in self.classified_rows:
            if r.get("subject") != subject:
                continue
            _ex = r.get("exercise", "")
            if not _ex:
                continue
            _lst = _stamps_by_ex.setdefault(_ex, [])
            _dt = r.get("date_time")
            if _dt is not None:
                _lst.append(_dt)

        # Curriculum order, used only to break ties and to place undated exercises.
        _full_to_num: dict[str, int] = {}
        for _abb, _meta in EXERCISE_DEFS.items():
            _fn = (_meta.get("exerc_full") or "").strip()
            if _fn:
                _full_to_num[_fn] = _meta.get("exerc_number", 9999)

        def _first_attempt_key(ex: str):
            """Chronological by first attempt; exercises with no usable timestamp
            fall to the end in curriculum order rather than being dropped."""
            stamps = _stamps_by_ex.get(ex) or []
            num = _full_to_num.get(ex, 9999)
            if stamps:
                return (0, min(stamps), num, ex)
            return (1, datetime.max, num, ex)

        exercises = sorted(_stamps_by_ex.keys(), key=_first_attempt_key)

        self.exercise_combo.setEnabled(True)
        self.exercise_combo.blockSignals(True)
        self.exercise_combo.clear()
        self.exercise_combo.addItem("-- Select --")
        for ex in exercises:
            self.exercise_combo.addItem(ex)
        self.exercise_combo.blockSignals(False)

        self.attempts_table.setRowCount(0)
        self._set_summary_labels(0, 0)
        self._apply_column_visibility()

        self.current_rows = []
        self.current_subject = subject
        self.current_exercise = ""
        self.current_exerc_abb = ""
        self.btn_graphs.setEnabled(False)
        self.btn_proficiency_values.setEnabled(False)
        self._reset_reco_ui()

        # Auto-select the LAST exercise, i.e. the most recently started one now that
        # the list is in first-attempt order (must run last so on_exercise_changed
        # sees clean state). Index 0 is the "-- Select --" placeholder.
        if self.exercise_combo.count() > 1:
            self.exercise_combo.setCurrentIndex(self.exercise_combo.count() - 1)

    def _update_incomplete_attempts_label(self, subject: str, exercise: str) -> None:
        """Show the incomplete-attempt count for subject/exercise from the
        IncompleteAttempts_<subject>_*.csv file, or N/A if no file exists."""
        text = "Number of incomplete attempts: N/A"
        if subject and exercise:
            folder = os.path.dirname(os.path.abspath(self.clean_path))
            prefix = f"incompleteattempts_{subject.lower()}_"
            inc_path = None
            try:
                for name in os.listdir(folder):
                    if name.lower().startswith(prefix) and name.lower().endswith(".csv"):
                        inc_path = os.path.join(folder, name)
                        break
            except Exception:
                inc_path = None

            if inc_path:
                # File exists: exercises not listed in it have zero incompletes
                count = 0
                total_time = 0.0
                try:
                    with open(inc_path, "r", encoding="utf-8-sig", errors="replace") as f:
                        for raw in f:
                            parts = raw.strip().split(",")
                            if len(parts) < 4:
                                continue
                            ex_name = ",".join(parts[1:-2]).strip()
                            if parts[0].strip() == subject and ex_name == exercise:
                                try:
                                    count = int(parts[-2].strip())
                                except ValueError:
                                    pass
                                try:
                                    total_time = float(parts[-1].strip())
                                except ValueError:
                                    pass
                                break
                    mins, secs = divmod(int(round(total_time)), 60)
                    text = (
                        f"Number of incomplete attempts: {count} "
                        f"(total time: {mins}:{secs:02d})"
                    )
                except Exception:
                    pass
        self.lbl_incomplete_attempts.setText(text)

    def on_exercise_changed(self):
        subject = self.subject_combo.currentText()
        exercise = self.exercise_combo.currentText()

        if subject == "-- Select --" or exercise == "-- Select --":
            self.attempts_table.setRowCount(0)
            self._set_summary_labels(0, 0)
            self.lbl_perf_margin.setVisible(False)
            self.current_rows = []
            self.current_subject = subject if subject != "-- Select --" else ""
            self.current_exercise = ""
            self.current_exerc_abb = ""
            self.btn_graphs.setEnabled(False)
            self._reset_reco_ui()
            self._update_incomplete_attempts_label("", "")
            return

        rows = [
            r for r in self.classified_rows
            if r.get("subject") == subject and r.get("exercise") == exercise
        ]
        rows.sort(key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min))

        self.current_rows = rows
        self.current_subject = subject
        self.current_exercise = exercise
        self.current_exerc_abb = rows[0].get("exerc_abb", "") if rows else ""
        self.btn_proficiency_values.setEnabled(bool(self.current_exerc_abb))

        self._update_incomplete_attempts_label(subject, exercise)

        self.attempts_table.setRowCount(len(rows))

        # Determine which metric columns to show based on EXERCISE_METRICS
        exerc_abb = rows[0].get("exerc_abb", "") if rows else ""
        allowed_metrics = EXERCISE_METRICS.get(exerc_abb, [])
        allowed_score_keys: set[str] = {"overall_score"}
        for m in allowed_metrics:
            allowed_score_keys.add(f"{m}_score_raw")
            allowed_score_keys.add(f"{m}_score_200")

        # PASS / proficiency considers the score_200 metrics defined for this exercise
        score200_keys = [f"{m}_score_200" for m in allowed_metrics]
        self.current_valid_score200_keys = list(score200_keys)

        pass_flags: list[bool] = []

        for i, rec in enumerate(rows, start=1):
            # Attempt Number (col 0)
            self.attempts_table.setItem(i - 1, 0, QTableWidgetItem(str(i)))

            # score_200_pass_total per attempt
            rec["score_200_pass_total"] = compute_score200_pass_total(rec, score200_keys)

            # PASS (col 1) = YES if ALL *_score_200 >= 100
            all_pass = (rec["score_200_pass_total"] == len(score200_keys))
            pass_flags.append(all_pass)

            pass_item = QTableWidgetItem("YES" if all_pass else "NO")
            pass_item.setForeground(QBrush(QColor("green" if all_pass else "red")))
            self.attempts_table.setItem(i - 1, 1, pass_item)

            # Date - Time (col 2)
            self.attempts_table.setItem(i - 1, 2, QTableWidgetItem(_fmt_dt(rec.get("date_time"))))

            # Scores start at col 3
            col = 3
            for key, _label in SCORE_COLUMNS:
                val = rec.get(key)

                if val is None:
                    txt = ""
                elif isinstance(val, (int, float)):
                    txt = f"{float(val):.2f}"
                else:
                    txt = str(val)

                item = QTableWidgetItem(txt)

                # Color *_score_200 cells
                if key.endswith("_score_200"):
                    try:
                        num = float(val)
                        item.setForeground(QBrush(QColor("green" if num >= 100 else "red")))
                    except (TypeError, ValueError):
                        pass

                if key == "overall_score":
                    pass_item2 = self.attempts_table.item(i - 1, 1)
                    if pass_item2:
                        item.setForeground(QBrush(QColor("green" if pass_item2.text() == "YES" else "red")))

                self.attempts_table.setItem(i - 1, col, item)
                col += 1

            # Screenshot view button (last column)
            ss_file = rec.get("screenshot_file")
            if ss_file:
                script_dir = _script_dir()
                ss_path = os.path.join(script_dir, "analysis_screenshots", ss_file)
                if os.path.isfile(ss_path):
                    btn = QPushButton("View")
                    btn.setFixedSize(50, 22)
                    btn.setStyleSheet("font-size: 11px;")
                    btn.clicked.connect(lambda checked, p=ss_path: self._open_screenshot(p))
                    self.attempts_table.setCellWidget(i - 1, self._screenshot_col, btn)

        # Auto-hide metric columns not defined in EXERCISE_METRICS for this exercise
        self._auto_hidden_cols = set()
        for key, _lbl in SCORE_COLUMNS:
            if key not in allowed_score_keys:
                col = self._score_col_index.get(key)
                if col is not None:
                    self._auto_hidden_cols.add(col)

        # Update proficiency summary labels
        pass_attempts, max_consecutive = self._compute_pass_stats(pass_flags)
        self._set_summary_labels(pass_attempts, max_consecutive)

        # Proficiency Margin (mean across all PASS attempts)
        perf_margin = self._compute_performance_margin(rows, pass_flags)
        if perf_margin is not None:
            self.lbl_perf_margin.setText(f"Perf. Margin: {perf_margin:.2f}%")
            self.lbl_perf_margin.setStyleSheet("color: green;" if perf_margin > 0 else "color: red;")
            self.lbl_perf_margin.setVisible(True)
        else:
            self.lbl_perf_margin.setVisible(False)

        # ----------------------------
        # Phase 2: NAED-1 (WAIT / ACT)
        # ----------------------------

        naed1 = compute_naed1_metrics_and_decision(
            exercise_rows=rows,
            score200_keys=score200_keys,
            subject=subject,
            current_exercise=exercise,
            all_rows=self.classified_rows,
        )

        self._last_naed1_details = naed1

        decision = naed1.get("decision", "WAIT")
        conf = float(naed1.get("confidence", 0.0))

        self.lbl_next_reco.setText(f"NAED-1: {decision}")
        self.lbl_confidence.setText(f"Confidence: {conf:.2f}")

        is_act = (decision == "ACT")
        self.lbl_next_reco.setStyleSheet("color: green;" if is_act else "color: red;")

        # NAED-2 is only relevant if NAED-1 is ACT
        if is_act:
            self._last_naed2_details = compute_naed2_decision(
                all_attempt_rows=rows,
                naed1_metrics=naed1,
            )
        else:
            self._last_naed2_details = {}

        # Recommendations button appears only when NAED-1 == ACT
        self.btn_recommendations.setVisible(is_act)
        self.btn_recommendations.setEnabled(is_act)

        # Re-apply visibility after repopulating
        self._apply_column_visibility()

        # Enable graphs if we have data and matplotlib is available
        self.btn_graphs.setEnabled(len(self.current_rows) > 0 and Figure is not None and np is not None)

    
    def show_recommendations(self):
        if not self._last_naed1_details:
            QMessageBox.information(self, "No details", "No recommendation details are available yet.")
            return

        # NAED-2 exists only when NAED-1 is ACT (same gating as the previous separate buttons).
        naed2 = self._last_naed2_details or {}

        naed3: dict[str, Any] = {}
        naed2_dec = (naed2.get("decision") or "").strip() if isinstance(naed2, dict) else ""
        if naed2_dec in {"UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL"}:
            try:
                naed3 = compute_naed3_recommendation(self.current_exercise, naed2_dec, subject=self.current_subject)
            except Exception as e:
                naed3 = {"status": "ERROR", "message": str(e)}

        # Compute extra context for the live JSON entry
        exerc_abb = self.current_rows[0].get("exerc_abb", "") if self.current_rows else ""
        total_attempt_number = sum(
            1 for r in self.classified_rows if r.get("subject") == self.current_subject
        )
        exercise_attempt_number = len(self.current_rows)

        title = f"Recommendations - {self.current_subject} - {self.current_exercise}"
        w = RecommendationsWindow(
            title,
            naed1=self._last_naed1_details,
            naed2=naed2,
            naed3=naed3,
            clean_path=self.clean_path,
            subject=self.current_subject,
            exercise=self.current_exercise,
            exercise_abbreviation=exerc_abb,
            total_attempt_number=total_attempt_number,
            exercise_attempt_number=exercise_attempt_number,
        )
        self._recommendations_windows.append(w)
        w.show()

        if naed2_dec == "KEEP" and not _history_decision_exists(
            self.current_subject, exerc_abb, exercise_attempt_number
        ):
            QTimer.singleShot(100, lambda rec=w: self._show_keep_auto_accept(rec))

    def _show_keep_auto_accept(self, rec_window: RecommendationsWindow):
        """Show the KEEP countdown; accept the recommendation on OK/timeout,
        or leave the recommendation window untouched on Cancel."""
        dlg = KeepAutoAcceptDialog(parent=rec_window, seconds=10)
        if dlg.exec() == QDialog.Accepted:
            rec_window._on_accept_yes()

    def show_naed1_details(self):
        if not self._last_naed1_details:
            QMessageBox.information(self, "No details", "No NAED-1 details are available yet.")
            return

        title = f"NAED-1 Details - {self.current_subject} - {self.current_exercise}"
        w = NAED1DetailsWindow(title, self._last_naed1_details)
        self._naed1_details_windows.append(w)
        w.show()

    def show_naed2_details(self):
        if not self._last_naed2_details:
            QMessageBox.information(self, "No details", "No NAED-2 details are available yet.")
            return

        title = f"NAED-2 Details - {self.current_subject} - {self.current_exercise}"
        w = NAED2DetailsWindow(title, self._last_naed2_details, clean_path=self.clean_path, subject=self.current_subject, exercise=self.current_exercise)
        self._naed2_details_windows.append(w)
        w.show()

    def show_naed3_details(self):
        if not self._last_naed2_details:
            QMessageBox.information(self, "No details", "No NAED-2 details are available yet.")
            return

        naed2_dec = (self._last_naed2_details.get("decision") or "").strip() if isinstance(self._last_naed2_details, dict) else ""
        if naed2_dec not in {"UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL"}:
            QMessageBox.information(self, "Not applicable", "NAED-3 is not applicable for this NAED-2 decision.")
            return

        naed3 = compute_naed3_recommendation(self.current_exercise, naed2_dec, subject=self.current_subject)
        title = f"NAED-3 Details - {self.current_subject} - {self.current_exercise}"
        w = NAED3DetailsWindow(title, naed3)
        self._naed3_details_windows.append(w)
        w.show()


    def show_graphs(self):
            if not self.current_rows:
                QMessageBox.information(self, "No data", "Select a Subject and Exercise first.")
                return

            if Figure is None or FigureCanvas is None or np is None:
                QMessageBox.warning(
                    self,
                    "Matplotlib not found",
                    "Matplotlib is not installed or could not be imported.\n\n"
                    "Install it with:\n"
                    "  py -m pip install matplotlib"
                )
                return

            title = f"Graph - {self.current_subject} - {self.current_exercise}"
            try:
                w = GraphWindow(title, self.current_rows, self.current_valid_score200_keys)
            except Exception as e:
                QMessageBox.critical(self, "Graphs failed", f"Could not open graphs:\n{e}")
                return

            self._graph_windows.append(w)
            w.show()

    # ------------------------------------------------------------------
    # Subject-level progress helpers (for Progress Graph / Analysis)
    # ------------------------------------------------------------------

    def _compute_subject_progress(self, subject: str) -> dict[str, Any]:
        """Compute per-subject progress data from classified_rows.

        Returns a dict with keys:
            exercise_sequence  – list[str] of exerc_abb in chronological order
            cumulative_times   – list[float] parallel to exercise_sequence
            green_exercises    – set[str] of exerc_abb with proficiency
            exercise_time_secs – dict[str, float] total time per exerc_abb
        """
        rows = [r for r in self.classified_rows if r.get("subject") == subject]
        rows.sort(key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min))

        exercise_sequence: list[str] = []
        cumulative_times: list[float] = []
        running_time = 0.0
        exercise_time_secs: dict[str, float] = {}

        # Per-exercise pass stats
        exercise_stats: dict[str, dict[str, int]] = {}

        for rec in rows:
            abb = rec.get("exerc_abb", "")
            if not abb or abb not in EXERCISE_DEFS:
                continue

            # Sequence + cumulative time
            t = rec.get("ttc_score_raw")
            try:
                secs = float(t)
            except (TypeError, ValueError):
                secs = 0.0
            if secs < 0:
                secs = 0.0
            running_time += secs
            exercise_sequence.append(abb)
            cumulative_times.append(running_time)
            exercise_time_secs[abb] = exercise_time_secs.get(abb, 0.0) + secs

            # Pass flag for this attempt
            metrics = EXERCISE_METRICS.get(abb, [])
            score200_keys = [f"{m}_score_200" for m in metrics]
            pt = compute_score200_pass_total(rec, score200_keys) if score200_keys else 0
            passed = bool(score200_keys) and pt == len(score200_keys)

            st = exercise_stats.setdefault(abb, {"total": 0, "cur": 0, "max_consec": 0})
            if passed:
                st["total"] += 1
                st["cur"] += 1
                if st["cur"] > st["max_consec"]:
                    st["max_consec"] = st["cur"]
            else:
                st["cur"] = 0

        green_exercises = {
            ex for ex, st in exercise_stats.items()
            if st["total"] >= 3 and st["max_consec"] >= 2
        }

        return {
            "exercise_sequence": exercise_sequence,
            "cumulative_times": cumulative_times,
            "green_exercises": green_exercises,
            "exercise_time_secs": exercise_time_secs,
        }

    def _open_ds_progress_graph(self):
        subject = self.subject_combo.currentText()
        if subject == "-- Select --":
            QMessageBox.information(self, "No subject", "Please select a subject first.")
            return

        prog = self._compute_subject_progress(subject)
        title = f"Progress Graph - {subject}"

        curriculum = get_curriculum_for_subject(subject)
        svg_path = _curriculum_svg_path(curriculum) if curriculum else None

        if svg_path:
            try:
                w = AdaptiveKGProgressGraphWindow(
                    title,
                    prog["exercise_sequence"],
                    svg_path,
                    green_exercises=prog["green_exercises"],
                    cumulative_times=prog["cumulative_times"],
                    parent=self,
                )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Could not create progress graph:\n{e}")
                return
            self._ds_progress_graph_windows.append(w)
            w.show()
            return

        if Figure is None or FigureCanvas is None:
            QMessageBox.warning(self, "Matplotlib not found",
                                "Matplotlib is required for the Progress Graph.")
            return
        try:
            w = DSProgressGraphWindow(
                title,
                prog["exercise_sequence"],
                prog["green_exercises"],
                cumulative_times=prog["cumulative_times"],
                parent=self,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create progress graph:\n{e}")
            return
        self._ds_progress_graph_windows.append(w)
        w.show()

    def _open_ds_training_analysis(self):
        subject = self.subject_combo.currentText()
        if subject == "-- Select --":
            QMessageBox.information(self, "No subject", "Please select a subject first.")
            return

        prog = self._compute_subject_progress(subject)
        folder = os.path.dirname(os.path.abspath(self.clean_path))
        inc_count, inc_time = get_incomplete_totals(subject, folder)
        om = compute_om_summary(self.classified_rows, subject, inc_count, inc_time)
        title = f"Training Analysis - {subject}"
        try:
            w = DSTrainingAnalysisWindow(title, om, prog, parent=self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not create training analysis:\n{e}")
            return
        self._ds_training_analysis_windows.append(w)
        w.show()

    def _show_proficiency_values(self):
        """Open a read-only Proficiency Values window for the current exercise."""
        abb = self.current_exerc_abb
        if not abb:
            # Try to fall back to the exercise combo selection if current state is stale
            exercise = self.exercise_combo.currentText()
            if exercise and exercise != "-- Select --":
                row = next(
                    (
                        r for r in self.classified_rows
                        if r.get("subject") == self.subject_combo.currentText()
                        and r.get("exercise") == exercise
                    ),
                    None,
                )
                if row:
                    abb = row.get("exerc_abb", "")
        if not abb:
            QMessageBox.information(self, "No exercise", "Please select an exercise first.")
            return
        w = ProficiencyValuesWindow(parent=self, fixed_exercise=abb, read_only=True)
        self._ds_proficiency_windows.append(w)
        w.show()

    # ------------------------------------------------------------------
    # Retro History — retrospective NAED analysis exported as JSON
    # ------------------------------------------------------------------

    def _generate_retro_history_json(self):
        import json as _json

        subject = self.subject_combo.currentText()
        if subject == "-- Select --":
            QMessageBox.information(self, "No subject", "Please select a subject first.")
            return

        # All rows for this subject, chronological
        rows = [r for r in self.classified_rows if r.get("subject") == subject]
        rows.sort(key=lambda r: (r.get("date_time") is None, r.get("date_time") or datetime.min))
        total_lines = len(rows)
        if total_lines == 0:
            QMessageBox.information(self, "No data", "No attempt rows found for this subject.")
            return

        # Output path
        script_dir = _script_dir()
        hist_dir = os.path.join(script_dir, "analysis_history")
        os.makedirs(hist_dir, exist_ok=True)
        out_name = f"History_{subject}_{total_lines}-att.json"
        out_path = os.path.join(hist_dir, out_name)

        # Check for existing retro history file for this subject
        _existing_pat = re.compile(
            r"^History_" + re.escape(subject) + r"_(\d+)-att\.json$", re.IGNORECASE
        )
        existing_path_to_remove = None
        for fname in os.listdir(hist_dir):
            m = _existing_pat.match(fname)
            if m:
                existing_attempts = int(m.group(1))
                existing_path = os.path.join(hist_dir, fname)
                if existing_attempts >= total_lines:
                    QMessageBox.information(
                        self, "Up to date",
                        f"Retrospective history for {subject} already exists "
                        f"with {existing_attempts} attempts (current: {total_lines}).\n\n"
                        f"No update needed.",
                    )
                    return
                existing_path_to_remove = existing_path
                break

        if existing_path_to_remove is not None:
            reply = QMessageBox.question(
                self, "Overwrite existing file?",
                f"A retrospective history file for {subject} already exists "
                f"({os.path.basename(existing_path_to_remove)}).\n\n"
                f"Proceeding will overwrite (delete and regenerate) it. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        # Choose which curriculum logic to use for the retrospective recommendations
        _curriculum_choices = [
            ("Grad Student", "grad"),
            ("Resident - Fellow - Extensive", "resident_ext"),
        ]
        _labels = [lbl for lbl, _ in _curriculum_choices]
        chosen_label, ok = QInputDialog.getItem(
            self, "Choose Curriculum Logic",
            "Select which curriculum pathway should be used to compute the\n"
            "retrospective NAED-3 recommendations for this subject:",
            _labels, 0, False,
        )
        if not ok:
            return
        _retro_curriculum = dict(_curriculum_choices)[chosen_label]

        if existing_path_to_remove is not None:
            try:
                os.remove(existing_path_to_remove)
            except Exception:
                pass

        def _round(v, n=4):
            if isinstance(v, float):
                return round(v, n)
            return v

        _retro_connections = CURRICULA.get(_retro_curriculum, {}).get("connections", {})

        def _reverse_lookup_connection(from_abb: str, to_abb: str) -> str:
            """Find which connection type maps from_abb -> to_abb in the subject's curriculum."""
            if to_abb == from_abb:
                return "KEEP"
            conn = _retro_connections.get(from_abb, {})
            for conn_type, targets in conn.items():
                if to_abb in (targets if isinstance(targets, (list, tuple)) else [targets]):
                    return conn_type
            return "Unknown"

        results: list[dict[str, Any]] = []

        # Track per-exercise attempt counts as we iterate
        exercise_attempt_counts: dict[str, int] = {}
        # Track per-exercise accumulated rows
        exercise_rows_acc: dict[str, list[dict[str, Any]]] = {}

        for line_idx in range(total_lines):
            current_row = rows[line_idx]
            all_rows_up_to = rows[:line_idx + 1]

            exerc_abb = current_row.get("exerc_abb", "")
            exerc_full = EXERCISE_DEFS.get(exerc_abb, {}).get("exerc_full", exerc_abb)
            exercise_name_raw = (current_row.get("exercise") or "").strip()

            # Accumulate exercise rows
            exercise_rows_acc.setdefault(exerc_abb, []).append(current_row)
            exercise_attempt_counts[exerc_abb] = exercise_attempt_counts.get(exerc_abb, 0) + 1
            ex_attempt_num = exercise_attempt_counts[exerc_abb]

            # Exercise-specific rows up to this point
            ex_rows = exercise_rows_acc[exerc_abb][:]

            # Determine score200 keys for this exercise
            metrics = EXERCISE_METRICS.get(exerc_abb, [])
            score200_keys = [f"{m}_score_200" for m in metrics]

            # Ensure score_200_pass_total
            for rec in ex_rows:
                if "score_200_pass_total" not in rec:
                    rec["score_200_pass_total"] = compute_score200_pass_total(rec, score200_keys)

            # --- NAED-1 ---
            naed1 = compute_naed1_metrics_and_decision(
                exercise_rows=ex_rows,
                score200_keys=score200_keys,
                subject=subject,
                current_exercise=exercise_name_raw,
                all_rows=all_rows_up_to,
            )
            naed1_decision = naed1.get("decision")

            naed1_obj = {
                "window_n": naed1.get("window_n"),
                "total_n": naed1.get("total_n"),
                "reason": naed1.get("reason"),
                "confidence": _round(naed1.get("confidence")),
                "decision": naed1_decision,
            }

            # --- NAED-2 ---
            naed2_obj = None
            naed2_decision = None
            if naed1_decision == "ACT":
                naed2 = compute_naed2_decision(
                    all_attempt_rows=ex_rows,
                    naed1_metrics=naed1,
                )
                naed2_decision = naed2.get("decision")

                naed2_obj = {
                    "exercise_attempts": naed2.get("n"),
                    "Rm_last": _round(naed2.get("Rm_last")),
                    "slope_m": _round(naed2.get("slope_m")),
                    "mastery_bottleneck": naed2.get("mastery_bottleneck"),
                    "bottleneck_Rk": _round(naed2.get("bottleneck_Rk")),
                    "mean_other_Rk": _round(naed2.get("mean_other_Rk")),
                    "level_now": _round(naed2.get("level_now"), 2),
                    "level_now_norm": _round(naed2.get("level_now_norm")),
                    "pass_rate_all": _round(naed2.get("pass_rate_all")),
                    "pass_rate_weighted": _round(naed2.get("pass_rate_weighted")),
                    "consec_pass_all": naed2.get("consec_pass_all"),
                    "trailing_streak": naed2.get("trailing_streak"),
                    "directionality_plain": _round(naed2.get("directionality_plain")),
                    "directionality_weighted": _round(naed2.get("directionality")),
                    "volatility_weighted": _round(naed2.get("volatility")),
                    "spread": _round(naed2.get("spread")),
                    "stability": _round(naed2.get("stability")),
                    "outlier_downweighting": "MAD-based (Tukey-style)",
                    "Feedback_detection": {
                        "mastery_bottleneck": naed2.get("mastery_bottleneck"),
                        "bottleneck_Rk": _round(naed2.get("bottleneck_Rk")),
                        "mean_other_Rk": _round(naed2.get("mean_other_Rk")),
                        "mean_pass_total": _round(naed2.get("mean_pass_total"), 2),
                        "worst_metric": naed2.get("worst_metric"),
                        "worst_metric_pass_frac": _round(naed2.get("worst_metric_pass_frac")),
                        "avg_other_metric_pass_frac": _round(naed2.get("avg_other_metric_pass_frac")),
                        "feedback_trigger": naed2.get("feedback_trigger"),
                    },
                    "Rationale": naed2.get("rationale"),
                    "Logical_Rationale": naed2.get("logical_rationale"),
                    "Observation": naed2.get("observation") or None,
                    "Decision": naed2_decision,
                }

            # --- NAED-3 ---
            naed3_obj = None
            if naed2_decision in ("UPGRADE", "HP_UPGRADE", "DOWNGRADE", "LATERAL"):
                try:
                    naed3 = compute_naed3_recommendation(
                        exerc_abb, naed2_decision, subject=subject, curriculum=_retro_curriculum
                    )
                    naed3_obj = {
                        "status": naed3.get("status"),
                        "message": naed3.get("message"),
                        "curriculum": naed3.get("curriculum"),
                        "connection_used": naed3.get("connection_used"),
                        "candidates": naed3.get("candidates"),
                        "requires_choice": naed3.get("requires_choice", False),
                        "next_exercise_abb": naed3.get("next_exercise_abb"),
                        "next_exercise_full": naed3.get("next_exercise_full"),
                        "training_complete": naed3.get("training_complete", False),
                    }
                except Exception:
                    naed3_obj = {
                        "status": "ERROR",
                        "message": "NAED-3 computation failed",
                        "connection_used": None,
                        "next_exercise_abb": None,
                        "next_exercise_full": None,
                    }

            # --- Reality Check ---
            if line_idx < total_lines - 1:
                next_row = rows[line_idx + 1]
                next_exerc_abb = next_row.get("exerc_abb", "")

                reality_connection = _reverse_lookup_connection(exerc_abb, next_exerc_abb)

                # Determine reality_naed_match
                if naed1_decision != "ACT":
                    # Pipeline didn't produce any recommendation
                    reality_match = None
                elif naed2_decision == "KEEP":
                    # NAED-2 said KEEP; match if reality is also KEEP
                    reality_match = (next_exerc_abb == exerc_abb)
                elif naed3_obj is not None:
                    # NAED-3 was reached — compare recommended next vs actual
                    naed3_next = naed3_obj.get("next_exercise_abb") or ""
                    if naed3_next:
                        reality_match = (next_exerc_abb == naed3_next)
                    else:
                        # NAED-3 had no concrete suggestion (NO_OPTION etc.)
                        reality_match = None
                else:
                    reality_match = None

                reality_obj: dict[str, Any] = {
                    "next_exercise_abbreviation": next_exerc_abb,
                    "reality_connection_used": reality_connection,
                    "reality_naed_match": reality_match,
                }
            else:
                reality_obj = {
                    "next_exercise_abbreviation": None,
                    "reality_connection_used": None,
                    "reality_naed_match": None,
                }

            entry = {
                "analysis_type": "retrospective",
                "source": "retro",
                "subject": subject,
                "total_attempt_number": line_idx + 1,
                "exercise_fullname": exerc_full,
                "exercise_abbreviation": exerc_abb,
                "exercise_attempt_number": ex_attempt_num,
                "NAED-1": naed1_obj,
                "NAED-2": naed2_obj,
                "NAED-3": naed3_obj,
                "Reality_Check": reality_obj,
            }
            results.append(entry)

        # Write JSON
        with open(out_path, "w", encoding="utf-8") as f:
            _json.dump(results, f, indent=2, default=str, ensure_ascii=False)

        QMessageBox.information(
            self, "Retro History",
            f"Retro History saved ({total_lines} attempts):\n{out_path}",
        )


def _render_naed_history_entry_html(entry: dict[str, Any]) -> str:
    """Render one History JSON entry (NAED-1/2/3 + Reality_Check) as an HTML
    block, mirroring the tables shown in RecommendationsWindow._build_html.
    """
    def _esc(x: Any) -> str:
        s = "" if x is None else str(x)
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _fmt_decision_naed1(dec: str) -> str:
        d = (dec or "").strip().upper()
        if d == "WAIT":
            return f"<span style='color:red;'><b>{_esc(dec)}</b></span>"
        if d == "ACT":
            return f"<span style='color:green;'><b>{_esc(dec)}</b></span>"
        return f"<b>{_esc(dec)}</b>" if dec else ""

    def _fmt_decision_naed2(dec: str) -> str:
        d = (dec or "").strip().upper()
        if d in ("LATERAL", "NEIGHBOR", "LATERAL_MOVE", "LATERAL_MOVE / NEIGHBOR"):
            return f"<span style='color:orange;'><b>{_esc(dec)}</b></span>"
        if d == "DOWNGRADE":
            return f"<span style='color:red;'><b>{_esc(dec)}</b></span>"
        if d in ("HP_UPGRADE", "UPGRADE_HPP"):
            return f"<span style='color:blue;'><b>{_esc(dec)}</b></span>"
        if d in ("UPGRADE", "UPGRADE_NP"):
            return f"<span style='color:green;'><b>{_esc(dec)}</b></span>"
        return f"<b>{_esc(dec)}</b>" if dec else ""

    def _render_table(title: str, rows: list[tuple[str, str]]) -> str:
        out = [f"<h4>{_esc(title)}</h4>", "<table border='1' cellpadding='5' cellspacing='0' width='100%'>"]
        out.append("<tr><th align='left' width='34%'>Field</th><th align='left'>Value</th></tr>")
        for k, v_html in rows:
            out.append(f"<tr><td><b>{_esc(k)}</b></td><td>{v_html}</td></tr>")
        out.append("</table>")
        return "".join(out)

    parts: list[str] = []

    naed1 = entry.get("NAED-1") or {}
    if naed1:
        rows1 = [
            ("window_n", _esc(naed1.get("window_n"))),
            ("total_n", _esc(naed1.get("total_n"))),
            ("reason", _esc(naed1.get("reason"))),
            ("confidence", _esc(naed1.get("confidence"))),
            ("decision", _fmt_decision_naed1(str(naed1.get("decision") or ""))),
        ]
        parts.append(_render_table("NAED-1", rows1))
    else:
        parts.append("<h4>NAED-1</h4><p><i>No data.</i></p>")

    parts.append("<br>")

    naed2 = entry.get("NAED-2") or {}
    if naed2:
        fb = naed2.get("Feedback_detection") or {}
        fb_keys = [
            "mastery_bottleneck", "bottleneck_Rk", "mean_other_Rk", "mean_pass_total",
            "worst_metric", "worst_metric_pass_frac", "avg_other_metric_pass_frac",
            "feedback_trigger",
        ]
        fb_items = [
            f"<li><b>{_esc(k)}</b>: {_esc(fb.get(k))}</li>"
            for k in fb_keys if fb.get(k) not in (None, "")
        ]
        fb_html = "<ul>" + "".join(fb_items) + "</ul>" if fb_items else "<i>No feedback detection details.</i>"

        order = [
            "exercise_attempts", "Rm_last", "slope_m", "mastery_bottleneck",
            "bottleneck_Rk", "mean_other_Rk", "level_now", "level_now_norm",
            "pass_rate_all", "pass_rate_weighted", "consec_pass_all",
            "trailing_streak", "directionality_plain", "directionality_weighted",
            "volatility_weighted", "spread", "stability", "outlier_downweighting",
        ]
        rows2: list[tuple[str, str]] = []
        for k in order:
            v = naed2.get(k)
            if v is None:
                continue
            rows2.append((k, _esc(v)))

        rows2.append(("Feedback detection", fb_html))

        rationale = naed2.get("Rationale")
        logical_rationale = naed2.get("Logical_Rationale")
        observation = naed2.get("Observation")
        decision2 = naed2.get("Decision")

        if rationale is not None:
            rows2.append(("Rationale", _esc(rationale)))
        if logical_rationale is not None:
            rows2.append(("Logical Rationale", _esc(logical_rationale)))
        if observation:
            rows2.append(("Observation", f"<span style='color:#B00000;'>{_esc(observation)}</span>"))
        if decision2 is not None:
            rows2.append(("Decision", _fmt_decision_naed2(str(decision2))))

        parts.append(_render_table("NAED-2", rows2))
    else:
        parts.append("<h4>NAED-2</h4><p><i>No data.</i></p>")

    parts.append("<br>")

    naed3 = entry.get("NAED-3") or {}
    if naed3:
        rows3: list[tuple[str, str]] = [
            ("status", _esc(naed3.get("status"))),
            ("message", _esc(naed3.get("message"))),
        ]
        cur_lbl = naed3.get("curriculum")
        if cur_lbl:
            rows3.append(("curriculum", _esc(cur_lbl)))
        rows3.append(("connection_used", _esc(naed3.get("connection_used"))))

        candidates = naed3.get("candidates") or []
        if isinstance(candidates, list) and len(candidates) > 1:
            cand_html = "<br>".join(
                _esc(f"{(c.get('full') or '').strip()} ({(c.get('abb') or '').strip()})")
                if isinstance(c, dict) else _esc(str(c))
                for c in candidates
            )
            rows3.append(("candidate next exercises", f"<b>{cand_html}</b>"))
            chosen = naed3.get("chosen_next_abb")
            if chosen:
                rows3.append(("chosen next exercise", f"<b>{_esc(chosen)}</b>"))
        else:
            rows3.append(("next_exercise_abb", _esc(naed3.get("next_exercise_abb"))))
            nxt_full = naed3.get("next_exercise_full")
            if nxt_full:
                rows3.append(("next_exercise_full", f"<b>{_esc(nxt_full)}</b>"))

        if naed3.get("training_complete"):
            rows3.append(("training_complete", "<b style='color:#2ca02c;'>TRUE</b>"))

        parts.append(_render_table("NAED-3", rows3))
    else:
        parts.append("<h4>NAED-3</h4><p><i>No data.</i></p>")

    rc = entry.get("Reality_Check") or {}
    if rc:
        parts.append("<br>")
        match_val = rc.get("reality_naed_match")
        if match_val is True:
            match_html = "<span style='color:green;'><b>MATCH</b></span>"
        elif match_val is False:
            match_html = "<span style='color:red;'><b>NO MATCH</b></span>"
        else:
            match_html = "<i>N/A</i>"
        rows_rc = [
            ("next_exercise_abbreviation", _esc(rc.get("next_exercise_abbreviation"))),
            ("reality_connection_used", _esc(rc.get("reality_connection_used"))),
            ("reality_naed_match", match_html),
        ]
        parts.append(_render_table("Reality Check", rows_rc))

    return "".join(parts)


class RetroSummaryWindow(QMainWindow):
    """Summary window for a Retrospective History JSON file.

    Shows top-level stats, then the full NAED-1/2/3 (+ Reality Check) decision
    log — one collapsible section per recorded attempt — mirroring everything
    shown in the live RecommendationsWindow.
    """

    def __init__(self, json_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        import json as _json

        self.setWindowTitle(f"Retrospective Summary – {os.path.basename(json_path)}")
        self.resize(900, 760)

        with open(json_path, "r", encoding="utf-8-sig") as f:
            data: list[dict[str, Any]] = _json.load(f)

        # --- Compute summary stats ---
        n_attempts = len(data)
        exercises_seen: set[str] = set()
        n_past_naed1 = 0
        n_matched = 0
        n_unmatched = 0

        for entry in data:
            exercises_seen.add(entry.get("exercise_abbreviation", ""))

            naed1 = entry.get("NAED-1") or {}
            if naed1.get("decision") == "ACT":
                n_past_naed1 += 1

            rc = entry.get("Reality_Check") or {}
            match_val = rc.get("reality_naed_match")
            if match_val is True:
                n_matched += 1
            elif match_val is False:
                n_unmatched += 1

        n_exercises = len(exercises_seen - {""})
        n_evaluated = n_matched + n_unmatched

        # --- Build UI ---
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        subject = data[0].get("subject", "Unknown") if data else "Unknown"
        heading = QLabel(f"<b>Subject:</b> {subject}")
        heading.setTextFormat(Qt.RichText)
        layout.addWidget(heading)

        table = QTableWidget(5, 2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

        rows_data = [
            ("Number of attempts", str(n_attempts)),
            ("Number of exercises", str(n_exercises)),
            ("Analyses past NAED-1 (ACT)", str(n_past_naed1)),
            ("NAED / Reality matched", f"{n_matched}  ({n_matched}/{n_evaluated})" if n_evaluated else "0"),
            ("NAED / Reality unmatched", f"{n_unmatched}  ({n_unmatched}/{n_evaluated})" if n_evaluated else "0"),
        ]

        for i, (label, value) in enumerate(rows_data):
            item_k = QTableWidgetItem(label)
            item_v = QTableWidgetItem(value)
            fnt = item_k.font()
            fnt.setBold(True)
            item_k.setFont(fnt)
            table.setItem(i, 0, item_k)
            table.setItem(i, 1, item_v)

        table.resizeColumnsToContents()
        layout.addWidget(table)

        # --- Full decision log (NAED-1/2/3 + Reality Check per attempt) ---
        sep = QLabel("<hr>")
        sep.setTextFormat(Qt.RichText)
        layout.addWidget(sep)

        plural = "s" if n_attempts != 1 else ""
        lbl_log_header = QLabel(f"<b>Decision Log</b>  ({n_attempts} recorded attempt{plural})")
        lbl_log_header.setTextFormat(Qt.RichText)
        layout.addWidget(lbl_log_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)

        for entry in data:
            total_n = entry.get("total_attempt_number", "")
            ex_full = entry.get("exercise_fullname") or entry.get("exercise_abbreviation", "")
            ex_n = entry.get("exercise_attempt_number", "")
            source = (entry.get("source") or entry.get("analysis_type") or "").strip()

            naed1 = entry.get("NAED-1") or {}
            naed1_dec = (naed1.get("decision") or "").strip()
            naed2 = entry.get("NAED-2") or {}
            naed2_dec = (naed2.get("Decision") or "").strip()

            dec_summary = naed2_dec if naed2_dec else (naed1_dec or "\u2014")
            source_tag = f"[{source}]  " if source else ""
            header_text = (
                f"#{total_n}  {source_tag}\u2014  {ex_full} (exercise attempt {ex_n})  \u2014  {dec_summary}"
            )

            body_label = QLabel()
            body_label.setTextFormat(Qt.RichText)
            body_label.setWordWrap(True)
            body_label.setText(_render_naed_history_entry_html(entry))

            section = _CollapsibleSection(
                header_text, body_label, expanded=False,
                color="#555555", hover_color="#666666",
            )
            scroll_layout.addWidget(section)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)


# =============================================================================
#  [SEC-15] AUXILIARY WINDOWS (Decision Details, Time Analysis, Progress Graph)
# =============================================================================

class DecisionDetailsWindow(QMainWindow):
    def __init__(self, title: str, bundle_lines: list[str]):
        super().__init__()
        self.setWindowTitle(title)
        self.resize(860, 680)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Simple HTML rendering inside a scroll area
        self.viewer = QLabel()
        self.viewer.setTextFormat(Qt.RichText)
        self.viewer.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.viewer.setWordWrap(True)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.viewer)
        layout.addWidget(scroll)

        html_parts: list[str] = []
        html_parts.append("<h2 style='text-align:center;'>Decision Details</h2>")
        html_parts.append("<hr>")

        def esc(x: Any) -> str:
            if x is None:
                return ""
            s = str(x)
            s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return s

        def render_kv_table(title: str, kv: list[tuple[str, str]]) -> str:
            if not kv:
                return f"<h3>{esc(title)}</h3><p><i>No data.</i></p>"
            rows = []
            rows.append("<table style='width:100%; border-collapse:collapse;'>")
            rows.append(f"<tr><th colspan='2' style='text-align:left; padding:6px; background:#f0f0f0;'>{esc(title)}</th></tr>")
            for k, v in kv:
                rows.append(
                    "<tr>"
                    f"<td style='width:34%; border-top:1px solid #ddd; padding:6px;'><b>{esc(k)}</b></td>"
                    f"<td style='border-top:1px solid #ddd; padding:6px;'>{esc(v)}</td>"
                    "</tr>"
                )
            rows.append("</table>")
            return "".join(rows)

        # Parse bundle lines into sections by type token at index 4
        sections: dict[str, list[tuple[str, str]]] = {}
        for ln in bundle_lines:
            if not ln.startswith("History,"):
                continue
            toks = [t.strip() for t in ln.split(",")]
            if len(toks) < 6:
                continue
            typ = toks[4]
            kv = []
            rest = toks[5:]
            # rest is key,value pairs; if odd, last value is blank
            for i in range(0, len(rest), 2):
                k = rest[i]
                v = rest[i+1] if i+1 < len(rest) else ""
                if k == "":
                    continue
                kv.append((k, v))
            sections.setdefault(typ, []).extend(kv)

        # Render in desired order if present
        for typ in ["NAED-1", "NAED-2", "NAED-3", "user_decision"]:
            if typ in sections:
                html_parts.append(render_kv_table(typ, sections.get(typ, [])))
                html_parts.append("<br>")

        # Any other types
        for typ in sorted(k for k in sections.keys() if k not in {"NAED-1","NAED-2","NAED-3","user_decision"}):
            html_parts.append(render_kv_table(typ, sections.get(typ, [])))
            html_parts.append("<br>")

        self.viewer.setText("".join(html_parts))



class TimeAnalysisDialog(QDialog):
    def __init__(self, exercise_time_seconds: dict[str, float], green_exercises: set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Time Analysis")
        self.resize(720, 520)

        central = QWidget()
        layout = QVBoxLayout(self)
        layout.addWidget(central)
        v = QVBoxLayout(central)

        # Table
        # Columns: exerc_number | Exercise | Proficiency | Time Spent
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["exerc_number", "Exercise", "Proficiency", "Time Spent"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        v.addWidget(self.table)

        # Total time
        self.lbl_total = QLabel("")
        self.lbl_total.setTextFormat(Qt.RichText)
        v.addWidget(self.lbl_total)

        # Total exercises passed
        self.lbl_total_passed = QLabel("")
        self.lbl_total_passed.setTextFormat(Qt.RichText)
        v.addWidget(self.lbl_total_passed)

        # Close
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

        self._populate(exercise_time_seconds, green_exercises)

    @staticmethod
    def _hhmmss_from_seconds(seconds: float | int) -> str:
        try:
            total = int(round(float(seconds)))
        except Exception:
            total = 0
        if total < 0:
            total = 0
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _populate(self, exercise_time_seconds: dict[str, float], green_exercises: set[str]):
        # Only exercises present in the History Show computation (keys of exercise_time_seconds).
        exercises = [e for e in exercise_time_seconds.keys() if str(e).strip() != ""]

        def _norm(s: str) -> str:
            return re.sub(r"\s+", " ", str(s or "").strip()).lower()

        def _lookup_def(ex: str) -> dict[str, Any] | None:
            # Primary: direct key match (e.g., 'pb1', 'pp1', etc.).
            if ex in EXERCISE_DEFS:
                return EXERCISE_DEFS.get(ex)

            # Fallback: match against exerc_full (History may store full exercise names).
            exn = _norm(ex)
            if not exn:
                return None
            for _abbr, d in EXERCISE_DEFS.items():
                try:
                    full = d.get("exerc_full")
                except Exception:
                    full = None
                if full and _norm(full) == exn:
                    return d
            return None

        def _exerc_number(ex: str) -> int:
            try:
                d = _lookup_def(ex)
                v = (d or {}).get("exerc_number")
                return int(v) if isinstance(v, (int, float)) else 999999
            except Exception:
                return 999999

        # Sort by exerc_number ascending; unknown numbers go to the end.
        exercises_sorted = sorted(exercises, key=lambda ex: (_exerc_number(str(ex)), _norm(str(ex))))


        self.table.setRowCount(len(exercises_sorted))

        green_fg = QBrush(QColor("#1f7a1f"))  # readable green text

        total_seconds = 0.0
        for r, ex in enumerate(exercises_sorted):
            ex = str(ex)
            secs = float(exercise_time_seconds.get(ex, 0.0) or 0.0)
            total_seconds += secs

            num = _exerc_number(ex)

            prof_yes = (ex in green_exercises)
            prof = "Yes" if prof_yes else "No"

            it_num = QTableWidgetItem("" if num == 999999 else str(num))
            it_ex = QTableWidgetItem(ex)
            it_prof = QTableWidgetItem(prof)
            it_time = QTableWidgetItem(self._hhmmss_from_seconds(secs))

            # Alignments
            it_num.setTextAlignment(Qt.AlignCenter)
            it_prof.setTextAlignment(Qt.AlignCenter)
            it_time.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # Green font for proficient exercises (entire row)
            if prof_yes:
                for _it in (it_num, it_ex, it_prof, it_time):
                    _it.setForeground(green_fg)

            self.table.setItem(r, 0, it_num)
            self.table.setItem(r, 1, it_ex)
            self.table.setItem(r, 2, it_prof)
            self.table.setItem(r, 3, it_time)

        self.table.resizeColumnsToContents()
        self.lbl_total.setText(f"<b>Total time:</b> {self._hhmmss_from_seconds(total_seconds)}")

        # Summary counts
        total_passed = sum(1 for ex in exercises_sorted if str(ex) in green_exercises)
        self.lbl_total_passed.setText(f"<b>Total exercises passed:</b> {total_passed}")


class ProgressGraphWindow(QMainWindow):
    """Displays the curriculum progress graph for a single subject."""

    COLS = 5          # boxes per row before zigzag turn
    BOX_W = 1.8       # box width in data units
    BOX_H = 0.7       # box height in data units
    H_GAP = 0.6       # horizontal gap between boxes
    V_GAP = 0.9       # vertical gap between rows

    # Clock emojis for 1–11 hours
    HOUR_CLOCKS = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]

    def __init__(self, title: str, exercise_sequence: list[str],
                 green_exercises: set[str], *,
                 cumulative_times: list[float] | None = None,
                 subject: str = "", parent=None):
        super().__init__(parent)

        if Figure is None or FigureCanvas is None:
            raise RuntimeError("Matplotlib is not available.")

        self.setWindowTitle(title)
        self.resize(1300, 700)

        # v7.0: connection types are resolved against the subject's curriculum
        self._connections = CURRICULA.get(
            get_curriculum_for_subject(subject), {}
        ).get("connections", {})

        # Build chronological step list: one box per transition
        # Collapse consecutive repeats of the same exercise into one box.
        # Track the cumulative time at the end of each collapsed step.
        steps: list[str] = []
        step_cumtimes: list[float] = []
        for i, ex in enumerate(exercise_sequence):
            if ex and ex in EXERCISE_DEFS:
                ct = cumulative_times[i] if cumulative_times and i < len(cumulative_times) else 0.0
                if not steps or steps[-1] != ex:
                    steps.append(ex)
                    step_cumtimes.append(ct)
                else:
                    step_cumtimes[-1] = ct  # update to latest time for this step

        # Determine which steps cross hour milestones
        # step_hour_marks[step_idx] = list of hour numbers crossed at that step
        step_hour_marks: dict[int, list[int]] = {}
        next_hour = 1
        for idx, ct in enumerate(step_cumtimes):
            while next_hour <= 11 and ct >= next_hour * 3600:
                step_hour_marks.setdefault(idx, []).append(next_hour)
                next_hour += 1

        # Build UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        n_boxes = max(len(steps), 1)
        n_rows = math.ceil(n_boxes / self.COLS)
        fig_w = self.COLS * (self.BOX_W + self.H_GAP) + 0.5
        fig_h = max(3.0, n_rows * (self.BOX_H + self.V_GAP) + 1.0)
        self._fig = Figure(figsize=(fig_w, fig_h), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)

        ax = self._fig.add_subplot(111)
        self._frame_groups = self._render(ax, steps, green_exercises, step_hour_marks)
        self._fig.tight_layout()

        if self._frame_groups:
            from matplotlib.animation import FuncAnimation
            self._anim = FuncAnimation(
                self._fig, self._animate_frame,
                frames=len(self._frame_groups),
                interval=150, repeat=False, blit=False,
            )
        self._canvas.draw()

    def _animate_frame(self, frame_idx):
        """Reveal the artists belonging to *frame_idx*."""
        for artist in self._frame_groups[frame_idx]:
            artist.set_visible(True)

    def _render(self, ax, steps, green_exercises, step_hour_marks):
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
        from matplotlib.lines import Line2D

        ax.axis('off')

        if not steps:
            ax.text(0.5, 0.5, "No exercises recorded.",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14)
            return []

        frame_groups: list[list] = []

        # Compute zigzag positions for each step
        positions: list[tuple[float, float]] = []
        for idx in range(len(steps)):
            row = idx // self.COLS
            col = idx % self.COLS
            if row % 2 == 1:
                col = self.COLS - 1 - col
            x = col * (self.BOX_W + self.H_GAP)
            y = -row * (self.BOX_H + self.V_GAP)
            positions.append((x, y))

        # Draw boxes (initially invisible for wipe-in animation)
        box_groups: list[list] = []
        for idx, ex in enumerate(steps):
            artists: list = []
            x, y = positions[idx]
            cat = EXERCISE_DEFS.get(ex, {}).get("exerc_cat", "")
            facecolor = EXERCISE_CAT_COLORS.get(cat, "#e0e0e0")

            is_green = ex in green_exercises
            edgecolor = '#2ca02c' if is_green else '#333333'
            linewidth = 3.0 if is_green else 1.2

            box = FancyBboxPatch(
                (x, y), self.BOX_W, self.BOX_H,
                boxstyle="round,pad=0.05",
                facecolor=facecolor, edgecolor=edgecolor,
                linewidth=linewidth,
                zorder=2, visible=False,
            )
            ax.add_patch(box)
            artists.append(box)

            cx = x + self.BOX_W / 2
            cy = y + self.BOX_H / 2
            full_name = EXERCISE_DEFS.get(ex, {}).get("exerc_full", ex)
            if len(full_name) > 15 and ' ' in full_name:
                # Break at last space that keeps first line <= 15 chars
                best = full_name.rfind(' ', 0, 16)
                if best == -1:
                    best = full_name.index(' ')
                full_name = full_name[:best] + '\n' + full_name[best + 1:]
            txt = ax.text(cx, cy, full_name, ha='center', va='center',
                          fontsize=9, fontweight='bold', zorder=3, visible=False)
            artists.append(txt)

            # Draw hour milestone clock emoji below the box
            if idx in step_hour_marks:
                hours = step_hour_marks[idx]
                for h in hours:
                    clock = self.HOUR_CLOCKS[h - 1] if h <= len(self.HOUR_CLOCKS) else "⏰"
                    label = f"{clock} {h} hour{'s' if h > 1 else ''}"
                    ht = ax.text(cx, y - 0.15, label,
                                 ha='center', va='top', fontsize=8,
                                 fontfamily='Segoe UI Emoji', zorder=6,
                                 visible=False)
                    artists.append(ht)

            box_groups.append(artists)

        # Draw arrows between consecutive steps (initially invisible)
        arrow_groups: list[list] = []
        used_conn_types: set[str] = set()
        for i in range(len(steps) - 1):
            from_ex = steps[i]
            to_ex = steps[i + 1]

            # Compute arrow endpoints at box borders
            fx, fy = positions[i]
            tx, ty = positions[i + 1]
            fc_x = fx + self.BOX_W / 2
            fc_y = fy + self.BOX_H / 2
            tc_x = tx + self.BOX_W / 2
            tc_y = ty + self.BOX_H / 2
            dx = tc_x - fc_x
            dy = tc_y - fc_y
            # From-box: exit point on border (+ margin to clear rounded pad)
            margin = 0.03
            half_w = self.BOX_W / 2 + margin
            half_h = self.BOX_H / 2 + margin
            if abs(dx) > abs(dy):
                x1 = fc_x + (half_w if dx > 0 else -half_w)
                y1 = fc_y
            else:
                x1 = fc_x
                y1 = fc_y + (half_h if dy > 0 else -half_h)
            # To-box: entry point on border
            if abs(dx) > abs(dy):
                x2 = tc_x - (half_w if dx > 0 else -half_w)
                y2 = tc_y
            else:
                x2 = tc_x
                y2 = tc_y - (half_h if dy > 0 else -half_h)

            # Determine connection type (v7.0: multi-destination lists per type)
            conn_type = ""
            conn = self._connections.get(from_ex, {})
            for ct, targets in conn.items():
                if to_ex in (targets if isinstance(targets, (list, tuple)) else [targets]):
                    conn_type = ct
                    break
            color = CONNECTION_TYPE_COLORS.get(conn_type, "#888888")
            if conn_type:
                used_conn_types.add(conn_type)

            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle='->', mutation_scale=14,
                color=color, linewidth=1.8,
                connectionstyle="arc3,rad=0.0",
                shrinkA=2, shrinkB=2,
                zorder=5, visible=False,
            )
            ax.add_patch(arrow)
            arrow_groups.append([arrow])

        # Set axis limits
        all_x = [p[0] for p in positions]
        all_y = [p[1] for p in positions]
        ax.set_xlim(min(all_x) - 0.5, max(all_x) + self.BOX_W + 0.5)
        ax.set_ylim(min(all_y) - 0.5, max(all_y) + self.BOX_H + 1.5)
        ax.set_aspect('equal')

        # Legend (visible from the start)
        legend_handles = []
        for ct in CONNECTION_TYPES:
            if ct in used_conn_types:
                c = CONNECTION_TYPE_COLORS.get(ct, "#888888")
                label = CONNECTION_TYPE_LABELS.get(ct, ct)
                legend_handles.append(
                    Line2D([0], [0], color=c, linewidth=2, label=label))
        for cat_key, cat_label in EXERCISE_CAT_LABELS.items():
            c = EXERCISE_CAT_COLORS.get(cat_key, "#e0e0e0")
            legend_handles.append(
                Line2D([0], [0], marker='s', color='w', markerfacecolor=c,
                       markersize=10, label=cat_label))
        if legend_handles:
            ax.legend(handles=legend_handles, loc='upper right',
                      fontsize=8, ncol=2, framealpha=0.9)

        # Build animation frames: frame 0 = first box, frame N = arrow N-1 + box N
        frame_groups.append(box_groups[0])
        for i in range(1, len(steps)):
            frame: list = []
            if i - 1 < len(arrow_groups):
                frame.extend(arrow_groups[i - 1])
            frame.extend(box_groups[i])
            frame_groups.append(frame)

        return frame_groups


class DSProgressGraphWindow(QMainWindow):
    """Simplified Progress Graph for DataShow — black arrows, no arrow legend, smaller boxes."""

    COLS = 5
    BOX_W = 1.4
    BOX_H = 0.55
    H_GAP = 0.5
    V_GAP = 0.75

    HOUR_CLOCKS = ["🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]

    def __init__(self, title: str, exercise_sequence: list[str],
                 green_exercises: set[str], *,
                 cumulative_times: list[float] | None = None, parent=None):
        super().__init__(parent)

        if Figure is None or FigureCanvas is None:
            raise RuntimeError("Matplotlib is not available.")

        self.setWindowTitle(title)
        self.resize(1200, 650)

        # Collapse consecutive repeats
        steps: list[str] = []
        step_cumtimes: list[float] = []
        for i, ex in enumerate(exercise_sequence):
            if ex and ex in EXERCISE_DEFS:
                ct = cumulative_times[i] if cumulative_times and i < len(cumulative_times) else 0.0
                if not steps or steps[-1] != ex:
                    steps.append(ex)
                    step_cumtimes.append(ct)
                else:
                    step_cumtimes[-1] = ct

        # Hour milestones
        step_hour_marks: dict[int, list[int]] = {}
        next_hour = 1
        for idx, ct in enumerate(step_cumtimes):
            while next_hour <= 11 and ct >= next_hour * 3600:
                step_hour_marks.setdefault(idx, []).append(next_hour)
                next_hour += 1

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        n_boxes = max(len(steps), 1)
        n_rows = math.ceil(n_boxes / self.COLS)
        fig_w = self.COLS * (self.BOX_W + self.H_GAP) + 0.5
        fig_h = max(3.0, n_rows * (self.BOX_H + self.V_GAP) + 1.0)
        self._fig = Figure(figsize=(fig_w, fig_h), dpi=100)
        self._canvas = FigureCanvas(self._fig)
        layout.addWidget(self._canvas)

        ax = self._fig.add_subplot(111)
        self._frame_groups = self._render(ax, steps, green_exercises, step_hour_marks)
        self._fig.tight_layout()

        if self._frame_groups:
            from matplotlib.animation import FuncAnimation
            self._anim = FuncAnimation(
                self._fig, self._animate_frame,
                frames=len(self._frame_groups),
                interval=150, repeat=False, blit=False,
            )
        self._canvas.draw()

    def _animate_frame(self, frame_idx):
        for artist in self._frame_groups[frame_idx]:
            artist.set_visible(True)

    def _render(self, ax, steps, green_exercises, step_hour_marks):
        from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
        from matplotlib.lines import Line2D

        ax.axis('off')

        if not steps:
            ax.text(0.5, 0.5, "No exercises recorded.",
                    ha='center', va='center', transform=ax.transAxes,
                    fontsize=14)
            return []

        frame_groups: list[list] = []

        # Zigzag positions
        positions: list[tuple[float, float]] = []
        for idx in range(len(steps)):
            row = idx // self.COLS
            col = idx % self.COLS
            if row % 2 == 1:
                col = self.COLS - 1 - col
            x = col * (self.BOX_W + self.H_GAP)
            y = -row * (self.BOX_H + self.V_GAP)
            positions.append((x, y))

        # Draw boxes
        box_groups: list[list] = []
        for idx, ex in enumerate(steps):
            artists: list = []
            x, y = positions[idx]
            cat = EXERCISE_DEFS.get(ex, {}).get("exerc_cat", "")
            facecolor = EXERCISE_CAT_COLORS.get(cat, "#e0e0e0")

            is_green = ex in green_exercises
            edgecolor = '#2ca02c' if is_green else '#333333'
            linewidth = 3.0 if is_green else 1.2

            box = FancyBboxPatch(
                (x, y), self.BOX_W, self.BOX_H,
                boxstyle="round,pad=0.04",
                facecolor=facecolor, edgecolor=edgecolor,
                linewidth=linewidth,
                zorder=2, visible=False,
            )
            ax.add_patch(box)
            artists.append(box)

            cx = x + self.BOX_W / 2
            cy = y + self.BOX_H / 2
            full_name = EXERCISE_DEFS.get(ex, {}).get("exerc_full", ex)
            if len(full_name) > 15 and ' ' in full_name:
                best = full_name.rfind(' ', 0, 16)
                if best == -1:
                    best = full_name.index(' ')
                full_name = full_name[:best] + '\n' + full_name[best + 1:]
            txt = ax.text(cx, cy, full_name, ha='center', va='center',
                          fontsize=9, fontweight='bold', zorder=3, visible=False)
            artists.append(txt)

            if idx in step_hour_marks:
                hours = step_hour_marks[idx]
                for h in hours:
                    clock = self.HOUR_CLOCKS[h - 1] if h <= len(self.HOUR_CLOCKS) else "⏰"
                    label = f"{clock} {h} hour{'s' if h > 1 else ''}"
                    ht = ax.text(cx, y - 0.12, label,
                                 ha='center', va='top', fontsize=8,
                                 fontfamily='Segoe UI Emoji', zorder=6,
                                 visible=False)
                    artists.append(ht)

            box_groups.append(artists)

        # Draw arrows — all BLACK
        arrow_groups: list[list] = []
        for i in range(len(steps) - 1):
            fx, fy = positions[i]
            tx, ty = positions[i + 1]
            fc_x = fx + self.BOX_W / 2
            fc_y = fy + self.BOX_H / 2
            tc_x = tx + self.BOX_W / 2
            tc_y = ty + self.BOX_H / 2
            dx = tc_x - fc_x
            dy = tc_y - fc_y
            margin = 0.03
            half_w = self.BOX_W / 2 + margin
            half_h = self.BOX_H / 2 + margin
            if abs(dx) > abs(dy):
                x1 = fc_x + (half_w if dx > 0 else -half_w)
                y1 = fc_y
            else:
                x1 = fc_x
                y1 = fc_y + (half_h if dy > 0 else -half_h)
            if abs(dx) > abs(dy):
                x2 = tc_x - (half_w if dx > 0 else -half_w)
                y2 = tc_y
            else:
                x2 = tc_x
                y2 = tc_y - (half_h if dy > 0 else -half_h)

            arrow = FancyArrowPatch(
                (x1, y1), (x2, y2),
                arrowstyle='->', mutation_scale=14,
                color='#333333', linewidth=1.8,
                connectionstyle="arc3,rad=0.0",
                shrinkA=2, shrinkB=2,
                zorder=5, visible=False,
            )
            ax.add_patch(arrow)
            arrow_groups.append([arrow])

        # Axis limits
        all_x = [p[0] for p in positions]
        all_y = [p[1] for p in positions]
        ax.set_xlim(min(all_x) - 0.5, max(all_x) + self.BOX_W + 0.5)
        ax.set_ylim(min(all_y) - 0.5, max(all_y) + self.BOX_H + 1.5)
        ax.set_aspect('equal')

        # Legend — exercise category colors only (no arrow legend)
        legend_handles = []
        for cat_key, cat_label in EXERCISE_CAT_LABELS.items():
            c = EXERCISE_CAT_COLORS.get(cat_key, "#e0e0e0")
            legend_handles.append(
                Line2D([0], [0], marker='s', color='w', markerfacecolor=c,
                       markersize=10, label=cat_label))
        if legend_handles:
            ax.legend(handles=legend_handles, loc='upper right',
                      fontsize=8, ncol=1, framealpha=0.9)

        # Animation frames
        frame_groups.append(box_groups[0])
        for i in range(1, len(steps)):
            frame: list = []
            if i - 1 < len(arrow_groups):
                frame.extend(arrow_groups[i - 1])
            frame.extend(box_groups[i])
            frame_groups.append(frame)

        return frame_groups


class AdaptiveKGProgressGraphWindow(QMainWindow):
    """Progress Graph for Adaptive-arm subjects whose curriculum has a
    knowledge-graph SVG ("grad" and "resident_ext").

    Exercises the subject has completed appear one at a time (with a short
    pause between each, like the box-style Progress Graph's animation), and
    each newly-revealed exercise shows only the single arrow connecting it
    to the exercise immediately before it — not every arrow between visible
    nodes. A checkbox lets the user switch to viewing the complete knowledge
    graph (every exercise and every connection) at any time.
    """

    REVEAL_INTERVAL_MS = 500

    def __init__(self, title: str, exercise_sequence: list[str],
                 svg_path: str, *, green_exercises: set[str] | None = None,
                 cumulative_times: list[float] | None = None, parent=None):
        super().__init__(parent)

        if not _HAS_QTSVG or QSvgWidget is None:
            raise RuntimeError("PySide6.QtSvgWidgets is not available.")
        if CurriculumDiagram is None:
            raise RuntimeError("curriculum_svg module could not be imported.")

        self.setWindowTitle(title)
        self.resize(1300, 800)

        self.diagram = CurriculumDiagram(svg_path)
        valid_abbs = set(self.diagram.node_abbreviations())

        # Collapse consecutive repeats of the same exercise into one step,
        # same convention used by the box-style Progress Graph.
        self._steps: list[str] = []
        for ex in exercise_sequence:
            if ex and ex in valid_abbs:
                if not self._steps or self._steps[-1] != ex:
                    self._steps.append(ex)

        self._reveal_index = 0  # number of steps currently revealed

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        top_row = QHBoxLayout()
        self._chk_full_kg = QCheckBox("Show the complete Knowledge Graph")
        self._chk_full_kg.stateChanged.connect(self._on_toggle_full_kg)
        top_row.addWidget(self._chk_full_kg)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        self.svg_widget = QSvgWidget()
        self.svg_widget.setStyleSheet("background: white;")
        layout.addWidget(self.svg_widget)

        self._timer = QTimer(self)
        self._timer.setInterval(self.REVEAL_INTERVAL_MS)
        self._timer.timeout.connect(self._advance_reveal)

        if self._steps:
            self._reveal_index = 1
            self._render()
            if len(self._steps) > 1:
                self._timer.start()
        else:
            self._render()

    def _advance_reveal(self) -> None:
        self._reveal_index += 1
        if self._reveal_index >= len(self._steps):
            self._reveal_index = len(self._steps)
            self._timer.stop()
        self._render()

    def _on_toggle_full_kg(self, _state) -> None:
        self._render()

    def _render(self) -> None:
        if self._chk_full_kg.isChecked():
            all_nodes = set(self.diagram.node_abbreviations())
            svg_text = self.diagram.build_filtered_svg(all_nodes, edge_rule="both_visible")
        elif self._steps:
            svg_text = self.diagram.build_progress_svg(self._steps[: self._reveal_index])
        else:
            svg_text = self.diagram.build_progress_svg([])
        self.svg_widget.load(svg_text.encode("utf-8"))


class CollapsibleSection(QWidget):
    """A header button that shows/hides its content widget when clicked."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._is_expanded = True

        self._toggle = QPushButton(f"\u25bc {title}")
        self._toggle.setStyleSheet(
            "QPushButton { text-align: left; background: #008941; color: white; "
            "padding: 8px 12px; border: none; border-radius: 4px; font-weight: bold; font-size: 14px; }"
        )
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.clicked.connect(self._on_toggle)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 10, 0, 0)
        self.content_layout.setSpacing(10)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._toggle)
        outer.addWidget(self.content)

    def _on_toggle(self):
        self._is_expanded = not self._is_expanded
        self.content.setVisible(self._is_expanded)
        arrow = "\u25bc" if self._is_expanded else "\u25b6"
        self._toggle.setText(f"{arrow} {self._title}")


class DSTrainingAnalysisWindow(QMainWindow):
    """Training Analysis window for DataShow — Outcome Measures summary + per-exercise detail."""

    def __init__(self, title: str, om: dict[str, Any], prog: dict[str, Any], *, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        # Open at the exact screen position and size measured with AutoHotkey Spy.
        # Qt sets the client area; the OS adds the frame (title bar + borders).
        # To get a screen size of 873x824, the client area must be 857x785.
        self.setFixedSize(857, 785)
        self.move(448, 19)

        central = QWidget()
        self.setCentralWidget(central)
        v_main = QVBoxLayout(central)
        v_main.setContentsMargins(12, 12, 12, 12)
        v_main.setSpacing(6)

        # --- Summary section ---
        summary_group = QWidget()
        sg = QVBoxLayout(summary_group)
        sg.setContentsMargins(0, 0, 0, 0)
        sg.setSpacing(4)

        def _bold_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setTextFormat(Qt.RichText)
            return lbl

        self._summary_rows = self._build_summary_rows(om)
        avg_pm = om.get("avg_perf_margin")
        pm_color = "green" if avg_pm is not None and avg_pm > 0 else ("red" if avg_pm is not None else "gray")
        for label, value in self._summary_rows:
            if label == "Average Proficiency Margin":
                value = f"<span style='color:{pm_color};'>{value}</span>"
            if label.startswith("  "):
                sg.addWidget(_bold_label(f"&nbsp;&nbsp;&nbsp;&nbsp;{label.strip()}: {value}"))
            else:
                sg.addWidget(_bold_label(f"<b>{label}:</b> {value}"))

        summary_btn_row = QHBoxLayout()
        self.btn_export_summary = QPushButton("Export Summary (CSV)")
        self.btn_export_summary.clicked.connect(self._export_summary_to_csv)
        summary_btn_row.addStretch(1)
        summary_btn_row.addWidget(self.btn_export_summary)
        sg.addLayout(summary_btn_row)

        v_main.addWidget(summary_group)

        # --- Separator ---
        sep = QLabel("<hr>")
        sep.setTextFormat(Qt.RichText)
        v_main.addWidget(sep)

        # --- Collapsible per-exercise section ---
        self._detail_visible = True
        self.btn_toggle = QPushButton("Per-Exercise Details  [−]")
        self.btn_toggle.setStyleSheet(
            "QPushButton { background: #555; color: white; padding: 6px 14px; "
            "border: none; border-radius: 3px; text-align: left; }"
            "QPushButton:hover { background: #666; }"
        )
        self.btn_toggle.clicked.connect(self._toggle_details)

        self.btn_export = QPushButton("Export to Excel (CSV)")
        self.btn_export.clicked.connect(self._export_to_csv)

        header_row = QHBoxLayout()
        header_row.addWidget(self.btn_toggle, stretch=1)
        header_row.addWidget(self.btn_export)
        v_main.addLayout(header_row)

        self.detail_widget = QWidget()
        self.detail_widget.setVisible(True)
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 4, 0, 0)

        # Per-exercise table
        # Columns: # | Exercise | Completed Attempts | Total Attempts | Completed Non-PASS |
        #          Total Non-PASS | Proficiency | Prof. Margin | Time Spent
        col_headers = ["#", "Exercise", "Completed\nAttempts", "Total\nAttempts",
                        "Completed\nNon-PASS", "Total\nNon-PASS",
                        "Proficiency", "Prof.\nMargin", "Time\nSpent"]
        self.detail_table = QTableWidget(0, len(col_headers))
        self.detail_table.setHorizontalHeaderLabels(col_headers)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setSelectionMode(QTableWidget.SingleSelection)
        hdr = self.detail_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in range(2, len(col_headers)):
            hdr.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        detail_layout.addWidget(self.detail_table)
        v_main.addWidget(self.detail_widget, stretch=1)

        self._populate_detail_table(om, prog)

    @staticmethod
    def _hhmmss(seconds: float | int) -> str:
        try:
            total = int(round(float(seconds)))
        except Exception:
            total = 0
        if total < 0:
            total = 0
        h = total // 3600
        m = (total % 3600) // 60
        s = total % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def _build_summary_rows(self, om: dict[str, Any]) -> list[tuple[str, str]]:
        """Build the summary as an ordered list of (label, value) plain-text
        pairs, shared by the on-screen labels and the CSV export.

        Labels prefixed with two spaces are rendered as indented sub-items.
        """
        rows: list[tuple[str, str]] = []

        rows.append(("Total Number of Attempts (including incomplete)",
                     str(om.get("total_attempts_incl_incomplete", 0))))
        rows.append(("Number of PASS Attempts", str(om.get("total_passes", 0))))
        rows.append(("Total Time (including incomplete attempts)",
                     self._hhmmss(om.get("total_time_incl_incomplete", 0.0))))
        rows.append(("Total Time Spent on PASS Attempts",
                     self._hhmmss(om.get("total_time_pass", 0.0))))
        rows.append(("Total Time Spent on Non-PASS Attempts (including incomplete)",
                     self._hhmmss(om.get("total_time_fail_incl_incomplete", 0.0))))

        pct_pass = om.get("pct_time_pass")
        rows.append(("% of Time Spent on PASS Attempts",
                     f"{pct_pass:.2f}%" if pct_pass is not None else "N/A"))

        rows.append(("Total Exercise Proficiencies", str(om.get("exercises_passed", 0))))

        avg_pm = om.get("avg_perf_margin")
        rows.append(("Average Proficiency Margin",
                     f"{avg_pm:.2f}%" if avg_pm is not None else "N/A"))

        # Corridor Lanes, grouped into three bands
        agg = om.get("mastery_aggregation", {})
        agg_total = agg.get("total", 0)
        counts = agg.get("counts", {})
        bands = [
            ("Strong Mastery + Corridor-high", ["Strong mastery", "Corridor-high"]),
            ("Corridor-stable", ["Corridor-stable"]),
            ("Struggling + Excessively difficult", ["Struggling", "Excessively difficult"]),
        ]
        rows.append((f"Corridor Lanes (n={agg_total})", "" if agg_total else "N/A (not enough attempts)"))
        for band_label, labels in bands:
            cnt = sum(int(counts.get(l, 0)) for l in labels)
            pct = (cnt / agg_total * 100.0) if agg_total else None
            value = f"{cnt} ({pct:.1f}%)" if pct is not None else "N/A"
            rows.append((f"  {band_label}", value))

        return rows

    def _export_summary_to_csv(self):
        subject = self.windowTitle().replace("Training Analysis - ", "")
        safe_subject = re.sub(r"[^A-Za-z0-9_-]+", "_", subject) or "subject"
        default_name = f"TrainingSummary_{safe_subject}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Training Analysis Summary", default_name, "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["Subject", subject])
                writer.writerow([])
                writer.writerow(["Measure", "Value"])
                for label, value in self._summary_rows:
                    writer.writerow([label.strip(), value])
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export CSV:\n{e}")
            return
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")

    def _toggle_details(self):
        self._detail_visible = not self._detail_visible
        self.detail_widget.setVisible(self._detail_visible)
        sign = "−" if self._detail_visible else "+"
        self.btn_toggle.setText(f"Per-Exercise Details  [{sign}]")

    def _export_to_csv(self):
        subject = self.windowTitle().replace("Training Analysis - ", "")
        safe_subject = re.sub(r"[^A-Za-z0-9_-]+", "_", subject) or "subject"
        default_name = f"PerExerciseDetails_{safe_subject}.csv"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Per-Exercise Details", default_name, "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                headers = [
                    self.detail_table.horizontalHeaderItem(c).text().replace("\n", " ")
                    for c in range(self.detail_table.columnCount())
                ]
                writer.writerow(headers)
                for r in range(self.detail_table.rowCount()):
                    row = []
                    for c in range(self.detail_table.columnCount()):
                        item = self.detail_table.item(r, c)
                        row.append(item.text() if item else "")
                    writer.writerow(row)
        except Exception as e:
            QMessageBox.critical(self, "Export Failed", f"Could not export CSV:\n{e}")
            return
        QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")

    def _populate_detail_table(self, om: dict[str, Any], prog: dict[str, Any]):
        green = prog.get("green_exercises", set())
        exercise_time_secs = prog.get("exercise_time_secs", {})

        # Collect all exercises that appear in the data (from om computation)
        mastery_tables = om.get("mastery_tables", {})
        all_exercises = set(exercise_time_secs.keys()) | set(mastery_tables.keys())

        def _exerc_number(ex: str) -> int:
            d = EXERCISE_DEFS.get(ex, {})
            v = d.get("exerc_number")
            return int(v) if isinstance(v, (int, float)) else 999999

        exercises_sorted = sorted(all_exercises, key=lambda ex: (_exerc_number(ex), ex))
        self.detail_table.setRowCount(len(exercises_sorted))

        green_fg = QBrush(QColor("#1f7a1f"))

        # Pre-compute per-exercise stats from om's internal data
        # We need attempts count and non-pass count per exercise.
        # These are embedded in om_summary's computation; we can recompute
        # from mastery_tables + green_exercises + exercise_time_secs.
        # But it's cleaner to recompute from the original classified_rows.
        # Since we have om already, let's extract from prog data.

        # Actually we need to iterate the classified_rows again. The parent passed us om and prog.
        # om has total counts but not per-exercise. Let's recompute per-exercise from prog.
        # We'll build our own per-exercise stats from the parent's classified_rows via prog.
        # Since prog doesn't carry per-exercise attempt counts, we compute from mastery_tables
        # and performance_margin. But the simplest approach: recompute from the OM internals.

        # The OM summary doesn't expose per-exercise stats directly, but we have
        # green_exercises, exercise_time_secs, and mastery_tables.
        # We also need attempts and non-pass per exercise. Let's get the parent's classified_rows.

        parent = self.parent()
        classified_rows = getattr(parent, "classified_rows", []) if parent else []
        subject = self.windowTitle().replace("Training Analysis - ", "")
        subj_rows = [r for r in classified_rows if r.get("subject") == subject]

        clean_path = getattr(parent, "clean_path", "") if parent else ""
        folder = os.path.dirname(os.path.abspath(clean_path)) if clean_path else ""
        incomplete_stats = get_incomplete_stats_by_exercise(subject, folder) if folder else {}

        # Group by exercise abb
        by_exercise: dict[str, list[dict]] = {}
        for r in subj_rows:
            abb = r.get("exerc_abb", "")
            if abb:
                by_exercise.setdefault(abb, []).append(r)

        for row_idx, ex in enumerate(exercises_sorted):
            ex_rows = by_exercise.get(ex, [])
            num = _exerc_number(ex)

            inc = incomplete_stats.get(ex, {})
            inc_count = int(inc.get("count", 0))
            inc_time = float(inc.get("time", 0.0))

            # Attempts
            n_attempts = len(ex_rows)
            total_attempts = n_attempts + inc_count

            # Non-PASS count
            metrics = EXERCISE_METRICS.get(ex, [])
            s200_keys = [f"{m}_score_200" for m in metrics]
            non_pass = 0
            pass_flags: list[bool] = []
            for r in ex_rows:
                pt = compute_score200_pass_total(r, s200_keys) if s200_keys else 0
                passed = bool(s200_keys) and pt == len(s200_keys)
                pass_flags.append(passed)
                if not passed:
                    non_pass += 1
            total_non_pass = non_pass + inc_count

            # Proficiency
            prof_yes = ex in green
            prof_text = "Yes" if prof_yes else "No"

            # Proficiency Margin
            pm = compute_performance_margin(ex_rows, pass_flags)
            pm_text = f"{pm:.2f}%" if pm is not None else ""

            # Time (including incomplete attempts)
            secs = exercise_time_secs.get(ex, 0.0) + inc_time
            time_text = self._hhmmss(secs)

            it_num = QTableWidgetItem("" if num == 999999 else str(num))
            full_name = EXERCISE_DEFS.get(ex, {}).get("exerc_full", ex)
            it_ex = QTableWidgetItem(full_name)
            it_att = QTableWidgetItem(str(n_attempts))
            it_tot_att = QTableWidgetItem(str(total_attempts))
            it_np = QTableWidgetItem(str(non_pass))
            it_tot_np = QTableWidgetItem(str(total_non_pass))
            it_prof = QTableWidgetItem(prof_text)
            it_pm = QTableWidgetItem(pm_text)
            it_time = QTableWidgetItem(time_text)

            it_num.setTextAlignment(Qt.AlignCenter)
            it_att.setTextAlignment(Qt.AlignCenter)
            it_tot_att.setTextAlignment(Qt.AlignCenter)
            it_np.setTextAlignment(Qt.AlignCenter)
            it_tot_np.setTextAlignment(Qt.AlignCenter)
            it_prof.setTextAlignment(Qt.AlignCenter)
            it_pm.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            it_time.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

            if prof_yes:
                for _it in (it_num, it_ex, it_att, it_tot_att, it_np, it_tot_np,
                            it_prof, it_pm, it_time):
                    _it.setForeground(green_fg)

            self.detail_table.setItem(row_idx, 0, it_num)
            self.detail_table.setItem(row_idx, 1, it_ex)
            self.detail_table.setItem(row_idx, 2, it_att)
            self.detail_table.setItem(row_idx, 3, it_tot_att)
            self.detail_table.setItem(row_idx, 4, it_np)
            self.detail_table.setItem(row_idx, 5, it_tot_np)
            self.detail_table.setItem(row_idx, 6, it_prof)
            self.detail_table.setItem(row_idx, 7, it_pm)
            self.detail_table.setItem(row_idx, 8, it_time)

        self.detail_table.resizeColumnsToContents()


# =============================================================================
#  [SEC-16] GRAPH WINDOW
# =============================================================================

class GraphWindow(QMainWindow):
    def __init__(self, title: str, rows: list[dict[str, Any]], score200_keys: list[str] | None = None):
        super().__init__()

        if Figure is None or FigureCanvas is None or np is None:
            raise RuntimeError("Matplotlib is not available.")

        self.setWindowTitle(title)
        self.resize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        fig = Figure(figsize=(10, 6), tight_layout=True)
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        # Charts are generated dynamically based on available metrics for this selection.
        n = len(rows)
        x_vals = list(range(1, n + 1))

        # PASS rule (selection-dependent):
        # YES iff ALL valid *_score_200 >= 100 for this exercise selection.
        if score200_keys is None:
            score200_keys = [
                k for k in sorted({k for r in rows for k in r.keys() if k.endswith("_score_200")})
                if any((rr.get(k) not in (None, "")) for rr in rows)
            ]
        else:
            # Defensive: enforce exclusion and ignore empty-only metrics if caller passed a broader list.
            score200_keys = [
                k for k in score200_keys
                if any((rr.get(k) not in (None, "")) for rr in rows)
            ]
        def is_pass(rec: dict[str, Any]) -> bool:
            pt = rec.get("score_200_pass_total")
            if isinstance(pt, int):
                return pt == len(score200_keys)
            return compute_score200_pass_total(rec, score200_keys) == len(score200_keys)

        pass_flags = [is_pass(r) for r in rows]

        def get_y_list(key: str) -> list[float]:
            y = []
            for r in rows:
                v = r.get(key)
                if isinstance(v, (int, float)):
                    y.append(float(v))
                else:
                    try:
                        y.append(float(v))
                    except (TypeError, ValueError):
                        y.append(float("nan"))
            return y

        def color_for_value(v: float) -> str:
            if math.isnan(v):
                return "red"
            return "green" if v >= 100 else "red"

        def color_for_pass(p: bool) -> str:
            return "green" if p else "red"

        def plot_colored_line(ax, x: list[int], y: list[float], point_colors: list[str]):
            for i in range(len(x) - 1):
                y1, y2 = y[i], y[i + 1]
                if math.isnan(y1) or math.isnan(y2):
                    continue
                ax.plot([x[i], x[i + 1]], [y1, y2], color=point_colors[i], linewidth=1.5)

            xs, ys, cs = [], [], []
            for xi, yi, ci in zip(x, y, point_colors):
                if math.isnan(yi):
                    continue
                xs.append(xi)
                ys.append(yi)
                cs.append(ci)
            if xs:
                ax.scatter(xs, ys, c=cs, s=18)

        def plot_colored_bars(ax, x: list[int], y: list[float], bar_colors: list[str]):
            xs, ys, cs = [], [], []
            for xi, yi, ci in zip(x, y, bar_colors):
                if math.isnan(yi):
                    continue
                xs.append(xi)
                ys.append(yi)
                cs.append(ci)
            if xs:
                ax.bar(xs, ys, color=cs)

        plots = [
            ("overall_score", "line"),
        ]

        # Dynamic _score_200 plots: only include metrics that exist for this selection.
        
        candidate_score200_keys = [k for k, _ in SCORE_COLUMNS if k.endswith("_score_200")]
        available_score200_keys = [
            k for k in candidate_score200_keys
            if any((rr.get(k) not in (None, "")) for rr in rows)
        ]

        plot_kind_map = {
            "drp_score_200": "bar",
        }

        for k in available_score200_keys:
            if k == "overall_score":
                continue
            plots.append((k, plot_kind_map.get(k, "line")))

        # Build the subplot grid dynamically to match the number of plots.
        n_plots = len(plots)
        ncols = 2
        nrows = max(1, math.ceil(n_plots / ncols))
        axes = fig.subplots(nrows, ncols)
        try:
            axes = axes.flatten()
        except Exception:
            axes = [axes]

        # Hide any unused axes (e.g., odd number of plots in a 2-column grid).
        for ax in axes[n_plots:]:
            ax.set_visible(False)

        # Reference scale for the overall_score panel: this exercise's own ceiling,
        # not a flat 1200, which cut the top off exercises that reach higher.
        _abb = next(
            (str(r.get("exerc_abb") or "").strip() for r in rows
             if str(r.get("exerc_abb") or "").strip()),
            "",
        )
        overall_reference = overall_score_norm_divisor(_abb)

        def _y_top(values, reference: float) -> float:
            """Upper y limit: the reference scale, widened if the data exceeds it.

            Scores are not capped at their reference, so a fixed limit silently hid
            the best attempts instead of showing them.
            """
            top = float(reference)
            nums = [
                float(v) for v in values
                if isinstance(v, (int, float)) and not math.isnan(float(v))
            ]
            if nums and max(nums) > top:
                top = max(nums) * 1.05
            return top

        for ax, (key, kind) in zip(axes, plots):
            y = get_y_list(key)

            if key == "overall_score":
                point_colors = [color_for_pass(p) for p in pass_flags]
                plot_colored_line(ax, x_vals, y, point_colors)
                ax.set_ylim(0, _y_top(y, overall_reference))
            else:
                point_colors = [color_for_value(v) for v in y]
                if kind == "bar":
                    plot_colored_bars(ax, x_vals, y, point_colors)
                else:
                    plot_colored_line(ax, x_vals, y, point_colors)
                ax.set_ylim(0, _y_top(y, 200.0))

            ax.set_title(key)
            ax.set_xlim(1, max(1, n))
            ax.set_xlabel("Attempt")
            ax.set_ylabel("Score")
            ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.5)

        canvas.draw()


# =============================================================================
#  [SEC-17] OVERRIDE DECISION DIALOG (JSON-based)
# =============================================================================

# Closed list of connection types used in Reality_Check (v7.0 nomenclature)
_CONNECTION_TYPE_OPTIONS = [
    "KEEP",
    "upgrade",
    "hp_upgrade",
    "downgrade",
    "lateral",
]


class OverrideDecisionDialog(QDialog):
    """Dialog shown when the user clicks NO in the Recommendations window.

    The user picks:
      1) next_exercise_abbreviation (closed list from EXERCISE_DEFS)
      2) reality_connection_used (closed list of connection types)
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Override — Reality Check")
        self.resize(540, 200)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("What exercise will the subject do next?"))

        self.cmb_exercise = QComboBox()
        try:
            items = []
            for abb, info in (EXERCISE_DEFS or {}).items():
                full = str(info.get("exerc_full") or "").strip()
                if not full:
                    continue
                items.append((full, abb))
            items.sort(key=lambda t: t[0].lower())
            for full, abb in items:
                self.cmb_exercise.addItem(f"{full}  ({abb})", abb)
        except Exception:
            pass
        layout.addWidget(self.cmb_exercise)

        layout.addWidget(QLabel("Connection type used:"))

        self.cmb_connection = QComboBox()
        self.cmb_connection.addItems(_CONNECTION_TYPE_OPTIONS)
        layout.addWidget(self.cmb_connection)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_override(self) -> dict[str, Any]:
        """Returns a Reality_Check dict with reality_naed_match = False."""
        abb = self.cmb_exercise.currentData()
        abb = str(abb).strip() if abb is not None else ""
        conn = (self.cmb_connection.currentText() or "").strip()
        return {
            "next_exercise_abbreviation": abb,
            "reality_connection_used": conn,
            "reality_naed_match": False,
        }


# =============================================================================
#  [SEC-18] NO-OVERRIDE HANDLER (JSON-based)
# =============================================================================

def _on_accept_no_override(self):
    """Handle NO click: open override dialog and write live JSON entry."""
    try:
        dlg = OverrideDecisionDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        reality_check = dlg.get_override()

        out_path = _save_live_decision_json(self, reality_check)

        try:
            self.btn_accept_yes.setEnabled(False)
            self.btn_accept_no.setEnabled(False)
        except Exception:
            pass

        QMessageBox.information(self, "Override saved", f"Override recorded in:\n{out_path}")
        self.decision_made.emit()
        self.close()
    except Exception as e:
        QMessageBox.critical(self, "Override failed", str(e))


# =============================================================================
#  [SEC-19] RECOMMENDATIONS PATCH (bind NO handler)
# =============================================================================

# Bind the NO override handler to both RecommendationsWindow and NAED2DetailsWindow.
try:
    RecommendationsWindow._on_accept_no = _on_accept_no_override
except Exception:
    pass

try:
    NAED2DetailsWindow._on_accept_no = _on_accept_no_override
except Exception:
    pass

# =============================================================================
#  [SEC-20] ENTRY POINT
# =============================================================================


def main():

    app = QApplication(sys.argv)
    win_holder = show_splash_and_start_main(app)
    sys.exit(app.exec())



if __name__ == "__main__":
    main()


