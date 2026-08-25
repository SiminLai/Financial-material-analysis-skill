from tools.base_tool import BaseTool


class PDFParserTool(BaseTool):

    name = "pdf_parser"
    description = "Parse PDF into structured document"

    input_schema = {
        "type": "dict",
        "required_fields": ["pdf_path"],
        "field_types": {
            "pdf_path": str,
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

    def __init__(self, pdf_provider):
        self._pdf_provider = pdf_provider

    def _execute(self, input_data):

        if isinstance(input_data, dict):
            pdf_path = input_data.get("pdf_path")
        else:
            pdf_path = input_data

        document = self._pdf_provider.get(pdf_path)

        return document