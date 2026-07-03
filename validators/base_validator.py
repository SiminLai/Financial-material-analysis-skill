from __future__ import annotations

from typing import Any, Dict, List, Optional, Type


class ValidationError(ValueError):
    """统一校验异常。"""


def _resolve_expected_type(expected_type: Any) -> Any:
    if expected_type is None:
        return Any

    if isinstance(expected_type, str):
        mapping = {
            "str": str,
            "string": str,
            "int": int,
            "float": float,
            "bool": bool,
            "dict": dict,
            "list": list,
            "tuple": tuple,
            "set": set,
            "any": Any,
        }
        if expected_type in mapping:
            return mapping[expected_type]
        raise ValidationError(f"Unsupported schema type name: {expected_type}")

    if isinstance(expected_type, (list, tuple)):
        return tuple(_resolve_expected_type(item) for item in expected_type)

    return expected_type


def _describe_expected_type(expected_type: Any) -> str:
    resolved_type = _resolve_expected_type(expected_type)
    if isinstance(resolved_type, tuple):
        return " | ".join(getattr(item, "__name__", str(item)) for item in resolved_type)
    return getattr(resolved_type, "__name__", str(resolved_type))


def validate_type(value: Any, expected_type: Any, field_name: str = "value") -> None:
    resolved_type = _resolve_expected_type(expected_type)
    if resolved_type is Any:
        return
    if not isinstance(value, resolved_type):
        raise ValidationError(
            f"{field_name} must be of type {_describe_expected_type(expected_type)}, got {type(value).__name__}"
        )


def validate_dict_schema(
    payload: Dict[str, Any],
    required_fields: Optional[List[str]] = None,
    field_types: Optional[Dict[str, Type[Any]]] = None,
    field_name: str = "payload",
) -> None:
    validate_type(payload, dict, field_name)

    if required_fields:
        missing = [field for field in required_fields if field not in payload]
        if missing:
            raise ValidationError(f"{field_name} missing required fields: {missing}")

    if field_types:
        for field, expected_type in field_types.items():
            if field in payload:
                validate_type(payload[field], expected_type, field_name=f"{field_name}.{field}")


def validate_list_schema(payload: List[Any], item_type: Optional[Type[Any]] = None, field_name: str = "payload") -> None:
    validate_type(payload, list, field_name)
    if item_type is not None:
        for idx, item in enumerate(payload):
            validate_type(item, item_type, field_name=f"{field_name}[{idx}]")


def validate_payload(payload: Any, schema: Optional[Dict[str, Any]] = None, *, field_name: str = "payload") -> None:
    if schema is None:
        return

    schema_type = schema.get("type", Any)
    if schema_type == "dict" or schema_type is dict:
        required_fields = schema.get("required_fields") or []
        field_types = schema.get("field_types") or {}
        validate_dict_schema(payload, required_fields, field_types, field_name)
    elif schema_type == "list" or schema_type is list:
        item_type = schema.get("item_type")
        validate_list_schema(payload, item_type, field_name)
    else:
        validate_type(payload, schema_type, field_name)
