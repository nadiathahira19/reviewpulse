"""Sentiment analysis. The real IndoBERT model is added later; for now there is a simple fake."""

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol


@dataclass(frozen=True)
class SentimentResult:
    label: str
    score: float


class SentimentAnalyzer(Protocol):
    model_version: str

    def analyze(self, texts: list[str]) -> list[SentimentResult]: ...


POSITIVE_WORDS = {"bagus", "suka", "cocok", "mantap", "recommended"}
NEGATIVE_WORDS = {"jelek", "kecewa", "iritasi", "rusak", "buruk"}


class FakeAnalyzer:
    """Keyword based stand-in. It is NOT a real model and only exists to build the API around."""

    model_version: str = "fake-keyword-v0"

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        return [self._analyze_one(text) for text in texts]

    @staticmethod
    def _analyze_one(text: str) -> SentimentResult:
        words = set(re.findall(r"\w+", text.lower()))
        positive = len(words & POSITIVE_WORDS)
        negative = len(words & NEGATIVE_WORDS)
        if positive > negative:
            return SentimentResult(label="positive", score=0.9)
        if negative > positive:
            return SentimentResult(label="negative", score=0.9)
        return SentimentResult(label="neutral", score=0.5)


@lru_cache
def get_analyzer() -> SentimentAnalyzer:
    """Return one analyzer per process. In PR 12b this loads the real model once."""
    return FakeAnalyzer()
