#!/usr/bin/env python3
"""Generate OpenAPI spec and SDK stubs for the Bhapi Public API.

Usage:
    python scripts/generate_sdk.py              # Export spec only
    python scripts/generate_sdk.py --generate   # Export spec + run openapi-generator

Requires: @openapitools/openapi-generator-cli (npm) for --generate mode.
"""
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.main import create_app  # noqa: E402
from src.api_platform.openapi_export import export_public_openapi  # noqa: E402

SPEC_PATH = Path("sdks/openapi.json")
SDK_LANGUAGES = {
    "python": {
        "generator": "python",
        "output": "sdks/python",
        "extra": "-p packageName=bhapi",
    },
    "js": {
        "generator": "typescript-fetch",
        "output": "sdks/js",
        "extra": "",
    },
    "swift": {
        "generator": "swift5",
        "output": "sdks/swift",
        "extra": "",
    },
    "kotlin": {
        "generator": "kotlin",
        "output": "sdks/kotlin",
        "extra": "",
    },
}


def main() -> None:
    app = create_app()
    spec = export_public_openapi(app)
    SPEC_PATH.parent.mkdir(parents=True, exist_ok=True)
    SPEC_PATH.write_text(json.dumps(spec, indent=2))
    print(f"OpenAPI spec written to {SPEC_PATH}")
    print(f"  Routes: {len(spec.get('paths', {}))}")

    if "--generate" in sys.argv:
        import subprocess

        for lang, cfg in SDK_LANGUAGES.items():
            cmd = (
                f"npx @openapitools/openapi-generator-cli generate "
                f"-i {SPEC_PATH} -g {cfg['generator']} "
                f"-o {cfg['output']} {cfg['extra']}"
            ).strip()
            print(f"\nGenerating {lang} SDK...")
            subprocess.run(cmd, shell=True, check=True)
    else:
        print("\nTo generate SDKs, run with --generate flag.")
        print("Or manually run openapi-generator per language:")
        for lang, cfg in SDK_LANGUAGES.items():
            cmd = (
                f"  npx @openapitools/openapi-generator-cli generate "
                f"-i {SPEC_PATH} -g {cfg['generator']} "
                f"-o {cfg['output']} {cfg['extra']}"
            ).strip()
            print(f"  {cmd}")


if __name__ == "__main__":
    main()
