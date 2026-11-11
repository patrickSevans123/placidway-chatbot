# Write-up

## What I would improve with another week

**A change report on top of the scheduled refresh.** The refresh now runs daily, detects which pages
changed, and refuses to replace a corpus that lost content. What it does not do is say *what*
changed. I would diff the two corpora and post a short summary — which prices moved, which chunks
appeared or disappeared. For a site whose main question is "how much does it cost", a price change
is the event worth knowing about, and right now it is only visible as a page slug in a log line.

**A real evaluation set instead of fourteen cases.** Fourteen cases prove the pipeline works; they do
not measure it. I would build 60–100 questions with known correct answers, split by type (cost,
inclusion, comparison, refusal, adversarial), and track two numbers per release: the share of
answers whose every claim is supported by a cited passage, and the share of refusals that should
have been answers. Those two move in opposite directions, so tuning one without measuring the other
is how a bot becomes either a liar or a coward.

**A claim-level verifier.** The current guard checks citations and numbers deterministically, which
catches the failure that matters most here — an invented price. It does not check whether a
non-numeric claim is supported. A second model call that takes each sentence plus its cited chunk
and answers "supported / contradicted / not stated" would close that gap. It costs one extra call
per answer, so I would run it on a sample rather than on every request.

**Better handling of the video page.** The page is a list of titles. The bot can say a video exists
and link to it, but it cannot answer "what does the patient say about recovery?". Pulling the
YouTube transcripts for those videos and indexing them would turn a list of links into content.

**Streaming responses.** Answers take 2–5 seconds. Streaming the first token would make the wait feel
much shorter, and the UI already has a typing indicator to replace.

## Known limitations

- **Seven pages, hard-coded.** The crawler cannot leave the allow-list, by design. Anything outside
  those pages is refused rather than guessed.
- **Prices are a snapshot.** The corpus is refreshed daily and rebuilt when a page's text changes,
  but an answer does not say how old the price is. A price that moved this morning is quoted with
  the same confidence as one that has not moved in a year.
- **The refusal gate is a heuristic.** It uses IDF-weighted vocabulary overlap between the question
  and the retrieved evidence. It separates this corpus well, but it is not a calibrated probability,
  and a question that reuses the corpus vocabulary for a different purpose can slip past it. The
  model's own instruction to refuse is the second line of defence.
- **The numeric guard is exact-match.** It rejects any money amount that is not literally in the
  evidence. That is the right trade-off for prices, but it also rejects a correct total the model
  computed by adding two listed figures.
- **One language pair at a time.** The answer is written in the visitor's language from English
  sources. Retrieval itself is English-only, so a Spanish question is rewritten to English for
  search. That works for Spanish and Arabic in testing, but a corpus in another language would need
  a multilingual embedding model.
- **Single process, in-memory index.** Fine at this size. A larger corpus needs a real vector store
  and a shared cache across workers.
- **No authentication on the chat endpoint.** It is a public demo, rate limiting is left to
  Cloudflare, and the admin endpoints are disabled unless `ADMIN_TOKEN` is set.
