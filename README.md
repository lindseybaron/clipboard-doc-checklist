# Clipboard -> Google Doc Checklist

Small automation project for capturing clipboard lines like `todo: ...` or `a2: ...` and appending them into a Google Doc under fixed H1 sections, newest first.

## What this includes

- `apps_script/Code.gs`: Google Apps Script Web App (`doPost`) that writes to your Google Doc.
- `tools/todo_it_clipboard.py`: Python clipboard watcher that POSTs matching lines.
- `config.example.json`: user-specific config template.
- `scripts/bootstrap.sh`: one-command local setup (venv + deps + config scaffold).

## Prefix routing

Case-insensitive tags map to these exact Doc section headings:

- `todo:` -> `TODO`
- `it:` -> `Apex 2 Integration Test Approach`
- `a2:` -> `Apex 2 General`
- `aiqa:` -> `AI in QA Proposal`
- `fu:` -> `Follow Up`
- `misc:` -> `Miscellany`

## Setup (under 10 minutes)

### Quick start (recommended)

From the repo root:

```bash
bash scripts/bootstrap.sh
```

Then edit `config.json` and run:

```bash
source .venv/bin/activate
python tools/todo_it_clipboard.py
```

### 1) Prepare your Google Doc

Create a Google Doc and add these six headings exactly, as **Heading 1**:

1. `TODO`
2. `Apex 2 Integration Test Approach`
3. `Apex 2 General`
4. `AI in QA Proposal`
5. `Follow Up`
6. `Miscellany`

If any heading is missing, the script creates it as H1.

### 2) Deploy Apps Script Web App

1. Open [https://script.google.com](https://script.google.com) and create a project.
2. Paste `apps_script/Code.gs` contents into the project.
3. In `Code.gs`, set:
   - `DOC_ID = '<YOUR_DOC_ID>'`
4. Save.
5. Deploy -> New deployment -> Web app:
   - **Execute as**: `Me`
   - **Who has access**: `Anyone in domain` (preferred) or `Anyone with the link`
6. Copy the `/exec` URL.

Notes:
- Endpoint expects JSON via POST body.
- Success response is plain text `OK`.

### 3) Configure local watcher

From the repo root:

```bash
cp config.example.json config.json
```

Edit `config.json`:

- `google_doc_url`: your full Google Doc URL
- `web_app_url`: your deployed Apps Script `/exec` URL
- `who`: initials/name to stamp in each entry (default `LB`)
- `poll_interval`: clipboard polling interval in seconds (default `0.5`)
- `unknown_prefix_behavior`: `map_to_misc` or `ignore` (default `map_to_misc`)

### 4) Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python tools/todo_it_clipboard.py
```

## Verification checklist

Copy each line to your clipboard and confirm behavior:

1. `TODO: test python watcher end-to-end`
   - appears under `TODO`
   - inserted at top of section
   - checkbox item (unchecked), or `[ ]` fallback
2. `a2: figure out who owns the event flows`
   - appears under `Apex 2 General`
3. `It: add negative-path coverage`
   - routes case-insensitively to `Apex 2 Integration Test Approach`

Expected item text format:

- `- yyyy-MM-dd HH:mm [LB]: <note>`

## Troubleshooting

- No entries in the Doc:
  - verify `DOC_ID` in Apps Script
  - verify `web_app_url` in `config.json`
  - redeploy and ensure you are using latest `/exec` URL
- Permission errors:
  - review deployment access (`Anyone in domain` vs `Anyone with the link`)
- Checkbox glyph not present:
  - script tries `DocumentApp.GlyphType.CHECKBOX`
  - if not supported, it falls back to plain paragraph starting with `[ ] `

## Security notes

- Text is sent over HTTPS POST to your Apps Script endpoint.
- Clipboard content is not put into URL query strings.
- Anyone with your `/exec` URL may be able to POST; prefer domain-restricted deployment when possible.

## License

MIT. See `LICENSE`.

## Publish to GitHub

```bash
git init
git add .
git commit -m "Initial clipboard-to-google-doc checklist automation"
git branch -M main
git remote add origin <YOUR_GITHUB_REPO_URL>
git push -u origin main
```
