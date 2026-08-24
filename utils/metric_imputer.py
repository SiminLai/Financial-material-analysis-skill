import re
from typing import Dict, Any, Optional


def _extract_number(text: str) -> Optional[float]:
    if not text:
        return None
    # find first numeric token like 1,234 or 1234.56 or $1,234
    m = re.search(r"[\$¥€£]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?", text)
    if not m:
        return None
    s = m.group(0)
    s = re.sub(r"[\$¥€£,\s]", "", s)
    try:
        return float(s)
    except Exception:
        return None


def compute_debt_ratio_from_evidence(evidence_store, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Attempt to compute debt_ratio from evidence (table cells).

    Looks for evidence content containing keywords for total debt/liabilities and total assets.
    If found, computes debt_ratio = total_debt / total_assets and returns updated metrics and evidence_meta.
    """
    if evidence_store is None:
        return metrics

    existing = metrics.copy()
    if existing.get('debt_ratio') is not None:
        return existing

    assets = None
    debt = None

    # use stricter keywords to avoid implicit/ambiguous matches that can
    # incorrectly collapse to debt_ratio ~= 1.0.
    asset_keywords = ['total assets', 'total asset']
    debt_keywords = ['total liabilities', 'total debt']

    # search through all evidence items
    for ev in evidence_store._store.values():
        content = (ev.get('content') or '').lower()
        if any(k in content for k in asset_keywords):
            val = _extract_number(content)
            if val is not None:
                assets = val
        if any(k in content for k in debt_keywords):
            val = _extract_number(content)
            if val is not None:
                debt = val
        if assets is not None and debt is not None:
            break

    # only impute when ratio is plausible; otherwise keep missing as missing
    if assets and debt and assets != 0:
        ratio = debt / assets
        if 0 <= ratio <= 2.0:
            existing['debt_ratio'] = float(ratio)

    # explicit missing marker for downstream logic/debugging
    if existing.get('debt_ratio') is None:
        meta = existing.get('meta') if isinstance(existing.get('meta'), dict) else {}
        meta['debt_ratio_status'] = 'UNKNOWN'
        existing['meta'] = meta
    return existing
