"""Run every tests/drill_*.py, each in its own process, with the credentials blanked.

    python tests/run_drills.py

Free and offline. The key names are read from .env.example and set to "" in the
child's environment, so a drill that reaches for a credential sees none.
Every drill runs even after one fails, so all failures show; the exit code is
non-zero if any did (AGENTS.md "Gates").

The drills run in parallel, min(8, CPU count) at a time, except the ones named in ALONE
(an end-to-end drill with a start window that a busy machine would starve), which start one
after the other once the pool has finished; PROJECT_DRILL_WORKERS=1 runs them one by one
for debugging. Results are collected and printed in sorted
name order afterwards, so the output does not depend on which drill finished
first. Each drill keeps its files in its own temp directory, so they do not share
state.
"""

import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ALONE = ()


def credential_names():
    names = []
    if not (ROOT / ".env.example").is_file():
        return names
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        names.append(line.split("=", 1)[0].strip())
    return names


def run_drill(drill, env):
    return subprocess.run(
        [sys.executable, str(drill)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def worker_count():
    workers = min(8, os.cpu_count() or 1)
    override = os.environ.get("PROJECT_DRILL_WORKERS", "")
    if override.isdigit() and int(override) >= 1:
        workers = int(override)
    return workers


def main(directory=HERE):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    for name in credential_names():
        env[name] = ""

    drills = sorted(directory.glob("drill_*.py"))
    # An empty glob (a moved directory, a wrong pattern) would otherwise print ALL PASSED.
    if not drills:
        print("FAILED: no drill_*.py found in " + str(directory) + ", nothing was checked")
        raise SystemExit(1)
    with ThreadPoolExecutor(max_workers=worker_count()) as pool:
        futures = {}
        for index in range(len(drills)):
            if drills[index].name not in ALONE:
                futures[index] = pool.submit(run_drill, drills[index], env)
        for index in futures:
            futures[index] = futures[index].result()
    results = []
    for index in range(len(drills)):
        if index in futures:
            results.append(futures[index])
        else:
            results.append(run_drill(drills[index], env))

    failed = []
    for index in range(len(drills)):
        drill = drills[index]
        result = results[index]
        if result.returncode == 0:
            print("ok    " + drill.name)
        else:
            print("FAIL  " + drill.name)
            print(result.stdout)
            print(result.stderr)
            failed.append(drill.name)

    print("")
    if failed:
        print("FAILED: " + ", ".join(failed))
        raise SystemExit(1)
    print("ALL PASSED")


if __name__ == "__main__":
    main()
