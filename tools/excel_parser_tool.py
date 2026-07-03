from .base_tool import BaseTool


class ExcelParserTool(BaseTool):

    name = "excel_parser"
    description = "Parse XLSX into structured document"

    input_schema = {
        "type": "dict",
        "required_fields": ["xlsx_path"],
        "field_types": {
            "xlsx_path": str,
        },
    }

    output_schema = {
        "type": "dict",
        "required_fields": ["text", "tables", "meta"],
        "field_types": {
            "text": str,
            "tables": list,
            "meta": dict,
        },
    }

    def __init__(self, excel_provider):
        self._excel_provider = excel_provider

    def _execute(self, input_data):

        if isinstance(input_data, dict):
            xlsx_path = input_data.get("xlsx_path")
        else:
            xlsx_path = input_data

        document = self._excel_provider.get(xlsx_path)

                
        # print("=" * 80)
        # print("DOCUMENT")
        # print("=" * 80)
        # print(document)
        
        return document
