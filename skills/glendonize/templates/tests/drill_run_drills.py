"""Drill for tests/run_drills.py: a runner that finds no drill must fail, not print ALL
PASSED. Free and offline.

    python tests/run_drills.py
"""

import os
import tempfile
import time
from pathlib import Path

import run_drills
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
        "an empty drill directory exits non-zero instead of ALL PASSED", code == 1
    )


SPAN_DRILL = (
    "import time\n"
    "began = time.time()\n"
    "time.sleep(0.6)\n"
    "with open({log!r}, 'a') as out:\n"
    "    out.write({name!r} + ' ' + str(began) + ' ' + str(time.time()) + chr(10))\n"
)


def drill_alone_runs_after_the_pool():
    print("run_drills.main starts a drill named in ALONE only after the pool has finished")
    ok = True
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        log = folder / "spans.log"
        for name in ("drill_a.py", "drill_b.py", "drill_c_alone.py"):
            text = SPAN_DRILL.format(log=str(log), name=name)
            (folder / name).write_text(text, encoding="utf-8")
        saved = (run_drills.ALONE, run_drills.ROOT, os.environ.get("PROJECT_DRILL_WORKERS"))
        run_drills.ALONE = ("drill_c_alone.py",)
        run_drills.ROOT = folder
        os.environ["PROJECT_DRILL_WORKERS"] = "3"
        (folder / ".env.example").write_text("SOME_KEY=\n", encoding="utf-8")
        code = None
        try:
            try:
                main(folder)
            except SystemExit as exit_:
                code = exit_.code
        finally:
            run_drills.ALONE, run_drills.ROOT = saved[0], saved[1]
            if saved[2] is None:
                os.environ.pop("PROJECT_DRILL_WORKERS", None)
            else:
                os.environ["PROJECT_DRILL_WORKERS"] = saved[2]
        spans = {}
        for line in log.read_text(encoding="utf-8").splitlines():
            name, began, ended = line.split()
            spans[name] = (float(began), float(ended))
        ok &= expect("all three drills ran and the run passed", code is None and len(spans) == 3)
        ok &= expect(
            "the pooled drills overlap each other",
            spans["drill_a.py"][0] < spans["drill_b.py"][1]
            and spans["drill_b.py"][0] < spans["drill_a.py"][1],
        )
        later = max(spans["drill_a.py"][1], spans["drill_b.py"][1])
        ok &= expect(
            "the ALONE drill starts after every pooled drill has ended",
            spans["drill_c_alone.py"][0] >= later,
        )
    return ok


def main_drill():
    passed = drill_empty_glob()
    passed &= drill_alone_runs_after_the_pool()
    print("")
    print("ALL PASSED" if passed else "SOME FAILED")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main_drill()
