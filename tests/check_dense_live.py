"""Direct evidence that the dense half of retrieval is live, not just configured.

Prints whether the index has vectors, whether a query produced dense hits, and
which passages only the dense half found (BM25 rank missing, dense rank present).
"""

from __future__ import annotations

import sys

from app.config import settings
from app.retrieve import search
from app.store import store

print(f"use_dense={settings.use_dense} backend={settings.embedding_backend} model={settings.embedding_model}")
print(f"embeddings_path={settings.embeddings_path} exists={settings.embeddings_path.exists()}")
if not store.ready:
    store.reload()

index = store.snapshot
print(f"chunks={len(index.chunks)} dense_ready={index.dense_ready}")
if index.embeddings is not None:
    print(f"vectors shape={index.embeddings.shape}")

queries = [
    "how expensive is the alternative treatment programme",
    "are outcomes better abroad than back home",
    "what does the doctor team look like",
    "can i pay in instalments",
]

for question in queries:
    result = search(question)
    dense_only = [h for h in result.hits if h.dense_rank is not None and h.bm25_rank is None]
    both = [h for h in result.hits if h.dense_rank is not None and h.bm25_rank is not None]
    print()
    print(f"Q: {question}")
    print(f"  used_dense={result.used_dense} confidence={result.confidence:.3f} hits={len(result.hits)}")
    print(f"  hits found by both halves={len(both)}  by dense only={len(dense_only)}")
    for hit in result.hits[:4]:
        print(
            f"    bm25_rank={hit.bm25_rank} dense_rank={hit.dense_rank} "
            f"{hit.chunk['page_type']}/{hit.chunk['section'][:44]}"
        )

if index.embeddings is None or not index.dense_ready:
    print()
    print("FAIL: dense half is not ready")
    sys.exit(1)
