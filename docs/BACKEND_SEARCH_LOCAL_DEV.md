# Backend, Search, and Local Development Notes

Last verified: 2026-06-05.

## Backend Stack

The backend is a FastAPI application under `backend/app`.

- Runtime: FastAPI + Uvicorn, async SQLAlchemy 2.x, Pydantic v2, pydantic-settings.
- API shape: routers are aggregated in `app/api/v1/router.py` and mounted under `/api/v1`.
- Database: SQLite is supported for local development; production uses PostgreSQL with `asyncpg`.
- Migrations: Alembic exists, but `app.main` also calls `Base.metadata.create_all()` during startup for development bootstrapping.
- Storage: `app/services/storage.py` supports local filesystem and S3-compatible object storage. Production uses MinIO.
- Auth/security: JWT via `python-jose`, password hashing via `passlib`/`bcrypt`, role checks in `app/core/deps.py`.
- AI analysis: provider configuration can come from environment variables or DB-backed `ai_provider_configs`; runtime flags are resolved in `app/services/runtime_settings.py`.
- Background work: default task dispatcher can run via FastAPI background tasks; Celery/Redis settings exist for queue-backed operation.
- Media processing: Pillow-based image processing creates thumbnails and compressed images.
- Taxonomy: controlled facets/nodes/aliases live in `taxonomy_facets`, `taxonomy_nodes`, `taxonomy_aliases`, and `photo_classifications`.

Important local data observed in `backend/visual_buct.db`:

- `photos`: 496
- `tags`: 839
- `photo_tags`: 2782
- `taxonomy_facets`: 8
- `taxonomy_nodes`: 83
- `taxonomy_aliases`: 118
- `photo_classifications`: 2211

## Search Architecture

There are two search surfaces with different behavior.

### 1. Public photo list search

Endpoint: `GET /api/v1/photos/public`

Relevant files:

- `backend/app/api/v1/endpoints/photos.py`
- `backend/app/crud/photo.py`
- `backend/app/services/search_interpreter.py`
- `backend/app/services/taxonomy.py`

Modes:

- Plain keyword search: `search=<query>` checks filename, description, free tags, taxonomy node names, and taxonomy aliases using SQL `ilike`.
- Structured filters: `season`, `campus`, `building`/`landmark`, `gallery_series`, `gallery_year`, `award_level`, `photo_type`, `documentary_topic`.
- Smart search: `smart=true&search=<query>` runs `SearchInterpreter`.

`SearchInterpreter` works in layers:

- Builds a TTL in-memory alias index from active taxonomy facets, nodes, and aliases.
- Rule interpretation maps words such as `秋天` to facet filters such as `season=秋季`.
- Optional AI rewrite can call configured AI providers to rewrite natural language into facet filters and keywords.
- Fallback returns plain keywords.

This endpoint is currently the most robust local-development search path because it does not require Milvus or sentence-transformer dependencies.

### 2. Standalone vector search

Endpoint: `GET /api/v1/search`

Relevant files:

- `backend/app/api/v1/endpoints/search.py`
- `backend/app/services/vector_search_service.py`
- `backend/app/services/embedding_service.py`
- `backend/app/services/milvus_client.py`
- `backend/scripts/vectorize_tags.py`

Flow:

1. Encode query text with `BAAI/bge-small-zh-v1.5` into a 512-dimensional vector.
2. Query Milvus collection `photo_vectors`.
3. Extract matched `tag_text` values.
4. Query relational DB for photos that have those tags.
5. Load approved photos and return tags/classifications with a normalized score.

Production observations:

- Milvus is running in Docker on the server and exposes `19530`.
- Collection `photo_vectors` exists with 1156 entities and 512-dimensional vectors.
- The embedding model cache exists at `/data/visual-buct/vector-search/models/bge-small-zh`.

Current risks:

- `sentence-transformers` and `pymilvus` are used by code but are not listed in `backend/requirements.txt`.
- `milvus_client.py` hardcodes `localhost:19530`, so a local backend must either run local Milvus or use an SSH tunnel.
- `embedding_service.py` hardcodes a Linux cache path under `/data/...`, which is awkward on Windows and causes network/model-cache coupling.
- `/api/v1/search` has no keyword fallback. If embeddings or Milvus are unavailable, it returns an empty result set.
- The vector index is tag-centric, not photo-centric. It searches tag names, then maps tags back to photos; it does not embed full photo captions/descriptions/classifications as one document.
- Structured filters inside `VectorSearchService` compare attributes on `Photo` (`season`, `campus`, etc.) and do not fully use the taxonomy classification table. This can drift from the rest of the gallery search.
- The response schema currently omits full photo data, so frontend code that expects richer photo fields must fetch details separately or use `/photos/public`.

## Search Improvement Directions

Recommended order:

1. Add operational fallbacks.
   - Add `sentence-transformers` and `pymilvus` to an optional/vector requirements file or extras group.
   - Make Milvus host/port and embedding cache dir configurable.
   - Add a keyword/taxonomy fallback for `/api/v1/search` when vector dependencies fail.

2. Unify search semantics.
   - Reuse `SearchInterpreter` in `/api/v1/search`, not only `/photos/public`.
   - Apply structured filters through `photo_classifications` consistently instead of mixed legacy `Photo` fields.
   - Return a `search_mode` field such as `vector`, `keyword`, or `hybrid` so clients know what happened.

3. Improve retrieval quality.
   - Index a photo-level search document, for example: title/filename, description, free tags, taxonomy labels, author/competition metadata, and AI caption.
   - Keep tag-level vectors as signals, but combine them with photo-level vectors and relational filters.
   - Add deterministic score blending: vector similarity + exact facet match + tag match + recency/view boosts if desired.

4. Improve maintenance.
   - Trigger vector upsert/delete when tags or classifications change.
   - Add a health endpoint or admin status for embedding model readiness, Milvus connectivity, collection entity count, and last vectorization time.
   - Add tests for rule interpretation, keyword fallback, taxonomy filters, and vector-unavailable behavior.

## Local Backend Setup

The recommended local backend uses the local codebase against the real server
data services via SSH tunnels:

- PostgreSQL via local port `15432`
- MinIO via local port `19000`
- Milvus via local port `19530`

SQLite is only a fallback for isolated experiments and is not production-parity.

Start SSH tunnels:

```powershell
ssh -N -L 19530:127.0.0.1:19530 -L 19000:127.0.0.1:9000 yanp@121.195.148.85
```

For full parity, include PostgreSQL:

```powershell
ssh -N -L 15432:127.0.0.1:5432 -L 19000:127.0.0.1:9000 -L 19530:127.0.0.1:19530 yanp@121.195.148.85
```

Start backend from `backend/`:

```powershell
$env:DEBUG = 'True'
$env:AI_ENABLED = 'false'
$env:AI_SEARCH_ENABLED = 'false'
$env:DATABASE_URL = 'postgresql+asyncpg://visual_buct:<password>@127.0.0.1:15432/visual_buct'
$env:S3_ENDPOINT = 'http://127.0.0.1:19000'
$env:S3_SECRET_KEY = '<minio-secret>'
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Or use the repo helper from the repository root:

```powershell
# Put real values in backend/.env.remote-dev. This file is intentionally gitignored.
# DATABASE_URL=postgresql+asyncpg://visual_buct:<password>@127.0.0.1:15432/visual_buct
# S3_SECRET_KEY=<minio-secret>
.\scripts\start_local_backend.ps1
```

Use the SQLite fallback only when explicitly needed:

```powershell
.\scripts\start_local_backend.ps1 -UseSqlite
```

Why these overrides matter:

- The host environment had `DEBUG=release`, which overrides `.env` and fails Pydantic boolean parsing.
- `AI_ENABLED=false` prevents accidental local model/provider calls.
- `AI_SEARCH_ENABLED=false` keeps `/photos/public?smart=true` on rule-based interpretation unless explicitly testing AI rewrite.
- `S3_ENDPOINT=http://127.0.0.1:19000` makes local media reads go through the SSH tunnel to production MinIO.

Verified local endpoints:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/photos/public?limit=3'
Invoke-RestMethod 'http://127.0.0.1:8000/api/v1/photos/public?limit=3&search=%E7%A7%8B%E5%A4%A9&smart=true'
Invoke-WebRequest 'http://127.0.0.1:8000/api/v1/photos/d348b9f6-2203-5fcd-a6ca-de3cefb0c006/image/thumbnail' -OutFile $env:TEMP\buct_thumb_test.jpg
```

Observed behavior:

- Health check works.
- Public photo listing works against the remote PostgreSQL data via tunnel.
- Thumbnail retrieval works through the MinIO SSH tunnel.
- Smart gallery search works in rule mode; for `秋天`, it interprets `season=秋季`.
- Standalone `/api/v1/search` works when `pymilvus`, `sentence-transformers`, the BGE model cache, and the Milvus SSH tunnel are available.

## Parity Check Before Feature Work

Run the parity check before starting backend work and again before deploying:

```powershell
python scripts/check_backend_parity.py
```

The script checks:

- local and remote git commit/branch/worktree status
- local and remote Python version
- key backend packages, including vector-search packages
- local MinIO and Milvus SSH tunnel ports
- local embedding model cache
- local `/health`, `/photos/public`, and `/search` endpoints

Known current differences:

- Production Python is `3.12.13`; the preferred Windows local venv is `.venv312` on Python `3.12.6`.
- Production runs PostgreSQL; parity local development reaches it through an SSH tunnel.
- Production MinIO/Milvus are local to the server; parity local development reaches them through SSH tunnels.
- `backend/requirements.txt` uses ranges, so package patch versions can drift. Use `scripts/check_backend_parity.py` to detect drift before deployment-sensitive work.

Deployment-sensitive rules:

- If new code depends on a Python package, add it to `backend/requirements.txt`; production deploy runs `pip install -r requirements.txt`.
- Production deploy also applies `backend/constraints-prod.txt` to avoid accidental package drift.
- When production packages intentionally change, regenerate or update `backend/constraints-prod.txt` from the verified server environment.
- If new code changes schema, add an Alembic migration; production deploy runs `alembic upgrade head`.
- If new code changes taxonomy assumptions, verify `backend/scripts/migrate_taxonomy_2026.py --apply` still succeeds; production deploy runs it.
- If new code touches vector search, verify `/api/v1/search` locally with the Milvus tunnel and on production after deploy.
- If new code touches media access, verify a thumbnail/original image endpoint locally with the MinIO tunnel.

Recommended feature workflow:

```powershell
# 1. Keep tunnels open in a separate shell.
ssh -N -L 19530:127.0.0.1:19530 -L 19000:127.0.0.1:9000 yanp@121.195.148.85

# 2. Start backend from backend/.
.\scripts\start_local_backend.ps1

# 3. From repo root, check parity.
$env:LOCAL_BACKEND_PYTHON = 'D:\BUCT_Media_System\.venv312\Scripts\python.exe'
python scripts/check_backend_parity.py
```

## Docker Note

No Docker image pull is required for the basic local backend. If a fully local Milvus/MinIO/PostgreSQL stack is needed later, prefer fixing Docker Desktop registry/proxy separately before introducing containers into this backend setup.
