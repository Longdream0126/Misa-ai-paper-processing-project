"""测试用的文件构造器：手工拼出最小可用的 PNG / JPEG / DOCX / PDF。"""

from __future__ import annotations

import io
import struct
import zipfile
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _png_chunk(ctype: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + ctype
        + data
        + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    )


def build_png(width: int = 4, height: int = 4, texts: dict[str, str] | None = None,
              include_exif: bool = False, c2pa: bool = False) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes([200, 40, 40] * width) for _ in range(height))
    out = bytearray(PNG_SIG)
    out += _png_chunk(b"IHDR", ihdr)
    for key, val in (texts or {}).items():
        out += _png_chunk(b"tEXt", key.encode("latin-1") + b"\x00" + val.encode("latin-1"))
    if include_exif:
        out += _png_chunk(b"eXIf", b"II*\x00\x08\x00\x00\x00\x00\x00")
    if c2pa:
        out += _png_chunk(b"caBX", b"\x00\x00\x00\x10jumb" + b"\x00" * 8)
    out += _png_chunk(b"IDAT", zlib.compress(raw))
    out += _png_chunk(b"IEND", b"")
    return bytes(out)


def _jpeg_segment(marker: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([marker]) + struct.pack(">H", len(payload) + 2) + payload


def build_jpeg(xmp: str | None = None, comment: str | None = None) -> bytes:
    out = bytearray(b"\xff\xd8")
    out += _jpeg_segment(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
    if xmp:
        out += _jpeg_segment(
            0xE1, b"http://ns.adobe.com/xap/1.0/\x00" + xmp.encode("utf-8")
        )
    if comment:
        out += _jpeg_segment(0xFE, comment.encode("latin-1"))
    out += _jpeg_segment(0xDB, b"\x00" + bytes(64))
    out += b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00" + b"\x12\x34\x56\xff\xd9"
    return bytes(out)


CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:creator>{creator}</dc:creator>
  <cp:lastModifiedBy>{creator}</cp:lastModifiedBy>
  <cp:revision>7</cp:revision>
</cp:coreProperties>"""

APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>{app}</Application>
  <AppVersion>16.0000</AppVersion>
  <Company>Example Inc.</Company>
</Properties>"""

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

DOCUMENT_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body>
</w:document>"""


def build_docx(creator: str = "ChatGPT", app: str = "Microsoft Office Word") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", "<Relationships/>")
        z.writestr("word/document.xml", DOCUMENT_XML)
        z.writestr("docProps/core.xml", CORE_XML.format(creator=creator))
        z.writestr("docProps/app.xml", APP_XML.format(app=app))
    return buf.getvalue()


def build_pdf(producer: str = "Microsoft Word 2021") -> bytes:
    body = f"%PDF-1.4\n1 0 obj\n<< /Producer ({producer}) /Creator (Writer) >>\nendobj\n%%EOF\n"
    return body.encode("latin-1")


def make_watermarked_text(hits: int = 12, key: str = "test-key") -> str:
    """模拟一段带绿名单水印的文本（纯字母 token，且避免退化成同一对 token 重复）。"""
    from misa.watermark.greenlist import GreenList

    gl = GreenList(key, 0.25)
    letters = "abcdefghijklmnopqrstuvwxyz"
    pool = [f"z{letters[i % 26]}{letters[(i // 26) % 26]}" for i in range(400)]
    tokens = ["start"]
    for i in range(hits):
        prev = tokens[-1]
        greens = [w for w in pool if w != prev and gl.is_green(w, prev)]
        tokens.append(greens[(i * 13) % len(greens)])
    return " ".join(tokens)
