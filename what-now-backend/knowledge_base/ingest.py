"""Ingest KB documents into Moss index. Optionally parse via Unsiloed first."""

import asyncio
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

DOCS_DIR = Path(__file__).parent / "docs"
UNSILOED_BASE = os.getenv("UNSILOED_BASE_URL", "https://prod.visionapi.unsiloed.ai")


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_with_unsiloed(path: Path, api_key: str) -> str | None:
    """Optional: parse document through Unsiloed API. Returns text or None on failure."""
    try:
        with path.open("rb") as f:
            response = httpx.post(
                f"{UNSILOED_BASE}/parse",
                headers={"api-key": api_key},
                files={"file": (path.name, f, "text/plain")},
                timeout=60.0,
            )
        if response.status_code != 200:
            print(f"  Unsiloed parse failed for {path.name}: {response.status_code}")
            return None

        job_id = response.json().get("job_id")
        if not job_id:
            return None

        for _ in range(30):
            time.sleep(2)
            status_resp = httpx.get(
                f"{UNSILOED_BASE}/parse/{job_id}",
                headers={"api-key": api_key},
                timeout=30.0,
            )
            if status_resp.status_code != 200:
                continue
            data = status_resp.json()
            if data.get("status") == "Succeeded":
                chunks = data.get("chunks", [])
                return "\n\n".join(
                    c.get("embed", c.get("text", "")) for c in chunks if c
                )
            if data.get("status") in ("Failed", "Cancelled"):
                print(f"  Unsiloed job failed for {path.name}")
                return None
    except Exception as exc:
        print(f"  Unsiloed error for {path.name}: {exc}")
    return None


def _load_documents() -> list[tuple[str, str, dict]]:
    unsiloed_key = os.getenv("UNSILOED_API_KEY", "").strip()
    documents = []

    for path in sorted(DOCS_DIR.glob("*.txt")):
        print(f"Loading {path.name}...")
        text = None
        if unsiloed_key:
            text = _parse_with_unsiloed(path, unsiloed_key)
        if not text:
            text = _read_txt(path)

        doc_id = path.stem
        metadata = {"source": path.name, "category": doc_id.replace("_", " ")}
        documents.append((doc_id, text, metadata))
        print(f"  Loaded {len(text)} chars")

    return documents


async def _ingest_moss(documents: list[tuple[str, str, dict]]) -> None:
    from moss import DocumentInfo, MossClient

    project_id = os.getenv("MOSS_PROJECT_ID")
    project_key = os.getenv("MOSS_PROJECT_KEY")
    index_name = os.getenv("MOSS_INDEX_NAME", "what-now-kb")

    if not project_id or not project_key:
        raise ValueError("MOSS_PROJECT_ID and MOSS_PROJECT_KEY must be set in .env")

    client = MossClient(project_id, project_key)
    moss_docs = [
        DocumentInfo(id=doc_id, text=text, metadata=metadata)
        for doc_id, text, metadata in documents
    ]

    print(f"\nCreating Moss index '{index_name}' with {len(moss_docs)} documents...")
    await client.create_index(index_name, moss_docs, "moss-minilm")
    print("Loading index into runtime...")
    await client.load_index(index_name)
    print(f"\nDone. Moss index '{index_name}' is ready.")
    print(f"Set MOSS_INDEX_NAME={index_name} in .env (already default).")


def main():
    documents = _load_documents()
    if not documents:
        print(f"No .txt files found in {DOCS_DIR}")
        return
    asyncio.run(_ingest_moss(documents))


if __name__ == "__main__":
    main()
