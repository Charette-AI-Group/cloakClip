"""Skip markers for tests that need a capability the host platform lacks.

Keyed to the capability rather than to sys.platform, so each test starts
running by itself the day a backend provides what it needs — there is no
platform check left behind for someone to remember to remove. Adding
services/platform/macClipboard.py, for instance, un-skips the secret
marking tests without touching this file.
"""

from __future__ import annotations

import pytest

from cloakClip.services import clipboardService, passwordHistoryService

needsPasswordStore = pytest.mark.skipif(
    not passwordHistoryService.dpapiAvailable,
    reason="the password history is encrypted with DPAPI, which only Windows has",
)

needsSecretMarking = pytest.mark.skipif(
    not clipboardService.backend.supportsSecretMarking,
    reason="this platform's clipboard backend cannot mark text as secret",
)
