import ast
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    if sys.version_info < (3, 11):
        print("Use Python 3.11 or newer; Python 3.11 is the proposed baseline.")
        return 1
    failures = []
    for directory in ("runtime", "graph", "providers", "tools", "utils", "validators", "state", "tests", "scripts", "skills", "workflow", "mcp_local"):
        for path in (root / directory).rglob("*.py"):
            try:
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except (SyntaxError, UnicodeError) as error:
                failures.append(str(error))
    try:
        for entry in ("main.py", "server.py"):
            ast.parse((root / entry).read_text(encoding="utf-8"))
    except SyntaxError as error:
        failures.append(str(error))
    versions = {}
    for requirement in (root / "requirements.txt").read_text().splitlines():
        if "==" not in requirement:
            continue
        name, expected = requirement.split("==", 1)
        try:
            versions[name] = importlib.metadata.version(name)
            if versions[name] != expected:
                failures.append(name + ": expected " + expected + ", installed " + versions[name])
        except importlib.metadata.PackageNotFoundError:
            failures.append("Missing dependency: " + name)
    print(json.dumps({"python": sys.version, "platform": platform.platform(), "dependencies": versions, "preflight_failures": failures}, indent=2))
    if failures:
        return 1
    return subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], cwd=root).returncode


if __name__ == "__main__":
    raise SystemExit(main())
