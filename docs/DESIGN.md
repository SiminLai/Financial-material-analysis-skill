# Design Overview

This document summarizes the design decisions, data flows, and key components of the Financial Report Analysis Skill.

## Goals

- Evidence-first pipeline: persist structured evidence for every parsing, metric, risk, and external retrieval step.
- Traceable citations: memory entries and final reports include `evidence_ids` linking back to Evidence items.
- Integrate external web evidence (RAG/MCP) so it actively contributes to the final report.
- Provide a lightweight checkpoint of the LangGraph builder for debugging.

## High-level Components

- Parser Node: extracts text, tables, and granular table cells and persists as Evidence.
- Metric Node: extracts metrics and persists metric evidence; missing metrics trigger Imputer.
- Impute Node: computes derived metrics (e.g., debt_ratio) from evidence and persists results.
- Risk Node: calculates risk flags and risk score and persists evidence.
- Browser / RAG Node: performs external retrieval, compresses results, persists summaries and raw (policy-controlled), and optionally vectorizes summaries.
- Reflection Engine: runs analyzers (missing, completeness, consistency) and produces feedback evidence and memory entries.
- Report Generator: constructs final structured report; ensures `external_evidence` and `evidence_ids` are included.

## Evidence and Memory

- Evidence: stored via `reflection.EvidenceStore`; each Evidence item has a UUID and metadata linking to source, page, table, row, cell where available.
- Memory: persisted via `memory.MemoryManager` into `workspace/cache/memories.json`; memory items include `metadata.evidence_ids` to enable fast traceability from report → evidence.
- Vector Index: `memory.VectorStore` stores embeddings of summary chunks when `MemoryPolicy` allows `add_to_vector`.

## MemoryPolicy

- Implemented in `memory/policy.py`. The policy decides per-retrieval whether to:
  - store the raw payload (`store_raw`)
  - store a compressed summary (`store_summary`)
  - add summary chunks to the vector index (`add_to_vector`)

Policy thresholds and toggles should be exposed in runtime config in future work.

## LangGraph Checkpointing

- A lightweight checkpoint file is written during graph assembly at:

```
workspace/cache/langgraph_checkpoint.json
```

- The checkpoint contains node names and recorded edges for reproducibility and debugging; it does not serialize node functions.

## Running & Validation

1. Install dependencies: `pip install -r requirements.txt`.
2. (Optional) Configure external services via env vars: `DEEPSEEK_API_KEY`, `ENABLE_TAVILY`, `TAVILY_API_KEY`.
3. Run the pipeline: `python main.py`.
4. Inspect artifacts:
   - Checkpoint: `workspace/cache/langgraph_checkpoint.json`
   - Memories: `workspace/cache/memories.json`
   - Evidence store: see `reflection/evidence_store.py` persistence location

## Next Improvements

- Expose `MemoryPolicy` parameters in config and add unit tests for storage decisions.
- Add runtime toggle to switch stubs ↔ production services (env var `USE_PRODUCTION`).
- Expand table extractors (Camelot/Tabula) and formal `ITableExtractor` adapter.
