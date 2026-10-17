"""Command-line entry point.

    misa analyze draft.txt
    misa humanize draft.txt -o rewritten.txt --diff
    misa scan photo.png contract.docx
    misa strip photo.png
    misa watermark --key my-key
    misa serve
"""



import argparse
import json
import sys
from pathlib import Path

from . import __attribution__, __author__, __project__, __release__, __version__, i18n, report as R
from .analysis.calibration import Calibration, fit, load_corpus_dir
from .analysis.features import analyze
from .transform.humanize import humanize
from .watermark import metadata, toy_lm, unicode_scan
from .watermark.greenlist import detect_text


def _utf8_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def read_source(src: str) -> str:
    if src == "-":
        return sys.stdin.read()
    try:
        p = Path(src)
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")
    except (OSError, ValueError):
        pass
    return src


def _painter(args) -> R.Painter:
    if getattr(args, "no_color", False):
        return R.Painter(False)
    return R.Painter(R.color_enabled())


# --------------------------------------------------------------------------
# subcommands
# --------------------------------------------------------------------------


def cmd_analyze(args) -> int:
    text = read_source(args.source)
    if not text.strip():
        print(i18n.t("report.no_content", args.lang), file=sys.stderr)
        return 2
    cal = Calibration.load(args.calibration) if args.calibration else None
    result = analyze(text, args.text_lang, cal)
    payload = result.to_dict(args.lang)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(R.render_analysis(payload, _painter(args), args.sentences))
    if args.fail_above is not None and result.score > args.fail_above:
        return 3
    return 0


def cmd_humanize(args) -> int:
    text = read_source(args.source)
    if not text.strip():
        print(i18n.t("report.no_content", args.lang), file=sys.stderr)
        return 2
    result = humanize(
        text,
        level=args.level,
        lang=args.text_lang,
        use_contractions=not args.no_contractions,
        normalize_typography=args.normalize_typography,
    )
    if args.out:
        Path(args.out).write_text(result.text + "\n", encoding="utf-8")
    payload = result.to_dict(args.lang)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.text_only:
        print(result.text)
    else:
        print(R.render_humanize(payload, _painter(args), show_text=not args.no_text))
        if args.diff:
            print()
            print(R.render_diff(result.before.text, result.text))
    if args.out and not args.json:
        print(f"\nwritten to {args.out}", file=sys.stderr)
    return 0


def cmd_clean(args) -> int:
    text = read_source(args.source)
    cleaned, info = unicode_scan.clean_invisible(text, mode=args.mode)
    if args.out:
        Path(args.out).write_text(cleaned, encoding="utf-8")
        print(f"removed {info['total']} invisible characters -> {args.out}", file=sys.stderr)
    else:
        print(cleaned)
        if info["total"]:
            print(f"\n[removed {info['total']} invisible characters]", file=sys.stderr)
    if args.json:
        print(R.to_json(info), file=sys.stderr)
    return 0


def cmd_scan(args) -> int:
    paint = _painter(args)
    payload = []
    for raw in args.paths:
        p = Path(raw)
        if not p.is_file():
            print(f"skipped (not a file): {raw}", file=sys.stderr)
            continue
        data = p.read_bytes()
        kind = metadata.detect_kind(data, p.name)
        if args.json:
            entry = {"path": str(p), "kind": kind}
            if kind == "text":
                entry["invisible"] = unicode_scan.scan_invisible(data.decode("utf-8", "replace"), args.lang)
            entry["metadata"] = metadata.inspect_bytes(data, p.name, args.lang).to_dict()
            payload.append(entry)
            continue
        print()
        if kind == "text":
            text = data.decode("utf-8", "replace")
            print(R.render_invisible(unicode_scan.scan_invisible(text, args.lang), paint))
            print()
        print(R.render_meta(metadata.inspect_bytes(data, p.name, args.lang).to_dict(), paint))
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_strip(args) -> int:
    try:
        result = metadata.strip_path(args.path, args.out, drop_exif=args.drop_exif)
    except NotImplementedError as exc:
        print(f"cannot strip: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"已清理 {result['count']} 项：{', '.join(result['removed']) or '无'}")
        print(f"{result['bytes_before']} -> {result['bytes_after']} bytes")
        print(f"output: {result['output']}")
    return 0


def cmd_watermark(args) -> int:
    paint = _painter(args)
    if args.detect:
        text = read_source(args.detect)
        res = detect_text(text, args.key, args.gamma)
        if args.json:
            print(R.to_json(res))
        else:
            print(f"key {args.key} · gamma={args.gamma}")
            print(f"green {res.green}/{res.n_pairs} = {res.green / max(1, res.n_pairs):.2%}   z = {res.z:.2f}   p = {res.p_value:.2e}")
            print(res.verdict)
        return 0
    demo = toy_lm.demo(args.key, args.length, gamma=args.gamma, locale=args.lang)
    if args.json:
        print(json.dumps(demo, ensure_ascii=False, indent=2))
    else:
        print(R.render_watermark(demo, paint))
    return 0


def cmd_serve(args) -> int:
    from .web.server import serve

    serve(host=args.host, port=args.port, open_browser=args.open)
    return 0


def cmd_calibrate(args) -> int:
    human_texts, ai_texts = load_corpus_dir(args.dir)
    if not human_texts or not ai_texts:
        print("no .txt files in human/ or ai/", file=sys.stderr)
        return 2
    cal = fit(human_texts, ai_texts, args.text_lang)
    if args.json:
        print(R.to_json(cal))
    else:
        print(f"human samples: {cal.n_human} · AI samples: {cal.n_ai}")
        print(f"{'feature':<14}{'human':>10}{'AI':>10}{'sep':>9}{'weight':>9}")
        for key, spec in cal.features.items():
            print(f"{key:<14}{spec['human']:>10.3f}{spec['ai']:>10.3f}{spec.get('sep', 0):>9.2f}{spec['weight']:>9.3f}")
        for note in cal.notes:
            print("\n! " + note)
    if args.write:
        cal.save(args.write)
        print(f"\nwritten to {args.write}", file=sys.stderr)
    return 0


def cmd_demo(args) -> int:
    paint = _painter(args)
    root = Path(__file__).resolve().parent.parent / "data" / "samples"
    print(paint.bold(f"\n{__project__}  v{__release__}"))
    print(paint.dim(f"{__attribution__}\n"))
    print(paint.bold("\n=== 1. bundled samples, scored ==="))
    if root.is_dir():
        for p in sorted(root.glob("*.txt")):
            r = analyze(p.read_text(encoding="utf-8"))
            tag = "AI" if "ai_" in p.name else "human"
            print(f"  {p.name:<24} [{tag}]  {r.score:3d}/100  {r.to_dict(args.lang)['band']}")
    else:
        print("  (data/samples not found, skipping)")

    zh = root / "zh_ai_report.txt"
    en = root / "en_ai_product.txt"
    print(paint.bold("\n=== 2. rewriting ==="))
    for sample in (en, zh):
        if not sample.is_file():
            continue
        res = humanize(sample.read_text(encoding="utf-8"))
        print(f"\n  {sample.name}: {res.before.score} → {res.after.score}")
        print("  " + res.text.replace("\n", "\n  ")[:700] + "…")

    print(paint.bold("\n=== 3. watermark demo ==="))
    print(R.render_watermark(toy_lm.demo("misa-demo", 90, locale=args.lang), paint))
    print("\nnext: misa serve  # open the web UI")
    return 0


# --------------------------------------------------------------------------
# parser
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="misa",
        description=f"{__project__} v{__release__} — local AI-writing signal analysis, "
                    f"style rewriting and invisible-mark scanning (zero dependencies)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  misa analyze draft.txt\n"
            "  misa humanize draft.txt --level strong -o rewritten.txt --diff\n"
            "  misa scan photo.png contract.docx\n"
            "  misa watermark --key my-key\n"
            "  misa serve --open\n"
            "\n"
            f"{__attribution__}\n"
        ),
    )
    p.add_argument(
        "--lang", choices=i18n.LOCALES, default=None,
        help="interface language: en, zh-CN, zh-TW, ja (default: system locale, else en)",
    )
    p.add_argument(
        "-V", "--version",
        action="version",
        version=f"{__project__} v{__release__} · made by {__author__}",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="score a text for AI-like style")
    a.add_argument("source", help="file path, - for stdin, or a literal string")
    a.add_argument("--text-lang", choices=["en", "zh"], help="force the text language")
    a.add_argument("--json", action="store_true")
    a.add_argument("--no-color", action="store_true")
    a.add_argument("--sentences", type=int, default=5, help="how many top sentences to show")
    a.add_argument("--calibration", help="calib.json produced by `misa calibrate`")
    a.add_argument("--fail-above", type=int, default=None,
                   help="exit with code 3 when the score exceeds this value (for CI)")
    a.set_defaults(func=cmd_analyze)

    h = sub.add_parser("humanize", help="rewrite a text to look less AI-generated")
    h.add_argument("source")
    h.add_argument("--level", choices=["light", "standard", "strong"], default="standard")
    h.add_argument("--text-lang", choices=["en", "zh"])
    h.add_argument("-o", "--out", help="write the result to a file")
    h.add_argument("--json", action="store_true")
    h.add_argument("--diff", action="store_true")
    h.add_argument("--text-only", action="store_true", help="print only the rewritten text")
    h.add_argument("--no-text", action="store_true", help="print only the report")
    h.add_argument("--no-contractions", action="store_true", help="do not add English contractions")
    h.add_argument("--normalize-typography", action="store_true", help="convert CJK punctuation to full width")
    h.add_argument("--no-color", action="store_true")
    h.set_defaults(func=cmd_humanize)

    c = sub.add_parser("clean", help="remove invisible characters from text")
    c.add_argument("source")
    c.add_argument("--mode", choices=["default", "all", "zero-width"], default="default")
    c.add_argument("-o", "--out")
    c.add_argument("--json", action="store_true")
    c.set_defaults(func=cmd_clean)

    s = sub.add_parser("scan", help="inspect files: invisible characters, metadata, C2PA")
    s.add_argument("paths", nargs="+")
    s.add_argument("--json", action="store_true")
    s.add_argument("--no-color", action="store_true")
    s.set_defaults(func=cmd_scan)

    st = sub.add_parser("strip", help="strip metadata from PNG / JPEG / Office files")
    st.add_argument("path")
    st.add_argument("-o", "--out")
    st.add_argument("--drop-exif", action="store_true",
                    help="also drop EXIF (loses camera data and orientation)")
    st.add_argument("--json", action="store_true")
    st.set_defaults(func=cmd_strip)

    w = sub.add_parser("watermark", help="statistical watermark demo / detection")
    w.add_argument("--key", default="misa-demo", help="watermark key")
    w.add_argument("--gamma", type=float, default=0.25)
    w.add_argument("--detect", metavar="FILE", help="check a file with this key instead of running the demo")
    w.add_argument("--length", type=int, default=140, help="demo length in tokens")
    w.add_argument("--json", action="store_true")
    w.add_argument("--no-color", action="store_true")
    w.set_defaults(func=cmd_watermark)

    sv = sub.add_parser("serve", help="start the local web UI")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8765)
    sv.add_argument("--open", action="store_true", help="open the browser after start")
    sv.set_defaults(func=cmd_serve)

    cal = sub.add_parser("calibrate", help="re-fit the weights on your own corpus")
    cal.add_argument("dir", help="corpus root containing human/ and ai/ subfolders")
    cal.add_argument("--text-lang", choices=["en", "zh"])
    cal.add_argument("--write", metavar="FILE", help="write the result as JSON")
    cal.add_argument("--json", action="store_true")
    cal.set_defaults(func=cmd_calibrate)

    d = sub.add_parser("demo", help="run the full demo")
    d.add_argument("--no-color", action="store_true")
    d.set_defaults(func=cmd_demo)

    # Also accept --lang after the subcommand (argparse only defines it globally).
    for sp in sub.choices.values():
        sp.add_argument("--lang", choices=i18n.LOCALES, default=argparse.SUPPRESS,
                        help=argparse.SUPPRESS)
    return p


def main(argv: list[str] | None = None) -> int:
    _utf8_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\ninterrupted.", file=sys.stderr)
        return 130
    except FileNotFoundError as exc:
        print(f"file not found: {exc}", file=sys.stderr)
        return 2
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
