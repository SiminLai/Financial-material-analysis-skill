"""Safe release preparation script.

This script performs a dry-run listing of candidate files and folders
that are safe to remove from the repository prior to publishing to
GitHub. Run with `--apply` to actually delete them (USE WITH CAUTION).

By default the script runs in dry-run mode and prints suggested removals.
"""
import argparse
from pathlib import Path
import shutil
import json


ROOT = Path(__file__).resolve().parents[1]


DEFAULT_CANDIDATES = [
    "workspace/cache",
    "workspace/evidence",
    "workspace/experiences",
    "workspace/traces",
    "workspace/vectors",
    "workspace/lessons",
    "workspace/traces",
    "workspace/memories.json",
    "__pycache__",
    "*.pyc",
    ".pytest_cache",
    "node_modules",
]


def find_candidates(root: Path, candidates):
    found = []
    for p in candidates:
        # handle simple globbing
        for match in root.glob(p):
            found.append(match)
    return found


def main():
    parser = argparse.ArgumentParser(description="Prepare repository for release (dry-run by default).")
    parser.add_argument("--apply", action="store_true", help="Actually delete the candidate files (dangerous).")
    parser.add_argument("--list-only", action="store_true", help="Print JSON list of candidates and exit.")
    args = parser.parse_args()

    candidates = find_candidates(ROOT, DEFAULT_CANDIDATES)

    out = [str(p) for p in candidates]

    if args.list_only:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    print("Found the following candidate files/folders for removal:")
    for p in out:
        print(" -", p)

    if not args.apply:
        print("\nDry-run: no files were deleted. Re-run with --apply to delete after reviewing the list.")
        return

    # Confirm interactive
    confirm = input("Proceed and delete the listed files? Type 'yes' to confirm: ")
    if confirm.strip().lower() != "yes":
        print("Aborting. No files deleted.")
        return

    # Perform deletions
    for p in candidates:
        try:
            if p.is_dir():
                shutil.rmtree(p)
            else:
                p.unlink()
            print(f"Deleted {p}")
        except Exception as e:
            print(f"Failed to delete {p}: {e}")

    print("Cleanup complete.")


if __name__ == "__main__":
    main()
