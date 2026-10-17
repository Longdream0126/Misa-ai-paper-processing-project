# Publishing to GitHub

This machine does not have `git` or `gh` installed, so the repository could not be
pushed from here. Everything else is ready: the working tree, `.gitignore`, the MIT
licence, the English README, the tutorial, the CI workflow and this guide.

Two ways to finish the upload — pick one.

---

## Option A — upload from the browser (no tools needed)

1. Your GitHub page is already open. Click **+ → New repository**.
2. Name: `misa-ai-paper` · visibility: **Public** · do **not** initialise with a
   README, .gitignore or licence (the folder already has them).
3. On the empty repository page choose **uploading an existing file**.
4. Drag the **contents** of `D:\project\misa-ai-paper` in (the folder `misa/`,
   `tests/`, `docs/`, `data/`, `README.md`, `LICENSE`, `pyproject.toml`, …) —
   not the folder itself, so the repository root looks right.
5. Commit message: `Initial commit — Misa's AI Paper Processing Project v0.1`.
6. Optional: **Settings → Pages** and point it at `docs/` if you want the screenshots
   served as a static page.

The `.github/workflows/ci.yml` file will activate automatically: the *Actions* tab
turns green (or red) on the first push.

---

## Option B — install Git and push (recommended for later updates)

```powershell
winget install --id Git.Git -e --source winget
```

Close and reopen the terminal, then:

```powershell
cd D:\project\misa-ai-paper
git init -b main
git add .
git commit -m "feat: Misa's AI Paper Processing Project v0.1"
git remote add origin https://github.com/<your-account>/misa-ai-paper.git
git push -u origin main
```

With the GitHub CLI (`winget install GitHub.cli`) the last two lines become:

```powershell
gh repo create misa-ai-paper --public --source=. --remote=origin --push
```

The repository `publish.ps1` wraps the same sequence:

```powershell
.\publish.ps1 -Remote https://github.com/<your-account>/misa-ai-paper.git
```

---

## Before you publish — checklist

- [ ] Replace `<your-account>` in the badges at the top of `README.md`
      (two occurrences of `github.com/USER/...`).
- [ ] Replace `<your-account>` in the clone URL in `README.md` and `docs/USAGE.md`.
- [ ] Check `LICENSE` shows the name you want (currently `Misa`).
- [ ] Confirm `.gitignore` keeps `__pycache__/`, `*.clean.*` and `calib.json` out.
- [ ] Run the tests one last time:

```powershell
python -m unittest discover -s tests -t .
```

## Suggested repository metadata

| Field | Value |
| --- | --- |
| Description | Local AI-writing analysis, rewriting and invisible-mark scanning — zero dependencies, four languages |
| Topics | `ai-detection`, `watermark`, `c2pa`, `text-analysis`, `python`, `i18n`, `privacy` |
| Licence | MIT |
| Default branch | `main` |

## Release notes for v0.1

```
First public release.

- Analyze: 13 English / 6 Chinese style features, per-feature explanation, sentence heat map
- Rewrite: deterministic cliché/skeleton/contraction/sentence-length rewriting, three strengths
- Invisible marks: zero-width, tag characters, variation selectors, bidi, homoglyphs
- Files: PNG / JPEG / PDF / Office metadata + C2PA detection, stripping for PNG / JPEG / OOXML
- Watermark: green-list demonstration with right-key vs six wrong-key control
- Interface in English, 简体中文, 繁體中文, 日本語 (UI + CLI)
- Calibration on your own corpus, JSON output, CI-friendly exit codes
```
