#!/usr/bin/env python3
"""Create custom GeoSite and GeoIP source lists from opencck data."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SOURCE = "https://russia.iplist.opencck.org/?format=json"
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def load_source(source: str, timeout: int = 180) -> dict[str, dict[str, Any]]:
    """Load and minimally validate an opencck JSON document."""
    try:
        if source.startswith(("http://", "https://")):
            request = urllib.request.Request(
                source, headers={"User-Agent": "personal-happ-routing/1.0"}
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.load(response)
        else:
            data = json.loads(Path(source).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, urllib.error.URLError) as exc:
        raise RuntimeError(f"не удалось загрузить {source}: {exc}") from exc

    if not isinstance(data, dict) or not data:
        raise ValueError("источник opencck должен содержать непустой JSON-объект")
    if any(not isinstance(value, dict) for value in data.values()):
        raise ValueError("каждый сервис opencck должен быть JSON-объектом")
    return data


def read_extra(path: str | Path) -> list[str]:
    """Read a line-based user list, stripping comments and blank lines."""
    source = Path(path)
    if not source.exists():
        return []
    return [
        value
        for raw_line in source.read_text(encoding="utf-8").splitlines()
        if (value := raw_line.split("#", 1)[0].strip())
    ]


def strings(value: Any) -> Iterable[str]:
    """Yield strings from a JSON list and ignore malformed values."""
    if isinstance(value, list):
        yield from (item for item in value if isinstance(item, str))


def normalize_domain(value: str) -> str | None:
    domain = value.strip().lower().rstrip(".")
    if domain.startswith("*."):
        domain = domain[2:]
    try:
        domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    return domain if DOMAIN_RE.fullmatch(domain) else None


def reduce_domains(domains: Iterable[str]) -> list[str]:
    """Normalize domains and remove children already covered by a parent."""
    normalized = {item for value in domains if (item := normalize_domain(value))}
    kept: set[str] = set()
    for domain in sorted(normalized, key=lambda item: (item.count("."), item)):
        labels = domain.split(".")
        parents = (".".join(labels[index:]) for index in range(1, len(labels) - 1))
        if not any(parent in kept for parent in parents):
            kept.add(domain)
    return sorted(kept)


def collect_domains(service: dict[str, Any]) -> set[str]:
    result = set(strings(service.get("domains")))
    external = service.get("external")
    if isinstance(external, dict):
        result.update(strings(external.get("domains")))
    return result


def collect_cidrs(service: dict[str, Any], family: int) -> set[str]:
    suffix = "4" if family == 4 else "6"
    result = set(strings(service.get(f"cidr{suffix}")))

    replacements = service.get("replace")
    if isinstance(replacements, dict):
        family_replacements = replacements.get(f"cidr{suffix}")
        if isinstance(family_replacements, dict):
            for broad, narrow in family_replacements.items():
                if broad in result:
                    result.remove(broad)
                    result.update(strings(narrow))

    external = service.get("external")
    if isinstance(external, dict):
        result.update(strings(external.get(f"cidr{suffix}")))

    host_mask = "/32" if family == 4 else "/128"
    for address in strings(service.get(f"ip{suffix}")):
        result.add(f"{address}{host_mask}")
    if isinstance(external, dict):
        for address in strings(external.get(f"ip{suffix}")):
            result.add(f"{address}{host_mask}")
    return result


def collapse_cidrs(cidrs: Iterable[str], family: int) -> list[str]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for value in cidrs:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            print(f"warning: пропущен некорректный CIDR: {value}", file=sys.stderr)
            continue
        if network.version == family:
            networks.append(network)
    return [str(network) for network in ipaddress.collapse_addresses(networks)]


def build_lists(
    data: dict[str, dict[str, Any]],
    extra_domains: Iterable[str] = (),
    extra_cidrs: Iterable[str] = (),
) -> tuple[list[str], list[str], list[str]]:
    domains = set(extra_domains)
    cidrs = set(extra_cidrs)
    for service in data.values():
        domains.update(collect_domains(service))
        cidrs.update(collect_cidrs(service, 4))
        cidrs.update(collect_cidrs(service, 6))
    return reduce_domains(domains), collapse_cidrs(cidrs, 4), collapse_cidrs(cidrs, 6)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE, help="URL или путь к JSON")
    parser.add_argument("--outdir", default="build", help="каталог для списков")
    parser.add_argument("--extra-domains", default="custom/domains-extra.txt")
    parser.add_argument("--extra-cidr", default="custom/cidr-extra.txt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        data = load_source(args.source)
        domains, cidr4, cidr6 = build_lists(
            data, read_extra(args.extra_domains), read_extra(args.extra_cidr)
        )
        if not domains or not (cidr4 or cidr6):
            raise ValueError("после обработки получились пустые списки")
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    output = Path(args.outdir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "russia-inside").write_text("\n".join(domains) + "\n", encoding="utf-8")
    (output / "russia-inside.txt").write_text(
        "\n".join(cidr4 + cidr6) + "\n", encoding="utf-8"
    )

    print(f"opencck: {len(data)} сервисов")
    print(f"GeoSite russia-inside: {len(domains)} доменов")
    print(f"GeoIP russia-inside: IPv4={len(cidr4)}, IPv6={len(cidr6)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
