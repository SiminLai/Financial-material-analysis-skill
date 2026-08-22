"""Simple table extractor using PyMuPDF heuristics.

This is a lightweight fallback to detect table-like text blocks without
requiring camelot/tabula. It scans text blocks for rows where many lines
contain multiple whitespace-separated columns and emits tables as lists
of rows. Each cell is returned along with page and (approx) bbox info.
"""
from typing import List, Dict, Any
try:
    import fitz
except Exception:
    fitz = None
import re
from reflection.evidence import Evidence


def extract_tables_from_doc(doc) -> List[Dict[str, Any]]:
    """Given a fitz.Document, return list of table dicts: {page, rows, cells}

    Each `rows` is a list of lists (cells as strings)."""
    tables = []
    if fitz is None or doc is None:
        return tables

    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        # use dict text to preserve blocks
        try:
            d = page.get_text("dict")
        except Exception:
            continue
        blocks = d.get('blocks', [])
        for b in blocks:
            # consider only text blocks
            if b.get('type') != 0:
                continue
            lines = []
            for line in b.get('lines', []):
                spans = [s.get('text', '') for s in line.get('spans', [])]
                line_text = ' '.join(spans).strip()
                if line_text:
                    lines.append(line_text)

            if len(lines) < 2:
                continue

            # heuristic: many lines have multiple columns separated by two+ spaces
            candidate_rows = []
            col_counts = []
            for ln in lines:
                # split on 2+ spaces or pipe-like characters
                cells = re.split(r"\s{2,}|\||\t", ln)
                cells = [c.strip() for c in cells if c.strip()]
                candidate_rows.append(cells)
                col_counts.append(len(cells))

            # require that majority of lines have at least 2 columns
            multi_col = sum(1 for c in col_counts if c >= 2)
            if multi_col / max(1, len(col_counts)) >= 0.5:
                # normalize row lengths by padding
                max_cols = max(col_counts)
                normalized = [row + [""] * (max_cols - len(row)) for row in candidate_rows]
                tables.append({
                    'page': page_num + 1,
                    'rows': normalized,
                    'bbox': b.get('bbox')
                })

    return tables


def extract_evidence_from_tables(tables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert tables to Evidence dicts for ingestion. Returns list of dicts.
    """
    evs = []
    for t in tables:
        page = t.get('page')
        rows = t.get('rows', [])
        bbox = t.get('bbox')
        for r_idx, row in enumerate(rows):
            for c_idx, cell in enumerate(row):
                if not cell or not cell.strip():
                    continue
                e = Evidence(
                    id=f"table_p{page}_r{r_idx}_c{c_idx}",
                    content=cell.strip(),
                    source='table',
                    page=page,
                    bbox={'x0': bbox[0], 'y0': bbox[1], 'x1': bbox[2], 'y1': bbox[3]} if bbox else None,
                    row=r_idx,
                    col=c_idx,
                    confidence=0.9,
                    meta={'origin': 'pymupdf_table_extractor'}
                )
                evs.append(e.to_dict())
    return evs
