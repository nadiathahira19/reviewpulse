"""Sentiment analysis. A simple fake for tests, and a real transformers model for production."""

import importlib
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

BATCH_SIZE = 16
MAX_LENGTH = 256

# Used when the model only has generic names. This is the mapping given in the
# model card of mdhugol/indonesia-bert-sentiment-classification.
LABEL_NAMES = {"LABEL_0": "positive", "LABEL_1": "neutral", "LABEL_2": "negative"}


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
    """Keyword based stand-in. It is NOT a real model and is used when MODEL_NAME is not set."""

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


class TransformersAnalyzer:  # pragma: no cover
    """Real model from Hugging Face. Needs `pip install -r requirements-ml.txt`.

    transformers and torch are imported here and not at the top of the file, so the
    app and the tests still work without these heavy libraries.
    """

    def __init__(self, model_name: str) -> None:
        transformers = importlib.import_module("transformers")
        self._torch = importlib.import_module("torch")
        self.model_version: str = model_name
        self._tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
        self._model = transformers.AutoModelForSequenceClassification.from_pretrained(model_name)
        self._model.eval()

    def analyze(self, texts: list[str]) -> list[SentimentResult]:
        results: list[SentimentResult] = []
        for start in range(0, len(texts), BATCH_SIZE):
            chunk = texts[start : start + BATCH_SIZE]
            inputs = self._tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            )
            with self._torch.no_grad():
                logits = self._model(**inputs).logits
            probabilities = self._torch.softmax(logits, dim=-1)
            for row in probabilities:
                index = int(row.argmax())
                results.append(SentimentResult(label=self._label(index), score=float(row[index])))
        return results

    def _label(self, index: int) -> str:
        raw = str(self._model.config.id2label[index])
        return LABEL_NAMES.get(raw, raw.lower())


@lru_cache
def get_analyzer() -> SentimentAnalyzer:
    """Return one analyzer per process, so a real model is loaded only once."""
    model_name = os.environ.get("MODEL_NAME")
    if model_name:
        return TransformersAnalyzer(model_name)
    return FakeAnalyzer()
