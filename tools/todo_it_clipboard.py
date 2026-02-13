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
    "next": "Next Actions",
    "idea": "Ideas",
    "misc": "Miscellany",
}

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"
PREFIX_RE = re.compile(r"^([A-Za-z0-9]+):(.*)$")


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

    who = str(cfg.get("who", "ME")).strip() or "ME"
    poll_interval = float(cfg.get("poll_interval", 0.5))
    unknown_behavior = str(cfg.get("unknown_prefix_behavior", "map_to_misc")).strip().lower()
    if unknown_behavior not in {"map_to_misc", "ignore"}:
        raise ValueError("unknown_prefix_behavior must be 'map_to_misc' or 'ignore'")

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


def post_payload(web_app_url: str, payload: dict[str, str]) -> bool:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        web_app_url,
        data=body,
        headers={"Content-Type": "application/json"},
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

    # Prime baseline clipboard state so startup content is not posted.
    try:
        last_clipboard = pyperclip.paste()
    except Exception:
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
                ok = post_payload(config["web_app_url"], payload)
                if ok:
                    print(f"[sent] {payload['type']}: {payload['text']}")

        time.sleep(config["poll_interval"])


if __name__ == "__main__":
    sys.exit(main())
