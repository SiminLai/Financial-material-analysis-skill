from typing import Dict, Any, List


# Multilingual metric keywords mapping and normalization helpers
METRIC_KEYWORDS = {
    "revenue": [
        "revenue", "sales", "turnover", "total revenue", "net sales", "sales revenue",
        "收入", "营收", "销售收入", "营业收入"
    ],
    "net_income": [
        "net income", "net profit", "profit", "net earnings", "income attributable",
        "净利润", "归属于", "税后净利润"
    ],
    "eps": [
        "eps", "earnings per share", "per share", "diluted eps", "basic eps",
        "每股收益", "稀释每股收益", "基本每股收益"
    ]
}


def normalize_extractor_output(ex_out: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize various metric extractor outputs to the internal metric keys.

    Expected internal keys: `revenue`, `net_income`, `eps`.
    This function maps common extractor keys (e.g. `net_profit`) to internal names.
    """
    out = {}
    # revenue
    if "revenue" in ex_out and ex_out.get("revenue") is not None:
        out["revenue"] = ex_out.get("revenue")
    elif "sales" in ex_out and ex_out.get("sales") is not None:
        out["revenue"] = ex_out.get("sales")

    # net income / net profit
    if "net_income" in ex_out and ex_out.get("net_income") is not None:
        out["net_income"] = ex_out.get("net_income")
    elif "net_profit" in ex_out and ex_out.get("net_profit") is not None:
        out["net_income"] = ex_out.get("net_profit")

    # eps
    if "eps" in ex_out and ex_out.get("eps") is not None:
        out["eps"] = ex_out.get("eps")
    elif "earnings_per_share" in ex_out and ex_out.get("earnings_per_share") is not None:
        out["eps"] = ex_out.get("earnings_per_share")

    return out
