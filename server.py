import argparse
import hmac
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from runtime.a2ui import result_messages
from runtime.runtime import write_json


ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 20 * 1024 * 1024
TERMINAL = {"succeeded", "needs_review", "failed", "interrupted"}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def validate_document(path, suffix):
    if suffix == ".pdf":
        with path.open("rb") as stream:
            if not stream.read(1024).lstrip().startswith(b"%PDF-"):
                raise ValueError("不是有效的 PDF 文件头")
    elif suffix == ".xlsx":
        try:
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if len(members) > 10000 or sum(item.file_size for item in members) > 100 * 1024 * 1024:
                    raise ValueError("Excel 解压体积超过限制")
                if "xl/workbook.xml" not in archive.namelist() or "[Content_Types].xml" not in archive.namelist():
                    raise ValueError("不是有效的 XLSX 工作簿")
        except zipfile.BadZipFile as error:
            raise ValueError("损坏的 XLSX 文件") from error
    else:
        raise ValueError("仅支持 PDF / XLSX")


class Jobs:
    def __init__(self, directory, token, workers=1, capacity=8, timeout=900):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.token = token
        self.capacity = capacity
        self.timeout = timeout
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=workers)
        self.items = {}
        for path in self.directory.glob("*/job.json"):
            item = json.loads(path.read_text(encoding="utf-8"))
            if item["status"] in {"queued", "running"}:
                item.update(status="interrupted", error="服务重启中断，请重新提交", updated_at=timestamp())
                write_json(path, item)
            self.items[item["id"]] = item

    def save(self, item):
        write_json(self.directory / item["id"] / "job.json", item)

    def snapshot(self):
        with self.lock:
            return [dict(item) for item in sorted(self.items.values(), key=lambda item: item["created_at"], reverse=True)]

    def submit(self, filename, body, demo):
        if not demo and not os.getenv("DEEPSEEK_API_KEY"):
            raise ValueError("服务器未配置 DEEPSEEK_API_KEY，请选择演示分析")
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".xlsx"}:
            raise ValueError("仅支持 PDF / XLSX")
        with self.lock:
            active = sum(item["status"] in {"queued", "running"} for item in self.items.values())
            if active >= self.capacity:
                raise OverflowError("任务队列已满，请稍后提交")
            identifier = uuid.uuid4().hex
            directory = self.directory / identifier
            directory.mkdir()
            source = directory / ("source" + suffix)
            source.write_bytes(body)
            try:
                validate_document(source, suffix)
            except Exception:
                source.unlink(missing_ok=True)
                directory.rmdir()
                raise
            item = {"id": identifier, "filename": filename, "size": len(body), "status": "queued",
                    "mode": "demo" if demo else "production", "created_at": timestamp(), "updated_at": timestamp()}
            self.save(item)
            self.items[identifier] = item
            self.executor.submit(self.run, identifier, source, demo)
            return dict(item)

    def run(self, identifier, source, demo):
        directory = self.directory / identifier
        with self.lock:
            self.items[identifier].update(status="running", updated_at=timestamp())
            self.save(self.items[identifier])
        command = [sys.executable, str(ROOT / "main.py"), "--input-file", str(source),
                   "--output-dir", str(directory / "runs"), "--run-id", identifier]
        if demo:
            command.append("--demo")
        try:
            with (directory / "stdout.log").open("wb") as output, (directory / "stderr.log").open("wb") as errors:
                process = subprocess.run(command, cwd=ROOT, stdout=output, stderr=errors, timeout=self.timeout)
            result = self.result(identifier)
            status = result.get("status")
            expected = {"succeeded": 0, "needs_review": 2, "failed": 1}
            if status not in expected or process.returncode != expected[status]:
                raise RuntimeError("分析退出码与结果不一致")
            changes = {"status": status}
            if status == "failed":
                changes["error"] = "分析失败，请查看研究结果及服务端日志"
        except subprocess.TimeoutExpired:
            changes = {"status": "failed", "error": "分析超时，进程已终止"}
        except Exception:
            changes = {"status": "failed", "error": "分析未产生有效交付结果，请检查服务器依赖与日志"}
        with self.lock:
            self.items[identifier].update(**changes, updated_at=timestamp())
            self.save(self.items[identifier])

    def result(self, identifier):
        if identifier not in self.items:
            raise KeyError(identifier)
        path = self.directory / identifier / "runs" / identifier / "result.json"
        return json.loads(path.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def send_bytes(self, status, data, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(data)

    def json(self, status, value):
        self.send_bytes(status, json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), "application/json; charset=utf-8")

    def authorized(self):
        host = self.headers.get("Host", "")
        allowed = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        origin = self.headers.get("Origin")
        if host not in allowed or (origin and origin not in {"http://" + value for value in allowed}):
            self.json(403, {"error": "不允许的来源"})
            return False
        supplied = self.headers.get("Authorization", "")
        if not hmac.compare_digest(supplied.encode(), ("Bearer " + self.server.jobs.token).encode()):
            self.json(401, {"error": "请填写服务器启动时显示的访问令牌"})
            return False
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        assets = {"/": "index.html", "/app.js": "app.js", "/a2ui.js": "a2ui.js", "/styles.css": "styles.css"}
        if path in assets:
            suffix = Path(assets[path]).suffix
            mime = {".html": "text/html", ".js": "text/javascript", ".css": "text/css"}[suffix]
            self.send_bytes(200, (ROOT / "frontend" / assets[path]).read_bytes(), mime + "; charset=utf-8")
            return
        if not self.authorized():
            return
        if path == "/api/jobs":
            self.json(200, {"jobs": self.server.jobs.snapshot(), "capacity": self.server.jobs.capacity})
            return
        preview = re.fullmatch(r"/api/jobs/([a-f0-9]{32})/pages/([1-9][0-9]{0,3})", path)
        if preview:
            identifier, number = preview.groups()
            try:
                if identifier not in self.server.jobs.items:
                    raise ValueError('Unknown job')
                source = self.server.jobs.directory / identifier / 'source.pdf'
                if not source.is_file():
                    raise ValueError('Page preview is only available for PDF')
                import fitz
                with fitz.open(source) as document:
                    if int(number) > len(document):
                        raise ValueError('Page out of range')
                    page = document[int(number) - 1]
                    scale = min(1.5, 1800 / max(page.rect.width, page.rect.height))
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    self.send_bytes(200, pixmap.tobytes('png'), 'image/png')
            except ImportError:
                self.json(503, {'error': 'Page preview requires optional PyMuPDF'})
            except (ValueError, OSError, RuntimeError):
                self.json(400, {'error': 'Unable to render requested page'})
            return
        match = re.fullmatch(r"/api/jobs/([a-f0-9]{32})/(result|ui)", path)
        if match:
            identifier, kind = match.groups()
            try:
                item = self.server.jobs.items[identifier]
                if item["status"] not in TERMINAL:
                    self.json(409, {"error": "任务尚未完成"})
                    return
                try:
                    result = self.server.jobs.result(identifier)
                except FileNotFoundError:
                    result = {"schema_version": "research-1.0", "run_id": identifier, "status": "failed",
                              "execution_mode": item["mode"], "error": item.get("error", "任务中断")}
                if item["status"] in {"failed", "interrupted"}:
                    result.update(status="failed", error=item.get("error", "任务失败"))
                if kind == "ui":
                    data = "\n".join(json.dumps(message, ensure_ascii=False) for message in result_messages(result, identifier)) + "\n"
                    self.send_bytes(200, data.encode(), "application/x-ndjson; charset=utf-8")
                else:
                    self.json(200, result)
            except (KeyError, ValueError):
                self.json(404, {"error": "任务不存在或结果损坏"})
            return
        self.json(404, {"error": "接口不存在"})

    def do_POST(self):
        if not self.authorized():
            return
        if urlsplit(self.path).path != "/api/jobs":
            self.json(404, {"error": "接口不存在"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if self.headers.get("Transfer-Encoding") or not 0 < length <= MAX_UPLOAD:
                self.close_connection = True
                self.json(413, {"error": "文件必须在 1 字节至 20 MB 之间"})
                return
            filename = unquote(self.headers.get("X-Filename", ""))
            if not filename or len(filename) > 180 or any(ord(char) < 32 for char in filename) or "/" in filename or "\\" in filename:
                raise ValueError("文件名不合法")
            mode = self.headers.get("X-Analysis-Mode", "demo")
            if mode not in {"demo", "production"}:
                raise ValueError("分析模式不合法")
            if mode == "production" and self.headers.get("X-Data-Consent") != "yes":
                raise ValueError("正式分析需要确认模型数据传输授权")
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("文件传输不完整")
            self.json(202, self.server.jobs.submit(filename, body, mode == "demo"))
        except OverflowError as error:
            self.json(429, {"error": str(error)})
        except (ValueError, OSError) as error:
            self.close_connection = True
            self.json(400, {"error": str(error)})


def main():
    parser = argparse.ArgumentParser(description="Optional single-user local research workbench")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default="workspace/web")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    token = os.getenv("RESEARCH_UI_TOKEN") or secrets.token_urlsafe(32)
    jobs = Jobs(args.data_dir, token, args.workers)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.jobs = jobs
    print(f"Open http://127.0.0.1:{server.server_port} · access token: {token}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        jobs.executor.shutdown(wait=True)


if __name__ == "__main__":
    main()
