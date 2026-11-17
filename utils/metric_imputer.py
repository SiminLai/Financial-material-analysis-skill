from copy import deepcopy
from math import isfinite


def compute_debt_ratio_from_evidence(evidence_store, metrics):
    result = deepcopy(metrics)
    if result.get("debt_ratio") is not None:
        return result
    sources = result.setdefault("meta", {}).setdefault("metric_sources", {})
    assets = sources.get("total_assets", {})
    liabilities = sources.get("total_liabilities", {})
    compatible = all(assets.get(key) not in (None, "", "unknown")
                     and assets.get(key) == liabilities.get(key)
                     for key in ("period", "scope", "currency", "unit"))
    grounded = all(source.get("row") and not source.get("ambiguous")
                   and (source.get("page") is not None or source.get("sheet"))
                   for source in (assets, liabilities))
    try:
        asset_value = float(assets["value"])
        liability_value = float(liabilities["value"])
    except (KeyError, TypeError, ValueError):
        return result
    if not compatible or not grounded or not all(map(isfinite, (asset_value, liability_value))):
        return result
    if asset_value <= 0 or liability_value < 0:
        return result
    result["debt_ratio"] = liability_value / asset_value
    sources["debt_ratio"] = {
        "source_type": "derived", "formula": "total_liabilities / total_assets",
        "inputs": ["total_liabilities", "total_assets"], "period": assets["period"],
        "scope": assets["scope"], "unit": "ratio", "value": result["debt_ratio"],
    }
    return result
