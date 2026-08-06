"""The version is declared in two places; a release must not ship them apart."""

from __future__ import annotations

import tomllib

import pytest

from cloakClip import appConfig

pyprojectFile = appConfig.projectRoot / "pyproject.toml"


@pytest.mark.skipif(not pyprojectFile.exists(), reason="running from an installed package")
def testAppVersionMatchesPyproject() -> None:
    packaging = tomllib.loads(pyprojectFile.read_text(encoding="utf-8"))

    assert packaging["project"]["version"] == appConfig.appVersion, (
        "appConfig.appVersion and pyproject.toml disagree — the About box would "
        "report a different version from the one released"
    )
