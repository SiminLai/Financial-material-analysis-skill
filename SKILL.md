---
name: financial-report-analysis-skill
description: Analyze local PDF/XLSX reports into evidence-linked research worksheets, exposing missing data and review requirements without trading recommendations.
---

# Financial research workflow

Run from the repository root using a configured Python environment:

    python main.py --input-file "path/to/report.pdf" --output-dir workspace/runs

Use --demo explicitly for offline demonstrations. Production requires DEEPSEEK_API_KEY.
Model selection uses --model; external search is disabled unless --enable-external-search is explicitly authorized.
Do not transmit private financial materials to model or search providers without the user's authorization.

Read stdout as one JSON result. Exit codes: 0 succeeded, 2 needs_review, 1 failed.
Always inspect status, execution_mode and validation before explaining the report.
Do not treat demo output as production research. Unknown financial risk is not low risk.
Do not invent missing numbers, periods, currencies, issuer identity or publication time.
Do not turn heuristic research signals into BUY/HOLD/SELL advice.

Use result.json as the delivery envelope; facts.json, evidence.json and report.md are supporting artifacts.
The optional frontend is a local read-only viewer; it is not needed for execution.
Do not run the old report generator or fallback workflow as a substitute when validation fails.
See docs/UPGRADE_BATCH_2.md for architecture boundaries and target-machine acceptance commands.
