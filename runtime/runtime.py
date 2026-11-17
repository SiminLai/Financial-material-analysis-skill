import hashlib
import importlib.metadata
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from runtime.research import SCHEMA_VERSION


def write_json(path, payload):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    temporary.replace(path)


def source_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def code_hash():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    files = [root / "main.py", root / "requirements.txt"]
    for directory in ("runtime", "graph", "providers", "tools", "utils", "validators", "state", "mcp_local"):
        files.extend((root / directory).rglob("*.py"))
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def markdown_report(result):
    lines = ["# Financial research worksheet", "", "Status: " + result["status"],
             "Mode: " + result["execution_mode"], "", "Not an investment recommendation.", "", "## Facts"]
    for fact in result.get("facts", []):
        lines.append("- " + fact["metric"] + ": " + str(fact["value"]) + " (" + fact["validation_status"] + ")")
    lines.extend(["", "## Review issues"])
    for issue in result.get("validation", {}).get("issues", []):
        lines.append("- " + issue["code"] + " " + issue.get("fact_id", ""))
    return "\n".join(lines) + "\n"


async def analyze_document(input_file, output_dir="workspace/runs", run_id=None,
                           model="deepseek-chat", demo=False, allow_external_search=False,
                           graph_factory=None):
    identifier = run_id or "run-" + uuid.uuid4().hex
    mode = "demo" if demo else "production"
    result = {"schema_version": SCHEMA_VERSION, "run_id": identifier,
              "execution_mode": mode, "status": "failed", "artifact_paths": {}}
    directory = None
    logger = logging.Logger("research." + str(identifier))
    logger.setLevel(logging.INFO)
    logger.propagate = False
    handler = None
    manifest = {}
    manager = None
    try:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", identifier):
            raise ValueError("run_id must be 1-64 ASCII letters, digits, hyphens or underscores")
        root = Path(output_dir).resolve()
        root.mkdir(parents=True, exist_ok=True)
        candidate = root / identifier
        candidate.mkdir(exist_ok=False)
        directory = candidate
        handler = logging.FileHandler(directory / "run.log", encoding="utf-8")
        logger.addHandler(handler)
        logger.info("Run started")
        source = Path(input_file).resolve(strict=True)
        if not source.is_file() or source.suffix.lower() not in {".pdf", ".xlsx"}:
            raise ValueError("Input must be an existing PDF or XLSX file")
        versions = {}
        for package in ("langgraph", "openpyxl", "pdfplumber", "PyPDF2", "requests"):
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = None
        manifest = {"schema_version": SCHEMA_VERSION, "run_id": identifier,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "source_file": str(source), "source_sha256": source_hash(source),
                    "source_publication_time": None, "source_publication_time_status": "unknown",
                    "model": model, "execution_mode": mode, "external_search": allow_external_search,
                    "retrieval": "disabled", "code_sha256": code_hash(), "dependencies": versions}
        write_json(directory / "manifest.json", manifest)
        if graph_factory is None:
            from graph.financial_graph import create_finance_graph
            from providers.excel_provider import ExcelProvider
            from providers.llm_provider import LLMProvider
            from providers.pdf_provider import PDFProvider
            from tools.document_parser_tool import DocumentParserTool
            from tools.excel_parser_tool import ExcelParserTool
            from tools.metric_extractor_tool import MetricExtractorTool
            from tools.pdf_parser_tool import PDFParserTool
            from tools.risk_detection_tool import RiskDetectionTool
            provider = LLMProvider(model_name=model, demo=demo)
            search_tool = None
            if allow_external_search:
                if demo:
                    raise ValueError("External search is disabled in demo mode")
                import os
                if not os.getenv("TAVILY_API_KEY"):
                    raise ValueError("External search requires TAVILY_API_KEY")
                from mcp_local.manager import MCPManager
                manager = MCPManager(str(Path(__file__).resolve().parents[1] / "config" / "mcp.json"))
                await manager.register("tavily")
                search_tool = manager.get_tool("tavily")
            graph = create_finance_graph(
                DocumentParserTool(PDFParserTool(PDFProvider()), ExcelParserTool(ExcelProvider())),
                MetricExtractorTool(provider), RiskDetectionTool(), browser_tool=search_tool,
            )
        else:
            graph = graph_factory(directory)
        state = await graph.ainvoke({"input_file": str(source), "thread_id": identifier, "execution_mode": mode},
                                    config={"configurable": {"thread_id": identifier}})
        if source_hash(source) != manifest["source_sha256"]:
            raise ValueError("Source changed during analysis; results cannot be published")
        for key in ("status", "facts", "evidence", "report", "validation", "risk"):
            result[key] = state[key]
        if result["status"] not in {"succeeded", "needs_review"}:
            raise ValueError("Invalid graph delivery status")
        if demo and result["status"] == "succeeded":
            raise ValueError("Demo output cannot pass production validation")
        logger.info("Analysis finished: %s", result["status"])
    except Exception as error:
        logger.exception("Analysis failed")
        result.update({"status": "failed", "error": {"type": type(error).__name__, "message": str(error)},
                       "validation": {"status": "failed", "issues": [{"code": "execution_failed", "severity": "blocking"}]}})
    finally:
        if manager is not None:
            try:
                await manager.close()
            except Exception:
                logger.exception("External tool cleanup failed")
        if directory is not None:
            try:
                manifest.update({"status": result["status"], "finished_at": datetime.now(timezone.utc).isoformat()})
                artifacts = {"manifest": manifest, "facts": result.get("facts", []),
                             "evidence": result.get("evidence", []), "validation": result.get("validation", {}),
                             "report": result.get("report", {})}
                for name, payload in artifacts.items():
                    path = directory / (name + ".json")
                    write_json(path, payload)
                    result["artifact_paths"][name] = str(path)
                (directory / "report.md").write_text(markdown_report(result), encoding="utf-8")
                result["artifact_paths"].update({"markdown": str(directory / "report.md"),
                                                 "log": str(directory / "run.log"), "result": str(directory / "result.json")})
                write_json(directory / "result.json", result)
            except Exception as error:
                result.update({"status": "failed", "artifact_paths": {},
                               "validation": {"status": "failed", "issues": [{"code": "artifact_write_failed", "severity": "blocking"}]},
                               "error": {"type": "ArtifactWriteError", "message": str(error)}})
                if isinstance(result.get("report"), dict):
                    result["report"]["status"] = "failed"
                try:
                    write_json(directory / "manifest.json", {**manifest, "status": "failed"})
                    write_json(directory / "result.json", result)
                except OSError:
                    logger.exception("Unable to persist failure; disregard incomplete run directory")
            if handler:
                logger.removeHandler(handler)
                handler.close()
    return result
