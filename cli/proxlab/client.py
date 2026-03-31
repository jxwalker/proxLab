"""Shared httpx client that reads API URL + token from ~/.config/proxlab/config.toml"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import httpx

_CONFIG_PATH = Path.home() / ".config" / "proxlab" / "config.toml"


def _load_config() -> dict:
    if not _CONFIG_PATH.exists():
        print(
            "[red]proxlab not configured.[/red]\n"
            f"Run: proxlab config set --url http://<proxlab-host>:8000 --token <token>",
            file=sys.stderr,
        )
        raise SystemExit(1)
    with open(_CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def get_client() -> httpx.Client:
    cfg = _load_config()
    url = cfg.get("api_url", "")
    token = cfg.get("api_token", "")
    if not url or not token:
        print("proxlab config is incomplete. Run: proxlab config set", file=sys.stderr)
        raise SystemExit(1)
    return httpx.Client(
        base_url=url,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )


def api_get(path: str) -> dict | list:
    with get_client() as c:
        resp = c.get(path)
        resp.raise_for_status()
        return resp.json()


def api_post(path: str, json: dict | None = None) -> dict | list:
    with get_client() as c:
        resp = c.post(path, json=json)
        resp.raise_for_status()
        return resp.json()


def api_delete(path: str) -> None:
    with get_client() as c:
        resp = c.delete(path)
        resp.raise_for_status()
