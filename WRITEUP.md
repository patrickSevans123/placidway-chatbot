# Write-up

## What I would improve with another week

**Replace the coverage gate with an off-topic classifier.** Confidence is
IDF-weighted vocabulary overlap between the question and the retrieved evidence.
It fails one way: "do you offer a hair transplant in Istanbul?" scores 0.86,
because every word is in the corpus. A small classifier trained on the
answerable and unanswerable questions I labelled would separate the two
populations better than any threshold, and refusal is weighted 20%.

**Reconcile two evaluations that disagree.** The retrieval benchmark says the
dense half of the hybrid costs hit@8 and makes the gate leakier; the
answer-level evaluation says removing it fails two comparison questions. Both
are in `docs/EVALUATION.md`. The fix is to calibrate the gate per configuration
rather than pick a side.

**Check non-numeric claims with a second model.** The guard is deterministic on
citations and amounts, so "20 years of experience" is unsupported and unchecked.
Sentence plus cited chunk, scored supported / contradicted / not stated, sampled
rather than run on every request, would close that gap cheaply.

**Turn feedback into a queue.** Thumbs-down ratings are stored but never
clustered. Grouping them by intent and retrieval confidence shows which page is
missing, which is what the content team can act on.

## Known limitations

- **Seven pages, hard-coded.** The crawler cannot leave the allow-list; anything
  else is refused rather than guessed.
- **Prices are a snapshot.** Answers carry "Prices checked <date>", but the bot
  cannot tell whether the page itself has gone stale.
- **The refusal gate is a heuristic.** Its second line of defence is the model's
  own instruction to refuse.
- **The numeric guard is exact-match.** It reads `$18,995`, `18,995 USD`,
  `18.995 USD` and a bare `18,995`; a bare `18995` is not treated as money. It
  also rejects a correct total computed by adding two listed prices — the trade I
  would rather make than be wrong.
- **Streaming precedes the final guard.** The money filter stops an unsupported
  price from appearing, but a wrong citation marker can be visible for the second
  before a `replace` event corrects it. In practice the model returns its whole
  answer in under 300 ms after a 1.5-3 s wait, so a visitor rarely sees it arrive
  in pieces at all.
- **The price record belongs to one package.** It prints the adenocarcinoma
  package's two tiers, so it renders only when the answer cites that page and
  states a figure. A question about the adrenal or anal package therefore gets no
  record at all: the price lives in the sentence the model wrote, with its
  citation, and the record would have shown a different clinic package's numbers
  under a note naming the wrong page. Showing every package would mean a record
  per package, which is a build I did not do in the time available.
- **One language pair at a time.** Retrieval is English-only, so Spanish and
  Arabic questions are rewritten to English for search.
