import asyncio
import os
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MAX_RETRIES = 1
# 15ms — miss fast and use local KB fallback for demo latency
MOSS_TIMEOUT = float(os.getenv("MOSS_TIMEOUT_MS", "15")) / 1000.0

DOCS_DIR = Path(__file__).parent / "docs"

_moss_client = None
_index_loaded = False


def _get_moss_client():
    global _moss_client
    if _moss_client is not None:
        return _moss_client

    from moss import MossClient

    project_id = os.getenv("MOSS_PROJECT_ID")
    project_key = os.getenv("MOSS_PROJECT_KEY")
    if not project_id or not project_key:
        raise ValueError("MOSS_PROJECT_ID and MOSS_PROJECT_KEY must be set in .env")
    _moss_client = MossClient(project_id, project_key)
    return _moss_client


def local_search(query: str) -> str:
    """
    Fast local search over KB docs.
    Used when Moss is unavailable.
    """
    query_words = set(query.lower().split())
    best_chunks: list[tuple[int, str]] = []

    if not DOCS_DIR.is_dir():
        return ""

    for filename in os.listdir(DOCS_DIR):
        if not filename.endswith(".txt"):
            continue

        filepath = DOCS_DIR / filename
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        paragraphs = [
            p.strip() for p in content.split("\n\n") if len(p.strip()) > 50
        ]

        for para in paragraphs:
            para_words = set(para.lower().split())
            overlap = len(query_words & para_words)
            if overlap >= 2:
                best_chunks.append((overlap, para[:500]))

    best_chunks.sort(reverse=True, key=lambda x: x[0])
    top = [chunk for _, chunk in best_chunks[:3]]

    if top:
        return "\n\n".join(top)
    return ""


def _format_results(results) -> str:
    chunks = []
    for doc in results.docs[:3]:
        score = getattr(doc, "score", 0)
        text = getattr(doc, "text", str(doc))
        chunks.append(f"[score={score:.2f}] {text}")
    return "\n\n".join(chunks)


async def _search_async(query: str) -> str:
    global _index_loaded

    from moss import QueryOptions

    client = _get_moss_client()
    index_name = os.getenv("MOSS_INDEX_NAME", "what-now-kb")

    if not _index_loaded:
        try:
            await asyncio.wait_for(
                client.load_index(index_name),
                timeout=MOSS_TIMEOUT,
            )
            _index_loaded = True
        except asyncio.TimeoutError:
            print(f"[MOSS] ⏱️ index load timeout ({int(MOSS_TIMEOUT * 1000)}ms) — local fallback")
        except Exception as exc:
            print(f"[Moss] Could not load index '{index_name}': {exc}")

    start = time.perf_counter()

    for attempt in range(MAX_RETRIES):
        try:
            results = await asyncio.wait_for(
                client.query(
                    index_name,
                    query,
                    QueryOptions(top_k=3, alpha=0.6),
                ),
                timeout=MOSS_TIMEOUT,
            )
            if results.docs:
                elapsed = int((time.perf_counter() - start) * 1000)
                print(f"[MOSS] ✅ {elapsed}ms")
                return _format_results(results)

            print("[MOSS] ⚠️ empty results — local fallback")
            break
        except asyncio.TimeoutError:
            print(f"[MOSS] ⏱️ query timeout ({int(MOSS_TIMEOUT * 1000)}ms) — local fallback")
            break
        except Exception as exc:
            err = str(exc)
            if "503" in err:
                print("[MOSS] ⚠️ 503 — local fallback")
            else:
                print(f"[MOSS] ❌ {exc} — local fallback")
            break

    result = local_search(query)
    elapsed = int((time.perf_counter() - start) * 1000)
    print(f"[MOSS] 📁 local fallback {elapsed}ms")
    return result or "No specific information found for this query."


def search_kb(query: str) -> str:
    return asyncio.run(_search_async(query))
