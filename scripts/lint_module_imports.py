#!/usr/bin/env python3
"""Lint cross-module imports in src/ to enforce module isolation.

Allowed:
- Imports from src.exceptions, src.models, src.schemas, src.config,
  src.database, src.dependencies, src.encryption, src.redis_client,
  src.__version__
- Imports from a module's own __init__.py (e.g., src.groups can import from src.groups)
- Self-imports (a module importing from itself)
- Deferred imports inside function bodies (these are acceptable for breaking cycles)

Forbidden:
- Top-level imports from another module's internal files
  (e.g., src/alerts/service.py importing from src.groups.models)
"""
import ast
import sys
from pathlib import Path

SHARED_MODULES = {
    "src.exceptions",
    "src.models",
    "src.schemas",
    "src.config",
    "src.database",
    "src.dependencies",
    "src.encryption",
    "src.redis_client",
    "src.__version__",
}


def get_module_name(file_path: Path) -> str:
    """Extract the module name from a file path (e.g., src/alerts/service.py -> alerts)."""
    parts = file_path.parts
    if "src" in parts:
        idx = parts.index("src")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return ""


def check_file(file_path: Path) -> list[str]:
    """Check a file for forbidden top-level cross-module imports."""
    violations: list[str] = []
    module_name = get_module_name(file_path)
    if not module_name:
        return violations

    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except SyntaxError:
        return violations

    for node in ast.iter_child_nodes(tree):
        # Only check top-level imports (not inside functions)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                import_module = node.module
                # Check if it's a src.* import
                if import_module.startswith("src."):
                    parts = import_module.split(".")
                    if len(parts) >= 2:
                        imported_module = parts[1]
                        full_prefix = f"src.{imported_module}"

                        # Skip shared modules
                        if import_module in SHARED_MODULES or full_prefix in SHARED_MODULES:
                            continue
                        # Skip self-imports
                        if imported_module == module_name:
                            continue
                        # Skip __init__.py imports (public interface) — only 2 path components
                        if len(parts) == 2:
                            continue
                        # This is a cross-module internal import
                        violations.append(
                            f"{file_path}:{node.lineno}: "
                            f"forbidden cross-module import '{import_module}' "
                            f"(module '{module_name}' importing from '{imported_module}' internals)"
                        )

    return violations


def main() -> None:
    # --strict flag causes non-zero exit on any violation; default is warn-only.
    # Rationale: there is an existing backlog of 138 violations tracked in
    # docs/audits/module_isolation_audit.txt (a dedicated refactor task).
    # Warn-only in CI surfaces new violations on every push without blocking
    # merges until the backlog is cleared, at which point --strict can be
    # enabled to prevent regressions.
    strict = "--strict" in sys.argv

    src_dir = Path("src")
    all_violations: list[str] = []

    for py_file in src_dir.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        violations = check_file(py_file)
        all_violations.extend(violations)

    if all_violations:
        print(f"Found {len(all_violations)} cross-module import violations:\n")
        for v in all_violations:
            print(f"  {v}")
        print("\nFix by importing through the module's __init__.py public interface,")
        print("or by using deferred imports inside function bodies.")
        if strict:
            sys.exit(1)
        print("\n(warn-only mode: exiting 0. Pass --strict to fail on violations.)")
        sys.exit(0)
    else:
        print("No cross-module import violations found.")
        sys.exit(0)


if __name__ == "__main__":
    main()
