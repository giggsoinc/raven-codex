#!/usr/bin/env python3
"""DOMAIN_SKILL_MAP precision regression — the false-positive Oracle bug.

A stray migration/SQLite-schema/test-fixture .sql file must NOT brand a
project Oracle, and first-match-wins must not shadow later strong signals
(e.g. fastapi in requirements.txt). Loads the detector via importlib
(hyphenated filename) and runs 10 filesystem fixtures.
"""

import importlib.util
import tempfile
import unittest
from pathlib import Path

DETECTOR = Path(__file__).resolve().parent.parent / "scripts" / "session-start.py"

spec = importlib.util.spec_from_file_location("session_start", DETECTOR)
session_start = importlib.util.module_from_spec(spec)
spec.loader.exec_module(session_start)
detect_domain = session_start.detect_domain


def fixture(files=(), dirs=(), contents=None):
    """Build a temp project tree; returns its Path (caller's ctx manages life)."""
    tmp = Path(tempfile.mkdtemp())
    for d in dirs:
        (tmp / d).mkdir(parents=True, exist_ok=True)
    for f in files:
        p = tmp / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text((contents or {}).get(f, ""))
    return tmp


class TestDomainDetection(unittest.TestCase):
    def test_1_stray_sql_is_not_oracle(self):
        root = fixture(files=["migrations/001_init.sql", "app.py"])
        skill, name, strength = detect_domain(root)
        self.assertNotEqual(name, "Oracle")

    def test_2_fastapi_beats_stray_sql(self):
        root = fixture(
            files=["requirements.txt", "fixtures/schema.sql"],
            contents={"requirements.txt": "fastapi==0.110\nuvicorn\n"})
        skill, name, strength = detect_domain(root)
        self.assertEqual(name, "FastAPI")
        self.assertEqual(strength, "strong")

    def test_3_tnsnames_is_oracle_strong(self):
        root = fixture(files=["tnsnames.ora"])
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Oracle", "strong"))

    def test_4_cx_oracle_keyword_is_oracle_strong(self):
        root = fixture(files=["requirements.txt"],
                       contents={"requirements.txt": "cx_Oracle==8.3\n"})
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Oracle", "strong"))

    def test_5_oracledb_keyword_in_pyproject_is_oracle_strong(self):
        root = fixture(files=["pyproject.toml"],
                       contents={"pyproject.toml": "[project]\ndependencies=['oracledb']\n"})
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Oracle", "strong"))

    def test_6_pkb_glob_is_oracle_strong(self):
        root = fixture(files=["pkg/billing.pkb"])
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Oracle", "strong"))

    def test_7_lone_k8s_dir_is_weak(self):
        root = fixture(dirs=["k8s"])
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Kubernetes", "weak"))

    def test_8_k8s_plus_helm_is_strong(self):
        root = fixture(dirs=["k8s", "helm"])
        skill, name, strength = detect_domain(root)
        self.assertEqual((name, strength), ("Kubernetes", "strong"))

    def test_9_charts_dir_with_js_detects_nothing(self):
        root = fixture(files=["charts/revenue.js"], dirs=["charts"])
        skill, name, strength = detect_domain(root)
        self.assertIsNone(name)

    def test_10_generic_template_yaml_not_aws_but_aws_content_is(self):
        generic = fixture(files=["template.yaml"],
                          contents={"template.yaml": "name: my-thing\n"})
        skill, name, strength = detect_domain(generic)
        self.assertNotEqual(name, "AWS")
        sam = fixture(files=["template.yaml"],
                      contents={"template.yaml": "Resources:\n  Fn:\n    Type: AWS::Serverless::Function\n"})
        skill, name, strength = detect_domain(sam)
        self.assertEqual((name, strength), ("AWS", "strong"))


if __name__ == "__main__":
    unittest.main()
