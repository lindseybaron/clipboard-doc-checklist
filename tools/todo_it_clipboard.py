#!/usr/bin/env python3
"""Clipboard watcher that sends tagged lines to a Google Apps Script Web App."""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pyperclip


DEFAULT_TAG_MAP = {
    "todo": "TODO",
    "fu": "Follow Up",
    "misc": "Miscellany",
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
PREFIX_RE = re.compile(r"^([A-Za-z0-9]+):(.*)$")


def resolve_path_(base_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def load_config(config_path: Path) -> dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found at {config_path}. "
            "Copy config.example.json to config.json and update values."
        )

    with config_path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)

    web_app_url = str(cfg.get("web_app_url", "")).strip()
    if not web_app_url:
        raise ValueError("config.json is missing required field: web_app_url")

    who = str(cfg.get("who", "LB")).strip() or "LB"
    poll_interval = float(cfg.get("poll_interval", 0.5))
    unknown_behavior = str(cfg.get("unknown_prefix_behavior", "map_to_misc")).strip().lower()
    if unknown_behavior not in {"map_to_misc", "ignore"}:
        raise ValueError("unknown_prefix_behavior must be 'map_to_misc' or 'ignore'")

    auth_mode = str(cfg.get("auth_mode", "none")).strip().lower()
    if auth_mode not in {"none", "oauth_user"}:
        raise ValueError("auth_mode must be 'none' or 'oauth_user'")

    oauth_cfg = cfg.get("oauth", {})
    if not isinstance(oauth_cfg, dict):
        oauth_cfg = {}
    oauth_scopes = oauth_cfg.get(
        "scopes",
        [
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
    )
    if not isinstance(oauth_scopes, list) or not oauth_scopes:
        raise ValueError("oauth.scopes must be a non-empty list")
    oauth_scopes = [str(scope).strip() for scope in oauth_scopes if str(scope).strip()]
    if not oauth_scopes:
        raise ValueError("oauth.scopes must contain at least one non-empty scope")

    client_secrets_file = str(oauth_cfg.get("client_secrets_file", "oauth_client_secret.json")).strip()
    token_file = str(oauth_cfg.get("token_file", ".secrets/oauth_token.json")).strip()

    tag_map_cfg = cfg.get("tag_map", {})
    tag_map = dict(DEFAULT_TAG_MAP)
    if isinstance(tag_map_cfg, dict):
        for key, value in tag_map_cfg.items():
            key_norm = str(key).strip().lower()
            if key_norm:
                tag_map[key_norm] = str(value)

    return {
        "google_doc_url": str(cfg.get("google_doc_url", "")).strip(),
        "web_app_url": web_app_url,
        "who": who,
        "poll_interval": poll_interval,
        "unknown_prefix_behavior": unknown_behavior,
        "auth_mode": auth_mode,
        "oauth": {
            "client_secrets_file": str(resolve_path_(config_path.parent, client_secrets_file)),
            "token_file": str(resolve_path_(config_path.parent, token_file)),
            "scopes": oauth_scopes,
        },
        "tag_map": tag_map,
    }


def parse_clipboard_text(
    raw_text: str, unknown_behavior: str, tag_map: dict[str, str]
) -> dict[str, str] | None:
    if raw_text is None:
        return None

    # First non-empty line only.
    line = ""
    for candidate in raw_text.splitlines():
        if candidate.strip():
            line = candidate.strip()
            break
    if not line:
        return None

    match = PREFIX_RE.match(line)
    if not match:
        return None

    prefix_raw = match.group(1)
    text = match.group(2).strip()
    if not text:
        return None

    prefix = prefix_raw.lower()
    if prefix not in tag_map:
        if unknown_behavior == "map_to_misc":
            prefix = "misc"
        else:
            return None

    section = str(tag_map.get(prefix, "")).strip()
    if not section:
        return None

    return {"type": prefix, "section": section, "text": text}


def get_oauth_access_token(oauth_cfg: dict[str, Any]) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        raise RuntimeError(
            "Missing OAuth dependencies. Run: pip install -r requirements.txt"
        ) from exc

    token_path = Path(str(oauth_cfg["token_file"]))
    client_secrets_path = Path(str(oauth_cfg["client_secrets_file"]))
    scopes = [str(scope) for scope in oauth_cfg["scopes"]]

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes=scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secrets_path.exists():
                raise FileNotFoundError(
                    f"OAuth client secrets file not found: {client_secrets_path}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path), scopes=scopes
            )
            print("[auth] Starting OAuth login in browser...")
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.token:
        raise RuntimeError("Could not obtain OAuth access token")

    return str(creds.token)


def post_payload(web_app_url: str, payload: dict[str, str], config: dict[str, Any]) -> bool:
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if config["auth_mode"] == "oauth_user":
        try:
            token = get_oauth_access_token(config["oauth"])
            headers["Authorization"] = f"Bearer {token}"
        except Exception as exc:  # noqa: BLE001
            print(f"[error] auth failure: {exc}")
            return False

    req = urllib.request.Request(
        web_app_url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = getattr(resp, "status", resp.getcode())
            text = resp.read().decode("utf-8", errors="replace").strip()
            if 200 <= status < 300 and text == "OK":
                return True
            print(f"[error] server response status={status} body={text}")
            return False
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"[error] HTTP {exc.code}: {detail}")
    except urllib.error.URLError as exc:
        print(f"[error] network issue: {exc}")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] unexpected failure: {exc}")

    return False


def main() -> int:
    try:
        config = load_config(DEFAULT_CONFIG_PATH)
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] {exc}")
        return 1

    print("[watching] clipboard watcher started")
    if config["google_doc_url"]:
        print(f"[info] target doc: {config['google_doc_url']}")
    if config["auth_mode"] == "oauth_user":
        print("[info] auth mode: oauth_user")
        print(f"[info] oauth client secrets: {config['oauth']['client_secrets_file']}")

    last_clipboard = None
    while True:
        try:
            current = pyperclip.paste()
        except Exception as exc:  # noqa: BLE001
            print(f"[error] clipboard read failed: {exc}")
            time.sleep(config["poll_interval"])
            continue

        if current != last_clipboard:
            last_clipboard = current
            parsed = parse_clipboard_text(
                raw_text=current,
                unknown_behavior=config["unknown_prefix_behavior"],
                tag_map=config["tag_map"],
            )
            if parsed:
                payload = {
                    "type": parsed["type"],
                    "section": parsed["section"],
                    "text": parsed["text"],
                    "who": config["who"],
                }
                ok = post_payload(config["web_app_url"], payload, config)
                if ok:
                    print(f"[sent] {payload['type']}: {payload['text']}")

        time.sleep(config["poll_interval"])


if __name__ == "__main__":
    sys.exit(main())
