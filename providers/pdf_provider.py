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
try:
    from providers.table_extractor import extract_tables_from_doc, extract_evidence_from_tables
except Exception:
    extract_tables_from_doc = None
    extract_evidence_from_tables = None


class PDFProvider(BaseProvider):

    name = "pdf_provider"

    def _request(self, pdf_path: str, **kwargs):
        return self._parse_pdf(pdf_path)

    def _parse_pdf(self, pdf_path: str):
        if not os.path.isfile(pdf_path):
            return {
                "text": "",
                "tables": [],
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
                if extract_tables_from_doc:
                    try:
                        tables = extract_tables_from_doc(doc)
                        if extract_evidence_from_tables:
                            table_evidence = extract_evidence_from_tables(tables)
                    except Exception:
                        tables = []
                        table_evidence = []
                for page_num in range(pages_count):
                    page = doc.load_page(page_num)
                    text = page.get_text("text") or ""
                    if text:
                        raw_text += f"\n--- Page {page_num + 1} ---\n{text}"
                    else:
                        # low text: try OCR if available
                        if pytesseract and Image:
                            pix = page.get_pixmap()
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            ocr_text = pytesseract.image_to_string(img) or ""
                            if ocr_text:
                                raw_text += f"\n--- Page {page_num + 1} (ocr) ---\n{ocr_text}"
                return {
                    "text": raw_text.strip(),
                    "tables": tables,
                    "evidence": table_evidence,
                    "meta": {
                        "source": pdf_path,
                        "pages": pages_count,
                        "mock": False,
                        "method": "pymupdf"
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
                    return {
                        "text": raw_text.strip(),
                        "tables": tables,
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
                        "tables": [],
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
            "tables": [],
            "meta": {
                "source": pdf_path,
                "pages": 0,
                "mock": False,
                "error": "No PDF parser available"
            }
        }
