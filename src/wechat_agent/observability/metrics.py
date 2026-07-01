from __future__ import annotations

from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self._counter: Counter[str] = Counter()

    def increment(self, name: str, amount: int = 1) -> None:
        self._counter[name] += amount

    def get(self, name: str) -> int:
        return self._counter[name]
