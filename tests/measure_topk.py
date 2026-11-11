"""Does raising TOP_K from 8 to 12 actually add anything?

For each eval question, look at what ranks 9-12 contain that ranks 1-8 do not.
If they only repeat pages already present, the extra four chunks are prompt
tokens and nothing else.
"""

from __future__ import annotations

import sys

from app.retrieve import search
from tests.run_eval import CASES


def main() -> int:
    added_any = 0
    for case in CASES:
        query = case.question
        result = search(query, top_k=12)
        pages = [hit.chunk["page_type"] for hit in result.hits]
        first8 = set(pages[:8])
        extra = [p for p in pages[8:] if p not in first8]
        if extra:
            added_any += 1
        print(
            f"[{case.number:2}] conf={result.confidence:.2f} "
            f"top8={len(first8)} new_at_9_12={extra or '-'}  {case.kind}"
        )
    print()
    print(f"questions where ranks 9-12 add a page not already present: {added_any}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
