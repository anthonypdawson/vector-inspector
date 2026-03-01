#!/usr/bin/env python3
"""
Simple wrapper to allow `pdm run bumpver patch|minor|major`.
Runs the installed `bumpver` executable (must be available in PATH when run
via `pdm run bumpver ...`).

This script:
- reads current version via `bumpver show`
- runs `bumpver test` to compute the new version
- runs `bumpver update ... --set-version NEW` to apply changes

It does NOT commit or tag; you should inspect changes and commit/tag manually.
"""

import re
import shutil
import subprocess
import sys


def run(cmd):
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr)
        raise SystemExit(proc.returncode)
    return proc.stdout.strip()


def find_version(text):
    m = re.search(r"(\d+\.\d+\.\d+)", text)
    return m.group(1) if m else None


def main(argv):
    # simple arg parsing: allow an optional --dry-run flag anywhere
    dry_run = "--dry-run" in argv
    args = [a for a in argv[1:] if a != "--dry-run"]

    if len(args) < 1:
        print("Usage: pdm run bumpver [patch|minor|major] [--dry-run]")
        return 2
    action = args[0]
    if action not in ("patch", "minor", "major"):
        print("Unknown action:", action)
        print("Usage: pdm run bumpver [patch|minor|major] [--dry-run]")
        return 2

    bv = shutil.which("bumpver") or shutil.which("bumpver.EXE")
    if not bv:
        print("bumpver executable not found in PATH. Ensure you run via `pdm run` so the virtualenv is active.")
        return 3

    # get current version
    out = run([bv, "show"])
    old = find_version(out)
    if not old:
        print("Could not determine current version from bumpver show output:")
        print(out)
        return 4
    print("current version:", old)

    # decide flags
    if action == "patch":
        inc_flag = "-p"
    elif action == "minor":
        inc_flag = "-m"
    else:
        inc_flag = "--major"

    # compute new version with test
    out = run([bv, "test", old, "MAJOR.MINOR.PATCH", inc_flag])
    new = find_version(out)
    if not new:
        print("Could not compute new version from bumpver test output:")
        print(out)
        return 5
    print("new version will be:", new)

    update_cmd = [bv, "update", old, "MAJOR.MINOR.PATCH", "--set-version", new]
    if dry_run:
        print("\nCommand to run:")
        print(" ".join(update_cmd))
        print("\nDry run; no files were changed.")
        return 0

    # apply update
    print("Applying update...")
    run(update_cmd)

    print("\nDone. Review changes with `git status` / `git diff` and commit/tag manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
