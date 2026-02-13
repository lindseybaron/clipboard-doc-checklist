#!/usr/bin/env python3
"""Run quick health checks for Clipto setup."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise ValueError("config.json must be a JSON object")
    return cfg


def validate_config(cfg: dict) -> list[str]:
    errors: list[str] = []
    web_app_url = str(cfg.get("web_app_url", "")).strip()
    if not web_app_url:
        errors.append("web_app_url is missing")
    elif "<YOUR_DEPLOYMENT_ID>" in web_app_url or "<REPLACE" in web_app_url:
        errors.append("web_app_url still contains placeholder text")
    elif not web_app_url.startswith("https://script.google.com/"):
        errors.append("web_app_url should start with https://script.google.com/")

    tag_map = cfg.get("tag_map")
    if not isinstance(tag_map, dict) or not tag_map:
        errors.append("tag_map must be a non-empty object")
    else:
        for key, value in tag_map.items():
            k = str(key).strip()
            v = str(value).strip()
            if not k:
                errors.append("tag_map contains an empty key")
            if ":" in k:
                errors.append(f"tag_map key '{k}' must not include ':'")
            if not v:
                errors.append(f"tag_map value for '{k}' is empty")

    return errors


def build_probe_payload(cfg: dict) -> dict[str, str]:
    tag_map = cfg["tag_map"]
    if "misc" in tag_map:
        type_key = "misc"
    else:
        type_key = next(iter(tag_map.keys()))
    section = str(tag_map[type_key]).strip()
    who = str(cfg.get("who", "ME")).strip() or "ME"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "type": type_key,
        "section": section,
        "text": f"[healthcheck] {timestamp}",
        "who": who,
    }


def post_probe(url: str, payload: dict[str, str]) -> tuple[bool, str]:
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=12) as resp:
            status = getattr(resp, "status", resp.getcode())
            body = resp.read().decode("utf-8", errors="replace").strip()
            if 200 <= status < 300 and body == "OK":
                return True, "OK"
            return False, f"unexpected response status={status} body={body!r}"
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {detail}"
    except URLError as exc:
        return False, f"network error: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unexpected error: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate setup and optionally send a probe entry.")
    parser.add_argument(
        "--write-test",
        action="store_true",
        help="Send a probe entry to the Google Doc to verify end-to-end posting.",
    )
    args = parser.parse_args()

    print("[healthcheck] loading config...")
    try:
        cfg = load_config(CONFIG_PATH)
    except Exception as exc:  # noqa: BLE001
        print(f"[fail] {exc}")
        return 1

    errors = validate_config(cfg)
    if errors:
        print("[fail] config validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("[pass] config validation")

    if not args.write_test:
        print("[info] skipping network probe (run with --write-test to verify web app/doc access)")
        return 0

    payload = build_probe_payload(cfg)
    print(f"[healthcheck] posting probe to {cfg['web_app_url']}")
    ok, message = post_probe(str(cfg["web_app_url"]), payload)
    if ok:
        print(f"[pass] web app POST succeeded; probe sent to section '{payload['section']}'")
        return 0

    print(f"[fail] web app POST failed: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
