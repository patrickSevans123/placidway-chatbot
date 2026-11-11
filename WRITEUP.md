# Write-up

## What I would improve with another week

**Replace coverage-based confidence with an off-topic classifier.** The gate
scores IDF-weighted vocabulary overlap between the question and the retrieved
evidence. It fails in one specific, documented way: "do you offer a hair
transplant in Istanbul?" scores 0.86, because every word in it appears in the
corpus. A small classifier trained on the 41 answerable and 10 unanswerable
questions I labelled would separate those two populations far better than a
threshold on a coverage score. This is the single change with the most effect on
the criterion the brief weights at 20%.

**Reconcile the two evaluations.** The retrieval benchmark says the dense half
of the hybrid costs me hit@8 and makes the refusal gate leakier; the
answer-level evaluation says removing it fails two comparison questions. Both
are measured, both are in `docs/EVALUATION.md`, and they disagree because the
gate threshold was calibrated against the hybrid distribution. The fix is not to
pick a side, it is to calibrate the gate per configuration and re-measure, or
drop the dense half after fixing the duplicate-package ranking that actually
causes the misses.

**Check non-numeric claims with a second model.** The guard checks citations and
amounts deterministically, which catches the failure that matters here. It does
not check whether a sentence like "the clinic has 20 years of experience" is
supported by the chunk it cites. A cheap second call — sentence, cited chunk,
supported / contradicted / not stated — run on a sample rather than every
request, would close that gap without doubling the latency of every answer.

**Turn the feedback into a queue.** Thumbs-down ratings are recorded but nothing
clusters them. Grouping the down-voted questions by intent and retrieval
confidence would show which page is missing, which is the output the content
team can act on.

## Known limitations

- **Seven pages, hard-coded.** The crawler cannot leave the allow-list. Anything
  outside it is refused rather than guessed.
- **Prices are a snapshot.** The corpus is rebuilt when a page's text changes,
  and every price answer now carries "Prices checked <date>". It does not know
  whether the page itself is stale.
- **The refusal gate is a heuristic**, as above. The model's own instruction to
  refuse is the second line of defence.
- **The numeric guard is exact-match.** It reads `$18,995`, `18,995 USD`,
  `18.995 USD` and a bare `18,995`, but a bare `18995` with no separator is not
  treated as money. It also rejects a correct total the model computed by adding
  two listed prices, which is the trade I would rather make than be wrong.
- **Streaming shows text before the final guard runs.** The money filter stops an
  unsupported price from ever appearing, but a wrong citation marker can be
  visible for the second before a `replace` event corrects it.
- **One language pair at a time.** Retrieval is English-only, so a Spanish or
  Arabic question is rewritten to English for search. That works in testing; a
  non-English corpus would need a multilingual embedding model.
