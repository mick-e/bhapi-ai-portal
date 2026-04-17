"""Export filtered OpenAPI spec for public API SDK generation."""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi


def export_public_openapi(app: FastAPI) -> dict:
    """Generate OpenAPI 3.1 spec filtered to public API routes only."""
    public_routes = [
        r
        for r in app.routes
        if hasattr(r, "path") and r.path.startswith("/api/v1/platform/")
    ]
    spec = get_openapi(
        title="Bhapi Public API",
        version="1.0.0",
        description=(
            "Public API for the Bhapi Family AI Governance Platform. "
            "Manage API keys, monitor AI safety events, and integrate "
            "with your school or family management system."
        ),
        routes=public_routes,
    )
    spec["servers"] = [
        {"url": "https://api.bhapi.ai", "description": "Production"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ]
    return spec


def write_spec(output_path: Path, app: FastAPI) -> None:
    """Write the filtered OpenAPI spec to a JSON file."""
    spec = export_public_openapi(app)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2))
