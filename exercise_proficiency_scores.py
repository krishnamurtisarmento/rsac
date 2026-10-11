from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

# EXERCISE_DEFS — single source of truth lives in exercise_defs.py, now a sibling.
# Deliberately NOT imported from the main application module: that was a circular
# dependency and it broke silently when the app file was renamed.
_own_dir = str(Path(__file__).resolve().parent)
if _own_dir not in sys.path:
    sys.path.insert(0, _own_dir)
from exercise_defs import EXERCISE_DEFS  # noqa: E402

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
    "Incorrect Cuts": "icu",
    "Incorrect Cut Length": "icl",
    "Incorrect Suture Cuts": "isc",
    "Instrument Switches": "isw",
    "Points": "pts",
    "Master Workspace Range": "mwr",
}

# --- BEGIN PROFICIENCY_BASELINES (rewritten by Settings > Exercises > Proficiency Values) ---
PROFICIENCY_BASELINES: dict[str, dict[str, dict[str, float | int | str]]] = {
    "pp1": {
        "drp": {"mean": 0.15, "stddev": 0.46, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3926, "norm_max": 200},
        "mwr": {"mean": 8.87, "stddev": 1.17, "prof_raw": 10.04, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3928, "norm_max": 40},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3925, "norm_max": 200},
        "eom": {"mean": 127.01, "stddev": 22.11, "prof_raw": 149.12, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3924, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3929, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3927, "norm_max": 200},
        "ttc": {"mean": 45.00, "stddev": 22.58, "prof_raw": 67.58, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3923, "norm_max": 200}
    },
    "pb1": {
        "drp": {"mean": 0.45, "stddev": 0.8, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4223, "norm_max": 200},
        "mwr": {"mean": 10.02, "stddev": 2.76, "prof_raw": 12.78, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4225, "norm_max": 40},
        "ico": {"mean": 0.89, "stddev": 1.55, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4222, "norm_max": 200},
        "eom": {"mean": 186.88, "stddev": 81.83, "prof_raw": 268.71, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4221, "norm_max": 200},
        "exf": {"mean": 0.1, "stddev": 0.31, "prof_raw": 0.41, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4226, "norm_max": 200},
        "iov": {"mean": 0.56, "stddev": 2.00, "prof_raw": 2.56, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4224, "norm_max": 200},
        "ttc": {"mean": 102.22, "stddev": 70.39, "prof_raw": 172.61, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4220, "norm_max": 200}
    },
    "pb2": {
        "drp": {"mean": 0.37, "stddev": 0.66, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4230, "norm_max": 200},
        "mwr": {"mean": 10.53, "stddev": 1.99, "prof_raw": 12.52, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4232, "norm_max": 40},
        "ico": {"mean": 0.5, "stddev": 1.05, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4229, "norm_max": 200},
        "eom": {"mean": 281.11, "stddev": 80.2, "prof_raw": 361.31, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4228, "norm_max": 200},
        "exf": {"mean": 0.28, "stddev": 1.2, "prof_raw": 1.48, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4233, "norm_max": 200},
        "iov": {"mean": 0.72, "stddev": 2.34, "prof_raw": 3.06, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4231, "norm_max": 200},
        "ttc": {"mean": 114.76, "stddev": 51.15, "prof_raw": 165.91, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4227, "norm_max": 200}
    },
    "pb3": {
        "mwr": {"mean": 11.97, "stddev": 1.79, "prof_raw": 13.76, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4238, "norm_max": 40},
        "ico": {"mean": 1.01, "stddev": 1.84, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4236, "norm_max": 200},
        "eom": {"mean": 845.77, "stddev": 195.69, "prof_raw": 1041.46, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4235, "norm_max": 200},
        "exf": {"mean": 3.98, "stddev": 8.55, "prof_raw": 12.53, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4239, "norm_max": 200},
        "iov": {"mean": 11.87, "stddev": 22.7, "prof_raw": 34.57, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4237, "norm_max": 200},
        "ttc": {"mean": 281.43, "stddev": 95.00, "prof_raw": 376.43, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4234, "norm_max": 200}
    },
    "rtt": {
        "drp": {"mean": 0.82, "stddev": 0.69, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5319, "norm_max": 200},
        "eom": {"mean": 178.26, "stddev": 44.81, "prof_raw": 223.07, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5326, "norm_max": 200},
        "ico": {"mean": 0.19, "stddev": 0.6, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5320, "norm_max": 200},
        "iov": {"mean": 5.35, "stddev": 13.59, "prof_raw": 18.94, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5321, "norm_max": 200},
        "ttc": {"mean": 113.46, "stddev": 43.25, "prof_raw": 156.71, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5322, "norm_max": 200},
        "tko": {"mean": 0.03, "stddev": 0.16, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5325, "norm_max": 200},
        "wrc": {"mean": 15.00, "stddev": 8.00, "prof_raw": 23.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5323, "norm_max": 200},
        "wcd": {"mean": 21.65, "stddev": 24.88, "prof_raw": 46.53, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5324, "norm_max": 200}
    },
    "mb1": {
        "drp": {"mean": 0.27, "stddev": 0.77, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4187, "norm_max": 200},
        "mwr": {"mean": 10.51, "stddev": 2.24, "prof_raw": 12.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4189, "norm_max": 40},
        "ico": {"mean": 1.52, "stddev": 2.37, "prof_raw": 4.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4186, "norm_max": 200},
        "eom": {"mean": 395.68, "stddev": 194.32, "prof_raw": 590.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4185, "norm_max": 200},
        "exf": {"mean": 1.2, "stddev": 4.19, "prof_raw": 5.39, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4190, "norm_max": 200},
        "iov": {"mean": 1.74, "stddev": 5.19, "prof_raw": 6.93, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4188, "norm_max": 200},
        "ttc": {"mean": 212.35, "stddev": 148.3, "prof_raw": 360.65, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4184, "norm_max": 200}
    },
    "mb2": {
        "drp": {"mean": 0.22, "stddev": 0.59, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4194, "norm_max": 200},
        "mwr": {"mean": 11.9, "stddev": 1.87, "prof_raw": 13.77, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4196, "norm_max": 40},
        "ico": {"mean": 0.18, "stddev": 0.47, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4193, "norm_max": 200},
        "eom": {"mean": 316.49, "stddev": 119.02, "prof_raw": 435.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4192, "norm_max": 200},
        "exf": {"mean": 6.55, "stddev": 10.39, "prof_raw": 16.94, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4197, "norm_max": 200},
        "iov": {"mean": 4.9, "stddev": 17.02, "prof_raw": 21.92, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4195, "norm_max": 200},
        "ttc": {"mean": 129.88, "stddev": 84.44, "prof_raw": 214.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4191, "norm_max": 200}
    },
    "mb3": {
        "drp": {"mean": 0.51, "stddev": 1.14, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4201, "norm_max": 200},
        "mwr": {"mean": 14.05, "stddev": 2.1, "prof_raw": 16.15, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4203, "norm_max": 40},
        "ico": {"mean": 1.64, "stddev": 4.2, "prof_raw": 6.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4200, "norm_max": 200},
        "eom": {"mean": 646.84, "stddev": 190.14, "prof_raw": 836.98, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4199, "norm_max": 200},
        "exf": {"mean": 123.12, "stddev": 125.95, "prof_raw": 249.07, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4204, "norm_max": 200},
        "iov": {"mean": 22.97, "stddev": 25.19, "prof_raw": 48.16, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4202, "norm_max": 200},
        "ttc": {"mean": 327.59, "stddev": 150.52, "prof_raw": 478.11, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4198, "norm_max": 200}
    },
    "4ac": {
        "drp": {"mean": 1.64, "stddev": 2.54, "prof_raw": 4.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5327, "norm_max": 200},
        "eom": {"mean": 132.37, "stddev": 61.13, "prof_raw": 193.5, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5334, "norm_max": 200},
        "icl": {"mean": 1.1, "stddev": 0.38, "prof_raw": 1.48, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5331, "norm_max": 200},
        "isc": {"mean": 0.61, "stddev": 1.12, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5333, "norm_max": 200},
        "ico": {"mean": 0.44, "stddev": 1.11, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5328, "norm_max": 200},
        "isw": {"mean": 8.83, "stddev": 2.77, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5332, "norm_max": 200},
        "iov": {"mean": 3.9, "stddev": 8.73, "prof_raw": 12.63, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5329, "norm_max": 200},
        "ttc": {"mean": 71.55, "stddev": 32.77, "prof_raw": 104.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5330, "norm_max": 200}
    },
    "rr1": {
        "drp": {"mean": 0.03, "stddev": 0.17, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4243, "norm_max": 200},
        "mwr": {"mean": 8.00, "stddev": 1.86, "prof_raw": 9.86, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4245, "norm_max": 40},
        "ico": {"mean": 0.43, "stddev": 1.1, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4242, "norm_max": 200},
        "eom": {"mean": 56.21, "stddev": 40.02, "prof_raw": 96.23, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4241, "norm_max": 200},
        "exf": {"mean": 1.81, "stddev": 7.47, "prof_raw": 9.28, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4246, "norm_max": 200},
        "iov": {"mean": 0.32, "stddev": 0.72, "prof_raw": 1.04, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4244, "norm_max": 200},
        "ttc": {"mean": 47.02, "stddev": 52.99, "prof_raw": 100.01, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4240, "norm_max": 200}
    },
    "rr2": {
        "drp": {"mean": 0.16, "stddev": 0.4, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3933, "norm_max": 200},
        "mwr": {"mean": 10.2, "stddev": 2.01, "prof_raw": 12.21, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3935, "norm_max": 40},
        "ico": {"mean": 4.38, "stddev": 5.09, "prof_raw": 9.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3932, "norm_max": 200},
        "eom": {"mean": 386.33, "stddev": 153.49, "prof_raw": 539.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3931, "norm_max": 200},
        "exf": {"mean": 12.85, "stddev": 51.24, "prof_raw": 64.09, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3936, "norm_max": 200},
        "iov": {"mean": 3.09, "stddev": 6.67, "prof_raw": 9.76, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3934, "norm_max": 200},
        "ttc": {"mean": 201.16, "stddev": 110.11, "prof_raw": 311.27, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3930, "norm_max": 200}
    },
    "rw1": {
        "mwr": {"mean": 8.94, "stddev": 2.42, "prof_raw": 11.36, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4251, "norm_max": 40},
        "ico": {"mean": 0.95, "stddev": 1.43, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4249, "norm_max": 200},
        "eom": {"mean": 94.2, "stddev": 37.6, "prof_raw": 131.8, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4248, "norm_max": 200},
        "exf": {"mean": 0.27, "stddev": 0.78, "prof_raw": 1.05, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4252, "norm_max": 200},
        "iov": {"mean": 0.12, "stddev": 0.48, "prof_raw": 0.6, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4250, "norm_max": 200},
        "ttc": {"mean": 71.83, "stddev": 29.9, "prof_raw": 101.73, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4247, "norm_max": 200}
    },
    "rw2": {
        "mwr": {"mean": 11.45, "stddev": 2.05, "prof_raw": 13.5, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4257, "norm_max": 40},
        "ico": {"mean": 1.37, "stddev": 2.42, "prof_raw": 4.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4255, "norm_max": 200},
        "eom": {"mean": 247.13, "stddev": 132.87, "prof_raw": 380.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4254, "norm_max": 200},
        "exf": {"mean": 1.03, "stddev": 3.64, "prof_raw": 4.67, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4258, "norm_max": 200},
        "iov": {"mean": 3.03, "stddev": 7.4, "prof_raw": 10.43, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4256, "norm_max": 200},
        "ttc": {"mean": 139.74, "stddev": 75.26, "prof_raw": 215.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4253, "norm_max": 200}
    },
    "rw3": {
        "mwr": {"mean": 14.33, "stddev": 2.86, "prof_raw": 17.19, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4263, "norm_max": 40},
        "ico": {"mean": 6.45, "stddev": 8.03, "prof_raw": 14.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4261, "norm_max": 200},
        "eom": {"mean": 337.83, "stddev": 150.62, "prof_raw": 488.45, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4260, "norm_max": 200},
        "exf": {"mean": 17.53, "stddev": 28.03, "prof_raw": 45.56, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4264, "norm_max": 200},
        "iov": {"mean": 10.55, "stddev": 26.03, "prof_raw": 36.59, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4262, "norm_max": 200},
        "ttc": {"mean": 225.03, "stddev": 139.26, "prof_raw": 364.29, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4259, "norm_max": 200}
    },
    "vop": {
        "pts": {"mean": 40.3, "stddev": 8.8, "prof_raw": 31.00, "direction": "higher", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3947, "norm_max": 200}
    },
    "ct1": {
        "mwr": {"mean": 10.47, "stddev": 2.82, "prof_raw": 13.29, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3882, "norm_max": 40},
        "ico": {"mean": 0.31, "stddev": 1.18, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3880, "norm_max": 200},
        "eom": {"mean": 181.69, "stddev": 63.88, "prof_raw": 245.57, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3879, "norm_max": 200},
        "exf": {"mean": 0.58, "stddev": 3.09, "prof_raw": 3.67, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3883, "norm_max": 200},
        "iov": {"mean": 6.74, "stddev": 19.44, "prof_raw": 26.18, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3881, "norm_max": 200},
        "ttc": {"mean": 83.97, "stddev": 38.21, "prof_raw": 122.18, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3878, "norm_max": 200}
    },
    "ct2": {
        "drp": {"mean": 0.06, "stddev": 0.21, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4141, "norm_max": 200},
        "mwr": {"mean": 11.96, "stddev": 2.39, "prof_raw": 14.35, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4144, "norm_max": 40},
        "ico": {"mean": 0.63, "stddev": 2.06, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4142, "norm_max": 200},
        "eom": {"mean": 279.43, "stddev": 118.04, "prof_raw": 397.47, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4140, "norm_max": 200},
        "exf": {"mean": 4.74, "stddev": 18.09, "prof_raw": 22.83, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4145, "norm_max": 200},
        "iov": {"mean": 9.79, "stddev": 23.51, "prof_raw": 33.3, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4143, "norm_max": 200},
        "ttc": {"mean": 124.49, "stddev": 77.86, "prof_raw": 202.35, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4139, "norm_max": 200}
    },
    "ppc": {
        "drp": {"mean": 0.11, "stddev": 0.32, "prof_raw": 0.43, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5207, "norm_max": 200},
        "eom": {"mean": 260.00, "stddev": 38.00, "prof_raw": 298.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5205, "norm_max": 200},
        "exf": {"mean": 5.00, "stddev": 2.00, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5210, "norm_max": 200},
        "ico": {"mean": 0.33, "stddev": 0.69, "prof_raw": 1.02, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5206, "norm_max": 200},
        "iov": {"mean": 3.00, "stddev": 1.00, "prof_raw": 4.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5208, "norm_max": 200},
        "mwr": {"mean": 13.00, "stddev": 4.00, "prof_raw": 17.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5209, "norm_max": 40},
        "ttc": {"mean": 79.00, "stddev": 20.00, "prof_raw": 99.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5204, "norm_max": 200}
    },
    "mbc": {
        "drp": {"mean": 2.00, "stddev": 0.00, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5213, "norm_max": 200},
        "eom": {"mean": 294.00, "stddev": 56.00, "prof_raw": 350.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5212, "norm_max": 200},
        "exf": {"mean": 2.63, "stddev": 6.38, "prof_raw": 9.01, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5217, "norm_max": 200},
        "ico": {"mean": 4.00, "stddev": 0.00, "prof_raw": 4.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5214, "norm_max": 200},
        "iov": {"mean": 0.4, "stddev": 0.96, "prof_raw": 1.36, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5215, "norm_max": 200},
        "mwr": {"mean": 10.19, "stddev": 2.81, "prof_raw": 13.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5216, "norm_max": 40},
        "ttc": {"mean": 151.83, "stddev": 28.17, "prof_raw": 180.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5211, "norm_max": 200}
    },
    "es1": {
        "mwr": {"mean": 11.85, "stddev": 2.92, "prof_raw": 14.77, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3921, "norm_max": 40},
        "ico": {"mean": 0.16, "stddev": 0.69, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3919, "norm_max": 200},
        "eom": {"mean": 173.92, "stddev": 39.34, "prof_raw": 213.26, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3917, "norm_max": 200},
        "exf": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3918, "norm_max": 200},
        "iov": {"mean": 0.17, "stddev": 0.65, "prof_raw": 0.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3920, "norm_max": 200},
        "ttc": {"mean": 118.7, "stddev": 41.6, "prof_raw": 160.3, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3916, "norm_max": 200},
        "met": {"mean": 7.82, "stddev": 4.84, "prof_raw": 12.66, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3922, "norm_max": 200}
    },
    "es2": {
        "mwr": {"mean": 11.88, "stddev": 0.63, "prof_raw": 12.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5223, "norm_max": 40},
        "ico": {"mean": 1.88, "stddev": 0.63, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5221, "norm_max": 200},
        "eom": {"mean": 193.75, "stddev": 21.25, "prof_raw": 215.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5219, "norm_max": 200},
        "exf": {"mean": 1.88, "stddev": 0.63, "prof_raw": 2.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5220, "norm_max": 200},
        "iov": {"mean": 1.88, "stddev": 0.63, "prof_raw": 2.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5222, "norm_max": 200},
        "ttc": {"mean": 93.75, "stddev": 11.25, "prof_raw": 105.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5218, "norm_max": 200},
        "met": {"mean": 5.63, "stddev": 0.88, "prof_raw": 6.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5224, "norm_max": 200}
    },
    "ed2": {
        "mwr": {"mean": 8.22, "stddev": 1.57, "prof_raw": 9.79, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4168, "norm_max": 40},
        "ico": {"mean": 2.19, "stddev": 4.19, "prof_raw": 6.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4166, "norm_max": 200},
        "eom": {"mean": 163.6, "stddev": 72.45, "prof_raw": 236.05, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4164, "norm_max": 200},
        "exf": {"mean": 0.74, "stddev": 3.17, "prof_raw": 3.91, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4165, "norm_max": 200},
        "iov": {"mean": 0.31, "stddev": 1.11, "prof_raw": 1.42, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4167, "norm_max": 200},
        "ttc": {"mean": 166.29, "stddev": 89.5, "prof_raw": 255.79, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4163, "norm_max": 200},
        "met": {"mean": 33.24, "stddev": 24.27, "prof_raw": 57.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4169, "norm_max": 200},
        "blv": {"mean": 156.21, "stddev": 157.07, "prof_raw": 313.28, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4170, "norm_max": 200},
        "bve": {"mean": 0.05, "stddev": 0.23, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4171, "norm_max": 200}
    },
    "ed3": {
        "mwr": {"mean": 7.33, "stddev": 1.88, "prof_raw": 9.21, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5228, "norm_max": 40},
        "ico": {"mean": 0.89, "stddev": 2.05, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5229, "norm_max": 200},
        "eom": {"mean": 111.47, "stddev": 31.15, "prof_raw": 142.62, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5230, "norm_max": 200},
        "exf": {"mean": 0.22, "stddev": 1.18, "prof_raw": 1.4, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5231, "norm_max": 200},
        "iov": {"mean": 0.04, "stddev": 0.16, "prof_raw": 0.2, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5232, "norm_max": 200},
        "ttc": {"mean": 117.75, "stddev": 52.3, "prof_raw": 170.05, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5233, "norm_max": 200},
        "blv": {"mean": 23.57, "stddev": 32.92, "prof_raw": 56.49, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5225, "norm_max": 200},
        "bve": {"mean": 0.01, "stddev": 0.11, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5226, "norm_max": 200},
        "met": {"mean": 20.96, "stddev": 15.12, "prof_raw": 36.08, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5227, "norm_max": 200}
    },
    "tr1": {
        "drp": {"mean": 0.8, "stddev": 1.6, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3958, "norm_max": 200},
        "mwr": {"mean": 8.00, "stddev": 2.24, "prof_raw": 10.24, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3960, "norm_max": 40},
        "ico": {"mean": 0.83, "stddev": 1.47, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3957, "norm_max": 200},
        "eom": {"mean": 270.00, "stddev": 50.00, "prof_raw": 320.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3956, "norm_max": 200},
        "exf": {"mean": 4.00, "stddev": 2.4, "prof_raw": 6.4, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3961, "norm_max": 200},
        "iov": {"mean": 0.8, "stddev": 1.00, "prof_raw": 1.8, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3959, "norm_max": 200},
        "ttc": {"mean": 140.00, "stddev": 32.00, "prof_raw": 172.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3955, "norm_max": 200}
    },
    "tr2": {
        "drp": {"mean": 0.33, "stddev": 0.68, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4114, "norm_max": 200},
        "mwr": {"mean": 8.5, "stddev": 1.64, "prof_raw": 10.14, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4116, "norm_max": 40},
        "ico": {"mean": 4.16, "stddev": 4.21, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4113, "norm_max": 200},
        "eom": {"mean": 290.12, "stddev": 140.48, "prof_raw": 430.6, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4112, "norm_max": 200},
        "exf": {"mean": 5.32, "stddev": 8.99, "prof_raw": 14.31, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4117, "norm_max": 200},
        "iov": {"mean": 1.67, "stddev": 5.15, "prof_raw": 6.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4115, "norm_max": 200},
        "ttc": {"mean": 170.15, "stddev": 88.86, "prof_raw": 259.01, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4111, "norm_max": 200}
    },
    "nt1": {
        "drp": {"mean": 0.26, "stddev": 0.72, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4208, "norm_max": 200},
        "eom": {"mean": 267.93, "stddev": 156.63, "prof_raw": 424.56, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4206, "norm_max": 200},
        "exf": {"mean": 1.04, "stddev": 3.38, "prof_raw": 4.42, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4211, "norm_max": 200},
        "ico": {"mean": 1.73, "stddev": 3.78, "prof_raw": 6.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4207, "norm_max": 200},
        "iov": {"mean": 1.17, "stddev": 4.8, "prof_raw": 5.97, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4209, "norm_max": 200},
        "mwr": {"mean": 9.63, "stddev": 2.07, "prof_raw": 11.7, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4210, "norm_max": 40},
        "mtg": {"mean": 3.44, "stddev": 3.14, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4212, "norm_max": 200},
        "ttc": {"mean": 181.63, "stddev": 146.32, "prof_raw": 327.95, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4205, "norm_max": 200}
    },
    "ss1": {
        "drp": {"mean": 1.00, "stddev": 1.00, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3942, "norm_max": 200},
        "mwr": {"mean": 7.00, "stddev": 2.5, "prof_raw": 9.5, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3944, "norm_max": 40},
        "ico": {"mean": 2.97, "stddev": 5.37, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3941, "norm_max": 200},
        "eom": {"mean": 320.00, "stddev": 160.00, "prof_raw": 480.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3940, "norm_max": 200},
        "exf": {"mean": 0.95, "stddev": 5.04, "prof_raw": 5.99, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3945, "norm_max": 200},
        "iov": {"mean": 1.23, "stddev": 6.09, "prof_raw": 7.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3943, "norm_max": 200},
        "ttc": {"mean": 305.00, "stddev": 100.00, "prof_raw": 405.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3939, "norm_max": 200},
        "mtg": {"mean": 16.00, "stddev": 12.00, "prof_raw": 28.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 3946, "norm_max": 200}
    },
    "ss2": {
        "drp": {"mean": 0.1, "stddev": 0.3, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4280, "norm_max": 200},
        "mwr": {"mean": 7.17, "stddev": 1.65, "prof_raw": 8.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4282, "norm_max": 40},
        "ico": {"mean": 5.13, "stddev": 6.68, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4279, "norm_max": 200},
        "eom": {"mean": 336.59, "stddev": 148.63, "prof_raw": 485.22, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4278, "norm_max": 200},
        "exf": {"mean": 0.83, "stddev": 2.26, "prof_raw": 3.09, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4283, "norm_max": 200},
        "iov": {"mean": 0.8, "stddev": 2.39, "prof_raw": 3.19, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4281, "norm_max": 200},
        "ttc": {"mean": 250.02, "stddev": 126.57, "prof_raw": 376.59, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4277, "norm_max": 200},
        "mtg": {"mean": 14.51, "stddev": 16.47, "prof_raw": 31.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4284, "norm_max": 200}
    },
    "ss3": {
        "drp": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4288, "norm_max": 200},
        "mwr": {"mean": 7.3, "stddev": 1.52, "prof_raw": 8.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4290, "norm_max": 40},
        "ico": {"mean": 1.38, "stddev": 1.92, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4287, "norm_max": 200},
        "eom": {"mean": 315.55, "stddev": 85.31, "prof_raw": 400.86, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4286, "norm_max": 200},
        "exf": {"mean": 0.04, "stddev": 0.23, "prof_raw": 0.27, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4291, "norm_max": 200},
        "iov": {"mean": 1.88, "stddev": 4.29, "prof_raw": 6.17, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4289, "norm_max": 200},
        "ttc": {"mean": 233.98, "stddev": 83.44, "prof_raw": 317.42, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4285, "norm_max": 200},
        "mtg": {"mean": 8.26, "stddev": 6.55, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4292, "norm_max": 200}
    },
    "row": {
        "mwr": {"mean": 5.81, "stddev": 1.47, "prof_raw": 7.28, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4275, "norm_max": 40},
        "ico": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4273, "norm_max": 200},
        "eom": {"mean": 115.6, "stddev": 21.32, "prof_raw": 136.92, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4272, "norm_max": 200},
        "exf": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4274, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4276, "norm_max": 200},
        "ttc": {"mean": 62.85, "stddev": 19.97, "prof_raw": 82.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4271, "norm_max": 200}
    },
    "wcv": {
        "mwr": {"mean": 7.91, "stddev": 1.6, "prof_raw": 9.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5290, "norm_max": 40},
        "ico": {"mean": 4.00, "stddev": 5.4, "prof_raw": 9.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5291, "norm_max": 200},
        "eom": {"mean": 233.92, "stddev": 92.00, "prof_raw": 325.92, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5292, "norm_max": 200},
        "exf": {"mean": 3.76, "stddev": 6.00, "prof_raw": 9.76, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5293, "norm_max": 200},
        "iov": {"mean": 2.03, "stddev": 5.2, "prof_raw": 7.23, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5294, "norm_max": 200},
        "ttc": {"mean": 96.7, "stddev": 48.00, "prof_raw": 144.7, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5296, "norm_max": 200},
        "mtg": {"mean": 6.5, "stddev": 12.1, "prof_raw": 19.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5295, "norm_max": 200}
    },
    "tcv": {
        "mwr": {"mean": 7.91, "stddev": 4.00, "prof_raw": 11.91, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4307, "norm_max": 40},
        "ico": {"mean": 4.00, "stddev": 11.00, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4308, "norm_max": 200},
        "eom": {"mean": 253.92, "stddev": 184.00, "prof_raw": 437.92, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4309, "norm_max": 200},
        "exf": {"mean": 3.76, "stddev": 12.00, "prof_raw": 15.76, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4310, "norm_max": 200},
        "iov": {"mean": 2.03, "stddev": 11.00, "prof_raw": 13.03, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4311, "norm_max": 200},
        "ttc": {"mean": 116.7, "stddev": 96.00, "prof_raw": 212.7, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4313, "norm_max": 200},
        "mtg": {"mean": 6.5, "stddev": 25.00, "prof_raw": 32.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4312, "norm_max": 200}
    },
    "wch": {
        "mwr": {"mean": 8.38, "stddev": 2.00, "prof_raw": 10.38, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5297, "norm_max": 40},
        "ico": {"mean": 1.4, "stddev": 2.00, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5298, "norm_max": 200},
        "eom": {"mean": 231.19, "stddev": 62.00, "prof_raw": 293.19, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5299, "norm_max": 200},
        "exf": {"mean": 1.66, "stddev": 4.6, "prof_raw": 6.26, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5300, "norm_max": 200},
        "iov": {"mean": 2.74, "stddev": 10.2, "prof_raw": 12.94, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5301, "norm_max": 200},
        "ttc": {"mean": 98.33, "stddev": 30.00, "prof_raw": 128.33, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5303, "norm_max": 200},
        "mtg": {"mean": 2.9, "stddev": 5.4, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5302, "norm_max": 200}
    },
    "tch": {
        "mwr": {"mean": 8.38, "stddev": 4.00, "prof_raw": 12.38, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4300, "norm_max": 40},
        "ico": {"mean": 1.4, "stddev": 4.00, "prof_raw": 5.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4301, "norm_max": 200},
        "eom": {"mean": 357.68, "stddev": 162.32, "prof_raw": 520.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4302, "norm_max": 200},
        "exf": {"mean": 1.66, "stddev": 10.00, "prof_raw": 11.66, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4303, "norm_max": 200},
        "iov": {"mean": 2.74, "stddev": 21.00, "prof_raw": 23.74, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4304, "norm_max": 200},
        "ttc": {"mean": 222.29, "stddev": 112.71, "prof_raw": 335.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4306, "norm_max": 200},
        "mtg": {"mean": 2.9, "stddev": 11.00, "prof_raw": 14.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4305, "norm_max": 200}
    },
    "sug": {
        "cac": {"mean": 3.65, "stddev": 0.64, "prof_raw": 4.29, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5435, "norm_max": 200},
        "eom": {"mean": 610.16, "stddev": 176.87, "prof_raw": 787.03, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5436, "norm_max": 200},
        "esf": {"mean": 1.71, "stddev": 10.1, "prof_raw": 11.81, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5434, "norm_max": 200},
        "ico": {"mean": 9.21, "stddev": 5.99, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5429, "norm_max": 200},
        "iov": {"mean": 22.01, "stddev": 22.32, "prof_raw": 44.33, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5430, "norm_max": 200},
        "mtg": {"mean": 1.1, "stddev": 1.61, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5432, "norm_max": 200},
        "pid": {"mean": 1.05, "stddev": 0.22, "prof_raw": 1.27, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5433, "norm_max": 200},
        "ttc": {"mean": 354.49, "stddev": 98.25, "prof_raw": 452.74, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5431, "norm_max": 200}
    },
    "tu1": {
        "mwr": {"mean": 11.88, "stddev": 0.63, "prof_raw": 12.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4297, "norm_max": 40},
        "ico": {"mean": 1.88, "stddev": 0.63, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4295, "norm_max": 200},
        "eom": {"mean": 515.62, "stddev": 34.38, "prof_raw": 550.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4294, "norm_max": 200},
        "exf": {"mean": 5.00, "stddev": 1.00, "prof_raw": 6.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4298, "norm_max": 200},
        "iov": {"mean": 1.88, "stddev": 0.63, "prof_raw": 2.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4296, "norm_max": 200},
        "ttc": {"mean": 254.68, "stddev": 25.32, "prof_raw": 280.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4293, "norm_max": 200},
        "mtg": {"mean": 22.9, "stddev": 2.1, "prof_raw": 25.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4299, "norm_max": 200}
    },
    "tah": {
        "mwr": {"mean": 11.00, "stddev": 4.00, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5311, "norm_max": 40},
        "ico": {"mean": 8.00, "stddev": 4.00, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5312, "norm_max": 200},
        "eom": {"mean": 250.00, "stddev": 100.00, "prof_raw": 350.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5313, "norm_max": 200},
        "exf": {"mean": 10.00, "stddev": 5.00, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5314, "norm_max": 200},
        "iov": {"mean": 3.00, "stddev": 10.00, "prof_raw": 13.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5315, "norm_max": 200},
        "ttc": {"mean": 400.00, "stddev": 100.00, "prof_raw": 500.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5317, "norm_max": 200},
        "mtg": {"mean": 25.00, "stddev": 10.00, "prof_raw": 35.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5316, "norm_max": 200}
    },
    "tu2": {
        "mwr": {"mean": 11.88, "stddev": 0.63, "prof_raw": 12.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5254, "norm_max": 40},
        "ico": {"mean": 1.88, "stddev": 0.63, "prof_raw": 3.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5252, "norm_max": 200},
        "eom": {"mean": 375.00, "stddev": 25.00, "prof_raw": 400.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5251, "norm_max": 200},
        "exf": {"mean": 5.00, "stddev": 1.00, "prof_raw": 6.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5255, "norm_max": 200},
        "iov": {"mean": 1.88, "stddev": 0.63, "prof_raw": 2.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5253, "norm_max": 200},
        "ttc": {"mean": 213.75, "stddev": 21.25, "prof_raw": 235.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5250, "norm_max": 200},
        "mtg": {"mean": 6.88, "stddev": 0.63, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5263, "norm_max": 200}
    },
    "tav": {
        "mwr": {"mean": 11.00, "stddev": 4.00, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5304, "norm_max": 40},
        "ico": {"mean": 8.00, "stddev": 4.00, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5305, "norm_max": 200},
        "eom": {"mean": 250.00, "stddev": 100.00, "prof_raw": 350.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5306, "norm_max": 200},
        "exf": {"mean": 10.00, "stddev": 5.00, "prof_raw": 15.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5307, "norm_max": 200},
        "iov": {"mean": 3.00, "stddev": 10.00, "prof_raw": 13.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5308, "norm_max": 200},
        "ttc": {"mean": 400.00, "stddev": 100.00, "prof_raw": 500.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5310, "norm_max": 200},
        "mtg": {"mean": 25.00, "stddev": 10.00, "prof_raw": 35.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5309, "norm_max": 200}
    },
    "tu3": {
        "mwr": {"mean": 11.88, "stddev": 0.63, "prof_raw": 12.51, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5261, "norm_max": 40},
        "ico": {"mean": 3.7, "stddev": 1.2, "prof_raw": 5.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5259, "norm_max": 200},
        "eom": {"mean": 750.00, "stddev": 50.00, "prof_raw": 800.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5258, "norm_max": 200},
        "exf": {"mean": 10.00, "stddev": 2.00, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5262, "norm_max": 200},
        "iov": {"mean": 3.7, "stddev": 1.2, "prof_raw": 4.9, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5260, "norm_max": 200},
        "ttc": {"mean": 213.75, "stddev": 21.25, "prof_raw": 235.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5257, "norm_max": 200},
        "mtg": {"mean": 6.88, "stddev": 0.63, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5256, "norm_max": 200}
    },
    "kr1": {
        "mwr": {"mean": 10.71, "stddev": 5.4, "prof_raw": 16.11, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4172, "norm_max": 40},
        "ico": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4173, "norm_max": 200},
        "eom": {"mean": 43.95, "stddev": 9.4, "prof_raw": 53.35, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4174, "norm_max": 200},
        "exf": {"mean": 3.00, "stddev": 4.00, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4175, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4176, "norm_max": 200},
        "ttc": {"mean": 13.27, "stddev": 4.4, "prof_raw": 17.67, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4177, "norm_max": 200}
    },
    "kr2": {
        "mwr": {"mean": 11.73, "stddev": 4.8, "prof_raw": 16.53, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4178, "norm_max": 40},
        "ico": {"mean": 0.3, "stddev": 1.4, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4179, "norm_max": 200},
        "eom": {"mean": 78.6, "stddev": 26.00, "prof_raw": 104.6, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4180, "norm_max": 200},
        "exf": {"mean": 3.00, "stddev": 4.00, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4181, "norm_max": 200},
        "iov": {"mean": 0.42, "stddev": 2.4, "prof_raw": 2.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4182, "norm_max": 200},
        "ttc": {"mean": 22.78, "stddev": 11.00, "prof_raw": 33.78, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4183, "norm_max": 200}
    },
    "kr3": {
        "mwr": {"mean": 8.3, "stddev": 4.6, "prof_raw": 12.9, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5264, "norm_max": 40},
        "ico": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5265, "norm_max": 200},
        "eom": {"mean": 55.43, "stddev": 5.4, "prof_raw": 60.83, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5266, "norm_max": 200},
        "exf": {"mean": 3.00, "stddev": 4.00, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5267, "norm_max": 200},
        "iov": {"mean": 0.04, "stddev": 0.28, "prof_raw": 0.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5268, "norm_max": 200},
        "ttc": {"mean": 18.12, "stddev": 4.4, "prof_raw": 22.52, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5269, "norm_max": 200}
    },
    "kr4": {
        "mwr": {"mean": 9.58, "stddev": 3.8, "prof_raw": 13.38, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5270, "norm_max": 40},
        "ico": {"mean": 0.64, "stddev": 1.4, "prof_raw": 2.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5271, "norm_max": 200},
        "eom": {"mean": 128.66, "stddev": 40.00, "prof_raw": 168.66, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5272, "norm_max": 200},
        "exf": {"mean": 3.00, "stddev": 4.00, "prof_raw": 7.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5273, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5274, "norm_max": 200},
        "ttc": {"mean": 46.91, "stddev": 15.4, "prof_raw": 62.31, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5275, "norm_max": 200}
    },
    "is1": {
        "eom": {"mean": 631.01, "stddev": 200.00, "prof_raw": 831.01, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5278, "norm_max": 200},
        "exf": {"mean": 7.51, "stddev": 11.6, "prof_raw": 19.11, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5279, "norm_max": 200},
        "isc": {"mean": 0.75, "stddev": 0.25, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5282, "norm_max": 200},
        "ico": {"mean": 4.00, "stddev": 6.4, "prof_raw": 10.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5277, "norm_max": 200},
        "iov": {"mean": 0.65, "stddev": 2.6, "prof_raw": 3.25, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5280, "norm_max": 200},
        "mwr": {"mean": 10.92, "stddev": 2.4, "prof_raw": 13.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5276, "norm_max": 40},
        "ttc": {"mean": 213.13, "stddev": 74.00, "prof_raw": 287.13, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5281, "norm_max": 200}
    },
    "is2": {
        "eom": {"mean": 481.65, "stddev": 104.00, "prof_raw": 585.65, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5285, "norm_max": 200},
        "exf": {"mean": 3.23, "stddev": 4.6, "prof_raw": 7.83, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5286, "norm_max": 200},
        "isc": {"mean": 0.75, "stddev": 0.25, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5289, "norm_max": 200},
        "ico": {"mean": 3.2, "stddev": 5.8, "prof_raw": 9.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5284, "norm_max": 200},
        "iov": {"mean": 0.05, "stddev": 0.28, "prof_raw": 0.33, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5287, "norm_max": 200},
        "mwr": {"mean": 10.52, "stddev": 2.8, "prof_raw": 13.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5283, "norm_max": 40},
        "ttc": {"mean": 155.98, "stddev": 52.00, "prof_raw": 207.98, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5288, "norm_max": 200}
    },
    "30d": {
        "ttc": {"mean": 135.98, "stddev": 39.23, "prof_raw": 175.22, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4795, "norm_max": 200},
        "eom": {"mean": 402.69, "stddev": 94.4, "prof_raw": 497.09, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4796, "norm_max": 200},
        "ico": {"mean": 0.51, "stddev": 1.06, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4797, "norm_max": 200},
        "iov": {"mean": 66.62, "stddev": 29.51, "prof_raw": 96.14, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4798, "norm_max": 200},
        "exf": {"mean": 1.28, "stddev": 3.47, "prof_raw": 4.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4800, "norm_max": 200},
        "mwr": {"mean": 11.55, "stddev": 2.5, "prof_raw": 14.05, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4799, "norm_max": 40},
        "drp": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4801, "norm_max": 200}
    },
    "ttr": {
        "ttc": {"mean": 109.23, "stddev": 10.92, "prof_raw": 120.15, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5391, "norm_max": 200},
        "eom": {"mean": 256.95, "stddev": 25.7, "prof_raw": 282.65, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5392, "norm_max": 200},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5393, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5395, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5397, "norm_max": 200},
        "mwr": {"mean": 8.87, "stddev": 1.17, "prof_raw": 10.04, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5396, "norm_max": 40},
        "drp": {"mean": 0.15, "stddev": 0.46, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5394, "norm_max": 200}
    },
    "rc1": {
        "ttc": {"mean": 45.00, "stddev": 22.58, "prof_raw": 67.58, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5335, "norm_max": 200},
        "eom": {"mean": 127.01, "stddev": 22.11, "prof_raw": 149.12, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5336, "norm_max": 200},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5337, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5339, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5341, "norm_max": 200},
        "mwr": {"mean": 11.26, "stddev": 1.13, "prof_raw": 12.39, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5340, "norm_max": 40},
        "drp": {"mean": 0.15, "stddev": 0.46, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5338, "norm_max": 200}
    },
    "rc2": {
        "ttc": {"mean": 45.00, "stddev": 22.58, "prof_raw": 67.58, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5342, "norm_max": 200},
        "eom": {"mean": 156.2, "stddev": 15.6, "prof_raw": 171.8, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5343, "norm_max": 200},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5344, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5346, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5348, "norm_max": 200},
        "mwr": {"mean": 11.5, "stddev": 1.15, "prof_raw": 12.65, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5347, "norm_max": 40},
        "drp": {"mean": 0.27, "stddev": 0.77, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5345, "norm_max": 200}
    },
    "rc3": {
        "ttc": {"mean": 84.08, "stddev": 8.41, "prof_raw": 92.49, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5349, "norm_max": 200},
        "eom": {"mean": 176.43, "stddev": 17.64, "prof_raw": 194.07, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5350, "norm_max": 200},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5351, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5353, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5355, "norm_max": 200},
        "mwr": {"mean": 11.98, "stddev": 1.2, "prof_raw": 13.18, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5354, "norm_max": 40},
        "drp": {"mean": 0.22, "stddev": 0.59, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5352, "norm_max": 200}
    },
    "rc4": {
        "ttc": {"mean": 120.32, "stddev": 12.03, "prof_raw": 132.35, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5356, "norm_max": 200},
        "eom": {"mean": 264.08, "stddev": 26.41, "prof_raw": 290.49, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5357, "norm_max": 200},
        "ico": {"mean": 0.15, "stddev": 0.42, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5358, "norm_max": 200},
        "iov": {"mean": 0.00, "stddev": 0.00, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5360, "norm_max": 200},
        "exf": {"mean": 0.29, "stddev": 2.46, "prof_raw": 2.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5362, "norm_max": 200},
        "mwr": {"mean": 8.87, "stddev": 1.17, "prof_raw": 10.04, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5361, "norm_max": 40},
        "drp": {"mean": 0.45, "stddev": 0.8, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5359, "norm_max": 200}
    },
    "sc1": {
        "pts": {"mean": 40.00, "stddev": 40.00, "prof_raw": 80.00, "direction": "higher", "best_multiplier": 3, "worst_multiplier": -1, "emet_id_RSAC_2026": 3937, "norm_max": 200}
    },
    "sc2": {
        "pts": {"mean": 35.00, "stddev": 35.00, "prof_raw": 70.00, "direction": "higher", "best_multiplier": 3, "worst_multiplier": -1, "emet_id_RSAC_2026": 3938, "norm_max": 200}
    },
    "ech": {
        "pts": {"mean": 18.75, "stddev": 3.75, "prof_raw": 15.00, "direction": "higher", "best_multiplier": 3, "worst_multiplier": -1, "emet_id_RSAC_2026": 5318, "norm_max": 200}
    },
    "ppd": {
        "ttc": {"mean": 249.89, "stddev": 86.6, "prof_raw": 336.49, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5449, "norm_max": 200},
        "eom": {"mean": 440.18, "stddev": 198.85, "prof_raw": 639.03, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5451, "norm_max": 200},
        "ico": {"mean": 6.78, "stddev": 5.81, "prof_raw": 13.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5447, "norm_max": 200},
        "iov": {"mean": 13.82, "stddev": 29.81, "prof_raw": 43.63, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5448, "norm_max": 200},
        "icu": {"mean": 5.33, "stddev": 4.73, "prof_raw": 10.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5452, "norm_max": 200},
        "icl": {"mean": 0.94, "stddev": 0.82, "prof_raw": 1.76, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5450, "norm_max": 200}
    },
    "ss0": {
        "ttc": {"mean": 250.02, "stddev": 126.57, "prof_raw": 376.59, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4802, "norm_max": 200},
        "eom": {"mean": 336.59, "stddev": 148.63, "prof_raw": 485.22, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4803, "norm_max": 200},
        "ico": {"mean": 5.13, "stddev": 6.68, "prof_raw": 12.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4804, "norm_max": 200},
        "iov": {"mean": 0.8, "stddev": 2.39, "prof_raw": 3.19, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4806, "norm_max": 200},
        "exf": {"mean": 0.83, "stddev": 2.26, "prof_raw": 3.09, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4808, "norm_max": 200},
        "mwr": {"mean": 7.17, "stddev": 1.65, "prof_raw": 8.82, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4807, "norm_max": 40},
        "drp": {"mean": 0.1, "stddev": 0.3, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4805, "norm_max": 200},
        "mtg": {"mean": 14.51, "stddev": 16.47, "prof_raw": 31.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 4809, "norm_max": 200}
    },
    "ss4": {
        "ttc": {"mean": 330.76, "stddev": 123.5, "prof_raw": 454.26, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5716, "norm_max": 200},
        "eom": {"mean": 523.51, "stddev": 275.38, "prof_raw": 798.89, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5717, "norm_max": 200},
        "ico": {"mean": 6.4, "stddev": 7.75, "prof_raw": 14.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5718, "norm_max": 200},
        "iov": {"mean": 15.77, "stddev": 16.17, "prof_raw": 31.94, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5720, "norm_max": 200},
        "exf": {"mean": 46.36, "stddev": 36.04, "prof_raw": 82.4, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5722, "norm_max": 200},
        "mwr": {"mean": 8.55, "stddev": 2.3, "prof_raw": 10.85, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5721, "norm_max": 40},
        "drp": {"mean": 0.27, "stddev": 0.77, "prof_raw": 1.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5719, "norm_max": 200},
        "mtg": {"mean": 22.3, "stddev": 9.35, "prof_raw": 32.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5723, "norm_max": 200}
    },
    "bgd": {
        "ttc": {"mean": 244.19, "stddev": 99.52, "prof_raw": 343.71, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5501, "norm_max": 200},
        "eom": {"mean": 287.62, "stddev": 121.25, "prof_raw": 408.87, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5502, "norm_max": 200},
        "ico": {"mean": 2.97, "stddev": 5.37, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5503, "norm_max": 200},
        "iov": {"mean": 1.23, "stddev": 6.09, "prof_raw": 7.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5505, "norm_max": 200},
        "exf": {"mean": 0.95, "stddev": 5.04, "prof_raw": 5.99, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5507, "norm_max": 200},
        "mwr": {"mean": 12.03, "stddev": 1.67, "prof_raw": 13.7, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5506, "norm_max": 40},
        "drp": {"mean": 0.03, "stddev": 0.17, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5504, "norm_max": 200},
        "mtg": {"mean": 11.38, "stddev": 8.48, "prof_raw": 20.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5508, "norm_max": 200}
    },
    "rrt": {
        "ttc": {"mean": 244.19, "stddev": 99.52, "prof_raw": 343.71, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5519, "norm_max": 200},
        "eom": {"mean": 570.26, "stddev": 101.79, "prof_raw": 672.05, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5520, "norm_max": 200},
        "ico": {"mean": 2.97, "stddev": 5.37, "prof_raw": 8.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5521, "norm_max": 200},
        "iov": {"mean": 1.23, "stddev": 6.09, "prof_raw": 7.32, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5523, "norm_max": 200},
        "exf": {"mean": 24.94, "stddev": 9.81, "prof_raw": 34.75, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5525, "norm_max": 200},
        "mwr": {"mean": 12.03, "stddev": 1.67, "prof_raw": 13.7, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5524, "norm_max": 40},
        "drp": {"mean": 0.03, "stddev": 0.17, "prof_raw": 0.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5522, "norm_max": 200},
        "mtg": {"mean": 11.38, "stddev": 8.48, "prof_raw": 20.00, "direction": "lower", "best_multiplier": -3, "worst_multiplier": 5, "emet_id_RSAC_2026": 5526, "norm_max": 200}
    }
}
# --- END PROFICIENCY_BASELINES ---


# =============================================================================
#  NORMALISED SCORE RANGE (norm_max) - MUST MIRROR THE SIMULATOR SETTINGS
# =============================================================================

# The simulator normalises each metric to a configurable range 0..norm_max, and
# treats half of that range as the proficiency (PASS) mark.  The setting is
# per exercise AND per metric, and it is editable in the simulator itself.
#
#   norm_max = 200  ->  score 0..200, PASS at 100   (the usual setting)
#   norm_max =  40  ->  score 0..40,  PASS at 20    (the Mimic default for mwr)
#
# THESE VALUES MUST MATCH WHAT YOUR SIMULATOR IS SET TO. They are not something
# this app can choose: they describe how the numbers arriving from the simulator
# were scaled. If they disagree with the simulator, every score read from a CSV
# export is silently mis-scaled.
#
# Internally this app always works on the CANONICAL scale 0..200 with PASS at
# 100, so that every metric is directly comparable. Values arriving from the
# simulator on a different range are converted on the way in - see
# simulator_to_canonical() - and converted back only when a number has to be
# compared against something the simulator displays (its Overall Score).

# "norm_max" is declared on every metric of every exercise in
# PROFICIENCY_BASELINES above, alongside mean/stddev/prof_raw, because it is the
# same kind of thing: a per-exercise, per-metric simulator setting. Shipped as 200
# everywhere except "mwr" (Master Workspace Range), which Mimic normalises to 40.
#
# If your simulator has an exercise set differently, change that metric's norm_max
# on its own line. For reference, this site's own exports (csv_clean/) contain mwr
# values above 40 - only possible on the 0..200 range - for exactly three
# exercises, each starting on a clean date boundary with nothing above 40 before:
#
#     ppc : from 2026-07-14  (93 attempts max 29.06  ->  133 attempts max 150.00)
#     kr1 : from 2026-08-26  (82 attempts max 33.15  ->   70 attempts max 160.92)
#     kr2 : from 2026-08-26  (104 attempts max 31.95 ->  111 attempts max 154.20)
#
# so on that simulator those three mwr entries should read "norm_max": 200.

NORM_MAX_CANONICAL = 200          # the scale this app analyses on
METRIC_NORM_MAX_DEFAULT = 200     # assumed when a metric declares no norm_max


def metric_norm_max(exerc_abb: str, metric_code: str) -> int:
    """The simulator's normalised maximum for one metric of one exercise.

    Read from that metric's own baseline entry. Falls back to the canonical 200 if
    the metric declares nothing, so an entry added by hand without a norm_max keeps
    working rather than scaling to zero.
    """
    entry = PROFICIENCY_BASELINES.get(exerc_abb, {}).get(metric_code) or {}
    value = entry.get("norm_max")
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return int(METRIC_NORM_MAX_DEFAULT)


def metric_pass_min_score(exerc_abb: str, metric_code: str) -> float:
    """The simulator-scale score that counts as proficient: half of norm_max."""
    return metric_norm_max(exerc_abb, metric_code) / 2.0


def simulator_to_canonical(score, exerc_abb: str, metric_code: str) -> float:
    """Rescale a score the simulator produced onto the canonical 0..200 range.

    A metric already on 0..200 is returned unchanged; one on 0..40 is multiplied
    by 5. This replaces the hardcoded x5 that used to be applied to mwr for every
    exercise regardless of the simulator's actual setting.
    """
    norm_max = metric_norm_max(exerc_abb, metric_code)
    if norm_max == NORM_MAX_CANONICAL:
        return float(score)
    return float(score) * NORM_MAX_CANONICAL / norm_max


def canonical_to_simulator(score, exerc_abb: str, metric_code: str) -> float:
    """Inverse of simulator_to_canonical.

    Needed only where a value must line up with what the simulator itself shows,
    such as the Overall Score on the score screen.
    """
    norm_max = metric_norm_max(exerc_abb, metric_code)
    if norm_max == NORM_MAX_CANONICAL:
        return float(score)
    return float(score) * norm_max / NORM_MAX_CANONICAL


# =============================================================================
#  OVERALL SCORE PROFICIENCY FLOOR
# =============================================================================

# The overall score proficiency floor is the lowest overall score an attempt
# can have while still being a PASS.
#
# An attempt is a PASS when every metric reaches its proficiency mark, so the
# floor is the sum of those marks - i.e. norm_max/2 per metric. Both the floor
# and the ceiling are expressed on the SIMULATOR's scale, because the
# overall_score they are compared against is the simulator's own number, read
# straight out of the CSV export.
#
#     floor   = sum(norm_max / 2) over the exercise's metrics
#     ceiling = sum(norm_max)     over the exercise's metrics
#
# With every metric at the default norm_max of 200 this reduces to the familiar
# 100 x n_metrics and 200 x n_metrics. The old hardcoded "-80 when mwr is
# present" is now simply what the formula yields when mwr's norm_max is 40.
#
# The metric set of each exercise is taken from PROFICIENCY_BASELINES above,
# which is the single source of truth for which metrics an exercise scores on.


def overall_score_proficiency_floor(metric_codes, exerc_abb: str = "") -> float:
    """Return the minimum overall score a PASS attempt can have, given the
    exercise's metric codes (e.g. ("ttc", "eom", "ico", "mwr", ...)).
    """
    return sum(metric_pass_min_score(exerc_abb, code) for code in set(metric_codes))


OVERALL_SCORE_PROFICIENCY_FLOOR: dict[str, float] = {
    exerc_abb: overall_score_proficiency_floor(metrics.keys(), exerc_abb)
    for exerc_abb, metrics in PROFICIENCY_BASELINES.items()
}


# Reference ceiling: the overall score of an attempt sitting at exactly norm_max
# on every metric.
#
# This is NOT a maximum. The simulator does not cap a metric at its norm_max: on
# an attempt where nothing fell below cutoff it adds the uncapped scores, so
# performance better than the "best" reference keeps accumulating credit. A single
# metric has been observed at 4.02x its norm_max (kr1/mwr at 160.92 with
# norm_max 40), and this site's own exports contain 6 attempts scoring slightly
# above their reference ceiling - legitimately, not as OCR errors.
#
# So treat this as a yardstick for "how good is good", not as a bound.


def overall_score_ceiling(metric_codes, exerc_abb: str = "") -> float:
    """Return the overall score of an attempt at norm_max on every metric.

    See the note above: attempts can and do exceed this.
    """
    return sum(metric_norm_max(exerc_abb, code) for code in set(metric_codes))


OVERALL_SCORE_CEILING: dict[str, float] = {
    exerc_abb: overall_score_ceiling(metrics.keys(), exerc_abb)
    for exerc_abb, metrics in PROFICIENCY_BASELINES.items()
}


# Validity limit: above this an overall score is not a good attempt but a bad
# read, and must be discarded rather than fed into downstream statistics.
#
# The failure mode being caught is a gross misread, above all a lost decimal
# point (61790 instead of 617.90), which is off by a factor of ~100. So the limit
# only needs to sit clear of legitimate scores, and the reference ceiling above is
# too tight for that - using it discarded real attempts.
#
# The factor is how far above the reference ceiling a real attempt is believed
# able to reach. The highest ratio in this site's 2596 exports is 1.03x, so 2x
# rejects nothing genuine while still catching a decimal shift by a wide margin.

OVERALL_SCORE_VALIDITY_FACTOR = 2.0


def overall_score_validity_limit(metric_codes, exerc_abb: str = "") -> float:
    """Return the overall score above which an attempt is treated as a bad read."""
    return overall_score_ceiling(metric_codes, exerc_abb) * OVERALL_SCORE_VALIDITY_FACTOR


OVERALL_SCORE_VALIDITY_LIMIT: dict[str, float] = {
    exerc_abb: overall_score_validity_limit(metrics.keys(), exerc_abb)
    for exerc_abb, metrics in PROFICIENCY_BASELINES.items()
}


def refresh_derived_tables() -> None:
    """Recompute the floor/ceiling/limit tables from the live baselines.

    Those three dicts are snapshots taken at import. Editing a norm_max, or adding
    or removing a metric, changes all of them - so anything that mutates
    PROFICIENCY_BASELINES must call this or the app keeps deciding PASS against the
    values the file had at startup.

    Updated in place: callers hold these exact objects.
    """
    for table, fn in (
        (OVERALL_SCORE_PROFICIENCY_FLOOR, overall_score_proficiency_floor),
        (OVERALL_SCORE_CEILING, overall_score_ceiling),
        (OVERALL_SCORE_VALIDITY_LIMIT, overall_score_validity_limit),
    ):
        table.clear()
        table.update({
            abb: fn(metrics.keys(), abb)
            for abb, metrics in PROFICIENCY_BASELINES.items()
        })


# =============================================================================
#  EDITING AND PERSISTING THE BASELINES
# =============================================================================

# The editor (Settings > Exercises > Proficiency Values) writes the block above
# back into this file. exercise_proficiency_scores_default.json is a read-only
# snapshot of the pristine values so that "reset to default" has something to
# restore from once they have been edited. Nothing writes to that snapshot.

DEFAULTS_FILENAME = "exercise_proficiency_scores_default.json"

# Canonical field order for one metric entry. Anything not listed is preserved
# after these, so a field added later is not silently dropped by a save.
BASELINE_FIELDS: tuple[str, ...] = (
    "mean",
    "stddev",
    "prof_raw",
    "direction",
    "best_multiplier",
    "worst_multiplier",
    "emet_id_RSAC_2026",
    "norm_max",
)

_FLOAT_FIELDS = frozenset({"mean", "stddev", "prof_raw"})
_INT_FIELDS = frozenset({"best_multiplier", "worst_multiplier", "emet_id_RSAC_2026", "norm_max"})

VALID_DIRECTIONS: tuple[str, ...] = ("lower", "higher")

METRIC_CODES: frozenset[str] = frozenset(METRIC_LABEL_MAP.values())


def defaults_path() -> str:
    import os

    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULTS_FILENAME)


def normalize_baselines(baselines: dict) -> dict:
    """Return a deep copy with canonical field order and coerced numeric types.

    Exercise and metric order is preserved rather than sorted, so a save is a
    minimal diff instead of reshuffling 60 exercises. Dict equality ignores order,
    so comparisons against the defaults snapshot are unaffected.
    """
    out: dict[str, dict[str, dict]] = {}
    for abb, metrics in baselines.items():
        if not isinstance(metrics, dict):
            continue
        new_metrics: dict[str, dict] = {}
        for code, entry in metrics.items():
            if not isinstance(entry, dict):
                continue
            new_entry: dict = {}
            for field in BASELINE_FIELDS:
                if field not in entry:
                    continue
                value = entry[field]
                if field in _FLOAT_FIELDS:
                    try:
                        new_entry[field] = float(value)
                    except (TypeError, ValueError):
                        new_entry[field] = value
                elif field in _INT_FIELDS:
                    try:
                        new_entry[field] = int(value)
                    except (TypeError, ValueError):
                        new_entry[field] = value
                else:
                    new_entry[field] = str(value)
            for field, value in entry.items():
                if field not in new_entry:
                    new_entry[field] = value
            new_metrics[str(code)] = new_entry
        out[str(abb)] = new_metrics
    return out


def check_baselines_consistency(baselines: dict | None = None) -> list[str]:
    """Report problems that would otherwise be invisible at runtime.

    Every item here breaks scoring silently rather than raising: an unknown metric
    code never matches a CSV column so the metric is simply absent from analysis;
    a bad direction scores every attempt backwards; a norm_max of 0 makes the
    rescale divide by zero. Save is refused while any of these stand.
    """
    data = PROFICIENCY_BASELINES if baselines is None else baselines
    problems: list[str] = []
    seen_emet: dict[int, str] = {}

    if not data:
        return ["The proficiency table is empty."]

    for abb, metrics in data.items():
        where = str(abb)
        if abb not in EXERCISE_DEFS:
            problems.append(
                f"{where}: not in the exercise catalogue, so no attempt can ever match it"
            )
        if not metrics:
            problems.append(f"{where}: has no metrics, so it can never produce a score")
            continue

        for code, entry in metrics.items():
            tag = f"{where}/{code}"
            if code not in METRIC_CODES:
                problems.append(
                    f"{tag}: unknown metric code - it will never match a simulator column"
                )

            for field in ("mean", "stddev", "prof_raw"):
                value = entry.get(field)
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    problems.append(f"{tag}: {field} is not a number ({value!r})")
                elif math.isnan(float(value)) or math.isinf(float(value)):
                    problems.append(f"{tag}: {field} is not finite")

            stddev = entry.get("stddev")
            if isinstance(stddev, (int, float)) and not isinstance(stddev, bool) and stddev < 0:
                problems.append(f"{tag}: stddev is negative ({stddev})")

            direction = entry.get("direction")
            if direction not in VALID_DIRECTIONS:
                problems.append(
                    f"{tag}: direction must be one of {', '.join(VALID_DIRECTIONS)}, "
                    f"not {direction!r} - every attempt would score backwards"
                )

            norm_max = entry.get("norm_max")
            if not isinstance(norm_max, (int, float)) or isinstance(norm_max, bool):
                problems.append(f"{tag}: norm_max is not a number ({norm_max!r})")
            elif norm_max <= 0:
                problems.append(f"{tag}: norm_max must be greater than 0, not {norm_max}")

            best = entry.get("best_multiplier")
            worst = entry.get("worst_multiplier")
            for field, value in (("best_multiplier", best), ("worst_multiplier", worst)):
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    problems.append(f"{tag}: {field} is not a number ({value!r})")
            if (
                isinstance(best, (int, float)) and isinstance(worst, (int, float))
                and not isinstance(best, bool) and not isinstance(worst, bool)
                and best == worst
            ):
                problems.append(
                    f"{tag}: best_multiplier and worst_multiplier are both {best}, "
                    f"which collapses the scoring range"
                )

            eid = entry.get("emet_id_RSAC_2026")
            if not isinstance(eid, int) or isinstance(eid, bool):
                problems.append(
                    f"{tag}: emet_id_RSAC_2026 is missing or not an integer ({eid!r}) - "
                    f"the simulator XML export needs it"
                )
            else:
                if eid in seen_emet:
                    problems.append(
                        f"{tag}: emet_id_RSAC_2026 {eid} is already used by "
                        f"{seen_emet[eid]}; ids must be unique"
                    )
                else:
                    seen_emet[eid] = tag

    return problems


def load_defaults() -> dict:
    """The pristine baseline. Returns {} if the file is missing or unreadable.

    An empty result is not fatal - the app runs off PROFICIENCY_BASELINES - but it
    does mean reverting is unavailable, which the editor shows rather than offering
    a reset that would silently do nothing.
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
    return normalize_baselines(data)


BASELINES_DEFAULTS: dict = load_defaults()


def revert_to_defaults() -> dict:
    """A fresh copy of the baseline values, for the editor. Never the live object."""
    return normalize_baselines(BASELINES_DEFAULTS)


def changed_from_defaults(baselines: dict | None = None) -> dict[str, list[str]]:
    """Which metrics differ from the snapshot, keyed by exercise.

    Returns {} when there is no snapshot, so a missing file reads as "nothing to
    compare" rather than "everything changed".
    """
    if not BASELINES_DEFAULTS:
        return {}
    current = normalize_baselines(
        PROFICIENCY_BASELINES if baselines is None else baselines
    )
    out: dict[str, list[str]] = {}
    for abb in set(current) | set(BASELINES_DEFAULTS):
        base = BASELINES_DEFAULTS.get(abb) or {}
        live = current.get(abb) or {}
        changed = [c for c in set(base) | set(live) if base.get(c) != live.get(c)]
        if changed:
            out[abb] = sorted(changed)
    return out


def write_defaults_file(baselines: dict | None = None, force: bool = False) -> str:
    """Create the snapshot from `baselines` (default: the live table).

    Refuses to overwrite an existing file unless `force`, because that would
    enshrine already-edited values as the thing to revert to and destroy the only
    copy of the originals. A one-off at packaging time, not a UI action.
    """
    import json
    import os

    path = defaults_path()
    if os.path.exists(path) and not force:
        raise FileExistsError(
            f"{path} already exists. Overwriting it would make the current "
            f"(possibly edited) values the new baseline. Pass force=True only if "
            f"that is intended."
        )

    payload = normalize_baselines(
        PROFICIENCY_BASELINES if baselines is None else baselines
    )
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)
    return path


# ---------------------------------------------------------------------------
#  Writing the baselines back into this file
# ---------------------------------------------------------------------------

_BASELINES_BEGIN = (
    "# --- BEGIN PROFICIENCY_BASELINES "
    "(rewritten by Settings > Exercises > Proficiency Values) ---"
)
_BASELINES_DECL = (
    "PROFICIENCY_BASELINES: dict[str, dict[str, dict[str, float | int | str]]] = {"
)
_BASELINES_END = "# --- END PROFICIENCY_BASELINES ---"


def _format_number(value) -> str:
    """Render a number without changing it: ints stay ints, floats keep precision."""
    if isinstance(value, bool):
        return repr(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value == int(value) and abs(value) < 1e15:
            return f"{value:.2f}"
        return repr(value)
    return repr(value)


def format_baselines_source(baselines: dict) -> str:
    """Render `baselines` as the marker-delimited source block, one metric per line."""
    import json

    normalized = normalize_baselines(baselines)
    lines = [_BASELINES_BEGIN, _BASELINES_DECL]
    exercises = list(normalized.items())
    for ex_i, (abb, metrics) in enumerate(exercises):
        lines.append(f"    {json.dumps(abb)}: {{")
        items = list(metrics.items())
        for m_i, (code, entry) in enumerate(items):
            parts = []
            for field, value in entry.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    parts.append(f"{json.dumps(field)}: {_format_number(value)}")
                else:
                    parts.append(f"{json.dumps(field)}: {json.dumps(value)}")
            comma = "," if m_i < len(items) - 1 else ""
            lines.append(f"        {json.dumps(code)}: {{{', '.join(parts)}}}{comma}")
        lines.append("    }" + ("," if ex_i < len(exercises) - 1 else ""))
    lines.append("}")
    lines.append(_BASELINES_END)
    return "\n".join(lines)


def _verify_baselines_source(source: str, expected: dict, path: str) -> None:
    """Parse the about-to-be-written source and confirm it round-trips `expected`."""
    try:
        compile(source, path, "exec")
    except SyntaxError as e:
        raise RuntimeError(f"Generated proficiency table is not valid Python: {e}") from e

    start = source.find(_BASELINES_DECL)
    end = source.find(_BASELINES_END)
    if start < 0 or end < 0:
        raise RuntimeError(
            "Generated source lost the PROFICIENCY_BASELINES declaration or END marker."
        )

    namespace: dict = {}
    try:
        exec(compile(source[start:end], path, "exec"), namespace)
    except Exception as e:
        raise RuntimeError(f"Generated proficiency table does not evaluate: {e}") from e

    written = namespace.get("PROFICIENCY_BASELINES")
    if written != expected:
        raise RuntimeError(
            "Generated proficiency table does not match the values it was built from; "
            "refusing to write."
        )


def save_baselines(baselines: dict) -> str:
    """Rewrite the PROFICIENCY_BASELINES block in this file. Returns the path.

    The candidate is validated, rendered, re-parsed and compared against what it was
    built from *before* it replaces anything, and the write itself is atomic. A bug
    in the editor can therefore fail the save but cannot leave a corrupt or truncated
    table on disk - which, for a file imported at startup, would be unrecoverable
    without git.

    PROFICIENCY_BASELINES is updated **in place**, because other modules hold this
    exact object via `from exercise_proficiency_scores import PROFICIENCY_BASELINES`;
    rebinding would leave them on the old values. The derived floor/ceiling tables
    are refreshed for the same reason.
    """
    import os

    path = os.path.abspath(__file__)
    if not path.endswith(".py"):
        raise RuntimeError(
            f"Cannot edit the proficiency table: {path} is not editable Python source. "
            f"This happens in a frozen/bundled build."
        )

    prepared = normalize_baselines(baselines)
    if not prepared:
        raise ValueError("Refusing to save an empty proficiency table.")

    problems = check_baselines_consistency(prepared)
    if problems:
        raise ValueError(
            "The proficiency table has unresolved problems:\n  - "
            + "\n  - ".join(problems)
        )

    with open(path, "r", encoding="utf-8") as f:
        original = f.read()

    start = original.find(_BASELINES_BEGIN)
    end = original.find(_BASELINES_END)
    if start < 0 or end < 0 or end < start:
        raise RuntimeError(
            f"Could not find the BEGIN/END PROFICIENCY_BASELINES markers in {path}. "
            f"Refusing to guess where the table starts."
        )

    updated = (
        original[:start]
        + format_baselines_source(prepared)
        + original[end + len(_BASELINES_END):]
    )

    _verify_baselines_source(updated, prepared, path)

    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(updated)
    os.replace(tmp, path)

    # Mutate in place - other modules hold this exact object - then rebuild
    # everything derived from it.
    PROFICIENCY_BASELINES.clear()
    PROFICIENCY_BASELINES.update(prepared)
    refresh_derived_tables()

    return path


def calc_score(
    raw,
    mean,
    sd,
    prof=None,
    direction="lower",
    best_multiplier=-3,
    worst_multiplier=5,
    proficiency=None,
    metric_code=None,
):
    if prof is None:
        prof = proficiency

    if metric_code == "pts":
        score = 100 * raw / 31
        return round(max(0, min(200, score)), 2)

    if metric_code == "mtg":
        best = max(0, math.floor(mean + best_multiplier * sd))
        worst = math.ceil(mean + worst_multiplier * sd)
    else:
        best = max(0, mean + best_multiplier * sd)
        if metric_code in {"drp", "ico"}:
            worst = math.ceil(mean + worst_multiplier * sd)
        else:
            worst = mean + worst_multiplier * sd

    if direction == "lower":
        if math.isclose(best, prof, abs_tol=1e-12) and math.isclose(prof, worst, abs_tol=1e-12):
            return 200.0 if raw <= prof else 0.0

        if metric_code == "drp" and math.isclose(best, prof, abs_tol=1e-12):
            if raw <= prof:
                return 200.0
            score = 100 - 100 * (raw - prof) / (worst - prof)
            return round(max(0, min(200, score)), 2)

        if math.isclose(best, prof, abs_tol=1e-12):
            return 200.0 if raw <= prof else 0.0

        if math.isclose(prof, worst, abs_tol=1e-12):
            return 200.0 if raw < prof else 100.0

        if raw <= prof:
            score = 200 - 100 * (raw - best) / (prof - best)
        else:
            score = 100 - 100 * (raw - prof) / (worst - prof)

    else:
        if math.isclose(best, prof, abs_tol=1e-12) and math.isclose(prof, worst, abs_tol=1e-12):
            return 200.0 if raw >= prof else 0.0
        if math.isclose(best, prof, abs_tol=1e-12):
            return 200.0 if raw >= prof else 0.0
        if math.isclose(prof, worst, abs_tol=1e-12):
            return 200.0 if raw > prof else 100.0

        if raw >= prof:
            score = 200 - 100 * (best - raw) / (best - prof)
        else:
            score = 100 - 100 * (prof - raw) / (prof - worst)

    return round(max(0, min(200, score)), 2)


def normalize_metric_code(raw_metric_name: str) -> str | None:
    name = raw_metric_name.strip()

    if name == "mwrp_score_pre_raw":
        return "mwr"

    if not name.endswith("_score_raw"):
        return None

    base = name[:-10]  # remove _score_raw

    # Explicit normalization for Master Workspace Range coming from CSV
    if base.startswith("mwrp"):
        return "mwr"

    # Standard case: ttc_score_raw -> ttc
    return base


def build_exercise_name_map() -> dict[str, str]:
    return {
        values["exerc_full"]: key
        for key, values in EXERCISE_DEFS.items()
        if isinstance(values, dict) and "exerc_full" in values
    }


def iter_csv_files(csv_clean_dir: Path):
    for path in sorted(csv_clean_dir.glob("*.csv")):
        if path.is_file():
            yield path


def compare_scores(base_dir: Path) -> tuple[int, int, int]:
    csv_clean_dir = base_dir / "csv_clean"
    output_path = base_dir / "200_scores_check.csv"
    no_matches_path = base_dir / "200_scores_check_NO_Matches.csv"

    if not csv_clean_dir.exists() or not csv_clean_dir.is_dir():
        raise FileNotFoundError(f'Folder not found: {csv_clean_dir}')

    exercise_name_map = build_exercise_name_map()

    yes_count = 0
    no_count = 0
    checked_count = 0

    header = [
        "exercise_full",
        "exercise_abbreviation",
        "metric_raw_name",
        "raw_value",
        "calculated_score",
        "real_score_200",
        "match",
    ]

    with output_path.open("w", newline="", encoding="utf-8-sig") as f_out:
        writer = csv.writer(f_out)
        writer.writerow(header)

        for csv_path in iter_csv_files(csv_clean_dir):
            with csv_path.open("r", newline="", encoding="utf-8-sig") as f_in:
                reader = csv.reader(f_in)

                for row_number, row in enumerate(reader, start=1):
                    if len(row) < 4:
                        continue

                    exercise_full = row[2].strip()
                    exercise_abbr = exercise_name_map.get(exercise_full)

                    if not exercise_abbr:
                        continue

                    baselines = PROFICIENCY_BASELINES.get(exercise_abbr)
                    if not baselines:
                        continue

                    i = 4
                    while i < len(row) - 1:
                        field_name = row[i].strip()
                        metric_code = normalize_metric_code(field_name)

                        if metric_code is None:
                            i += 1
                            continue

                        if i + 3 >= len(row):
                            break

                        try:
                            raw_value = float(row[i + 1].strip())
                        except ValueError:
                            i += 2
                            continue

                        score_name = row[i + 2].strip()
                        score_value_str = row[i + 3].strip()

                        if field_name == "mwrp_score_pre_raw":
                            expected_score_name = "mwrp_score_pre_200"
                        else:
                            expected_score_name = field_name.replace("_score_raw", "_score_200")

                        if score_name != expected_score_name:
                            i += 1
                            continue

                        try:
                            real_score = float(score_value_str)
                        except ValueError:
                            i += 4
                            continue

                        metric_baseline = baselines.get(metric_code)
                        if metric_baseline is None:
                            i += 4
                            continue

                        calculated_score = calc_score(
                            raw=raw_value,
                            mean=float(metric_baseline["mean"]),
                            sd=float(metric_baseline["stddev"]),
                            proficiency=float(metric_baseline["prof_raw"]),
                            direction=str(metric_baseline["direction"]),
                            best_multiplier=float(metric_baseline.get("best_multiplier", -3)),
                            worst_multiplier=float(metric_baseline.get("worst_multiplier", 5)),
                            metric_code=metric_code,
                        )

                        if field_name == "mwrp_score_pre_raw":
                            # The CSV holds this metric on the simulator's scale,
                            # so bring our canonical score back onto it before
                            # comparing. Was a hardcoded /5.
                            calculated_score = round(
                                canonical_to_simulator(calculated_score, exercise_abbr, metric_code), 2
                            )

                        is_match = abs(calculated_score - real_score) <= 0.5
                        match_text = "YES" if is_match else "NO"

                        checked_count += 1
                        if is_match:
                            yes_count += 1
                        else:
                            no_count += 1

                        writer.writerow([
                            exercise_full,
                            exercise_abbr,
                            field_name,
                            f"{raw_value:.2f}",
                            f"{calculated_score:.2f}",
                            f"{real_score:.2f}",
                            match_text,
                        ])

                        i += 4

        writer.writerow([])
        writer.writerow(["TOTAL_CHECKED", checked_count])
        writer.writerow(["YES", yes_count])
        writer.writerow(["NO", no_count])

    with output_path.open("r", newline="", encoding="utf-8-sig") as f_in, no_matches_path.open("w", newline="", encoding="utf-8-sig") as f_out:
        reader = csv.reader(f_in)
        writer = csv.writer(f_out)
        header_row = next(reader, None)
        if header_row:
            writer.writerow(header_row)
        for row in reader:
            if row and row[-1].strip().upper() == "NO":
                writer.writerow(row)

    return checked_count, yes_count, no_count


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    try:
        checked_count, yes_count, no_count = compare_scores(base_dir)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Done. Checked: {checked_count} | YES: {yes_count} | NO: {no_count}")
    print(f"Output files: {base_dir / '200_scores_check.csv'} and {base_dir / '200_scores_check_NO_Matches.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
