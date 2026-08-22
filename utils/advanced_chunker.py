import re
from typing import List


def sentence_split(text: str) -> List[str]:
    # naive sentence splitter using punctuation
    if not text:
        return []
    # normalize whitespace
    text = re.sub(r"\s+", " ", text.strip())
    # split on sentence enders followed by space and capital (approx)
    parts = re.split(r'(?<=[.!?；。！？])\s+', text)
    return [p.strip() for p in parts if p.strip()]


def chunk_by_sentences(text: str, max_chars: int = 800, overlap_chars: int = 100) -> List[str]:
    sentences = sentence_split(text)
    chunks = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) + 1 <= max_chars or not cur:
            if cur:
                cur += " " + s
            else:
                cur = s
        else:
            chunks.append(cur)
            # start next with overlap last characters
            if overlap_chars > 0:
                tail = cur[-overlap_chars:]
                cur = tail + " " + s
            else:
                cur = s

    if cur:
        chunks.append(cur)

    return chunks
