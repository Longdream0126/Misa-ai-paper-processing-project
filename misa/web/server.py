"""本地网页界面：标准库 http.server，不依赖 Flask/FastAPI。

所有请求都在本机处理，不发送任何数据到外部。默认只监听 127.0.0.1。
"""

from __future__ import annotations

import base64
import json
import mimetypes
import threading
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .. import __author__, __project__, __release__, __version__, i18n
from ..analysis.calibration import Calibration
from ..analysis.features import analyze
from ..transform.humanize import humanize
from ..watermark import metadata, toy_lm, unicode_scan
from ..watermark.greenlist import detect_text

STATIC_DIR = (Path(__file__).parent / "static").resolve()
MAX_BODY = 8 * 1024 * 1024  # 8 MB

TOOL_INFO = {
    "project": __project__,
    "author": __author__,
    "release": __release__,
    "version": __version__,
    "signature": f"本项目由 {__author__} 制作 · v{__release__}",
}


class Handler(BaseHTTPRequestHandler):
    server_version = f"misa/{__version__}"
    protocol_version = "HTTP/1.1"

    def handle(self) -> None:
        """浏览器关 keep-alive 连接时会抛 ConnectionResetError，属正常现象，
        没必要在控制台堆一屏 traceback 吓人。"""
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass

    # ---------------- 基础工具 ----------------

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _error(self, code: int, message: str) -> None:
        self._json(code, {"error": message})

    def _read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > MAX_BODY:
            raise ValueError("内容过大（上限 8 MB）")
        return self.rfile.read(length) if length else b""

    def _read_json(self) -> dict:
        raw = self._read_body()
        if not raw:
            return {}
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"请求体不是合法 JSON：{exc}") from exc
        return data if isinstance(data, dict) else {}

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(fmt, *args)

    # ---------------- 路由 ----------------

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._serve_file(STATIC_DIR / "index.html")
        if path in ("/favicon.ico", "/favicon.svg"):
            return self._serve_file(STATIC_DIR / "favicon.svg")
        if path.startswith("/static/"):
            name = unquote(path[len("/static/"):])
            target = (STATIC_DIR / name).resolve()
            if not target.is_relative_to(STATIC_DIR):
                return self._error(403, "越界路径")
            return self._serve_file(target)
        if path == "/api/i18n":
            loc = i18n.resolve(parse_qs(urlparse(self.path).query).get("locale", [None])[0])
            return self._json(200, {
                "locale": loc,
                "locales": list(i18n.LOCALES),
                "names": i18n.LOCALE_NAMES,
                "strings": i18n.strings(loc),
            })
        if path == "/api/health":
            return self._json(200, {"ok": True, **TOOL_INFO})
        if path == "/api/samples":
            return self._json(200, {"samples": _list_samples(), "tool": TOOL_INFO})
        return self._error(404, "not found")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/analyze":
                return self._api_analyze()
            if path == "/api/humanize":
                return self._api_humanize()
            if path == "/api/scan-text":
                return self._api_scan_text()
            if path == "/api/clean-text":
                return self._api_clean_text()
            if path == "/api/watermark":
                return self._api_watermark()
            if path == "/api/file":
                return self._api_file(parsed.query)
            if path == "/api/strip":
                return self._api_strip(parsed.query)
            return self._error(404, "not found")
        except ValueError as exc:
            return self._error(400, str(exc))
        except NotImplementedError as exc:
            return self._error(422, str(exc))
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            return self._error(500, f"{type(exc).__name__}: {exc}")

    # ---------------- 静态文件 ----------------

    def _serve_file(self, target: Path) -> None:
        if not target.is_file():
            return self._error(404, "文件不存在")
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in {"application/javascript", "application/json"}:
            ctype += "; charset=utf-8"
        self._send(200, target.read_bytes(), ctype)

    # ---------------- API ----------------

    def _api_analyze(self) -> None:
        data = self._read_json()
        text = str(data.get("text") or "")
        if not text.strip():
            return self._error(400, "文本是空的")
        lang = data.get("lang") or None
        cal = None
        if data.get("calibration"):
            try:
                cal = Calibration.from_dict(data["calibration"])
            except (TypeError, KeyError, ValueError):
                cal = None
        result = analyze(text, lang, cal)
        payload = result.to_dict(data.get("locale"))
        payload["tool"] = TOOL_INFO
        self._json(200, payload)

    def _api_humanize(self) -> None:
        data = self._read_json()
        text = str(data.get("text") or "")
        if not text.strip():
            return self._error(400, "文本是空的")
        result = humanize(
            text,
            level=str(data.get("level") or "standard"),
            lang=data.get("lang") or None,
            use_contractions=bool(data.get("contractions", True)),
            normalize_typography=bool(data.get("typography", False)),
        )
        payload = result.to_dict(data.get("locale"))
        payload["tool"] = TOOL_INFO
        self._json(200, payload)

    def _api_scan_text(self) -> None:
        data = self._read_json()
        text = str(data.get("text") or "")
        report = unicode_scan.scan_invisible(text, data.get("locale"))
        self._json(200, report)

    def _api_clean_text(self) -> None:
        data = self._read_json()
        text = str(data.get("text") or "")
        mode = str(data.get("mode") or "default")
        cleaned, info = unicode_scan.clean_invisible(text, mode=mode)
        info["text"] = cleaned
        self._json(200, info)

    def _api_watermark(self) -> None:
        data = self._read_json()
        key = str(data.get("key") or "misa-demo")
        length = int(data.get("length") or 120)
        gamma = float(data.get("gamma") or 0.25)
        if not key:
            return self._error(400, "密钥不能为空")
        length = max(30, min(400, length))
        demo = toy_lm.demo(key, length, gamma=gamma, locale=data.get("locale"))
        if data.get("detect_text"):
            demo["custom_detect"] = detect_text(str(data["detect_text"]), key, gamma).to_dict()
        demo["tool"] = TOOL_INFO
        self._json(200, demo)

    def _api_file(self, query: str) -> None:
        qs = parse_qs(query)
        name = (qs.get("name") or ["upload.bin"])[0]
        locale = (qs.get("locale") or [None])[0]
        data = self._read_body()
        if not data:
            return self._error(400, "空文件")
        report = metadata.inspect_bytes(data, name, locale).to_dict()
        kind = report["kind"]
        if kind == "text":
            report["invisible"] = unicode_scan.scan_invisible(
                data.decode("utf-8", "replace"), locale)
        report["strippable"] = kind in {"png", "jpeg", "docx", "xlsx", "pptx"}
        report["tool"] = TOOL_INFO
        self._json(200, report)

    def _api_strip(self, query: str) -> None:
        name = (parse_qs(query).get("name") or ["upload.bin"])[0]
        drop_exif = (parse_qs(query).get("drop_exif") or ["0"])[0] in {"1", "true"}
        data = self._read_body()
        if not data:
            return self._error(400, "空文件")
        stripped, info = metadata.strip_bytes(data, name, drop_exif=drop_exif)
        p = Path(name)
        info["name"] = f"{p.stem}.clean{p.suffix}"
        info["download"] = base64.b64encode(stripped).decode("ascii")
        self._json(200, info)


def _list_samples() -> list[dict]:
    root = Path(__file__).resolve().parents[2] / "data" / "samples"
    if not root.is_dir():
        return []
    out = []
    for p in sorted(root.glob("*.txt")):
        out.append({
            "name": p.name,
            "label": p.stem.replace("_", " "),
            "kind": "ai" if "ai_" in p.name else "human",
            "lang": "zh" if p.name.startswith("zh") else "en",
            "text": p.read_text(encoding="utf-8")[:6000],
        })
    return out


def serve(host: str = "127.0.0.1", port: int = 8765, open_browser: bool = False) -> None:
    try:
        httpd = ThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        print(f"无法监听 {host}:{port} —— {exc}", file=__import__("sys").stderr)
        print("换一个端口试试：misa serve --port 8766", file=__import__("sys").stderr)
        raise SystemExit(2) from exc

    url = f"http://{host}:{port}"
    print(f"{__project__}  v{__release__}", flush=True)
    print(f"本项目由 {__author__} 制作", flush=True)
    print(f"已启动 → {url}", flush=True)
    print("所有文本只在本机处理；按 Ctrl+C 停止。", flush=True)
    if open_browser:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()
