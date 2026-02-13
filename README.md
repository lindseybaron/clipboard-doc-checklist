# Clipto

Small automation project for capturing clipboard lines like `todo: ...` or `next: ...` and appending them into a Google Doc under configurable H1 sections, newest first.

## What this includes

- `apps_script/Code.gs`: Google Apps Script Web App (`doPost`) that writes to your Google Doc.
- `tools/clipto_watcher.py`: Python clipboard watcher that POSTs matching lines.
- `tools/healthcheck.py`: validates config and can send an end-to-end probe item.
- `tools/prepare_doc_headings.py`: creates missing H1 headings from `config.json` `tag_map`.
- `config.example.json`: user-specific config template.
- `scripts/install.sh`: one-command install + config validation + optional launchd setup.
- `scripts/bootstrap.sh`: one-command local setup (venv + deps + config scaffold).
- `scripts/uninstall.sh`: full uninstall (remove launchd + optional local cleanup).
- `scripts/install_launchagent.sh`: install/start macOS login auto-run via launchd.
- `scripts/uninstall_launchagent.sh`: remove/stop the launchd auto-run job.
- `scripts/pre-commit-block-config.sh`: optional git pre-commit guard to block `config.json`.

## Prefix routing

Case-insensitive tags map to the exact Doc section headings as defined in `config.json`. Add or edit as you'd like.

- `todo:` -> `TODO`
- `next:` -> `Next Actions`
- `idea:` -> `Ideas`
- `misc:` -> `Miscellany`
- `<tag>:` -> `Your Description Here` 

## Setup (under 10 minutes)

### Prerequisites

- macOS or Linux shell environment with `bash`
- `python3` available on `PATH` (recommended: Python 3.9+)
- internet access to install dependencies from `requirements.txt`
- a Google account to deploy the Apps Script Web App

Check your Python version before install:

```bash
python3 --version
```

### Quick start (recommended)

From the repo root:

```bash
bash scripts/install.sh
```

This command will:

- bootstrap your Python environment
- create `config.json` if missing
- validate required config fields
- optionally pre-create missing doc headings (`--prepare-headings`)
- optionally install launchd startup

Then run manually (if you skipped launchd):

```bash
source .venv/bin/activate
python tools/clipto_watcher.py
```

Or include heading pre-format during install:

```bash
bash scripts/install.sh --prepare-headings
```

Check command usage/version:

```bash
bash scripts/install.sh --help
bash scripts/install.sh --version
python3 tools/clipto_watcher.py --version
python3 tools/healthcheck.py --version
python3 tools/prepare_doc_headings.py --version
```

### 1) Prepare your Google Doc

Create a Google Doc. You can pre-create headings from your `config.json` `tag_map` values as **Heading 1**, but this is optional.

If a heading is missing, the script creates it automatically as H1.

### 2) Deploy Apps Script Web App

1. Open [https://script.google.com](https://script.google.com) and create a project.
2. Paste `apps_script/Code.gs` contents into the project.
3. In `Code.gs`, set:
   - `DOC_ID = '<YOUR_DOC_ID>'`
4. In Apps Script, enable **Advanced Google services**:
   - Click **Services (+)** in the left sidebar.
   - Add **Google Docs API**.
5. Save.
6. Deploy -> New deployment -> Web app:
   - **Execute as**: `Me`
   - **Who has access**: `Anyone`
7. Copy the `/exec` URL.

Notes:
- Endpoint expects JSON via POST body.
- `section` is required in the POST body (the Python watcher sends this from `config.json` `tag_map`).
- Success response is plain text `OK`.

### 3) Configure local watcher

From the repo root:

```bash
cp config.example.json config.json
```

Edit `config.json`:

- `google_doc_url`: your full Google Doc URL
- `web_app_url`: your deployed Apps Script `/exec` URL
- `who`: initials/name to stamp in each entry (template default `ME`)
- `poll_interval`: clipboard polling interval in seconds (default `0.5`)
- `unknown_prefix_behavior`: `map_to_misc` or `ignore` (default `map_to_misc`)
- `tag_map`: your tags and their target section headings (case-insensitive tags)

Example:

```json
"tag_map": {
  "todo": "TODO",
  "next": "Next Actions",
  "idea": "Ideas",
  "misc": "Miscellany"
}
```

### 4) Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 tools/clipto_watcher.py
```

### 5) Optional: run automatically at login (macOS launchd)

Install and start:

```bash
bash scripts/install_launchagent.sh
```

Check status:

```bash
launchctl print "gui/$(id -u)/com.clipto.watcher" | sed -n '1,40p'
```

Stop and remove:

```bash
bash scripts/uninstall.sh
```

Remove launchd plus local artifacts:

```bash
bash scripts/uninstall.sh --remove-all
```

Log files:

- `logs/launchd.out.log`
- `logs/launchd.err.log`

### 6) Run health checks

Validate local config only:

```bash
python3 tools/healthcheck.py
```

Validate config and send an end-to-end probe item:

```bash
python3 tools/healthcheck.py --write-test
```

### 7) Pre-format doc headings from config

Create any missing H1 headings based on `config.json` `tag_map` values:

```bash
python3 tools/prepare_doc_headings.py
```

This command is safe to rerun; existing headings are not duplicated.

You can also run it during install:

```bash
bash scripts/install.sh --prepare-headings
```

## Run tests

Run unit tests locally:

```bash
python -m unittest discover -s tests -v
```

GitHub Actions also runs this test suite for pull requests and pushes to `main`.

## Verification checklist

Copy each line to your clipboard and confirm behavior:

1. `TODO: test python watcher end-to-end`
   - appears under `TODO`
   - inserted at top of section
   - checkbox item (unchecked), or `[ ]` fallback
2. `next: follow up with release team`
   - appears under `Next Actions`
3. `Idea: automate smoke checks on deploy`
   - routes case-insensitively to `Ideas`

Expected item text format:

- `- yyyy-MM-dd HH:mm [ME]: <note>`

## Troubleshooting

- No entries in the Doc:
  - verify `DOC_ID` in Apps Script
  - verify `web_app_url` in `config.json`
  - verify the intended tag exists in `config.json` `tag_map`
  - redeploy and ensure you are using latest `/exec` URL
- Permission errors:
  - set Web App access to `Anyone`
  - redeploy and update `web_app_url` if deployment URL changed
- Checkbox glyph not present:
  - script tries `DocumentApp.GlyphType.CHECKBOX`
  - if not supported, it falls back to plain paragraph starting with `[ ] `

## Security notes

- Text is sent over HTTPS POST to your Apps Script endpoint.
- Clipboard content is not put into URL query strings.
- Anyone with your `/exec` URL may be able to POST; use only for low-sensitivity notes.

## License

MIT. See `LICENSE`.

## Project docs

- Contribution guide: `CONTRIBUTING.md`
- Changelog: `CHANGELOG.md`

## Publish to GitHub

### Public-release safety checklist

Run this before any public commit/push:

1. Verify ignore rule exists:

```bash
rg -n '^config\.json$' .gitignore
```

2. Verify `config.json` is not tracked:

```bash
git ls-files --error-unmatch config.json && echo "[FAIL] tracked" || echo "[OK] not tracked"
```

3. Verify `config.json` is not staged:

```bash
git diff --cached --name-only | rg -x 'config\.json' && echo "[FAIL] staged" || echo "[OK] not staged"
```

If either check fails, fix it before committing:

```bash
git restore --staged config.json 2>/dev/null || true
git rm --cached config.json
```

### Optional pre-commit guard (recommended)

Install the hook so commits fail automatically if `config.json` is tracked or staged:

```bash
mkdir -p .git/hooks
cp scripts/pre-commit-block-config.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

If you already have a `pre-commit` hook, merge the checks from `scripts/pre-commit-block-config.sh` instead of overwriting it.

```bash
git init
git add .
git commit -m "Initial clipboard-to-google-doc checklist automation"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
