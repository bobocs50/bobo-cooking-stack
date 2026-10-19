"""Drill for tests/run_drills.py: a runner that finds no drill must fail, not print ALL
PASSED. Free and offline.

    python tests/run_drills.py
"""

import tempfile
from pathlib import Path

from _drill import expect
from run_drills import main


def drill_empty_glob():
    print("run_drills.main over a directory with no drill_*.py")
    with tempfile.TemporaryDirectory() as tmp:
        code = None
        try:
            main(Path(tmp))
        except SystemExit as exit_:
            code = exit_.code
    return expect(
        "an empty drill directory exits non-zero instead of ALL PASSED (D-047)", code == 1
    )


def main_drill():
    passed = drill_empty_glob()
    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main_drill()
