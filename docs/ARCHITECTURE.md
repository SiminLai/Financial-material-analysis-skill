# Architecture Diagram

Below is a high-level architecture of the Financial Report Analysis Skill.

```mermaid
flowchart LR
  subgraph Input
    A[PDF / Excel Parser]
  end

  subgraph Processing
    B[Parser Node]
    C[Metric Extraction Node]
    D[Imputer Node]
    E[Risk Scoring Node]
    F[Browser / RAG Node]
    G[Reflection Engine]
    H[Report Generator]
  end

  subgraph Storage
    ES[EvidenceStore]
    MM[MemoryManager]
    VS[VectorStore]
  end

  A --> B --> C --> D --> E --> F --> G --> H
  B --> ES
  C --> ES
  D --> ES
  E --> ES
  F --> ES
  F --> VS
  G --> MM
  ES --> MM
  MM --> VS

  click ES "../reflection/evidence_store.py" "EvidenceStore implementation"
  click MM "../memory/manager.py" "MemoryManager implementation"
  click VS "../memory/vector_store.py" "VectorStore implementation"
```

Notes:
- The graph is assembled via `graph/create_finance_graph` and executed by `main.py`.
- External web evidence (RAG/MCP) is compressed, persisted to `EvidenceStore`, and optionally added to vector index.
- A lightweight LangGraph checkpoint is saved during graph construction at `workspace/cache/langgraph_checkpoint.json`.
