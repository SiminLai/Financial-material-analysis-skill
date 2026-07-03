PDF_PARSER_INPUT_SCHEMA = {
    "type": "dict",
    "required_fields": ["pdf_path"],
    "field_types": {
        "pdf_path": str,
    },
}

PDF_PARSER_OUTPUT_SCHEMA = {
    "type": "dict",
    "required_fields": ["text", "tables", "meta"],
    "field_types": {
        "text": str,
        "tables": list,
        "meta": dict,
    },
}

WORKFLOW_STATE_SCHEMA = {
    "type": "dict",
    "required_fields": ["input_text"],
    "field_types": {
        "input_text": str,
    },
}
