import os
from .base_tool import BaseTool
from .pdf_parser_tool import PDFParserTool
from .excel_parser_tool import ExcelParserTool


class DocumentParserTool(BaseTool):

    name = "document_parser"
    description = "Parse PDF or XLSX documents into a unified structured document"

    input_schema = {
        "type": "dict",
        "required_fields": ["file_path"],
        "field_types": {
            "file_path": str,
        },
    }

    output_schema = {
        "type": "dict",
        "required_fields": ["text", "tables", "meta"],
        "field_types": {
            "text": str,
            "tables": list,
            "table_regions": list,
            "meta": dict,
        },
    }

    def __init__(self, pdf_parser: PDFParserTool, excel_parser: ExcelParserTool):
        self._pdf_parser = pdf_parser
        self._excel_parser = excel_parser

    def _execute(self, input_data):
        file_path = input_data.get("file_path") if isinstance(input_data, dict) else input_data

        if not isinstance(file_path, str):
            raise TypeError("DocumentParserTool requires a file_path string")

        extension = os.path.splitext(file_path)[1].lower()

        if extension == ".pdf":
            return self._pdf_parser.invoke({"pdf_path": file_path})
        elif extension in {".xlsx", ".xlsm", ".xltx", ".xltm"}:
            return self._excel_parser.invoke({"xlsx_path": file_path})
        else:
            raise ValueError(f"Unsupported document type: {extension}")
