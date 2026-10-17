"""File metadata / content credentials (C2PA): inspection and cleanup.

This is the tractable half of "invisible watermarking": generative tools almost
always leave readable metadata behind — PNG tEXt chunks, JPEG XMP, Office
docProps, PDF /Producer, and C2PA content credentials (JUMBF boxes, caBX chunks).

What this module does:
* list every field that can identify the producing tool (read-only)
* detect whether C2PA / JUMBF is present
* rewrite a file to drop those fields, when explicitly asked (PNG / JPEG / OOXML)

Note: C2PA is *cryptographically signed*. Removing it only means the file no
longer carries a credential; it does not change where the content came from.
"""

from __future__ import annotations

import io
import json
import re
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .. import i18n
from ..analysis import lexicons

PNG_SIG = b"\x89PNG\r\n\x1a\n"

AI_MARKERS = {
    "trainedalgorithmicmedia": "IPTC / C2PA generative-AI declaration (trainedAlgorithmicMedia)",
    "c2pa.ai_generative_training": "C2PA generative-training declaration",
    "c2pa.actions": "C2PA action record (may contain c2pa.created)",
    "synthid": "Google SynthID watermark marker",
    "made with google": "Google generation-tool marker",
    "imagen": "Google Imagen marker",
    "dall-e": "OpenAI DALL·E marker",
    "dall·e": "OpenAI DALL·E marker",
    "midjourney": "Midjourney marker",
    "stable diffusion": "Stable Diffusion marker",
    "firefly": "Adobe Firefly marker",
    "chatgpt": "ChatGPT marker",
    "openai": "OpenAI marker",
    "copilot": "Microsoft Copilot marker",
    "nano banana": "Google Nano Banana marker",
    "runway": "Runway marker",
    "flux.1": "FLUX marker",
    "grok": "xAI Grok marker",
}

C2PA_MARKERS = [b"c2pa", b"jumb", b"caBX", b"JUMBF", b"urn:uuid:c2pa", b"adobe:ns:meta"]


@dataclass
class Finding:
    key: str
    value: str
    source: str
    risk: str = "info"

    def to_dict(self) -> dict:
        return {"key": self.key, "value": self.value, "source": self.source, "risk": self.risk}


@dataclass
class FileReport:
    name: str
    kind: str
    size: int
    findings: list[Finding] = field(default_factory=list)
    has_c2pa: bool = False
    ai_hints: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    structure: dict = field(default_factory=dict)
    locale: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "size": self.size,
            "findings": [f.to_dict() for f in self.findings],
            "has_c2pa": self.has_c2pa,
            "ai_hints": self.ai_hints,
            "notes": self.notes,
            "structure": self.structure,
        }


# --------------------------------------------------------------------------
# kind detection
# --------------------------------------------------------------------------


def detect_kind(data: bytes, name: str = "") -> str:
    if data.startswith(PNG_SIG):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if data.startswith(b"%PDF"):
        return "pdf"
    if data.startswith(b"PK\x03\x04"):
        return _ooxml_kind(data)
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if data.startswith(b"GIF8"):
        return "gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "webp"
    head = data[:4096].lstrip()
    if head.startswith(b"<svg") or b"<svg" in head[:512]:
        return "svg"
    return "text" if _looks_like_text(data) else "unknown"


def _ooxml_kind(data: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return "zip"
    if "word/document.xml" in names:
        return "docx"
    if "xl/workbook.xml" in names:
        return "xlsx"
    if "ppt/presentation.xml" in names:
        return "pptx"
    return "zip"


def _looks_like_text(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return True
    if b"\x00" in sample:
        return False
    try:
        text = sample.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = sample.decode("gb18030")
        except UnicodeDecodeError:
            text = sample.decode("utf-8", "replace")
    if text.count("\ufffd") / max(1, len(text)) > 0.01:
        return False
    return not any(ord(c) < 9 or (13 < ord(c) < 32) for c in text)


# --------------------------------------------------------------------------
# per-format parsers
# --------------------------------------------------------------------------


def _png_chunks(data: bytes) -> list[tuple[bytes, bytes, int]]:
    out: list[tuple[bytes, bytes, int]] = []
    pos = 8
    while pos + 8 <= len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        out.append((ctype, body, pos))
        pos += 12 + length
        if ctype == b"IEND" or pos > len(data):
            break
    return out


def _png_findings(data: bytes, rep: FileReport) -> None:
    chunks = _png_chunks(data)
    types = [c[0].decode("latin-1") for c in chunks]
    rep.structure["chunks"] = sorted(set(types))
    for ctype, body, _ in chunks:
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            key, _, val = body.partition(b"\x00")
            if ctype == b"zTXt":
                key2, _, val = body.partition(b"\x00")
                key = key2
                try:
                    import zlib
                    val = zlib.decompress(val[1:])
                except Exception:
                    val = b"<cannot decompress>"
            elif ctype == b"iTXt":
                key2, _, _ = body.partition(b"\x00")
                key = key2
                parts = val.split(b"\x00")
                val = parts[-1] if parts else b""
            text = val.decode("utf-8", "replace")
            rep.findings.append(Finding(key.decode("latin-1", "replace"),
                                        text[:200], "PNG tEXt"))
        elif ctype == b"eXIf":
            rep.findings.append(Finding("eXIf", f"{len(body)} bytes of EXIF data", "PNG eXIf", "warn"))
        elif ctype == b"caBX":
            rep.has_c2pa = True
            rep.findings.append(Finding("caBX", f"{len(body)} bytes of C2PA/JUMBF manifest", "PNG caBX", "high"))
        elif ctype in (b"iCCP", b"gAMA", b"sRGB", b"pHYs"):
            continue
    if not rep.findings:
        rep.notes.append(i18n.t("meta.note.png_clean", rep.locale))


def _jpeg_segments(data: bytes) -> list[tuple[int, bytes, int]]:
    segs: list[tuple[int, bytes, int]] = []
    pos = 2
    while pos + 4 <= len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xDA:
            segs.append((marker, b"", pos))
            break
        (length,) = struct.unpack(">H", data[pos + 2:pos + 4])
        payload = data[pos + 4:pos + 2 + length]
        segs.append((marker, payload, pos))
        pos += 2 + length
    return segs


def _tiff_ascii_tags(data: bytes) -> dict[int, str]:
    out: dict[int, str] = {}
    if len(data) < 8:
        return out
    endian = "<" if data[:2] == b"II" else ">"
    try:
        (ifd,) = struct.unpack(endian + "I", data[4:8])
        if ifd + 2 > len(data):
            return out
        (count,) = struct.unpack(endian + "H", data[ifd:ifd + 2])
        for i in range(min(count, 128)):
            off = ifd + 2 + i * 12
            if off + 12 > len(data):
                break
            tag, typ, n = struct.unpack(endian + "HHI", data[off:off + 8])
            if typ not in (2, 7):
                continue
            raw = data[off + 8:off + 12]
            if n > 4:
                (ptr,) = struct.unpack(endian + "I", raw)
                chunk = data[ptr:ptr + n]
            else:
                chunk = raw[:n]
            out[tag] = chunk.rstrip(b"\x00").decode("latin-1", "replace")
    except struct.error:
        pass
    return out


def _jpeg_findings(data: bytes, rep: FileReport) -> None:
    segs = _jpeg_segments(data)
    names = {0xE0: "APP0", 0xE1: "APP1", 0xE2: "APP2", 0xED: "APP13", 0xEE: "APP14", 0xFE: "COM"}
    rep.structure["segments"] = sorted({names.get(m, f"0x{m:02X}") for m, _, _ in segs})
    for marker, payload, _ in segs:
        if marker == 0xE1 and payload.startswith(b"Exif\x00\x00"):
            tags = _tiff_ascii_tags(payload[6:])
            label = {0x0131: "Software", 0x013B: "Artist", 0x010F: "Make", 0x0110: "Model",
                     0x0132: "DateTime", 0x8298: "Copyright"}
            for tag, val in tags.items():
                rep.findings.append(Finding(label.get(tag, f"tag 0x{tag:04X}"), val, "JPEG EXIF"))
        elif marker == 0xE1 and payload.startswith(b"http://ns.adobe.com/xap/1.0/\x00"):
            xmp = payload.split(b"\x00", 1)[1].decode("utf-8", "replace")
            for key in ("Software", "CreatorTool", "DigitalSourceType", "DocumentID",
                        "InstanceID", "Artist", "Author"):
                for m in re.finditer(rf"<{key}>(.*?)</{key}>", xmp, re.S | re.I):
                    rep.findings.append(Finding(key, m.group(1).strip()[:200], "JPEG XMP"))
            for m in re.finditer(rf"{key}\s*=\s*\"([^\"]{{0,200}})\"", xmp, re.I):
                rep.findings.append(Finding(key, m.group(1), "JPEG XMP"))
            if "c2pa" in xmp.lower() or "jumbf" in xmp.lower():
                rep.has_c2pa = True
        elif marker == 0xEB or (marker == 0xE1 and b"JUMBF" in payload[:32]):
            if b"jumb" in payload.lower() or b"c2pa" in payload.lower():
                rep.has_c2pa = True
                rep.findings.append(Finding("JUMBF", f"{len(payload)} bytes of C2PA manifest", "JPEG APP11", "high"))
        elif marker == 0xED:
            rep.findings.append(Finding("APP13", "Photoshop / IPTC data", "JPEG APP13"))
        elif marker == 0xFE:
            rep.findings.append(Finding("Comment", payload[:200].decode("latin-1", "replace"), "JPEG COM"))
    if not rep.findings:
        rep.notes.append(i18n.t("meta.note.png_clean", rep.locale))


def _pdf_findings(data: bytes, rep: FileReport) -> None:
    text = data.decode("latin-1", "replace")
    keys = ["Producer", "Creator", "Author", "Title", "CreationDate", "ModDate", "Keywords"]
    for key in keys:
        for m in re.finditer(rf"/{key}\s*\((.*?)\)", text, re.S):
            val = m.group(1)[:200]
            rep.findings.append(Finding(key, val, "PDF Info dict"))
    for m in re.finditer(r"/Producer\s*<([0-9A-Fa-f\s]+)>", text):
        try:
            raw = bytes.fromhex(re.sub(r"\s", "", m.group(1)))
            val = raw.decode("utf-16-be", "replace") if raw[:2] == b"\xfe\xff" else raw.decode("latin-1")
            rep.findings.append(Finding("Producer(hex)", val[:200], "PDF Info dict"))
        except ValueError:
            pass
    meta = re.search(rb"<x:xmpmeta.*?</x:xmpmeta>", data, re.S)
    if meta:
        xmp = meta.group(0).decode("utf-8", "replace")
        for key in ("Software", "CreatorTool", "DigitalSourceType", "Producer"):
            for m in re.finditer(rf"<{key}>(.*?)</{key}>", xmp, re.S | re.I):
                rep.findings.append(Finding(key, m.group(1).strip()[:200], "PDF XMP"))
        rep.structure["xmp_bytes"] = len(meta.group(0))
    rep.notes.append(i18n.t("meta.note.pdf", rep.locale))


OOXML_FIELDS = {
    "creator": "creator",
    "lastModifiedBy": "last modified by",
    "created": "created",
    "modified": "modified",
    "title": "title",
    "revision": "revision",
    "Application": "application",
    "AppVersion": "app version",
    "Company": "company",
    "TotalTime": "editing time",
    "Pages": "pages",
    "Words": "words",
    "Template": "template",
    "lastPrinted": "last printed",
}


def _ooxml_findings(data: bytes, rep: FileReport) -> None:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        rep.notes.append(i18n.t("meta.note.no_meta", rep.locale))
        return
    with zf:
        names = zf.namelist()
        rep.structure["parts"] = [n for n in names if n.startswith("docProps/")]
        for part in ("docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"):
            if part not in names:
                continue
            try:
                from xml.etree import ElementTree as ET
                root = ET.fromstring(zf.read(part))
            except Exception as exc:  # noqa: BLE001
                rep.notes.append(f"could not parse {part}: {exc}")
                continue
            for el in root.iter():
                tag = el.tag.split("}")[-1]
                if not (el.text or "").strip():
                    continue
                label = OOXML_FIELDS.get(tag, tag)
                risk = "warn" if tag in {"creator", "lastModifiedBy", "Application", "AppVersion"} else "info"
                rep.findings.append(Finding(label, el.text.strip()[:200], part, risk))
    if not rep.findings:
        rep.notes.append(i18n.t("meta.note.no_meta", rep.locale))


def _text_findings(data: bytes, rep: FileReport) -> None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "replace")
    from .unicode_scan import scan_invisible
    result = scan_invisible(text, rep.locale)
    if result["total"]:
        rep.findings.append(Finding("invisible characters", f"{result['total']} found", "text scan", "warn"))
        rep.notes.append(result["verdict"])
    for marker, desc in AI_MARKERS.items():
        if marker in text.lower():
            rep.ai_hints.append(desc)


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------


def inspect_bytes(data: bytes, name: str = "<memory>", locale: str | None = None) -> FileReport:
    kind = detect_kind(data, name)
    rep = FileReport(name=name, kind=kind, size=len(data), locale=locale)
    rep.locale = locale
    lower = data.lower()
    if b"c2pa" in lower or b"jumb" in lower or b"jumbf" in lower:
        rep.has_c2pa = True
    as_text = data.decode("latin-1", "replace").lower()
    for marker, desc in AI_MARKERS.items():
        if marker.encode("utf-8") in lower or marker in as_text:
            rep.ai_hints.append(desc)

    if kind == "png":
        _png_findings(data, rep)
    elif kind == "jpeg":
        _jpeg_findings(data, rep)
    elif kind == "pdf":
        _pdf_findings(data, rep)
    elif kind in {"docx", "xlsx", "pptx", "zip"}:
        _ooxml_findings(data, rep)
    elif kind == "text":
        _text_findings(data, rep)
    else:
        text = data.decode("latin-1", "replace")
        for tag in lexicons.METADATA_TAGS:
            if tag.lower() in text.lower():
                rep.findings.append(Finding(tag, "appears in the file body", "string scan"))

    if kind == "text":
        rep.notes.append(i18n.t("meta.note.text", rep.locale))
    if rep.has_c2pa:
        rep.notes.append(i18n.t("meta.note.c2pa", rep.locale))
    return rep


def inspect_path(path: str | Path) -> FileReport:
    p = Path(path)
    data = p.read_bytes()
    return inspect_bytes(data, p.name)


def strip_bytes(data: bytes, name: str = "<memory>", drop_exif: bool = False) -> tuple[bytes, dict]:
    """Rewrite a file without identifying metadata; returns (new bytes, report)."""
    kind = detect_kind(data, name)
    removed: list[str] = []
    if kind == "png":
        out, removed = _strip_png(data, drop_exif)
    elif kind == "jpeg":
        out, removed = _strip_jpeg(data, drop_exif)
    elif kind in {"docx", "xlsx", "pptx"}:
        out, removed = _strip_ooxml(data)
    elif kind == "pdf":
        raise NotImplementedError("PDFs need their xref table rebuilt; use qpdf or ExifTool.")
    else:
        raise NotImplementedError(f"stripping {kind} is not supported yet.")
    return out, {"kind": kind, "removed": removed, "count": len(removed)}


def _strip_png(data: bytes, drop_exif: bool) -> tuple[bytes, list[str]]:
    drop = {b"tEXt", b"iTXt", b"zTXt", b"caBX"}
    if drop_exif:
        drop.add(b"eXIf")
    out = bytearray(PNG_SIG)
    removed: list[str] = []
    for ctype, body, pos in _png_chunks(data):
        if ctype in drop:
            if ctype in (b"tEXt", b"iTXt", b"zTXt"):
                keyword = body.partition(b"\x00")[0].decode("latin-1", "replace")
                removed.append(keyword or ctype.decode("latin-1"))
            else:
                removed.append(ctype.decode("latin-1"))
            continue
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        out += data[pos:pos + 12 + length]
    return bytes(out), removed


def _strip_jpeg(data: bytes, drop_exif: bool) -> tuple[bytes, list[str]]:
    out = bytearray(b"\xff\xd8")
    removed: list[str] = []
    keep_tail = b""
    for marker, payload, pos in _jpeg_segments(data):
        if marker == 0xDA:
            keep_tail = data[pos:]
            break
        drop = False
        if marker == 0xFE:
            drop, label = True, "COM"
        elif marker == 0xED:
            drop, label = True, "APP13"
        elif marker == 0xEB:
            drop, label = True, "APP11(JUMBF)"
        elif marker == 0xE1 and payload.startswith(b"http://ns.adobe.com/xap/1.0/"):
            drop, label = True, "XMP"
        elif marker == 0xE1 and payload.startswith(b"Exif\x00\x00") and drop_exif:
            drop, label = True, "EXIF"
        if drop:
            removed.append(label)
            continue
        raw = data[pos:pos + 2 + len(payload)]
        out += raw
    out += keep_tail
    return bytes(out), removed


def _strip_ooxml(data: bytes) -> tuple[bytes, list[str]]:
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/'
        'metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"/>'
    )
    app = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        'extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/'
        '2006/docPropsVTypes"/>'
    )
    custom = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
        'custom-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/'
        '2006/docPropsVTypes"/>'
    )
    replaced = {"docProps/core.xml": core, "docProps/app.xml": app, "docProps/custom.xml": custom}
    removed: list[str] = []
    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(data)) as src, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename in replaced:
                if src.read(info.filename).strip() != replaced[info.filename].encode("utf-8").strip():
                    removed.append(info.filename)
                dst.writestr(info, replaced[info.filename])
            else:
                dst.writestr(info, src.read(info.filename))
    return buf.getvalue(), removed


def strip_path(path: str | Path, out_path: str | Path | None = None, drop_exif: bool = False) -> dict:
    p = Path(path)
    data = p.read_bytes()
    new, report = strip_bytes(data, p.name, drop_exif=drop_exif)
    target = Path(out_path) if out_path else p.with_name(f"{p.stem}.clean{p.suffix}")
    target.write_bytes(new)
    report["input"] = str(p)
    report["output"] = str(target)
    report["bytes_before"] = len(data)
    report["bytes_after"] = len(new)
    return report


def report_to_json(rep: FileReport) -> str:
    return json.dumps(rep.to_dict(), ensure_ascii=False, indent=2)
