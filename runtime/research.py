import math
from copy import deepcopy


REQUIRED_METRICS = ("revenue", "net_profit", "cash_flow", "debt_ratio")
SCHEMA_VERSION = "research-1.0"


def finite_number(value):
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def build_facts(metrics, input_file):
    sources = (metrics.get("meta") or {}).get("metric_sources", {})
    facts, evidence, issues = [], [], []
    names = list(REQUIRED_METRICS) + [name for name in ("total_assets", "total_liabilities") if name in sources]
    for name in names:
        source = sources.get(name, {})
        value = finite_number(metrics.get(name, source.get("value")))
        fact_id = "fact:" + name
        references = []
        problems = []
        if source.get("row"):
            evidence_id = "evidence:" + name
            references.append(evidence_id)
            evidence.append({"id": evidence_id, "source_file": input_file,
                             "page": source.get("page"), "sheet": source.get("sheet"),
                             "bbox": source.get("bbox"), "coordinate_system": "page_points_top_left",
                             "parser_engine": source.get("engine"),
                             "row_number": source.get("row_number"), "column_number": source.get("column_number"),
                             "raw_value": source.get("raw_value"), "content": source["row"],
                             "header": source.get("header"), "origin": "document"})
        derived = source.get("source_type") == "derived"
        if value is None:
            problems.append("missing_or_invalid_value")
        if not derived and not references:
            problems.append("no_grounded_evidence")
        if not derived and source.get("page") is None and not source.get("sheet"):
            problems.append("unknown_location")
        if source.get("ambiguous"):
            problems.append("ambiguous_columns_or_conflicting_occurrences")
        for field in ("period", "scope", "unit"):
            if source.get(field) in (None, "", "unknown"):
                problems.append("unknown_" + field)
        if name != "debt_ratio" and not source.get("currency"):
            problems.append("unknown_currency")
        if name == "debt_ratio" and source.get("unit") != "ratio":
            problems.append("unverified_ratio_unit")
        if not derived and value is not None and finite_number(source.get("value")) != value:
            problems.append("source_value_mismatch")
        facts.append({"id": fact_id, "metric": name, "value": value,
                      "raw_value": source.get("raw_value"), "period": source.get("period"),
                      "scope": source.get("scope"), "unit": source.get("unit"), "currency": source.get("currency"),
                      "source_file": input_file, "evidence_refs": references,
                      "method": "derived" if derived else "table" if references else "unverified_extraction",
                      "formula": source.get("formula"),
                      "input_fact_ids": ["fact:" + item for item in source.get("inputs", [])],
                      "validation_status": "needs_review" if problems else "validated"})
        issues.extend({"code": problem, "fact_id": fact_id, "severity": "blocking"} for problem in problems)
    by_id = {fact["id"]: fact for fact in facts}
    for fact in facts:
        if fact["method"] == "derived":
            inputs = [by_id.get(identifier) for identifier in fact["input_fact_ids"]]
            if not inputs or not all(item and item["validation_status"] == "validated" for item in inputs):
                fact["validation_status"] = "needs_review"
                issues.append({"code": "unverified_derivation_inputs", "fact_id": fact["id"], "severity": "blocking"})
            else:
                fact["evidence_refs"] = [reference for item in inputs for reference in item["evidence_refs"]]
    return facts, evidence, issues


def research_report(state):
    findings = [{"rule": check["rule"], "fact_ids": check["fact_ids"], "status": check["status"]}
                for check in state["risk"].get("rule_checks", []) if check["status"] == "triggered"]
    return {"schema_version": SCHEMA_VERSION,
            "title": "Evidence-first financial research worksheet",
            "company_name": state["metrics"].get("company_name"),
            "company_identity_status": "unverified",
            "facts": deepcopy(state["facts"]), "findings": findings,
            "risk_assessment": deepcopy(state["risk"]),
            "open_questions": list(state.get("issues", [])),
            "external_context": state.get("browser_result"),
            "limitations": ["Not an investment recommendation", "Company identity and publication time require independent verification",
                            "No implied cross-period comparability; no automatic BUY/HOLD/SELL output"]}


def finalize_research(state):
    issues = list(state.get("issues", []))
    facts = state.get("facts", [])
    present = {fact["metric"] for fact in facts}
    for metric in REQUIRED_METRICS:
        if metric not in present:
            issues.append({"code": "required_fact_missing", "fact_id": "fact:" + metric, "severity": "blocking"})
    for fact in facts:
        if fact.get("validation_status") != "validated" or finite_number(fact.get("value")) is None:
            issues.append({"code": "fact_not_validated", "fact_id": fact["id"], "severity": "blocking"})
        if not fact.get("evidence_refs"):
            issues.append({"code": "fact_without_evidence", "fact_id": fact["id"], "severity": "blocking"})
    evidence_ids = {item["id"] for item in state.get("evidence", [])}
    fact_ids = {fact["id"] for fact in state.get("facts", [])}
    for fact in state.get("facts", []):
        if any(reference not in evidence_ids for reference in fact["evidence_refs"]):
            issues.append({"code": "broken_evidence_reference", "fact_id": fact["id"], "severity": "blocking"})
    report = dict(state["report"])
    if len(fact_ids) != len(facts) or len(evidence_ids) != len(state.get("evidence", [])):
        issues.append({"code": "duplicate_identifier", "severity": "blocking"})
    expected = research_report(state)
    if report.get("findings") != expected["findings"] or report.get("risk_assessment") != state["risk"]:
        issues.append({"code": "report_rule_mismatch", "severity": "blocking"})
    if report.get("facts") != state.get("facts"):
        issues.append({"code": "report_fact_mismatch", "severity": "blocking"})
    for finding in report.get("findings", []):
        if not finding.get("fact_ids") or any(reference not in fact_ids for reference in finding["fact_ids"]):
            issues.append({"code": "ungrounded_finding", "severity": "blocking"})
    if state.get("execution_mode") == "demo":
        issues.append({"code": "demo_output_not_for_research", "severity": "blocking"})
    if state["risk"].get("assessment_status") != "complete":
        issues.append({"code": "risk_not_fully_evaluable", "severity": "blocking"})
    status = "needs_review" if issues else "succeeded"
    validation = {"status": status, "issues": issues, "validator_version": SCHEMA_VERSION,
                  "scope": "Numeric evidence and rule checks only; not issuer identity or publication chronology"}
    report.update({"status": status, "open_questions": issues})
    return {"report": report, "status": status, "validation": validation, "reflection": validation}
