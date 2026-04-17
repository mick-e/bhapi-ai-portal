"""Unit tests for scripts/lint_module_imports.py."""

import ast
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the linter functions directly
import importlib.util

_spec = importlib.util.spec_from_file_location(
    "lint_module_imports",
    Path(__file__).resolve().parents[2] / "scripts" / "lint_module_imports.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

check_file = _mod.check_file
get_module_name = _mod.get_module_name
SHARED_MODULES = _mod.SHARED_MODULES


# ---------------------------------------------------------------------------
# get_module_name
# ---------------------------------------------------------------------------


class TestGetModuleName:
    def test_module_in_subdir(self, tmp_path):
        p = tmp_path / "src" / "alerts" / "service.py"
        p.parent.mkdir(parents=True)
        p.touch()
        assert get_module_name(p) == "alerts"

    def test_top_level_file(self, tmp_path):
        p = tmp_path / "src" / "main.py"
        p.parent.mkdir(parents=True)
        p.touch()
        assert get_module_name(p) == "main.py"

    def test_nested_module(self, tmp_path):
        p = tmp_path / "src" / "reporting" / "generators" / "safety_report.py"
        p.parent.mkdir(parents=True)
        p.touch()
        assert get_module_name(p) == "reporting"

    def test_no_src_dir(self, tmp_path):
        p = tmp_path / "lib" / "utils.py"
        p.parent.mkdir(parents=True)
        p.touch()
        assert get_module_name(p) == ""


# ---------------------------------------------------------------------------
# check_file — violations
# ---------------------------------------------------------------------------


class TestCheckFileViolations:
    def _write(self, tmp_path, module, filename, code):
        p = tmp_path / "src" / module / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(code), encoding="utf-8")
        return p

    def test_cross_module_internal_import_flagged(self, tmp_path):
        p = self._write(tmp_path, "billing", "service.py", """\
            from src.auth.models import User
        """)
        violations = check_file(p)
        assert len(violations) == 1
        assert "forbidden cross-module import" in violations[0]
        assert "src.auth.models" in violations[0]

    def test_multiple_violations(self, tmp_path):
        p = self._write(tmp_path, "portal", "service.py", """\
            from src.alerts.models import Alert
            from src.groups.models import Group
            from src.risk.models import RiskEvent
        """)
        violations = check_file(p)
        assert len(violations) == 3

    def test_deep_internal_path_flagged(self, tmp_path):
        p = self._write(tmp_path, "reporting", "gen.py", """\
            from src.email.templates.report import build_html
        """)
        violations = check_file(p)
        assert len(violations) == 1


# ---------------------------------------------------------------------------
# check_file — allowed patterns
# ---------------------------------------------------------------------------


class TestCheckFileAllowed:
    def _write(self, tmp_path, module, filename, code):
        p = tmp_path / "src" / module / filename
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(textwrap.dedent(code), encoding="utf-8")
        return p

    def test_public_interface_import_allowed(self, tmp_path):
        """from src.auth import User — 2 path parts = public interface."""
        p = self._write(tmp_path, "billing", "service.py", """\
            from src.auth import User
        """)
        assert check_file(p) == []

    def test_self_import_allowed(self, tmp_path):
        """A module importing from its own internals is fine."""
        p = self._write(tmp_path, "auth", "router.py", """\
            from src.auth.models import User
            from src.auth.service import create_access_token
        """)
        assert check_file(p) == []

    def test_shared_module_import_allowed(self, tmp_path):
        """Imports from shared modules (database, config, etc.) are allowed."""
        p = self._write(tmp_path, "billing", "service.py", """\
            from src.database import get_db
            from src.config import get_settings
            from src.exceptions import NotFoundError
            from src.encryption import encrypt_credential
        """)
        assert check_file(p) == []

    def test_deferred_import_in_function_body_allowed(self, tmp_path):
        """Imports inside function bodies are not top-level and should be skipped."""
        p = self._write(tmp_path, "billing", "service.py", """\
            def process():
                from src.auth.models import User
                return User
        """)
        assert check_file(p) == []

    def test_stdlib_and_third_party_ignored(self, tmp_path):
        p = self._write(tmp_path, "billing", "service.py", """\
            from datetime import datetime
            from sqlalchemy import Column
            import structlog
        """)
        assert check_file(p) == []

    def test_empty_file(self, tmp_path):
        p = self._write(tmp_path, "billing", "empty.py", "")
        assert check_file(p) == []


# ---------------------------------------------------------------------------
# Integration: current codebase has zero violations
# ---------------------------------------------------------------------------


class TestCurrentCodebase:
    def test_no_violations_in_src(self):
        """The codebase should have zero violations (linter --strict passes)."""
        src_dir = Path("src")
        if not src_dir.exists():
            pytest.skip("Not running from project root")

        all_violations = []
        for py_file in src_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            all_violations.extend(check_file(py_file))

        assert all_violations == [], (
            f"Found {len(all_violations)} violations:\n"
            + "\n".join(all_violations[:10])
        )
