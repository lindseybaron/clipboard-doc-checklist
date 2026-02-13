# Clipboard -> Google Doc Checklist

Small automation project for capturing clipboard lines like `todo: ...` or `next: ...` and appending them into a Google Doc under configurable H1 sections, newest first.

## What this includes

- `apps_script/Code.gs`: Google Apps Script Web App (`doPost`) that writes to your Google Doc.
- `tools/todo_it_clipboard.py`: Python clipboard watcher that POSTs matching lines.
- `config.example.json`: user-specific config template.
- `scripts/bootstrap.sh`: one-command local setup (venv + deps + config scaffold).

## Prefix routing

Case-insensitive tags map to the exact Doc section headings as defined in `config.json`. Add or edit as you'd like.

- `todo:` -> `TODO`
- `next:` -> `Next Actions`
- `idea:` -> `Ideas`
- `misc:` -> `Miscellany`
- `<tag>:` -> `Your Description Here` 

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

Create a Google Doc. You can pre-create headings from your `config.json` `tag_map` values as **Heading 1**, but this is optional.

If a heading is missing, the script creates it automatically as H1.

### 2) Deploy Apps Script Web App

1. Open [https://script.google.com](https://script.google.com) and create a project.
2. Paste `apps_script/Code.gs` contents into the project.
3. In `Code.gs`, set:
   - `DOC_ID = '<YOUR_DOC_ID>'`
4. Save.
5. Deploy -> New deployment -> Web app:
   - **Execute as**: `Me`
   - **Who has access**:
     - `Anyone` for no-auth local client mode, or
     - `Anyone within your domain` / `Anyone with Google account` when using OAuth in the watcher
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
- `who`: initials/name to stamp in each entry (template default `ME`)
- `poll_interval`: clipboard polling interval in seconds (default `0.5`)
- `unknown_prefix_behavior`: `map_to_misc` or `ignore` (default `map_to_misc`)
- `auth_mode`: `none` or `oauth_user`
- `oauth`: OAuth client and token settings (used when `auth_mode` is `oauth_user`)
- `tag_map`: your tags and their target section headings (case-insensitive tags)

Example:

```json
"auth_mode": "none",
"oauth": {
  "client_secrets_file": "oauth_client_secret.json",
  "token_file": ".secrets/oauth_token.json",
  "scopes": [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
  ]
},
"tag_map": {
  "todo": "TODO",
  "next": "Next Actions",
  "idea": "Ideas",
  "misc": "Miscellany"
}
```

### 3b) Optional: enable authenticated posting (`auth_mode: oauth_user`)

Use this when your Apps Script is not public (`Anyone within your domain` or `Anyone with Google account`).

1. In Google Cloud Console, create an OAuth Client ID of type **Desktop app**.
2. Download the client JSON and place it in repo root as `oauth_client_secret.json` (or update path in config).
3. Set in `config.json`:
   - `"auth_mode": "oauth_user"`
4. Start watcher normally:
   - `python tools/todo_it_clipboard.py`
5. On first send, a browser login/consent flow appears; complete it with an allowed account.
6. Token is stored at `.secrets/oauth_token.json` for refresh/reuse.

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
  - if deployment is restricted, set `auth_mode` to `oauth_user`
  - confirm `oauth_client_secret.json` exists and first-run auth completed
  - ensure the signed-in OAuth account is allowed by deployment access policy
- Checkbox glyph not present:
  - script tries `DocumentApp.GlyphType.CHECKBOX`
  - if not supported, it falls back to plain paragraph starting with `[ ] `

## Security notes

- Text is sent over HTTPS POST to your Apps Script endpoint.
- Clipboard content is not put into URL query strings.
- In `auth_mode: none`, endpoint access relies on web app sharing settings.
- In `auth_mode: oauth_user`, requests include `Authorization: Bearer <Google access token>`.

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
