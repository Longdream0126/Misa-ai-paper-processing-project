from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from misa.web.server import Handler

from . import fixtures


class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=3)

    # ---------------- helpers ----------------

    def url(self, path: str) -> str:
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path: str) -> tuple[int, bytes]:
        with urllib.request.urlopen(self.url(path), timeout=5) as r:
            return r.status, r.read()

    def post(self, path: str, payload: dict | None = None,
             raw: bytes | None = None) -> tuple[int, dict]:
        body = raw if raw is not None else json.dumps(payload or {}).encode("utf-8")
        req = urllib.request.Request(self.url(path), data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    # ---------------- 静态页面 ----------------

    def test_health(self):
        status, body = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)["ok"])

    def test_index(self):
        status, body = self.get("/")
        self.assertEqual(status, 200)
        text = body.decode("utf-8")
        self.assertIn("misa", text)
        self.assertIn("panel-analyze", text)

    def test_static_assets(self):
        for path in ("/static/styles.css", "/static/app.js"):
            with self.subTest(path=path):
                status, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertGreater(len(body), 1000)

    def test_favicon(self):
        for path in ("/favicon.ico", "/favicon.svg", "/static/favicon.svg"):
            with self.subTest(path=path):
                status, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertIn(b"<svg", body)

    def test_path_traversal_blocked(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/static/../server.py")
        self.assertIn(ctx.exception.code, (403, 404))

    # ---------------- API ----------------

    def test_analyze_api(self):
        status, data = self.post("/api/analyze", {"text": (
            "Moreover, it is important to note that utilizing a comprehensive framework "
            "can facilitate optimization. Furthermore, this plays a crucial role in growth."
        )})
        self.assertEqual(status, 200)
        self.assertGreater(data["score"], 60)
        self.assertTrue(data["features"])
        self.assertIn("disclaimer", data)

    def test_analyze_empty(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/analyze", {"text": "  "})
        self.assertEqual(ctx.exception.code, 400)

    def test_analyze_bad_json(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post("/api/analyze", raw=b"{not json")
        self.assertEqual(ctx.exception.code, 400)

    def test_humanize_api(self):
        status, data = self.post("/api/humanize", {
            "text": "It is important to note that we delve into the details. Furthermore, we utilize it.",
            "level": "standard",
        })
        self.assertEqual(status, 200)
        self.assertNotIn("delve into", data["text"].lower())
        self.assertLess(data["after"]["score"], data["before"]["score"])

    def test_scan_text_api(self):
        status, data = self.post("/api/scan-text", {"text": "hi\u200bthere\u200b"})
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 2)

    def test_clean_text_api(self):
        status, data = self.post("/api/clean-text", {"text": "a\u200bb"})
        self.assertEqual(status, 200)
        self.assertEqual(data["text"], "ab")

    def test_watermark_api(self):
        status, data = self.post("/api/watermark", {"key": "abc", "length": 60})
        self.assertEqual(status, 200)
        self.assertGreater(data["marked"]["z"], 3)
        self.assertIn("note", data)

    def test_file_api_png(self):
        png = fixtures.build_png(texts={"Software": "Midjourney v6"})
        status, data = self.post("/api/file?name=a.png", raw=png)
        self.assertEqual(status, 200)
        self.assertEqual(data["kind"], "png")
        self.assertTrue(any(f["key"] == "Software" for f in data["findings"]))
        self.assertTrue(data["strippable"])

    def test_strip_api_png(self):
        import base64

        png = fixtures.build_png(texts={"Software": "Sora"})
        status, data = self.post("/api/strip?name=a.png", raw=png)
        self.assertEqual(status, 200)
        self.assertEqual(data["removed"], ["Software"])
        stripped = base64.b64decode(data["download"])
        self.assertNotIn(b"Sora", stripped)
        self.assertTrue(stripped.startswith(b"\x89PNG"))

    def test_samples_endpoint(self):
        status, body = self.get("/api/samples")
        samples = json.loads(body)["samples"]
        self.assertGreaterEqual(len(samples), 4)
        self.assertTrue(all("text" in s for s in samples))


if __name__ == "__main__":
    unittest.main()
