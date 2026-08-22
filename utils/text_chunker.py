from typing import List


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into chunks of approximately `chunk_size` characters with `overlap`.

    This is a simple, robust splitter that operates on whitespace boundaries when possible.
    """
    if not text:
        return []

    text = text.replace("\n", " ")
    words = text.split()
    chunks = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 <= chunk_size or not cur:
            cur.append(w)
            cur_len += len(w) + 1
        else:
            chunks.append(" ".join(cur))
            # start next chunk with overlap words
            if overlap > 0:
                # compute how many words to carry over by approximate char count
                carry = []
                carry_len = 0
                # iterate backwards over cur to collect overlap-sized tail
                for token in reversed(cur):
                    if carry_len + len(token) + 1 > overlap:
                        break
                    carry.insert(0, token)
                    carry_len += len(token) + 1
                cur = carry[:]  # start new chunk with overlap words
                cur_len = carry_len
            else:
                cur = []
                cur_len = 0
            # now add current word to new chunk
            cur.append(w)
            cur_len += len(w) + 1

    if cur:
        chunks.append(" ".join(cur))

    return chunks
