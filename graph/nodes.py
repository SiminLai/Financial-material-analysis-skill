"""
Node factory functions for LangGraph.
Each node:
1. Read data from State
2. Invoke Tool
3. Write result back to State
"""
import os

def create_parser_node(parser_tool, evidence_builder=None):

    def parser_node(state):

        file_path = state.get("input_file")
        if file_path is None:
            raise ValueError("state is missing required key: 'input_file'")

        document = parser_tool.invoke({
            "file_path": file_path
        })

        state["document"] = document

        # if an EvidenceBuilder is provided, persist document text and tables
        if evidence_builder is not None:
            try:
                text = document.get('text', '')
                if text:
                    doc_eid = evidence_builder.from_text(text[:2000], source=file_path, page=None)
                    state.setdefault('evidence_ids', []).append(doc_eid)
                    state.setdefault('internal_evidence_ids', []).append(doc_eid)

                tables = document.get('tables') or []
                # tables expected as list of dicts with 'page' and 'rows'
                table_items = []
                for t in tables:
                    rows = t.get('rows') if isinstance(t, dict) else []
                    for r_idx, row in enumerate(rows):
                        for c_idx, cell in enumerate(row):
                            if isinstance(cell, str) and cell.strip():
                                table_items.append({'content': cell, 'meta': {'source': 'table', 'page': t.get('page'), 'row': r_idx, 'col': c_idx}})

                if table_items:
                    tids = evidence_builder.from_table_items(table_items)
                    state.setdefault('evidence_ids', []).extend(tids)
                    state.setdefault('internal_evidence_ids', []).extend(tids)
            except Exception:
                pass

        return state

    return parser_node


def create_metric_node(metric_tool, evidence_store=None, evidence_builder=None):

    def metric_node(state):

        document = state.get("document")
        if document is None:
            raise ValueError("state is missing required key: 'document'")

        metrics = metric_tool.invoke(document)

        # if debt_ratio missing, attempt to compute from evidence_store immediately
        try:
            if metrics.get('debt_ratio') is None and evidence_store is not None:
                from utils.metric_imputer import compute_debt_ratio_from_evidence
                updated = compute_debt_ratio_from_evidence(evidence_store, metrics)
                if updated.get('debt_ratio') is not None:
                    metrics = updated
                    # persist evidence of imputation if builder present
                    if evidence_builder:
                        meta = {'origin': 'imputer', 'method': 'debt_ratio_from_tables'}
                        eid = evidence_builder.from_text(f"computed debt_ratio={metrics.get('debt_ratio')}", source='imputer', meta=meta)
                        state.setdefault('evidence_ids', []).append(eid)
                        state.setdefault('internal_evidence_ids', []).append(eid)
        except Exception:
            pass

        # keep missing debt_ratio explicitly marked as UNKNOWN instead of
        # allowing any implicit defaulting behavior.
        try:
            if metrics.get('debt_ratio') is None:
                mmeta = metrics.get('meta') if isinstance(metrics.get('meta'), dict) else {}
                mmeta['debt_ratio_status'] = 'UNKNOWN'
                metrics['meta'] = mmeta
        except Exception:
            pass

        state["metrics"] = metrics

        return state

    return metric_node


def create_risk_node(risk_tool, evidence_builder=None):

    def risk_node(state):

        metrics = state.get("metrics")
        if metrics is None:
            raise ValueError("state is missing required key: 'metrics'")

        risk = risk_tool.invoke(metrics)

        state["risk"] = risk

        # persist risk flags as evidence for traceability
        try:
            flags = risk.get("risk_flags", []) if isinstance(risk, dict) else []
            if evidence_builder and flags:
                for f in flags:
                    meta = {"origin": "risk_tool", "flag": f, "risk_score": risk.get("risk_score")}
                    eid = evidence_builder.from_text(str(f), source="risk_tool", page=None, meta=meta)
                    # attach meta to the stored evidence (store.add already saved basic content)
                    # we also append the evidence id to state for later use
                    state.setdefault('evidence_ids', []).append(eid)
                    state.setdefault('internal_evidence_ids', []).append(eid)
        except Exception:
            pass

        return state

    return risk_node


def create_browser_node(browser_tool, evidence_builder=None, summarizer=None, memory_manager=None, vector_store=None, memory_policy=None):

    async def browser_node(state):

        risk = state.get("risk")
        metrics = state.get("metrics")

        if risk is None:
            raise ValueError(
                "state is missing required key: 'risk'"
            )

        if metrics is None:
            raise ValueError(
                "state is missing required key: 'metrics'"
            )

        company = (
            metrics.get("company_name")
            or state.get("document", {}).get("company_name")
            or ""
        )

        risk_flags = risk.get(
            "risk_flags",
            []
        )

        risk_reason = " ".join(risk_flags)

        query = f"Company:\n{company}\n\nRisk factors:\n{risk_reason}\n\nRisk score:\n{risk.get('risk_score')}"

        browser_result = await browser_tool.ainvoke(
            {
                "query": query
            }
        )

        # compress/structure external result before adding to state
        compressed = None
        try:
            if summarizer:
                # summarizer expects a list of dict-like items or strings
                compressed = summarizer.summarize([browser_result])
            else:
                # best-effort: stringify and truncate
                compressed = (browser_result.get('text') if isinstance(browser_result, dict) else str(browser_result))[:1000]
        except Exception:
            compressed = (browser_result.get('text') if isinstance(browser_result, dict) else str(browser_result))[:1000]

        # build a structured browser_result with summary and optional evidence ids
        browser_obj = {
            'summary': compressed,
            'source': 'mcp'
        }

        # persist full MCP output and compressed summary as Evidence
        try:
            stored_eids = []
            raw_text = None
            if isinstance(browser_result, dict):
                # try to extract a sensible text field for raw storage
                raw_text = browser_result.get('text') or browser_result.get('content') or str(browser_result)
            else:
                raw_text = str(browser_result)

            if evidence_builder:
                # always create summary evidence if we have compressed summary
                sum_eid = None
                try:
                    sum_eid = evidence_builder.from_text(compressed, source='mcp.summary', meta={'origin':'mcp','type':'summary'})
                    stored_eids.append(sum_eid)
                except Exception:
                    sum_eid = None

                # decide whether to store raw/full result in memory based on policy
                store_raw = False
                add_to_vector = False
                try:
                    if memory_policy:
                        decision = memory_policy.decide(raw_text=raw_text, summary=compressed, metadata={'risk_flags': state.get('risk', {}).get('risk_flags', []), 'risk_score': state.get('risk', {}).get('risk_score')})
                        store_raw = decision.get('store_raw', False)
                        add_to_vector = decision.get('add_to_vector', False)
                    else:
                        # default: store summary only
                        store_raw = False
                except Exception:
                    store_raw = False

                if store_raw and raw_text:
                    try:
                        full_eid = evidence_builder.from_text(raw_text[:2000], source='mcp.raw', meta={'origin':'mcp','type':'raw'})
                        stored_eids.append(full_eid)
                        browser_obj.setdefault('evidence_ids', []).append(full_eid)
                    except Exception:
                        pass

                if sum_eid:
                    browser_obj.setdefault('evidence_ids', []).append(sum_eid)

                # optionally add to vector store for semantic retrieval
                if add_to_vector and vector_store and compressed:
                    try:
                        # chunk compressed summary and add to vector store
                        from utils.advanced_chunker import chunk_by_sections
                        chunks = chunk_by_sections(compressed, max_chars=800, overlap_chars=100)
                        docs = []
                        for i, c in enumerate(chunks):
                            docs.append({'id': f'mcp_chunk_{sum_eid}_{i}', 'text': c, 'meta': {'source': 'mcp', 'chunk_index': i}})
                        if docs:
                            vector_store.add_documents(docs)
                    except Exception:
                        pass

            # also persist into MemoryManager with types according to policy
            try:
                if memory_manager:
                    # reuse decision if available
                    if 'decision' not in locals() and memory_policy:
                        decision = memory_policy.decide(raw_text=raw_text, summary=compressed, metadata={'risk_flags': state.get('risk', {}).get('risk_flags', []), 'risk_score': state.get('risk', {}).get('risk_score')})
                    existing_eids = list(state.get('external_evidence_ids') or [])
                    meta_eids = list(set(existing_eids + stored_eids))
                    if decision.get('store_raw') and raw_text:
                        memory_manager.add(content=raw_text, type='external_raw', metadata={'source':'mcp', 'evidence_ids': meta_eids})
                    if decision.get('store_summary') and compressed:
                        memory_manager.add(content=compressed, type='external_summary', metadata={'source':'mcp', 'evidence_ids': meta_eids})
            except Exception:
                pass

            # attach stored evidence ids to state
            if stored_eids:
                state.setdefault('evidence_ids', []).extend(stored_eids)
                state.setdefault('external_evidence_ids', []).extend(stored_eids)
                browser_obj['evidence_ids'] = list(state.get('external_evidence_ids') or [])
        except Exception:
            pass

        state['browser_result'] = browser_obj

        return state

    return browser_node

def create_report_node(report_tool, evidence_store=None, evidence_builder=None):

    def report_node(state):

        document = state.get("document")
        metrics = state.get("metrics")
        risk = state.get("risk")

        if document is None:
            raise ValueError("state is missing required key: 'document'")

        if metrics is None:
            raise ValueError("state is missing required key: 'metrics'")

        if risk is None:
            raise ValueError("state is missing required key: 'risk'")

        tool_input = {
            "document": document,
            "metrics": metrics,
            "risk": risk,
            "reflection": state.get("reflection")
        }

        browser_result = state.get("browser_result")

        if browser_result:
            tool_input["browser_result"] = browser_result
            # ensure external_summary is populated from browser_result if not already
            try:
                if not state.get('external_summary') and isinstance(browser_result, dict):
                    bsum = browser_result.get('summary')
                    if bsum:
                        tool_input['external_summary'] = bsum
            except Exception:
                pass

        # include any external summaries or evidence ids from prior nodes
        # prefer explicit external_summary from state, otherwise use browser_result.summary if available
        external_summary = state.get('external_summary')
        if external_summary:
            tool_input['external_summary'] = external_summary
        else:
            br = state.get('browser_result') or {}
            if isinstance(br, dict) and br.get('summary'):
                tool_input['external_summary'] = br.get('summary')

        # gather EXTERNAL evidence ids from state and browser_result and dedupe
        evidence_ids = list(state.get('external_evidence_ids') or [])
        try:
            br = state.get('browser_result') or {}
            if isinstance(br, dict) and br.get('evidence_ids'):
                for eid in br.get('evidence_ids'):
                    if eid not in evidence_ids:
                        evidence_ids.append(eid)
        except Exception:
            pass

        if evidence_ids:
            tool_input['external_evidence_ids'] = evidence_ids

            # build human-readable citations for evidence ids
            try:
                citations = []
                if evidence_store:
                    items = evidence_store.get_many(evidence_ids)
                    for it in items:
                        eid = it.get('id')
                        src = it.get('source')
                        meta = it.get('meta') or {}
                        page = it.get('page')
                        cite = None
                        snippet = (it.get('content') or '')[:300]
                        # prefer precise table cell citations when row/col present
                        row = it.get('row')
                        col = it.get('col')
                        bbox = it.get('bbox')
                        if row is not None and col is not None:
                            # use 1-based row/col for human readability
                            cite = f"Table p{page} r{int(row)+1}c{int(col)+1} [{eid}]"
                        elif meta.get('type') == 'table' or src == 'table':
                            cite = f"Table p{page} [{eid}]"
                        elif src and isinstance(src, str) and src.lower().endswith('.pdf'):
                            cite = f"Document {os.path.basename(src)} p{page} [{eid}]"
                        else:
                            cite = f"Evidence {eid} (src={src})"

                        # attach bbox summary when available
                        if bbox and isinstance(bbox, dict):
                            try:
                                x0 = float(bbox.get('x0', 0))
                                y0 = float(bbox.get('y0', 0))
                                cite = cite + f" bbox=({x0:.1f},{y0:.1f})"
                            except Exception:
                                pass

                        citations.append({
                            'id': eid,
                            'cite': cite,
                            'snippet': snippet,
                        })

                if citations:
                    tool_input['external_citations'] = citations
            except Exception:
                pass

            # If no external_summary provided earlier, build a short injected summary from evidence snippets
            try:
                if not tool_input.get('external_summary') and evidence_store and evidence_ids:
                    items = evidence_store.get_many(evidence_ids)
                    snippets = []
                    for it in items[:5]:
                        snippets.append(((it.get('content') or '')[:300]).replace('\n', ' '))
                    if snippets:
                        injected = ' | '.join(snippets[:3])
                        tool_input['external_summary'] = f"Injected external evidence summary: {injected}"
            except Exception:
                pass

        report = report_tool.invoke(tool_input)

        state["report"] = report

        return state

    return report_node


def create_impute_node(evidence_store, evidence_builder=None):

    def impute_node(state):
        # attempt to compute missing metrics (e.g., debt_ratio) from evidence
        from utils.metric_imputer import compute_debt_ratio_from_evidence

        metrics = state.get('metrics') or {}
        try:
            updated = compute_debt_ratio_from_evidence(evidence_store, metrics)
            # if debt_ratio was computed, persist as internal evidence and update state
            if updated.get('debt_ratio') is not None and metrics.get('debt_ratio') is None:
                state['metrics'] = updated
                try:
                    if evidence_builder:
                        meta = {'origin': 'imputer', 'method': 'debt_ratio_from_tables'}
                        eid = evidence_builder.from_text(f"computed debt_ratio={updated.get('debt_ratio')}", source='imputer', meta=meta)
                        state.setdefault('evidence_ids', []).append(eid)
                        state.setdefault('internal_evidence_ids', []).append(eid)
                except Exception:
                    pass
        except Exception:
            pass

        return state

    return impute_node


def create_reflection_node(reflection_engine, rag_tool=None, evidence_builder=None, evidence_store=None, summarizer=None, memory_manager=None):

    def reflection_node(state):
        # build a semantic query (avoid dumping raw metrics/meta JSON)
        metrics = state.get('metrics') or {}
        document = state.get('document') or {}
        risk = state.get('risk') or {}
        report = state.get('report') or {}

        q_parts = ["financial risk validation"]
        company = metrics.get('company_name')
        if company:
            q_parts.append(f"company {company}")

        title = document.get('meta', {}).get('title') if isinstance(document, dict) else None
        if title:
            q_parts.append(str(title))

        flags = risk.get('risk_flags') or []
        if flags:
            q_parts.append("risk flags " + ", ".join([str(f) for f in flags[:6]]))

        missing = (metrics.get('meta') or {}).get('missing_fields') if isinstance(metrics.get('meta'), dict) else None
        if missing:
            q_parts.append("missing metrics " + ", ".join([str(m) for m in missing[:6]]))

        report_summary = report.get('summary') if isinstance(report, dict) else None
        if report_summary:
            q_parts.append(str(report_summary)[:300])

        query = ' '.join([p for p in q_parts if p]) or None

        external_override_ids = list(state.get('external_evidence_ids') or [])
        rag_summary = None
        rag_ids = []

        def _is_external_source(src):
            s = (src or '').lower()
            return any(k in s for k in ['mcp', 'tavily', 'web', 'external', 'news', 'internet'])

        # retrieve via rag_tool
        if rag_tool and query:
            try:
                items = rag_tool.retrieve(query, k=5)

                if evidence_builder:
                    rids = evidence_builder.from_rag_items(items)

                    rag_ids.extend(rids)
                    for idx, rid in enumerate(rids):
                        src = None
                        try:
                            src = ((items[idx] or {}).get('meta') or {}).get('source')
                        except Exception:
                            src = None

                        state.setdefault('evidence_ids', []).append(rid)

                        if _is_external_source(src):
                            state.setdefault('external_evidence_ids', []).append(rid)
                            external_override_ids.append(rid)
                        else:
                            state.setdefault('internal_evidence_ids', []).append(rid)

                else:
                    external_override_ids.extend(items)

            except Exception:
                items = []

            # produce compressed summary of RAG items and persist summary evidence
            try:
                if rag_ids and evidence_store:
                    rag_items = evidence_store.get_many(rag_ids)
                    if summarizer:
                        try:
                            rag_summary = summarizer.summarize(rag_items)
                        except Exception:
                            rag_summary = None
                    # fallback: build a short snippet-based summary from rag_items
                    if not rag_summary:
                        snippets = []
                        for it in (rag_items or [])[:5]:
                            c = (it.get('content') or '')
                            snippets.append((c or '')[:300])
                        if snippets:
                            rag_summary = " \n".join(snippets)

                    if rag_summary:
                        state['external_summary'] = rag_summary
                        if evidence_builder:
                            try:
                                sid = evidence_builder.from_text(rag_summary, source='rag.summary', meta={'origin':'rag','type':'summary'})
                                state.setdefault('evidence_ids', []).append(sid)
                                state.setdefault('external_evidence_ids', []).append(sid)
                            except Exception:
                                pass
            except Exception:
                pass

        # combine browser_result summary (if present) with rag_summary to form a single external_summary
        try:
            browser_summary = None
            br = state.get('browser_result')
            if br and isinstance(br, dict):
                browser_summary = br.get('summary')
            combined = None
            parts = []
            if browser_summary:
                parts.append(str(browser_summary))
            if rag_summary:
                parts.append(str(rag_summary))
            if parts:
                combined = "\n\n".join(parts)
                # persist combined summary into state and memory
                state['external_summary'] = combined
                if evidence_builder:
                    try:
                        cid = evidence_builder.from_text(combined, source='external.combined_summary', meta={'origin':'combined','type':'summary'})
                        state.setdefault('evidence_ids', []).append(cid)
                        state.setdefault('external_evidence_ids', []).append(cid)
                    except Exception:
                        pass
                # also add to memory with linked evidence ids
                try:
                    if memory_manager:
                        metadata = {'source': 'external.combined', 'evidence_ids': list(set(external_override_ids))}
                        memory_manager.add(content=combined, type='external_combined_summary', metadata=metadata)
                except Exception:
                    pass
        except Exception:
            pass

        # run reflection
        try:
            override = external_override_ids if external_override_ids else None
            out = reflection_engine.reflect(state, query=query, use_external=True, external_override=override)
            state['reflection'] = out

            # expose reflection as a formal part of final report output
            try:
                eval_map = {}
                for item in out.get('evaluation_results') or []:
                    name = (item or {}).get('name')
                    if name:
                        eval_map[name] = item

                def _status(name, threshold=0.8):
                    score = ((eval_map.get(name) or {}).get('score'))
                    if isinstance(score, (int, float)):
                        return 'PASS' if float(score) >= threshold else 'FAIL'
                    return 'UNKNOWN'

                conflicts = ((out.get('conflict_resolution') or {}).get('conflicts') or [])
                conflict_count = len(conflicts)
                overall = out.get('overall_score')
                needs_review = conflict_count > 0 or (isinstance(overall, (int, float)) and float(overall) < 0.8)

                reflection_summary = {
                    'overall_score': overall,
                    'consistency': _status('consistency'),
                    'completeness': _status('completeness'),
                    'conflict_count': conflict_count,
                    'needs_review': bool(needs_review),
                }

                state['reflection_summary'] = reflection_summary

                if isinstance(state.get('report'), dict):
                    state['report']['reflection'] = reflection_summary
            except Exception:
                pass
        except Exception:
            state['reflection'] = None

        return state

    return reflection_node