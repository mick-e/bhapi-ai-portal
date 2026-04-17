# Bhapi Public API SDKs

Auto-generated SDK clients for the Bhapi Public API.

## Directory Structure

```
sdks/
  openapi.json   # OpenAPI 3.1 spec (tracked in git)
  README.md      # This file (tracked in git)
  python/        # Generated Python SDK (gitignored)
  js/            # Generated TypeScript/JS SDK (gitignored)
  swift/         # Generated Swift SDK (gitignored)
  kotlin/        # Generated Kotlin SDK (gitignored)
```

## Regenerating the OpenAPI Spec

```bash
python scripts/generate_sdk.py
```

This creates `sdks/openapi.json` from the live FastAPI app, filtered to
public API routes (`/api/v1/platform/*`).

## Generating SDK Clients

Requires `@openapitools/openapi-generator-cli` (installed via npm):

```bash
# Generate all language SDKs at once
python scripts/generate_sdk.py --generate

# Or generate a single language manually
npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g python -o sdks/python -p packageName=bhapi

npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g typescript-fetch -o sdks/js

npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g swift5 -o sdks/swift

npx @openapitools/openapi-generator-cli generate \
  -i sdks/openapi.json -g kotlin -o sdks/kotlin
```

## CI/CD

The `sdk_release.yml` GitHub Actions workflow automatically regenerates
the spec and SDK stubs on tagged releases (`v*`).
