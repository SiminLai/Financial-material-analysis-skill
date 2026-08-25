import re
from typing import Dict, List, Tuple


PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*page\s+\d+\s+of\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*page\s+\d+\s*$", re.IGNORECASE),
    re.compile(r"^\s*第\s*\d+\s*页\s*$", re.IGNORECASE),
]


FINANCIAL_KEYWORDS = [
    "consolidated",
    "balance sheet",
    "balance sheets",
    "statements of operations",
    "statement of operations",
    "income statement",
    "cash flow",
    "fiscal year",
    "revenue",
    "net profit",
    "净利润",
    "营业收入",
    "资产负债",
    "现金流",
    "利润表",
    "单位",
    "in millions",
    "in thousands",
]


YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")
AMOUNT_OR_UNIT_PATTERN = re.compile(
    r"(\$|¥|￥|usd|rmb|万元|亿元|million|billion|thousand|元|%|eps)",
    re.IGNORECASE,
)


def _normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _contains_financial_signal(text: str) -> bool:
    t = (text or "").lower()
    if any(k in t for k in FINANCIAL_KEYWORDS):
        return True
    if YEAR_PATTERN.search(t):
        return True
    if AMOUNT_OR_UNIT_PATTERN.search(t):
        return True
    return False


def _is_page_number_line(text: str) -> bool:
    line = _normalize_line(text)
    if not line:
        return False
    return any(p.match(line) for p in PAGE_NUMBER_PATTERNS)


def _is_short_repeated_candidate(text: str) -> bool:
    line = _normalize_line(text)
    if not line:
        return False
    # Typical header/footer lines are short and stable across pages.
    return len(line) <= 80


def _collect_repeated_short_lines(page_blocks: List[List[Dict]], threshold_ratio: float = 0.5) -> set:
    page_count = max(1, len(page_blocks))
    page_presence = {}

    for blocks in page_blocks:
        seen_this_page = set()
        for b in blocks:
            text = _normalize_line(b.get("text", ""))
            if not _is_short_repeated_candidate(text):
                continue
            if _contains_financial_signal(text):
                continue
            seen_this_page.add(text.lower())
        for t in seen_this_page:
            page_presence[t] = page_presence.get(t, 0) + 1

    repeated = set()
    for line, seen_pages in page_presence.items():
        if (seen_pages / page_count) > threshold_ratio:
            repeated.add(line)
    return repeated


def _join_page_blocks(blocks: List[Dict]) -> str:
    out = []
    for b in blocks:
        text = (b.get("text") or "").strip()
        if text:
            out.append(text)
    return "\n".join(out)


def clean_layout_blocks(
    page_blocks: List[List[Dict]],
    top_ratio: float = 0.08,
    bottom_ratio: float = 0.08,
) -> Tuple[str, Dict]:
    """Filter noisy header/footer-like text while preserving finance/table signals.

    Args:
        page_blocks: list of page block lists. Block schema:
          {
            "page": int,
            "text": str,
            "bbox": (x0, y0, x1, y1),
            "page_height": float,
            "is_table_region": bool,
          }
    """
    repeated_short_lines = _collect_repeated_short_lines(page_blocks, threshold_ratio=0.5)
    kept_pages = []
    removed_blocks = 0

    for blocks in page_blocks:
        kept_blocks = []
        for b in blocks:
            text = _normalize_line(b.get("text", ""))
            if not text:
                continue

            if b.get("is_table_region"):
                kept_blocks.append({**b, "text": text})
                continue

            if _is_page_number_line(text):
                removed_blocks += 1
                continue

            page_height = float(b.get("page_height") or 0.0)
            bbox = b.get("bbox") or (0.0, 0.0, 0.0, 0.0)
            y0 = float(bbox[1]) if len(bbox) > 1 else 0.0
            y1 = float(bbox[3]) if len(bbox) > 3 else 0.0

            near_top = page_height > 0 and y0 <= (page_height * top_ratio)
            near_bottom = page_height > 0 and y1 >= (page_height * (1.0 - bottom_ratio))
            in_margin_area = near_top or near_bottom

            if in_margin_area and text.lower() in repeated_short_lines and not _contains_financial_signal(text):
                removed_blocks += 1
                continue

            if in_margin_area and not _contains_financial_signal(text) and len(text) <= 30:
                removed_blocks += 1
                continue

            kept_blocks.append({**b, "text": text})

        kept_pages.append(kept_blocks)

    cleaned_pages = []
    for page_index, blocks in enumerate(kept_pages, start=1):
        page_text = _join_page_blocks(blocks)
        if page_text:
            cleaned_pages.append(f"--- Page {page_index} ---\n{page_text}")

    cleaned_text = "\n\n".join(cleaned_pages).strip()
    stats = {
        "removed_blocks_count": removed_blocks,
        "repeated_short_lines_count": len(repeated_short_lines),
    }
    return cleaned_text, stats
