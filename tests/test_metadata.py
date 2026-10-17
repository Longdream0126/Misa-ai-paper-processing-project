from __future__ import annotations

import unittest

from misa.watermark import metadata

from . import fixtures


class KindTests(unittest.TestCase):
    def test_detect(self):
        self.assertEqual(metadata.detect_kind(fixtures.build_png()), "png")
        self.assertEqual(metadata.detect_kind(fixtures.build_jpeg()), "jpeg")
        self.assertEqual(metadata.detect_kind(fixtures.build_pdf()), "pdf")
        self.assertEqual(metadata.detect_kind(fixtures.build_docx()), "docx")
        self.assertEqual(metadata.detect_kind(b"just some text here"), "text")


class PngTests(unittest.TestCase):
    def test_finds_text_chunk(self):
        data = fixtures.build_png(texts={"Software": "Midjourney v6"})
        rep = metadata.inspect_bytes(data, "a.png")
        self.assertEqual(rep.kind, "png")
        keys = [f.key for f in rep.findings]
        self.assertIn("Software", keys)
        self.assertTrue(any("Midjourney" in f.value for f in rep.findings))

    def test_detects_c2pa(self):
        data = fixtures.build_png(c2pa=True)
        rep = metadata.inspect_bytes(data, "a.png")
        self.assertTrue(rep.has_c2pa)

    def test_strip_removes_text(self):
        data = fixtures.build_png(texts={"Software": "DALL-E", "Author": "bot"})
        stripped, info = metadata.strip_bytes(data, "a.png")
        self.assertEqual(sorted(info["removed"]), ["Author", "Software"])
        stripped_rep = metadata.inspect_bytes(stripped, "a.png")
        self.assertEqual(stripped_rep.findings, [])
        self.assertTrue(stripped.startswith(metadata.PNG_SIG))
        self.assertEqual(stripped[-8:-4], b"IEND")

    def test_strip_keeps_exif_by_default(self):
        data = fixtures.build_png(include_exif=True)
        stripped, info = metadata.strip_bytes(data, "a.png")
        self.assertNotIn("eXIf", info["removed"])
        self.assertIn(b"eXIf", stripped)

    def test_strip_exif_when_asked(self):
        data = fixtures.build_png(include_exif=True)
        stripped, info = metadata.strip_bytes(data, "a.png", drop_exif=True)
        self.assertIn("eXIf", info["removed"])
        self.assertNotIn(b"eXIf", stripped)

    def test_exif_kept_by_default(self):
        # 默认保留 eXIf 是刻意的：方向信息在里面
        data = fixtures.build_png(include_exif=True)
        _, info = metadata.strip_bytes(data, "a.png")
        self.assertFalse(info["removed"])


class JpegTests(unittest.TestCase):
    def test_finds_xmp(self):
        xmp = (
            '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF>'
            "<rdf:Description><Software>Adobe Firefly</Software>"
            "<DigitalSourceType>trainedAlgorithmicMedia</DigitalSourceType>"
            "</rdf:Description></rdf:RDF></x:xmpmeta>"
        )
        rep = metadata.inspect_bytes(fixtures.build_jpeg(xmp=xmp), "a.jpg")
        self.assertEqual(rep.kind, "jpeg")
        keys = [f.key for f in rep.findings]
        self.assertIn("Software", keys)
        self.assertIn("DigitalSourceType", keys)
        self.assertTrue(any("Firefly" in h for h in rep.ai_hints))

    def test_strip_removes_xmp_and_comment(self):
        xmp = "<x:xmpmeta><Software>Midjourney</Software></x:xmpmeta>"
        data = fixtures.build_jpeg(xmp=xmp, comment="generated")
        stripped, info = metadata.strip_bytes(data, "a.jpg")
        self.assertIn("XMP", info["removed"])
        self.assertIn("COM", info["removed"])
        self.assertNotIn(b"Midjourney", stripped)
        self.assertTrue(stripped.startswith(b"\xff\xd8"))
        self.assertTrue(stripped.endswith(b"\xff\xd9"))
        # 压缩数据（SOS 之后的部分）必须原样保留
        self.assertIn(b"\x12\x34\x56", stripped)


class OoxmlTests(unittest.TestCase):
    def test_finds_core_props(self):
        rep = metadata.inspect_bytes(fixtures.build_docx(), "a.docx")
        values = {f.key: f.value for f in rep.findings}
        self.assertEqual(values.get("creator"), "ChatGPT")
        self.assertEqual(values.get("last modified by"), "ChatGPT")
        self.assertEqual(values.get("application"), "Microsoft Office Word")

    def test_strip_rewrites_docprops(self):
        data = fixtures.build_docx(creator="ChatGPT")
        stripped, info = metadata.strip_bytes(data, "a.docx")
        self.assertTrue(info["removed"])
        rep = metadata.inspect_bytes(stripped, "a.docx")
        self.assertEqual(rep.findings, [])
        # 正文必须还在
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(stripped)) as z:
            self.assertIn("word/document.xml", z.namelist())
            self.assertIn(b"Hello", z.read("word/document.xml"))

    def test_pdf_not_supported_for_strip(self):
        with self.assertRaises(NotImplementedError):
            metadata.strip_bytes(fixtures.build_pdf(), "a.pdf")

    def test_pdf_inspect(self):
        rep = metadata.inspect_bytes(fixtures.build_pdf("Canva"), "a.pdf")
        self.assertEqual(rep.kind, "pdf")
        self.assertTrue(any("Canva" in f.value for f in rep.findings))


class TextTests(unittest.TestCase):
    def test_text_file_scans_invisible(self):
        data = "hello\u200bworld".encode("utf-8")
        rep = metadata.inspect_bytes(data, "note.txt")
        self.assertEqual(rep.kind, "text")
        self.assertTrue(any(f.key == "invisible characters" for f in rep.findings))

    def test_strip_path_writes_new_file(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "x.png"
            src.write_bytes(fixtures.build_png(texts={"Software": "Sora"}))
            result = metadata.strip_path(src)
            self.assertTrue(Path(result["output"]).is_file())
            self.assertTrue(result["output"].endswith(".clean.png"))
            self.assertEqual(result["count"], 1)
            self.assertTrue(src.exists())  # 原文件不动


if __name__ == "__main__":
    unittest.main()
