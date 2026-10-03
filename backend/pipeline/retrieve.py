"""Passage index + BM25 retrieval over the corpus.

The answer key is organized as a jurisdiction x category grid, so extraction asks
one question per cell ("what does the law say about security deposits in
Boston?"). This module finds the passages that can answer it. BM25 suits legal
text: exact terms and section numbers ("1947.12", "37.9") matter more than
semantic similarity, and it needs no embedding service.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

from .extract import Doc

WINDOW = 1600
STEP = 1100
TOKEN = re.compile(r"\d+(?:[.:-]\d+)*[a-z]?|[a-z]+", re.I)
STOP = set("the of and or to a in for on by any be is as that this with an at are from such shall may not "
           "which it its if than other who has have was were".split())


@dataclass
class Passage:
    pid: str
    doc: Doc
    start: int
    end: int
    text: str


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text) if t.lower() not in STOP and len(t) > 1]


def _is_boilerplate(window: str) -> bool:
    lines = [ln for ln in window.splitlines() if ln.strip()]
    if not lines:
        return True
    # Site navigation menus are many short lines; judge by characters so a page
    # whose few long lines carry the statute text is kept.
    short_chars = sum(len(ln) for ln in lines if len(ln) < 40)
    return short_chars / sum(len(ln) for ln in lines) > 0.85


def build_passages(docs: list[Doc]) -> list[Passage]:
    out = []
    for d in docs:
        body_start = d.text.find("\n\n") + 2 if d.text.startswith("SOURCE:") else 0
        i, n = body_start, 0
        while i < len(d.text):
            end = min(len(d.text), i + WINDOW)
            if end < len(d.text):
                nl = d.text.rfind("\n", i + WINDOW // 2, end)
                end = nl if nl > 0 else end
            chunk = d.text[i:end]
            if not _is_boilerplate(chunk):
                out.append(Passage(f"{d.doc_id}#{n}", d, i, end, chunk))
                n += 1
            if end >= len(d.text):
                break
            i = max(i + 1, end - (WINDOW - STEP))
    return out


class BM25:
    def __init__(self, passages: list[Passage], k1: float = 1.4, b: float = 0.75):
        self.passages = passages
        self.toks = [Counter(tokenize(p.text)) for p in passages]
        self.lens = [sum(t.values()) for t in self.toks]
        self.avg = sum(self.lens) / max(1, len(self.lens))
        df = Counter(term for t in self.toks for term in t)
        n = len(passages)
        self.idf = {term: math.log(1 + (n - c + 0.5) / (c + 0.5)) for term, c in df.items()}
        self.k1, self.b = k1, b

    def score(self, i: int, query: list[str]) -> float:
        t, dl, s = self.toks[i], self.lens[i], 0.0
        for q in query:
            f = t.get(q)
            if f:
                s += self.idf.get(q, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
        return s

    def search(self, query: str, allow, k: int = 10) -> list[tuple[float, Passage]]:
        q = tokenize(query)
        scored = [(self.score(i, q), p) for i, p in enumerate(self.passages) if allow(p)]
        scored = [x for x in scored if x[0] > 0]
        scored.sort(key=lambda x: -x[0])
        return scored[:k]
