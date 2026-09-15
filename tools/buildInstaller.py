r"""Build the Windows installer: folder bundle, self-test, then Inno Setup.

    .venv\Scripts\python.exe tools\buildInstaller.py

Produces dist\CloakClipSetup-<version>.exe. The version is read from the
application rather than typed into the .iss, so the installer, the About box
and the wheel cannot disagree about what this is - a person keeping three
files in step is the one thing here that is certain to drift.

Needs Inno Setup 6. On a GitHub Windows runner it is already there; locally,
winget install JRSoftware.InnoSetup puts it under LOCALAPPDATA rather than in
Program Files, so both are looked for.

Leaves dist\CloakClip.exe alone, so it can run after tools\buildStandalone.py
and both downloads end up side by side in dist\.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

projectRoot = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(projectRoot / "src"))

specFile = projectRoot / "cloakClip.spec"
scriptFile = projectRoot / "installer" / "cloakClip.iss"
bundleDir = projectRoot / "dist" / "CloakClip"
bundleExe = bundleDir / "CloakClip.exe"
outputDir = projectRoot / "dist"
buildTimeoutSeconds = 900.0
selfTestTimeoutSeconds = 120.0

compilerCandidates = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
    Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
]


def findCompiler() -> Path | None:
    for candidate in compilerCandidates:
        if candidate.name and candidate.is_file():
            return candidate
    return None


def appVersion() -> str:
    # appConfig is Qt-free, so reading the version does not drag PySide6 in.
    from cloakClip import appConfig

    return appConfig.appVersion


def run(command: list[str], environment: dict[str, str] | None = None) -> int:
    print(f"$ {subprocess.list2cmdline(command)}")
    completed = subprocess.run(
        command, cwd=projectRoot, env=environment, timeout=buildTimeoutSeconds
    )
    return completed.returncode


def buildBundle() -> int:
    # The installer packages the folder bundle, never the one-file exe: an
    # installed application should not unpack itself on every launch.
    environment = dict(os.environ, CLOAKCLIP_ONEDIR="1")
    command = [sys.executable, "-m", "PyInstaller", str(specFile), "--noconfirm"]
    return run(command, environment)


def selfTestBundle() -> str | None:
    """Run the bundle's own --selftest; return the version it reports.

    The folder bundle lays out its files differently from the one-file exe
    that CI already self-tests, so the winrt bindings and the icon have to be
    proven present here too - an installer is the worst place to find out.
    """
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "selftest.txt"
        completed = subprocess.run(
            [str(bundleExe), "--selftest", str(report)],
            timeout=selfTestTimeoutSeconds,
        )
        if not report.is_file():
            print(f"\n{bundleExe} wrote no self-test report.")
            return None
        text = report.read_text(encoding="utf-8")
    print(text)
    if completed.returncode != 0:
        print(f"\nThe bundle failed its self-test (code {completed.returncode}).")
        return None
    for line in text.splitlines():
        if line.startswith("version="):
            return line.partition("=")[2]
    print("\nThe self-test report carries no version line.")
    return None


def main() -> int:
    if sys.platform != "win32":
        print("The installer is a Windows artifact; nothing to do here.")
        return 0

    compiler = findCompiler()
    if compiler is None:
        print("Inno Setup 6 was not found. Looked in:")
        for candidate in compilerCandidates:
            print(f"  {candidate}")
        print("\nInstall it with:  winget install JRSoftware.InnoSetup")
        return 1

    buildCode = buildBundle()
    if buildCode != 0:
        print(f"\nPyInstaller failed with code {buildCode}.")
        return buildCode
    if not bundleExe.is_file():
        print(f"\nPyInstaller reported success but {bundleDir} holds no exe.")
        return 1

    version = appVersion()
    bundledVersion = selfTestBundle()
    if bundledVersion is None:
        return 1
    if bundledVersion != version:
        print(f"\nThe bundle reports {bundledVersion} but appConfig says {version}.")
        return 1

    compileCode = run([str(compiler), f"/DAppVersion={version}", str(scriptFile)])
    if compileCode != 0:
        print(f"\nInno Setup failed with code {compileCode}.")
        return compileCode

    installer = outputDir / f"CloakClipSetup-{version}.exe"
    if not installer.is_file():
        print(f"\nInno Setup reported success but {installer} is not there.")
        return 1
    print(f"\nInstaller: {installer}")
    print(f"Size     : {installer.stat().st_size / 1_000_000:.0f} MB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
