from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_routing import build_config, write_outputs
from scripts.fetch_opencck import build_lists, read_extra


ROOT = Path(__file__).resolve().parents[1]


class OpencckTests(unittest.TestCase):
    def test_lists_apply_replacements_collapse_networks_and_reduce_domains(self) -> None:
        source = {
            "bank": {
                "domains": ["bank.ru", "api.bank.ru", "*.wild.ru", "ПРИМЕР.РФ."],
                "cidr4": ["10.0.0.0/24"],
                "ip4": ["192.0.2.1"],
                "cidr6": ["2001:db8::/33", "2001:db8:8000::/33"],
                "ip6": [],
                "replace": {"cidr4": {"10.0.0.0/24": ["10.0.0.128/25"]}},
                "external": {
                    "domains": ["cdn.bank.ru", "external.ru"],
                    "cidr4": ["10.0.1.0/24"],
                    "ip4": [],
                    "cidr6": [],
                    "ip6": [],
                },
            }
        }

        domains, ipv4, ipv6 = build_lists(source, ["custom.ru"], ["198.51.100.1/32"])

        self.assertEqual(
            domains,
            ["bank.ru", "custom.ru", "external.ru", "wild.ru", "xn--e1afmkfd.xn--p1ai"],
        )
        self.assertEqual(
            ipv4,
            ["10.0.0.128/25", "10.0.1.0/24", "192.0.2.1/32", "198.51.100.1/32"],
        )
        self.assertEqual(ipv6, ["2001:db8::/32"])

    def test_extra_file_ignores_comments_and_blank_lines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "extra.txt"
            path.write_text("\nexample.ru # note\n# ignored\nother.ru\n", encoding="utf-8")
            self.assertEqual(read_extra(path), ["example.ru", "other.ru"])


class RoutingTests(unittest.TestCase):
    def test_profile_and_deeplinks_are_generated_for_this_repository(self) -> None:
        config = build_config(
            ROOT / "config/routing-template.json",
            "ArtemOtr/happ-routing",
            last_updated="1700000000",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            write_outputs(config, output)

            saved = json.loads((output / "ROUTING.JSON").read_text(encoding="utf-8"))
            self.assertEqual(saved, config)
            self.assertEqual(
                saved["Geositeurl"],
                "https://cdn.jsdelivr.net/gh/ArtemOtr/happ-routing@main/release/geosite.dat",
            )

            for filename, prefix in (
                ("ROUTING.DEEPLINK", "happ://routing/add/"),
                ("ROUTING.ONADD.DEEPLINK", "happ://routing/onadd/"),
            ):
                deeplink = (output / filename).read_text(encoding="utf-8").strip()
                self.assertTrue(deeplink.startswith(prefix))
                decoded = json.loads(base64.b64decode(deeplink.removeprefix(prefix)))
                self.assertEqual(decoded, config)

    def test_invalid_repository_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "OWNER/REPOSITORY"):
            build_config(ROOT / "config/routing-template.json", "not a repository")


if __name__ == "__main__":
    unittest.main()
