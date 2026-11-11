# Retrieval evaluation

Exploratory measurement, not a pre-registered experiment. The questions were
written after reading the corpus, so the labels and the corpus share an author.
Read the numbers as an estimate of what retrieval does on questions like these,
not as a prediction of production accuracy.

## What was measured

Does adding the dense half (`mistral-embed` + reciprocal rank fusion) to BM25
find the page that answers a visitor's question more often than BM25 alone?

A system that "cannot be shown to be wrong" is not measured. This one can: if
hybrid retrieval loses pages that BM25 alone finds, the dense half is not paying
for itself.

## Provenance

| Item | Value |
| --- | --- |
| Command | `.\.venv\Scripts\python.exe -m tests.retrieval_eval` |
| Script | `tests/retrieval_eval.py` |
| Corpus | `data/corpus.json`, `built_at` = **2026-11-11T09:38:42Z** |
| Corpus size | 7 pages, 183 chunks |
| Dense vectors | `data/embeddings.npy`, shape (183, 1024), `mistral-embed` via the API backend |
| Retrieval settings | `TOP_K=8`, `CANDIDATE_K=24`, RRF `k=60`, gate `MIN_RETRIEVAL_SCORE=0.40` |
| Model calls | none for generation; one embed call per question in the dense column |
| Determinism | run twice, stdout byte-identical, exit code 0 both times |

`data/embeddings.npy` is gitignored. On a clean checkout the dense column is
unavailable and the script prints `HYBRID COLUMN UNAVAILABLE` instead of a
number. The numbers below were produced on a machine where the cache exists.

The script runs itself twice as a subprocess, with `USE_DENSE=0` and
`USE_DENSE=1`. One process cannot hold both configurations because the index is
built at import time.

## How the labels were made

41 answerable questions and 10 unanswerable ones, 51 labels in total.

- A page is gold only if its text literally contains the answer. Where the same
  fact sits on more than one page (the three treatment packages share one price
  table; the profile repeats the headline price), every such page is gold,
  because a reader sent to any of them can answer.
- Questions that could not be labelled with confidence were dropped, not
  guessed. Cost questions asked against the price list were kept only where the
  list actually carries the procedure (breast, prostate, lung, pancreatic,
  colorectal, colon).
- The unanswerable set is ten questions about things the seven pages do not
  cover: dental implants, hair transplant, flights and hotels, refunds,
  insurance, paediatric oncology in Germany, clinic success rates, medical
  visas, Tijuana weather, and an unrelated sports question. Their purpose is to
  test the confidence gate, not retrieval.

**Limitation:** the labels are one person's reading of seven pages. There is no
second annotator and no inter-annotator agreement figure. A question whose gold
page a different reader would choose differently is a real source of error in
every number below.

## Results

| Metric | BM25 only | BM25 + dense | Delta |
| --- | --- | --- | --- |
| hit@1 | 78.0% | 78.0% | +0.0 pp |
| hit@3 | 80.5% | 82.9% | +2.4 pp |
| hit@8 | 92.7% | 87.8% | **-4.9 pp** |
| MRR | 0.814 | 0.809 | -0.005 |

38 of 41 answerable questions had a gold page in the top 3 for BM25 alone; 34 of
41 for hybrid.

Unanswerable questions, where the correct behaviour is refusal:

| Metric | BM25 only | BM25 + dense |
| --- | --- | --- |
| Mean confidence | 0.367 | 0.490 |
| Below the 0.40 gate (refused) | 7 of 10 | 4 of 10 |

## Where it misses

Five of 41 questions had no gold page anywhere in the top 8 under hybrid
retrieval. All five return the same three pages, in the same order: the anal,
adrenal and adenocarcinoma packages. The page-type prior gives any query that
says "treatment" a +0.15 boost to `Treatment package`, and the three packages
then outscore the profile that actually holds the answer.

| Question | Gold page | What came back |
| --- | --- | --- |
| What hidden costs should I budget for when travelling for treatment? | price-comparison | package-anal, package-adenocarcinoma, package-adrenal |
| What determines whether I am accepted for treatment? | clinic-profile | package-adrenal, package-anal, package-adenocarcinoma |
| Is the treatment gentle and non-toxic according to patients? | clinic-profile, clinic-videos | package-anal, package-adrenal, package-adenocarcinoma |
| Can alternative treatment be combined with chemotherapy? | clinic-profile | package-anal, package-adrenal, package-adenocarcinoma |
| What risks should I consider before choosing alternative treatment? | clinic-profile | package-anal, package-adrenal, package-adenocarcinoma |

All five still carry confidence at or above 0.47, so the gate does not catch
them. Confidence measures whether the evidence contains the question's words,
not whether it contains the answer. "Chemotherapy" and "risks" do appear in the
package chunks (in the "who should consider" and exclusion lists), so coverage
looks healthy while the page that answers the question is absent.

Six of the ten unanswerable questions pass the gate under hybrid retrieval
(against three under BM25). The two worst are questions the corpus cannot
answer at all:

| Question | Confidence | What came back |
| --- | --- | --- |
| Do you offer a hair transplant in Istanbul? | 0.86 | price-comparison, clinic-videos, package-adenocarcinoma, clinic-profile |
| What is the success rate for stage 4 pancreatic cancer at this clinic? | 0.87 | clinic-profile |

"Success rate" is close enough in words to the videos page and the profile; the
dense half pushes confidence up through its +0.15 cosine bonus, which is why
more off-topic questions pass the gate under hybrid than under BM25.

## Conclusion

Hybrid retrieval does not beat BM25 on this corpus, and the README should stop
claiming that the dense half is justified. The honest summary:

- hit@8 is **worse** under hybrid (87.8% vs 92.7%). Two questions that BM25
  found within eight chunks are pushed out by fused dense candidates.
- hit@3 is better (+2.4 pp) and hit@1 is unchanged. The dense half helps a
  little when the answer page is already near the top, and hurts when it is not.
- MRR is slightly lower (0.809 vs 0.814).
- Mean confidence on unanswerable questions rises from 0.367 to 0.490, and the
  number refused falls from 7 of 10 to 4 of 10. The gate gets less useful, not
  more.

The subtitle in `app/retrieve.py` says dense retrieval "covers the paraphrases
BM25 misses". On this labelled set that does not hold: the paraphrases that miss
under BM25 (`gentle and non-toxic`, `accepted for treatment`) are paraphrases of
a single page, and the dense half does not find that page either. The fusion
promotes the three near-identical package pages instead.

What the measurement supports instead:

1. BM25 plus the existing synonym expansion and page-type prior is a defensible
   choice for a seven-page corpus, and it is simpler.
2. The misses are a ranking problem, not a recall problem. Every missed gold
   page is in the corpus; it is crowded out by three near-duplicate package
   pages. Three package pages that score alike because they share headings are
   the real defect.
3. Coverage-based confidence is too weak for off-topic detection. "Do you
   offer a hair transplant in Istanbul?" scores 0.86 with BM25 alone and 0.87
   with hybrid, which no threshold on this scale separates from a real answer
   at the same confidence.

This is n=41 answerable and n=10 unanswerable, one annotator, one corpus build.
It is enough to say the dense half has not shown a benefit here. It is not
enough to say it never will, on a larger corpus or with a different embedding
model.

### What shipped as a result

The hybrid stays on, and the reason is that the two evaluations disagree.

- Retrieval benchmark: BM25 wins at hit@8 (92.7% vs 87.8%) and at the refusal
  gate (7/10 vs 4/10 off-topic questions below threshold).
- Answer-level evaluation: hybrid wins, **24/24 against 22/24**. Two comparison
  questions drop under the refusal threshold when the dense half is switched
  off, because the extra candidates stop lifting their coverage score.

`MIN_RETRIEVAL_SCORE=0.40` was calibrated against the hybrid distribution, which
is why removing the dense half moves two questions across the line rather than
improving anything. The answer-level measurement is closer to what the product
is judged on, so it decides, and the retrieval finding is recorded instead of
suppressed.

The open work this exposes is specific: either calibrate the gate per
configuration, or replace coverage-based confidence with an off-topic classifier.
The second is the real fix, because coverage cannot separate "hair transplant in
Istanbul" at 0.86 from a genuine answer at the same score.

## Reproducing

```powershell
cd C:\Users\patri\Documents\Improvement\job-applying\Placidway
.\.venv\Scripts\python.exe -m tests.retrieval_eval
```

The script exits 0 whether or not the numbers look good; it is a report, not a
gate. On a machine without `data/embeddings.npy` (and without `LLM_API_KEY` to
rebuild it) the dense column is reported as unavailable and only the BM25 column
is printed.
