import os
try:
    import pdfplumber
except ImportError:
    pdfplumber = None
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

from providers.base_provider import BaseProvider


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
