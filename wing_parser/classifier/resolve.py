"""Resolution order: cache, then patterns, then the optional model.

Holding the cache in memory and flushing once keeps a parse from writing
to disk 40 times. Names that stay unresolved are collected rather than
discarded, so the report can say "these need better names" instead of
silently skipping them.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.classifier import cache, llm, matcher
from wing_parser.classifier.matcher import UNKNOWN, Classification
from wing_parser.classifier.normalize import clean


class Classifier:
    def __init__(self, directory: Path | None = None, use_llm: bool = True) -> None:
        self._directory = directory
        self._use_llm = use_llm
        self._memo: dict[tuple[str, str], Classification] = {}
        self._pending: list[tuple[str, str, Classification]] = []
        self._unresolved: list[str] = []
        self._low: list[str] = []
        # Loaded on first use, not here: WingScene builds a Classifier
        # unconditionally, and a scene nobody asks about types for should
        # not touch the disk at all.
        self._disk: dict[str, dict[str, Classification]] | None = None

    def _cached(self, name: str, domain: str) -> Classification | None:
        """One read of the knowledge file per Classifier, not per name.

        cache.lookup() re-reads and re-parses the whole file on every
        call, and since Task 15 that parse is a ruamel round-trip that
        rebuilds the comment tree. Measured on a 200-entry cache: 50
        per-name lookups took 3.4 s, one load plus 50 in-memory lookups
        took 65 ms. The file is designed to grow one entry per name ever
        seen, so the per-name version gets slower exactly as ToanAZ uses
        the tool more -- 17 s at a thousand entries.
        """
        if self._disk is None:
            self._disk = cache.load(self._directory)
        return self._disk.get(domain, {}).get(clean(name))

    def resolve(self, name: str, domain: str) -> Classification:
        target = clean(name)
        # An unnamed channel is an empty slot, not a naming problem. Without
        # this, all six blank channels in the real file would land in
        # `unresolved` as an empty string, and the first one would spend a
        # model call asking what "" is.
        if not target:
            return UNKNOWN

        key = (domain, target)
        if key in self._memo:
            return self._memo[key]

        result = self._first_answer(name, domain)
        self._memo[key] = result

        if result.confidence == 0.0:
            self._unresolved.append(name)
        elif not matcher.is_confident(result):
            self._low.append(name)

        return result

    def _first_answer(self, name: str, domain: str) -> Classification:
        cached = self._cached(name, domain)
        if cached is not None:
            return cached

        found = matcher.classify(name, domain)
        if matcher.is_confident(found):
            return found

        if self._use_llm and llm.available():
            guessed = llm.classify(name, domain)
            if guessed is not None:
                self._pending.append((name, domain, guessed))
                return guessed

        # A weak pattern hit still beats nothing: `found` is already UNKNOWN
        # when nothing matched, so returning it covers both cases.
        return found

    def flush(self) -> None:
        for name, domain, result in self._pending:
            cache.remember(name, domain, result, directory=self._directory)
        self._pending.clear()
        # The in-memory copy is now behind the file. Drop it rather than
        # patch it, so the next read is honest.
        self._disk = None

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(self._unresolved)

    @property
    def low_confidence(self) -> tuple[str, ...]:
        return tuple(self._low)
