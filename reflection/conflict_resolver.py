import re
from typing import List, Dict, Any, Optional


def _normalize_unit(value_str: str) -> float:
    """Normalize a numeric string with optional unit suffixes into a float.

    Supports K/M/B, thousand, million, billion, Chinese 万/亿, and currency symbols.
    """
    s = value_str.strip()
    # remove currency symbols
    s = re.sub(r"[\$¥€£]", "", s)
    # detect unit
    unit = 1.0
    if re.search(r"\b(billion|bn)\b", s, flags=re.I):
        unit = 1e9
    elif re.search(r"\b(million|m)\b", s, flags=re.I):
        unit = 1e6
    elif re.search(r"\b(thousand|k)\b", s, flags=re.I):
        unit = 1e3
    elif re.search(r"万", s):
        unit = 1e4
    elif re.search(r"亿", s):
        unit = 1e8

    # strip non-numeric trailing words
    s = re.sub(r"[a-zA-Z%￥￥,\s]+$", "", s)
    s = s.replace(",", "")
    try:
        base = float(re.findall(r"-?\d+(?:\.\d+)?", s)[0])
        return base * unit
    except Exception:
        try:
            return float(s)
        except Exception:
            return None


def extract_numbers_with_context(text: str) -> List[Dict[str, Any]]:
    """Return list of {'value':float,'context':str,'raw':str} from a text blob."""
    if not text:
        return []
    results = []
    # find numeric token with some surrounding context (20 chars)
    for m in re.finditer(r"[\$¥€£]?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\s*(?:[a-zA-Z%万亿千MBbn]*)", text):
        raw = m.group(0)
        start, end = m.span()
        context = text[max(0, start - 30): min(len(text), end + 30)]
        val = _normalize_unit(raw)
        if val is not None:
            results.append({"value": val, "context": context, "raw": raw})
    return results


def resolve_conflicts(state: Dict[str, Any], external_items: List[Dict[str, Any]], evidence_store=None) -> Dict[str, Any]:
    """Resolve numeric conflicts between internal `state` and `external_items`.

    Strategy:
      - Extract candidate numbers from state (if keys like revenue/net_income/eps present)
      - Extract numbers from external_items content
      - For each named metric in state, look for differing numeric candidates in external items.
      - Resolution rules:
          * If state has a numeric and external has the same number (within tol), accept state.
          * If external sources concur (same value in >=2 items) and differ from state, prefer external consensus.
          * Otherwise prefer numeric present in state (assume extracted from doc table) but mark as 'needs_review'.
    Returns a dict with `conflicts` list and `resolved` mapping.
    """
    resolved = {}
    conflicts = []

    # metric-specific context keywords to improve matching precision
    metric_keywords = {
        "revenue": ["revenue", "sales", "turnover", "total revenue", "net sales", "sales revenue"],
        "net_income": ["net income", "profit", "net loss", "income attributable", "net earnings"],
        "eps": ["eps", "earnings per share", "per share", "diluted eps", "basic eps"],
    }

    # gather external numbers with context and weights
    ext_candidates = []
    for it in external_items:
        # external_items may be evidence IDs or dict items
        if isinstance(it, str):
            # lookup in evidence store if available
            if evidence_store:
                ev = evidence_store.get(it)
                txt = ev.get('content') if ev else ''
                meta = ev.get('meta') if ev else {}
            else:
                txt = ''
                meta = {}
        elif isinstance(it, dict):
            txt = it.get("content") or it.get("text") or ""
            meta = it.get("meta") or {}
        else:
            txt = str(it)
            meta = {}

        items = extract_numbers_with_context(txt)
        weight = 1
        src = meta.get("source")
        if src == "table":
            weight = 4
        elif src == "report":
            weight = 2
        for ic in items:
            # increase weight if context contains metric-specific keywords
            additional = 0
            ctxt = (ic.get("context") or "").lower()
            for mk, kws in metric_keywords.items():
                for kw in kws:
                    if kw in ctxt:
                        # add a moderate boost for keyword presence
                        additional += 2
                        break

            ic["weight"] = weight + additional
            ic["source_meta"] = meta
            # keep evidence id if present in meta
            ic["evidence_id"] = meta.get('id') or None
            ext_candidates.append(ic)

    # aggregate weighted counts by rounded values
    counts = {}
    for c in ext_candidates:
        key = round(c["value"], 2)
        counts[key] = counts.get(key, 0) + c.get("weight", 1)

    metrics = ["revenue", "net_income", "eps"]
    tol = 1e-2
    for m in metrics:
        s_val = state.get(m)
        candidates = list(counts.keys())
        chosen = None
        reason = None
        if s_val is not None:
            try:
                s_num = float(s_val)
                # check if any external candidate matches
                match = next((c for c in candidates if abs(c - round(s_num,2)) <= tol), None)
                if match is not None:
                    chosen = s_num
                    reason = "agreement"
                else:
                    # check external consensus (use weighted counts)
                        top = max(counts.items(), key=lambda x: x[1]) if counts else (None, 0)
                        if top[0] is not None and top[1] >= 3 and abs(top[0] - round(s_num,2)) > tol:
                            chosen = float(top[0])
                            reason = "external_consensus"
                            conflicts.append({"metric": m, "state": s_num, "external_consensus": top[0]})
                    else:
                        chosen = s_num
                        reason = "prefer_state_needs_review" if counts else "state_only"
            except Exception:
                chosen = None
                reason = "parse_error"
        else:
            # state missing, but external may provide value
            if counts:
                top = max(counts.items(), key=lambda x: x[1])
                # require at least small weight to accept
                if top[1] >= 2:
                    chosen = float(top[0])
                    reason = "external_only"

        if chosen is not None:
            resolved[m] = {"value": chosen, "reason": reason}

    return {"conflicts": conflicts, "resolved": resolved, "external_counts": counts}
