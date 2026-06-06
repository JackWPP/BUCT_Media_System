#!/usr/bin/env python3
"""Check local backend environment against the production server.

This script is intentionally dependency-free. It reports the differences that
usually make a local change work here but fail after deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
DEFAULT_LOCAL_PYTHON = REPO_ROOT / ".venv312" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
REMOTE_ROOT = "/opt/visual_buct/BUCT_Media_System"
REMOTE_BACKEND = f"{REMOTE_ROOT}/backend"
REMOTE_PYTHON = f"{REMOTE_BACKEND}/.venv/bin/python"
REMOTE_HOST = "yanp@121.195.148.85"

KEY_PACKAGES = [
    "fastapi",
    "sqlalchemy",
    "pydantic",
    "pydantic-settings",
    "uvicorn",
    "asyncpg",
    "boto3",
    "pymilvus",
    "sentence-transformers",
    "torch",
    "transformers",
]


def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def run_shell(command: str, timeout: int = 30) -> tuple[int, str]:
    return run(["ssh", REMOTE_HOST, command], cwd=REPO_ROOT, timeout=timeout)


def status(ok: bool, label: str, detail: str = "", warn: bool = False) -> None:
    mark = "OK" if ok else ("WARN" if warn else "FAIL")
    suffix = f" - {detail}" if detail else ""
    print(f"[{mark}] {label}{suffix}")


def parse_freeze(text: str) -> dict[str, str]:
    packages: dict[str, str] = {}
    for line in text.splitlines():
        if "==" not in line:
            continue
        name, version = line.split("==", 1)
        packages[name.lower().replace("_", "-")] = version
    return packages


def python_info(python: Path) -> tuple[str, dict[str, str]]:
    code, version = run([str(python), "--version"], cwd=BACKEND_DIR)
    if code != 0:
        return f"unavailable: {version}", {}
    code, freeze = run([str(python), "-m", "pip", "freeze"], cwd=BACKEND_DIR, timeout=90)
    return version, parse_freeze(freeze if code == 0 else "")


def remote_python_info() -> tuple[str, dict[str, str]]:
    command = f"cd {REMOTE_BACKEND} && {REMOTE_PYTHON} --version && {REMOTE_PYTHON} -m pip freeze"
    code, output = run_shell(command, timeout=90)
    if code != 0:
        return f"unavailable: {output}", {}
    lines = output.splitlines()
    return lines[0], parse_freeze("\n".join(lines[1:]))


def git_info(local: bool) -> tuple[str, str, str]:
    if local:
        head = run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT)[1]
        branch = run(["git", "branch", "--show-current"], cwd=REPO_ROOT)[1]
        dirty = run(["git", "status", "--short"], cwd=REPO_ROOT)[1]
        return head, branch, dirty
    command = f"cd {REMOTE_ROOT} && git rev-parse HEAD && git branch --show-current && git status --short"
    code, output = run_shell(command)
    if code != 0:
        return "unavailable", "", output
    lines = output.splitlines()
    return lines[0] if lines else "", lines[1] if len(lines) > 1 else "", "\n".join(lines[2:])


def tcp_open(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def compact_preview(value: Any, limit: int = 500) -> str:
    text = json.dumps(value, ensure_ascii=False)
    return text[:limit]


def http_json(url: str, timeout: int = 10) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            raw = response.read(4096)
            charset = response.headers.get_content_charset() or "utf-8"
            body = raw.decode(charset, errors="replace")
            try:
                parsed = json.loads(body)
                return True, compact_preview(parsed)
            except json.JSONDecodeError:
                return True, body[:500]
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--skip-remote", action="store_true")
    args = parser.parse_args()
    local_python = Path(os.environ.get("LOCAL_BACKEND_PYTHON", DEFAULT_LOCAL_PYTHON))

    print("== Git ==")
    local_head, local_branch, local_dirty = git_info(local=True)
    status(True, "local branch", local_branch)
    status(not local_dirty, "local worktree clean", local_dirty or "clean", warn=bool(local_dirty))

    remote_head = remote_branch = remote_dirty = ""
    if not args.skip_remote:
        remote_head, remote_branch, remote_dirty = git_info(local=False)
        status(remote_head == local_head, "remote HEAD matches local", f"local={local_head} remote={remote_head}", warn=remote_head != local_head)
        status(remote_branch == local_branch, "remote branch matches local", f"local={local_branch} remote={remote_branch}", warn=remote_branch != local_branch)
        status(not remote_dirty, "remote worktree clean", remote_dirty or "clean", warn=bool(remote_dirty))

    print("\n== Python and packages ==")
    local_version, local_packages = python_info(local_python)
    status(local_python.exists(), "local venv python", f"{local_python} ({local_version})", warn=not local_python.exists())

    remote_version = ""
    remote_packages: dict[str, str] = {}
    if not args.skip_remote:
        remote_version, remote_packages = remote_python_info()
        status(local_version == remote_version, "python version parity", f"local={local_version} remote={remote_version}", warn=local_version != remote_version)

    for package in KEY_PACKAGES:
        local_pkg = local_packages.get(package)
        remote_pkg = remote_packages.get(package) if remote_packages else None
        if args.skip_remote:
            status(bool(local_pkg), f"local package {package}", local_pkg or "missing", warn=not local_pkg)
        else:
            ok = bool(local_pkg and remote_pkg and local_pkg == remote_pkg)
            warn = bool(local_pkg and remote_pkg and local_pkg != remote_pkg)
            status(ok, f"package {package}", f"local={local_pkg or 'missing'} remote={remote_pkg or 'missing'}", warn=warn)

    print("\n== Local service dependencies ==")
    status(tcp_open("127.0.0.1", 19000), "MinIO tunnel 127.0.0.1:19000", warn=not tcp_open("127.0.0.1", 19000))
    status(tcp_open("127.0.0.1", 19530), "Milvus tunnel 127.0.0.1:19530", warn=not tcp_open("127.0.0.1", 19530))
    model_cache = Path("/data/visual-buct/vector-search/models/bge-small-zh").resolve()
    status(model_cache.exists(), "embedding model cache", str(model_cache), warn=not model_cache.exists())

    print("\n== Local API ==")
    ok, detail = http_json(f"{args.api_base}/health")
    status(ok, "health endpoint", detail, warn=not ok)
    ok, detail = http_json(f"{args.api_base}/api/v1/photos/public?limit=1")
    status(ok, "public photos endpoint", detail, warn=not ok)
    ok, detail = http_json(f"{args.api_base}/api/v1/search?q=%E5%9B%BE%E4%B9%A6%E9%A6%86&limit=1", timeout=30)
    status(ok, "vector search endpoint", detail, warn=not ok)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
