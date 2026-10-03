"""Locate a quoted span inside its source text, tolerant of whitespace and
typographic-quote differences. Shared by extraction (verification) and the API
(evidence highlighting), so it has no LLM dependencies."""

import difflib
import re


def _norm(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def verify_span(span: str, text: str) -> tuple[str | None, float]:
    """Find span in text. Returns (exact source substring, score) or (None, score)."""
    if span and span in text:
        return span, 1.0
    # Map normalized text back to original offsets.
    norm_chars, index = [], []
    prev_space = False
    for i, ch in enumerate(text):
        c = _norm(ch) if not ch.isspace() else " "
        if c == " ":
            if prev_space:
                continue
            prev_space = True
        else:
            prev_space = False
        for cc in c or " ":
            norm_chars.append(cc)
            index.append(i)
    ntext = "".join(norm_chars)
    nspan = _norm(span)
    if len(nspan) < 20:
        return None, 0.0
    pos = ntext.find(nspan)
    if pos >= 0:
        return text[index[pos]: index[pos + len(nspan) - 1] + 1], 1.0
    # Fuzzy: best window by difflib around the longest matching block.
    sm = difflib.SequenceMatcher(None, ntext, nspan, autojunk=False)
    m = sm.find_longest_match(0, len(ntext), 0, len(nspan))
    if m.size < 15:
        return None, 0.0
    start = max(0, m.a - m.b)
    window = ntext[start: start + len(nspan)]
    score = difflib.SequenceMatcher(None, window, nspan, autojunk=False).ratio()
    if score >= 0.9:
        return text[index[start]: index[min(start + len(nspan), len(index)) - 1] + 1], score
    return None, score



def locate_span(span: str, text: str) -> tuple[int, int] | None:
    """Character offsets of the span in text (for highlighting), or None."""
    exact, _ = verify_span(span, text)
    if exact is None:
        return None
    start = text.find(exact)
    return (start, start + len(exact)) if start >= 0 else None
