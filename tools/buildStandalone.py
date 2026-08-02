"""Build the standalone CloakClip app from cloakClip.spec.

    .venv\\Scripts\\python.exe tools\\buildStandalone.py

Output: dist\\CloakClip.exe on Windows, dist/CloakClip.app on macOS.
The same spec is used by the GitHub Actions build, so a local build and a
CI build produce the same thing.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
specFile = projectRoot / "cloakClip.spec"
distDir = projectRoot / "dist"
buildDir = projectRoot / "build"


def builtPath() -> Path:
    if sys.platform == "darwin":
        return distDir / "CloakClip.app"
    return distDir / "CloakClip.exe"


def folderSizeMb(path: Path) -> float:
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def main() -> int:
    if not specFile.exists():
        print(f"Missing {specFile}", file=sys.stderr)
        return 1

    if importlib.util.find_spec("PyInstaller") is None:
        print(
            "PyInstaller is not installed in this environment.\n"
            'Install the build tools:  python -m pip install -e ".[dev,build]"',
            file=sys.stderr,
        )
        return 1

    for folder in (buildDir, distDir):
        if folder.exists():
            shutil.rmtree(folder, ignore_errors=True)

    print("Building — this takes a couple of minutes ...")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", str(specFile), "--noconfirm", "--clean"],
        cwd=str(projectRoot),
    )
    if result.returncode != 0:
        print("PyInstaller failed.", file=sys.stderr)
        return result.returncode

    output = builtPath()
    if not output.exists():
        print(f"Build reported success but {output} is missing.", file=sys.stderr)
        return 1

    print(f"\nBuilt {output} ({folderSizeMb(output):.1f} MB)")
    print("Copy it anywhere and run it — no Python or venv needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
