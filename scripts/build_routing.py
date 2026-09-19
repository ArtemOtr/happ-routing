#!/usr/bin/env python3
"""Build Happ JSON and deeplinks from the editable routing template."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ROUTE_LISTS = (
    "DirectSites",
    "DirectIp",
    "ProxySites",
    "ProxyIp",
    "BlockSites",
    "BlockIp",
)


def validate_config(config: Any) -> dict[str, Any]:
    if not isinstance(config, dict):
        raise ValueError("шаблон должен содержать JSON-объект")
    if not isinstance(config.get("Name"), str) or not config["Name"].strip():
        raise ValueError("Name должен быть непустой строкой")
    for key in ROUTE_LISTS:
        value = config.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ValueError(f"{key} должен быть массивом строк")
        if len(value) != len(set(value)):
            raise ValueError(f"{key} содержит дубликаты")
    if not isinstance(config.get("DnsHosts"), dict):
        raise ValueError("DnsHosts должен быть JSON-объектом")
    return config


def build_config(
    template: str | Path,
    repository: str,
    branch: str = "main",
    last_updated: str | None = None,
) -> dict[str, Any]:
    if not REPOSITORY_RE.fullmatch(repository):
        raise ValueError("repository должен иметь вид OWNER/REPOSITORY")
    if not branch or any(character.isspace() for character in branch):
        raise ValueError("branch содержит недопустимые символы")
    timestamp = last_updated or str(int(time.time()))
    if not timestamp.isdigit() or int(timestamp) <= 0:
        raise ValueError("last-updated должен быть Unix timestamp")

    try:
        raw_config = json.loads(Path(template).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"не удалось прочитать шаблон: {exc}") from exc

    config = validate_config(raw_config)
    base_url = f"https://cdn.jsdelivr.net/gh/{repository}@{branch}/release"
    config["Geositeurl"] = f"{base_url}/geosite.dat"
    config["Geoipurl"] = f"{base_url}/geoip.dat"
    config["LastUpdated"] = timestamp
    return config


def write_outputs(config: dict[str, Any], output_directory: str | Path) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    pretty_json = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    compact_json = json.dumps(config, ensure_ascii=False, separators=(",", ":"))
    payload = base64.b64encode(compact_json.encode("utf-8")).decode("ascii")

    (output / "ROUTING.JSON").write_text(pretty_json, encoding="utf-8")
    (output / "ROUTING.DEEPLINK").write_text(
        f"happ://routing/add/{payload}\n", encoding="utf-8"
    )
    (output / "ROUTING.ONADD.DEEPLINK").write_text(
        f"happ://routing/onadd/{payload}\n", encoding="utf-8"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", default="config/routing-template.json")
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--branch", default="main")
    parser.add_argument("--last-updated", default=None)
    parser.add_argument("--outdir", default="HAPP")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.repo:
        print("error: укажите --repo OWNER/REPOSITORY", file=sys.stderr)
        return 2
    try:
        config = build_config(args.template, args.repo, args.branch, args.last_updated)
        write_outputs(config, args.outdir)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Happ profile: {config['Name']}")
    print(f"GeoSite: {config['Geositeurl']}")
    print(f"GeoIP: {config['Geoipurl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
