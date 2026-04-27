"""Export the FastAPI OpenAPI schema to JSON and YAML files."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
OUTPUT_DIR = ROOT / "docs" / "openapi"


def ensure_env() -> None:
    """Set safe defaults so schema export does not depend on local runtime env."""
    os.environ["DEBUG"] = "false"
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./visual_buct.db")
    os.environ.setdefault("UPLOAD_DIR", "./uploads")


def main() -> int:
    ensure_env()
    sys.path.insert(0, str(BACKEND_DIR))

    from app.main import app

    schema = app.openapi()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUTPUT_DIR / "openapi.json"
    yaml_path = OUTPUT_DIR / "openapi.yaml"

    json_path.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    yaml_path.write_text(
        yaml.safe_dump(
            schema,
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    print(f"Exported OpenAPI JSON: {json_path}")
    print(f"Exported OpenAPI YAML: {yaml_path}")
    print(f"Paths exported: {len(schema.get('paths', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
