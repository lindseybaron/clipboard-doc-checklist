#!/usr/bin/env python3
"""Create missing Google Doc section headings from config tag_map."""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config.json"


def load_config(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}. Copy config.example.json to config.json first."
        )
    with path.open("r", encoding="utf-8") as f:
        cfg = json.load(f)
    if not isinstance(cfg, dict):
        raise ValueError("config.json must be a JSON object")
    return cfg


def get_sections_from_tag_map(tag_map: dict) -> list[str]:
    if not isinstance(tag_map, dict) or not tag_map:
        raise ValueError("tag_map must be a non-empty object")
    seen: set[str] = set()
    sections: list[str] = []
    for value in tag_map.values():
        section = str(value).strip()
        if not section or section in seen:
            continue
        seen.add(section)
        sections.append(section)
    if not sections:
        raise ValueError("tag_map contains no valid section titles")
    return sections


def ensure_headings(web_app_url: str, sections: list[str]) -> tuple[bool, str]:
    payload = {"action": "ensure_sections", "sections": sections}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        web_app_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            status = getattr(resp, "status", resp.getcode())
            if 200 <= status < 300 and body == "OK":
                return True, "OK"
            if "Missing required field: type" in body:
                return (
                    False,
                    "apps script deployment is outdated for action=ensure_sections; "
                    "redeploy latest Code.gs and retry",
                )
            return False, f"unexpected response status={status} body={body!r}"
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return False, f"HTTP {exc.code}: {detail}"
    except urllib.error.URLError as exc:
        return False, f"network error: {exc}"
    except Exception as exc:  # noqa: BLE001
        return False, f"unexpected error: {exc}"


def main() -> int:
    try:
        cfg = load_config(CONFIG_PATH)
        web_app_url = str(cfg.get("web_app_url", "")).strip()
        if not web_app_url:
            raise ValueError("web_app_url is missing in config.json")
        sections = get_sections_from_tag_map(cfg.get("tag_map", {}))
    except Exception as exc:  # noqa: BLE001
        print(f"[fail] {exc}")
        return 1

    print("[prepare] ensuring these H1 headings exist:")
    for section in sections:
        print(f" - {section}")

    ok, message = ensure_headings(web_app_url, sections)
    if ok:
        print("[pass] headings ensured successfully")
        return 0

    print(f"[fail] could not ensure headings: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
