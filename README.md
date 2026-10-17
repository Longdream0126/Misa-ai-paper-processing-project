# Misa's AI Paper Processing Project

[![CI](https://github.com/USER/misa-ai-paper/actions/workflows/ci.yml/badge.svg)](https://github.com/USER/misa-ai-paper/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

**Local AI-writing analysis, rewriting and invisible-mark scanning. Zero dependencies, nothing uploaded, no API key, no model weights.**

---

> **Made by Misa · v0.1**
>
> This tool measures *style*, not authorship. It cannot prove a text was written by a
> human or by a model, and it does not remove vendor watermarks. Read
> [What this is not](#what-this-is-not) before relying on any number it prints.

---

## Quick start

```bash
git clone https://github.com/USER/misa-ai-paper.git
cd misa-ai-paper
python -m misa serve --open      # web UI at http://127.0.0.1:8765
python -m misa demo              # or run the CLI demo
```

On Windows you can also double-click **`start.bat`** (startup self-check: **`doctor.bat`**).

Requires Python 3.10+; nothing else. The whole app is the standard library.

![Analyze tab](docs/analyze.png)

## Languages

The interface ships in four languages, switchable at runtime from the picker in the
top-right corner (or with `?lang=` / `MISA_LANG` / `--lang`):

| Code | Language |
| --- | --- |
| `en` | English (default) |
| `zh-CN` | 简体中文 |
| `zh-TW` | 繁體中文 |
| `ja` | 日本語 |

The language covers the web UI, analysis verdicts, feature names, findings and the
verdict text of every CLI report. CLI table headings stay English. It does **not**
change how the text is scored — that depends on the language of the text you paste,
not on the interface language.

## What it does

### 1. Analyze — how AI-ish does this read?

Paste text, get a 0–100 score, five bands, and a per-feature breakdown where every
number is explained:

```
AI-likeness  EN  ·  medium confidence
  ██████████████████░░   88/100  Strongly AI-like
  137 words · 7 sentences · 3 paragraphs · avg 19.6/sentence · 20 clichés
```

* **13 features for English, 6 for Chinese** — cliché density, sentence-length spread,
  contractions, nominalisation, discourse openers, short-sentence share, character
  bigram repetition, sentence particles and more.
* **Length-gated.** A feature that cannot be measured reliably on a short text is
  dropped instead of producing a wild value; the score then shrinks toward 50 and the
  confidence label drops.
* **Traceable.** Each feature shows raw value, both anchors, weight and a one-line
  explanation; the *Findings* list names the phrases that triggered it.
* **Sentence heat map** — the most AI-like sentences, with reasons.

### 2. Rewrite — make it sound human again

Deterministic rules, three strengths. Same input always gives the same output, so you
can `--diff` it.

| Action | Example |
| --- | --- |
| Cliché replacement | `it is important to note that` → `note that` |
| Skeleton flattening | `plays a crucial role in` → `is central to` |
| De-inflation | `utilize` → `use`, `facilitate` → `support` |
| Contractions | `do not` → `don't`, `you are` → `you're` |
| Opener trimming | `Furthermore,` → `plus,` |
| Long-sentence splitting | break at commas / semicolons above 30 words |
| Rhythm breaking (strong) | split one of three consecutive equal-length sentences |

Safeguards: Chinese paired constructions (`只有…才`, `不仅…而且`) are never split,
fenced code blocks are untouched, and Markdown structure survives. Every run reports
the before/after score, a content-retention figure and the count of each change.

### 3. Invisible marks — what is hiding in the text or the file

Character level (no key needed):

| Category | Code points |
| --- | --- |
| Zero-width characters | U+200B–200D, U+2060, U+FEFF, soft hyphen |
| Tag characters | U+E0000–E007F (invisible ASCII) |
| Variation selectors | U+FE00–FE0F, U+E0100–E01EF |
| Bidirectional controls | U+202A–202E, U+2066–2069 |
| Mixed-script homoglyphs | Latin + Cyrillic/Greek in one word |

Runs of 8+ invisible characters are flagged as a suspected payload.

File level: PNG text chunks, JPEG EXIF/XMP/JUMBF, Office `docProps`, PDF `/Producer`,
and C2PA content credentials. `strip` rewrites PNG / JPEG / OOXML files without
touching pixels or body text; PDFs are read-only (use `qpdf` / ExifTool).

### 4. Watermark — a working demonstration

Not a remover: a demonstration of why removal is hard.

The demo samples two passages with a toy language model — one watermarked with a
green-list scheme, one not — then checks each with the right key and with six wrong
keys:

```
1. No watermark   → z ≈ 0,      p ≈ 0.6
2. Watermarked    → z ≈ 15,     p < 1e-6
3. Six wrong keys → z in −3…+3, none detected
```

That is the whole story of statistical watermarks: with the key you can verify,
without it you see normal text.

## CLI

```bash
python -m misa analyze draft.txt                 # score + findings
python -m misa analyze draft.txt --json          # machine-readable
python -m misa analyze draft.txt --fail-above 60 # exit code 3 above threshold (CI)

python -m misa humanize draft.txt -o rewritten.txt --diff
python -m misa humanize draft.txt --level strong --text-only

python -m misa scan screenshot.png report.docx   # metadata + invisible characters
python -m misa strip screenshot.png              # -> screenshot.clean.png

python -m misa clean messy.txt -o clean.txt      # drop invisible characters
python -m misa watermark --key my-secret         # run the demo
python -m misa watermark --key k --detect bid.txt

python -m misa calibrate my-corpus --write calib.json
python -m misa analyze draft.txt --calibration calib.json

python -m misa serve --open                      # web UI
```

`--lang {en,zh-CN,zh-TW,ja}` switches the interface language for any command.

## How the score is computed

Each feature is mapped linearly onto a 0–1 sub-score between a *human* anchor and an
*AI* anchor, weighted, then squashed through a logistic curve.

| Feature | EN weight | ZH weight |
| --- | --- | --- |
| Cliché density | 0.19 | 0.28 |
| Sentence-length spread | 0.15 | 0.10 |
| Contractions | 0.12 | — |
| Discourse openers | 0.10 | — |
| Nominalisation | 0.09 | — |
| Short sentences | 0.09 | 0.14 |
| Sentence particles | — | 0.16 |
| Informal markers | 0.06 | 0.10 |
| Trigram repetition | 0.06 | — |
| Lexical variety (MATTR) | 0.04 | — |
| Rare words | 0.03 | — |
| Average word length | 0.03 | — |
| Character bigram repetition | — | 0.10 |
| Questions | 0.02 | — |
| Repeated openers | 0.02 | — |

Paragraph uniformity and punctuation diversity were deliberately left out of the
score: in testing they were dominated by genre rather than by authorship.

**The anchors were tuned on the eight bundled samples — they are a reasonable default,
not a trained model.** If you have labelled text, re-fit them:

```bash
mkdir -p my-corpus/human my-corpus/ai   # 15+ files each, similar genre and length
python -m misa calibrate my-corpus --write calib.json
python -m misa analyze draft.txt --calibration calib.json
```

## What this is not

1. **Not an authorship detector.** No local statistic can establish who wrote a text.
   Academic prose, templated marketing copy and heavily edited drafts all score high.
2. **Not a watermark remover.** Statistical watermarks (SynthID-Text and friends) are
   keyed; without the key they are invisible and cannot be surgically removed.
   Character-level marks are a different thing, and those *are* removable.
3. **Not an arms race.** The rewrite step makes prose read more naturally. It does not
   target any specific product, and no detector result should decide a grade, a
   contract or a copyright question.
4. **Not bilingual-symmetric.** English has 13 features, Chinese 6 (no reliable
   segmentation without a dependency), so Chinese separation is weaker.

## Project layout

```
misa-ai-paper/
├── misa/                  Python package (`python -m misa`)
│   ├── i18n.py            en / zh-CN / zh-TW / ja catalogue
│   ├── cli.py             command line
│   ├── report.py          terminal rendering
│   ├── analysis/          features, tokeniser, lexicons, calibration
│   ├── transform/         rewriting rules
│   ├── watermark/         Unicode scan, metadata/C2PA, green-list demo
│   └── web/               local web UI (stdlib http.server)
├── data/samples/          8 bundled samples (AI / human, EN / ZH)
├── docs/                  screenshots and notes
├── tests/                 104 tests, including synthetic PNG/JPEG/DOCX fixtures
├── start.bat / doctor.bat Windows launchers
└── pyproject.toml         packaging (`misa-paper` entry point)
```

## Tests

```bash
python -m unittest discover -s tests -t .
```

104 tests: sentence boundaries, scoring direction, feature gating, rewrite
idempotence, CJK pair protection, invisible characters, PNG/JPEG/DOCX metadata
round-trips, watermark z-scores with right and wrong keys, and the HTTP API.

## Contributing

Issues and pull requests are welcome. The most useful contributions are lexicon
entries (new clichés, per-domain phrases) and labelled corpora for calibration.

## License

MIT — see [LICENSE](LICENSE).

**Misa's AI Paper Processing Project v0.1** · made by **Misa**.
