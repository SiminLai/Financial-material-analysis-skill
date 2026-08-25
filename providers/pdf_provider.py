import os
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None
try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None
try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None

from providers.base_provider import BaseProvider
from utils.pdf_cleaner import clean_layout_blocks
try:
    from providers.table_extractor import extract_tables_from_doc, extract_evidence_from_tables
except Exception:
    extract_tables_from_doc = None
    extract_evidence_from_tables = None


class PDFProvider(BaseProvider):

    name = "pdf_provider"

    @staticmethod
    def _bbox_overlap(b1, b2) -> bool:
        if not b1 or not b2 or len(b1) < 4 or len(b2) < 4:
            return False
        x0 = max(float(b1[0]), float(b2[0]))
        y0 = max(float(b1[1]), float(b2[1]))
        x1 = min(float(b1[2]), float(b2[2]))
        y1 = min(float(b1[3]), float(b2[3]))
        return x1 > x0 and y1 > y0

    def _extract_layout_blocks(self, page, page_num: int, table_bboxes):
        blocks_out = []
        page_height = float(getattr(page.rect, "height", 0.0) or 0.0)
        try:
            layout = page.get_text("dict")
        except Exception:
            return blocks_out

        for block in layout.get("blocks", []):
            if block.get("type") != 0:
                continue

            spans_as_lines = []
            for line in block.get("lines", []):
                span_texts = [s.get("text", "") for s in line.get("spans", []) if s.get("text")]
                if span_texts:
                    spans_as_lines.append(" ".join(span_texts).strip())
            text = "\n".join([t for t in spans_as_lines if t]).strip()
            if not text:
                continue

            bbox = tuple(block.get("bbox", (0.0, 0.0, 0.0, 0.0)))
            is_table_region = any(self._bbox_overlap(bbox, tb) for tb in table_bboxes)

            blocks_out.append(
                {
                    "page": page_num,
                    "text": text,
                    "bbox": bbox,
                    "page_height": page_height,
                    "is_table_region": is_table_region,
                }
            )

        return blocks_out

    @staticmethod
    def _render_raw_text(page_blocks):
        pages = []
        for idx, blocks in enumerate(page_blocks, start=1):
            body = "\n".join([(b.get("text") or "").strip() for b in blocks if (b.get("text") or "").strip()])
            if body:
                pages.append(f"--- Page {idx} ---\n{body}")
        return "\n\n".join(pages).strip()

    @staticmethod
    def _to_json_table_regions(tables):
        """Normalize table extraction output to JSON-safe 2D table regions.

        Keeps `rows` as a two-dimensional array and preserves page/bbox metadata.
        """
        table_regions = []
        for t in tables or []:
            page = t.get("page") if isinstance(t, dict) else None
            bbox = t.get("bbox") if isinstance(t, dict) else None
            rows = t.get("rows") if isinstance(t, dict) else None
            normalized_rows = []
            for row in rows or []:
                if isinstance(row, list):
                    normalized_rows.append(["" if c is None else str(c) for c in row])
                else:
                    normalized_rows.append(["" if row is None else str(row)])

            item = {
                "page": page,
                "rows": normalized_rows,
            }
            if bbox is not None:
                item["bbox"] = list(bbox)
            table_regions.append(item)

        return table_regions

    def _request(self, pdf_path: str, **kwargs):
        return self._parse_pdf(pdf_path)

    def _parse_pdf(self, pdf_path: str):
        if not os.path.isfile(pdf_path):
            return {
                "text": "",
                "raw_text": "",
                "cleaned_text": "",
                "tables": [],
                "table_regions": [],
                "meta": {
                    "source": pdf_path,
                    "pages": 0,
                    "mock": False,
                    "error": f"PDF file not found: {pdf_path}",
                }
            }

        raw_text = ""
        tables = []

        
        # Prefer pdfplumber, but try PyMuPDF (fitz) first if available because
        # it often preserves layout and can render pages for OCR fallback.
        if fitz:
            try:
                doc = fitz.open(pdf_path)
                pages_count = doc.page_count
                # attempt table extraction via PyMuPDF heuristics
                tables = []
                table_evidence = []
                table_bboxes_by_page = {}
                if extract_tables_from_doc:
                    try:
                        tables = extract_tables_from_doc(doc)
                        for t in tables:
                            page_idx = int(t.get("page") or 0)
                            bbox = t.get("bbox")
                            if page_idx > 0 and bbox:
                                table_bboxes_by_page.setdefault(page_idx, []).append(tuple(bbox))
                        if extract_evidence_from_tables:
                            table_evidence = extract_evidence_from_tables(tables)
                    except Exception:
                        tables = []
                        table_evidence = []
                        table_bboxes_by_page = {}

                page_blocks = []
                for page_num in range(pages_count):
                    page = doc.load_page(page_num)
                    current_page = page_num + 1
                    layout_blocks = self._extract_layout_blocks(
                        page,
                        page_num=current_page,
                        table_bboxes=table_bboxes_by_page.get(current_page, []),
                    )
                    if layout_blocks:
                        page_blocks.append(layout_blocks)
                    else:
                        # low text: try OCR if available
                        if pytesseract and Image:
                            pix = page.get_pixmap()
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text = pytesseract.image_to_string(img) or ""
                            if ocr_text:
                                page_blocks.append(
                                    [
                                        {
                                            "page": current_page,
                                            "text": ocr_text,
                                            "bbox": (0.0, 0.0, float(pix.width), float(pix.height)),
                                            "page_height": float(pix.height),
                                            "is_table_region": False,
                                        }
                                    ]
                                )
                            else:
                                page_blocks.append([])
                        else:
                            page_blocks.append([])

                raw_text = self._render_raw_text(page_blocks)
                cleaned_text, clean_stats = clean_layout_blocks(page_blocks)
                table_regions = self._to_json_table_regions(tables)
                print(f"Raw text length: {len(raw_text)}")
                print(f"Cleaned text length: {len(cleaned_text)}")
                print(f"Removed blocks count: {clean_stats.get('removed_blocks_count', 0)}")

                return {
                    # Keep `text` backward-compatible for current pipeline consumers.
                    "text": cleaned_text.strip(),
                    "raw_text": raw_text.strip(),
                    "cleaned_text": cleaned_text.strip(),
                    "tables": tables,
                    "table_regions": table_regions,
                    "evidence": table_evidence,
                    "meta": {
                        "source": pdf_path,
                        "pages": pages_count,
                        "mock": False,
                        "method": "pymupdf_layout_cleaned",
                        "removed_blocks_count": clean_stats.get("removed_blocks_count", 0),
                        "repeated_short_lines_count": clean_stats.get("repeated_short_lines_count", 0),
                    }
                }
            except Exception:
                # fall through to pdfplumber/PyPDF2
                pass

        if pdfplumber:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    pages_count = len(pdf.pages)
                    for page_num, page in enumerate(pdf.pages):
                        text = page.extract_text() or ""
                        if text:
                            raw_text += f"\n--- Page {page_num + 1} ---\n{text}"
                        page_tables = page.extract_tables() or []
                        for table in page_tables:
                            tables.append({
                                "page": page_num + 1,
                                "rows": table
                            })
                    table_regions = self._to_json_table_regions(tables)
                    return {
                        "text": raw_text.strip(),
                        "raw_text": raw_text.strip(),
                        "cleaned_text": raw_text.strip(),
                        "tables": tables,
                        "table_regions": table_regions,
                        "meta": {
                            "source": pdf_path,
                            "pages": pages_count,
                            "mock": False,
                            "method": "pdfplumber"
                        }
                    }
            except Exception:
                pass

        
        if PdfReader:
            try:
                with open(pdf_path, "rb") as f:
                    reader = PdfReader(f)
                    pages_count = len(reader.pages)
                    for page_num, page in enumerate(reader.pages):
                        text = page.extract_text() or ""
                        if text:
                            raw_text += f"\n--- Page {page_num + 1} ---\n{text}"
                    return {
                        "text": raw_text.strip(),
                        "raw_text": raw_text.strip(),
                        "cleaned_text": raw_text.strip(),
                        "tables": [],
                        "table_regions": [],
                        "meta": {
                            "source": pdf_path,
                            "pages": pages_count,
                            "mock": False,
                            "method": "PyPDF2"
                        }
                    }
            except Exception:
                pass

        
        return {
            "text": "Unable to parse PDF. Please install pdfplumber or PyPDF2.",
            "raw_text": "",
            "cleaned_text": "",
            "tables": [],
            "table_regions": [],
            "meta": {
                "source": pdf_path,
                "pages": 0,
                "mock": False,
                "error": "No PDF parser available"
            }
        }
