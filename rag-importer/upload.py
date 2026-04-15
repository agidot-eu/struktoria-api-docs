"""
upload.py — Send a Struktoria RAG SQLite import file to the RAG API.

Reads import_nodes from the local SQLite file and uploads them to a RAG source
via POST /v1/rag/api/sources/{source_id}/upload-nodes.
Optionally triggers the indexing job (chunking + embedding) afterwards.

Usage:
  python upload.py \\
      --db struktoria-db.sqlite \\
      --server https://struktoria-dev.agidot.eu \\
      --source-id <UUID> \\
      [--token "Bearer eyJ..."] \\
      [--prefix "imports/mssql"] \\
      [--batch-size 100] \\
      [--session-id <UUID>] \\
      [--trigger-index] \\
      [--async-proxy https://...] \\
      [--basic-user user --basic-pass pass] \\
      [--dry-run]

Authentication:
  --token    JWT Bearer token (or set STRUKTORIA_TOKEN env var)
  ~/.struktoria/config.json is NOT read — use upload.py as a standalone tool
  or pass credentials explicitly.

Requires:
  pip install requests
"""

import argparse
import base64
import json
import os
import sys
import time
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

from schema import ImportDb


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

class RagApiClient:
    def __init__(
        self,
        server_url: str,
        token: Optional[str],
        basic_user: Optional[str] = None,
        basic_pass: Optional[str] = None,
        timeout: int = 60,
    ):
        self.server_url = server_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()

        if token:
            self.session.headers["AgnetAuth"] = token
        if basic_user and basic_pass:
            creds = base64.b64encode(f"{basic_user}:{basic_pass}".encode()).decode()
            self.session.headers["Authorization"] = f"Basic {creds}"

    def _rag_url(self, path: str) -> str:
        return f"{self.server_url}/v1/rag/api/{path.lstrip('/')}"

    def _async_url(self, path: str) -> str:
        return f"{self.server_url}/v1/async/api/{path.lstrip('/')}"

    def upload_nodes(self, source_id: str, nodes: list[dict]) -> dict:
        """POST /v1/rag/api/sources/{id}/upload-nodes"""
        url = self._rag_url(f"sources/{source_id}/upload-nodes")
        resp = self.session.post(url, json={"nodes": nodes}, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def trigger_index(self, source_id: str) -> str:
        """POST /v1/rag/api/sources/{id}/index — returns job id."""
        url = self._rag_url(f"sources/{source_id}/index")
        resp = self.session.post(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("jobId") or data.get("id") or str(data)

    def poll_job(self, async_proxy_url: str, job_id: str, poll_interval: float = 2.0) -> dict:
        """Poll /v1/async/api/status/{jobId} until Completed or Failed."""
        url = f"{async_proxy_url.rstrip('/')}/v1/async/api/status/{job_id}"
        while True:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")
            if status in ("Completed", "Failed", "Faulted"):
                return data
            print(f"  Job status: {status}... (waiting {poll_interval:.0f}s)")
            time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Upload logic
# ---------------------------------------------------------------------------

def upload(
    db_path: str,
    server: str,
    source_id: str,
    token: Optional[str],
    prefix: Optional[str],
    batch_size: int,
    session_id: Optional[str],
    trigger_index: bool,
    async_proxy: Optional[str],
    basic_user: Optional[str],
    basic_pass: Optional[str],
    dry_run: bool,
):
    if not os.path.isfile(db_path):
        print(f"ERROR: SQLite file not found: {db_path}", file=sys.stderr)
        sys.exit(1)

    if not token:
        token = os.environ.get("STRUKTORIA_TOKEN")
    if not token:
        print(
            "ERROR: No authentication token provided.\n"
            "  Use --token or set the STRUKTORIA_TOKEN environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = RagApiClient(
        server_url=server,
        token=token,
        basic_user=basic_user,
        basic_pass=basic_pass,
    )

    print(f"SQLite file:  {db_path}")
    print(f"Server:       {server}")
    print(f"Source ID:    {source_id}")
    if prefix:
        print(f"Path prefix:  {prefix}")
    if dry_run:
        print("DRY RUN — no data will be sent to the API")
    print()

    total_created = 0
    total_skipped = 0
    batch_num = 0

    with ImportDb(db_path) as db:
        total_nodes = db.count_nodes(session_id)
        print(f"Nodes to upload: {total_nodes}")

        for batch in db.iter_nodes(session_id=session_id, batch_size=batch_size):
            batch_num += 1
            offset = (batch_num - 1) * batch_size
            print(f"[{min(offset + len(batch), total_nodes)}/{total_nodes}] Uploading batch {batch_num}...", end=" ", flush=True)

            nodes = []
            for row in batch:
                rel_path = row["relative_path"]
                if prefix:
                    rel_path = f"{prefix}/{rel_path}"
                nodes.append({
                    "relativePath": rel_path,
                    "content": row["content"],
                    "nodeType": row["node_type"],
                })

            if dry_run:
                print(f"(dry run, {len(nodes)} nodes)")
                total_created += len(nodes)
                continue

            try:
                result = client.upload_nodes(source_id, nodes)
                created = result.get("created", 0)
                skipped = result.get("skipped", 0)
                total_created += created
                total_skipped += skipped
                print(f"created={created}, skipped={skipped}")
            except requests.HTTPError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                print(f"Response: {e.response.text[:500]}", file=sys.stderr)
                sys.exit(1)

    print(f"\nUpload complete.")
    print(f"  Total created: {total_created}")
    print(f"  Total skipped: {total_skipped}")

    if trigger_index and not dry_run:
        print("\nTriggering index job (chunking + embedding)...")
        job_id = client.trigger_index(source_id)
        print(f"  Job ID: {job_id}")

        if async_proxy:
            print("  Polling for completion...")
            result = client.poll_job(async_proxy, job_id)
            status = result.get("status", "unknown")
            print(f"  Index job finished: {status}")
            if status not in ("Completed",):
                print(f"  Details: {json.dumps(result, indent=2)}", file=sys.stderr)
                sys.exit(1)
        else:
            print("  (use --async-proxy to poll job status)")

    elif trigger_index and dry_run:
        print("\n(dry run: skipping index trigger)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload a Struktoria RAG SQLite import file to the RAG API.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--db",
        required=True,
        help="Path to the SQLite import file",
    )
    parser.add_argument(
        "--server",
        required=True,
        help="Struktoria server base URL, e.g. https://struktoria-dev.agidot.eu",
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="RAG source UUID (must already exist on the server)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help='JWT Bearer token (or set STRUKTORIA_TOKEN env var)',
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Optional path prefix to prepend to all node paths in RAG",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of nodes per API request (default: 100)",
    )
    parser.add_argument(
        "--session-id",
        default=None,
        help="Only upload nodes from a specific import session UUID",
    )
    parser.add_argument(
        "--trigger-index",
        action="store_true",
        help="After upload, trigger the indexing job (chunking + embedding)",
    )
    parser.add_argument(
        "--async-proxy",
        default=None,
        help="Async proxy base URL for polling index job status (e.g. same as --server)",
    )
    parser.add_argument(
        "--basic-user",
        default=None,
        help="Basic Auth username (optional)",
    )
    parser.add_argument(
        "--basic-pass",
        default=None,
        help="Basic Auth password (optional)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read data but do not send to API",
    )

    args = parser.parse_args()

    upload(
        db_path=args.db,
        server=args.server,
        source_id=args.source_id,
        token=args.token,
        prefix=args.prefix,
        batch_size=args.batch_size,
        session_id=args.session_id,
        trigger_index=args.trigger_index,
        async_proxy=args.async_proxy,
        basic_user=args.basic_user,
        basic_pass=args.basic_pass,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
