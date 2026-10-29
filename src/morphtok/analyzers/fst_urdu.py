"""Stub wrapper for an external finite-state Urdu analyzer.

No Urdu FST resource has been supplied or verified for this project. This module
provides only the plumbing to call an external lookup command once one is
configured; it contains no Urdu morphology.

TODO(resource): identify a concrete Urdu analyzer, verify its licence, version and
output format against its primary documentation, and implement ``parse_output``.
TODO(science): define how the analyzer's analyses map to *segmentation* boundaries
(many FSTs output lemma+tags, not surface boundaries); this mapping is itself a
measurement decision that must be documented before Gate 2.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Sequence

from morphtok.analyzers.base import Analysis, Analyzer, AnalyzerNotConfiguredError


class UrduFSTAnalyzer(Analyzer):
    """Calls ``command`` with the word on stdin; parsing is deliberately unimplemented."""

    name = "urdu_fst"

    def __init__(
        self,
        command: Sequence[str] | None = None,
        version: str = "unverified",
        timeout_s: float = 5.0,
    ) -> None:
        self.command = list(command) if command else None
        self.version = version
        self.timeout_s = timeout_s

    @property
    def is_configured(self) -> bool:
        """True only when a command is given and its executable exists."""
        return bool(self.command) and shutil.which(self.command[0]) is not None  # type: ignore[index]

    def analyze(self, word: str) -> list[Analysis]:
        """Run the external analyzer and parse its output."""
        if not self.is_configured or self.command is None:
            raise AnalyzerNotConfiguredError(
                "no Urdu FST analyzer configured (configs/data/urdu.yaml: analyzer.command)"
            )
        proc = subprocess.run(  # noqa: S603 - command comes from local config only
            self.command,
            input=word + "\n",
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=self.timeout_s,
            check=False,
        )
        return self.parse_output(word, proc.stdout)

    def parse_output(self, word: str, stdout: str) -> list[Analysis]:
        """Convert analyzer output to surface boundaries.

        TODO(resource): implement once the output format has been verified.
        """
        raise NotImplementedError(
            "Urdu FST output parsing is unimplemented: the output format has not been "
            f"verified (word={word!r}, {len(stdout)} chars of output)"
        )
