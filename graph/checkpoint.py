import json
from pathlib import Path


def save_builder_checkpoint(builder, path=None):
    """Save a lightweight checkpoint of a StateGraph builder.

    The checkpoint records node names and edge records for debugging and
    inspection. It does NOT attempt to serialize callables.
    """
    if path is None:
        path = Path("workspace/cache/langgraph_checkpoint.json")
    else:
        path = Path(path)

    payload = {
        "nodes": [],
        "edges": [],
    }

    # Attempt to read nodes/edges from common attribute names
    nodes = getattr(builder, "_nodes", None) or getattr(builder, "nodes", None)
    edges = getattr(builder, "_edges", None) or getattr(builder, "edges", None)

    try:
        if isinstance(nodes, dict):
            payload["nodes"] = list(nodes.keys())
        elif isinstance(nodes, list):
            # list of (name, fn)
            payload["nodes"] = [n for n, _ in nodes]

        if edges is not None:
            payload["edges"] = edges
    except Exception:
        # Best-effort: ignore serialization errors
        pass

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return str(path)


def load_builder_checkpoint(path=None):
    if path is None:
        path = Path("workspace/cache/langgraph_checkpoint.json")
    else:
        path = Path(path)

    if not path.exists():
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
