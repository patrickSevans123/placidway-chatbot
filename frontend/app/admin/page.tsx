"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";

import "./admin.css";
import {
  ADMIN_TOKEN_KEY,
  AdminRequestError,
  getAdminHealth,
  getAdminStats,
  getRefreshStatus,
  getUnanswered,
  isAdminDisabled,
  isTokenRejected,
  postRefresh,
  type AdminHealth,
  type AdminStats,
  type RefreshOutcome,
  type RefreshStatus,
  type UnansweredRow,
} from "../lib/admin";

const POLL_INTERVAL_MS = 3_000;
const POLL_LIMIT_MS = 5 * 60 * 1_000;

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

// Fixed locale and UTC, so the exported page renders the same string at build
// time and in the tab, and two operators in two time zones read the same stamp.
function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) return value;
  const date = new Date(ms);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(date.getUTCDate())} ${MONTHS[date.getUTCMonth()]} ${date.getUTCFullYear()} · ${pad(
    date.getUTCHours(),
  )}:${pad(date.getUTCMinutes())} UTC`;
}

function formatCount(value: number | null | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  return value.toLocaleString("en-US");
}

interface QuestionGroup {
  question: string;
  count: number;
  latest: string | null;
  latestMs: number;
  intent: string | null;
  minConfidence: number | null;
  maxConfidence: number | null;
}

// The raw log records the same question once per occurrence, so the table is
// built from grouped rows: one line per distinct question, most frequent first.
function groupQuestions(rows: UnansweredRow[]): QuestionGroup[] {
  const groups = new Map<string, QuestionGroup>();

  for (const row of rows) {
    const question = row.question.trim();
    if (!question) continue;
    const ms = row.created_at ? Date.parse(row.created_at) : 0;
    const confidence = typeof row.confidence === "number" ? row.confidence : null;
    const existing = groups.get(question);

    if (!existing) {
      groups.set(question, {
        question,
        count: 1,
        latest: row.created_at,
        latestMs: Number.isNaN(ms) ? 0 : ms,
        intent: row.intent,
        minConfidence: confidence,
        maxConfidence: confidence,
      });
      continue;
    }

    existing.count += 1;
    if (!Number.isNaN(ms) && ms >= existing.latestMs) {
      // Intent and confidence come from the most recent occurrence, because a
      // re-asked question can be classified differently the second time.
      existing.latest = row.created_at;
      existing.latestMs = ms;
      existing.intent = row.intent;
    }
    if (confidence !== null) {
      existing.minConfidence =
        existing.minConfidence === null ? confidence : Math.min(existing.minConfidence, confidence);
      existing.maxConfidence =
        existing.maxConfidence === null ? confidence : Math.max(existing.maxConfidence, confidence);
    }
  }

  return [...groups.values()].sort((a, b) => b.count - a.count || b.latestMs - a.latestMs);
}

function formatConfidence(group: QuestionGroup): string {
  if (group.maxConfidence === null) return "—";
  const high = group.maxConfidence.toFixed(2);
  const low = group.minConfidence === null ? high : group.minConfidence.toFixed(2);
  return low === high ? high : `${low}–${high}`;
}

function describeError(error: unknown, subject: string): string {
  if (error instanceof AdminRequestError) {
    if (error.status === 0) {
      return "The API did not answer, so nothing was read. Check that the backend is running.";
    }
    return `The API answered ${error.status} for ${subject}${error.detail ? `: ${error.detail}` : "."}`;
  }
  return `Could not read ${subject}.`;
}

function describeOutcome(outcome: RefreshOutcome): string {
  const seconds = Math.round(outcome.seconds);
  if (!outcome.changed) {
    return `Refresh finished in ${seconds}s: no page text changed, so the live index was left as it is.`;
  }
  const changed = outcome.changed_pages.length;
  return `Refresh finished in ${seconds}s: the index was rebuilt${changed === 0 ? "" : ` and ${formatCount(changed)} page${changed === 1 ? "" : "s"} changed`}.`;
}

function describeRunFailure(error: unknown): string {
  if (error instanceof AdminRequestError) {
    if (error.status === 409) {
      return "A refresh is already running on the server, so this one was not started. Try again when it finishes.";
    }
    if (error.status === 503 && (error.detail ?? "").startsWith("refresh rejected")) {
      const reason = (error.detail ?? "").replace("refresh rejected: ", "");
      return `The sanity gate rejected the new corpus, so the live index was left untouched. Reason: ${reason}.`;
    }
    if (isAdminDisabled(error)) {
      return "Admin endpoints are disabled: the backend started without ADMIN_TOKEN. Set it and restart the backend.";
    }
    if (error.status === 0) {
      return "The API did not answer, so the refresh was not started.";
    }
    return `The refresh failed with ${error.status}${error.detail ? `: ${error.detail}` : "."}`;
  }
  return "The refresh failed.";
}

type DataState = "idle" | "loading" | "ready" | "error";

export default function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [connecting, setConnecting] = useState(false);
  const [gateError, setGateError] = useState<string | null>(null);

  const [dataState, setDataState] = useState<DataState>("idle");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [health, setHealth] = useState<AdminHealth | null>(null);
  const [refresh, setRefresh] = useState<RefreshStatus | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [rows, setRows] = useState<UnansweredRow[] | null>(null);
  const [preview, setPreview] = useState<AdminHealth | null>(null);
  const [previewState, setPreviewState] = useState<"loading" | "ready" | "error">("loading");

  const [running, setRunning] = useState(false);
  const [runNotice, setRunNotice] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [confirmForce, setConfirmForce] = useState(false);
  const [polledAt, setPolledAt] = useState<string | null>(null);

  const pollRef = useRef<number | null>(null);
  const runRef = useRef(0);

  function stopPolling() {
    runRef.current += 1;
    if (pollRef.current !== null) {
      window.clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  // The stored token is read after mount, so the static HTML never contains it
  // and the first paint does not guess at it. The gate is what the export
  // carries, which is also what a visitor without a token should see.
  useEffect(() => {
    const stored = window.sessionStorage.getItem(ADMIN_TOKEN_KEY);
    if (stored) setToken(stored);
  }, []);

  // /api/health needs no token, so the screen says what the index holds before
  // anyone authenticates. Only the three detail panels wait for the token.
  useEffect(() => {
    let cancelled = false;
    getAdminHealth()
      .then((payload) => {
        if (cancelled) return;
        setPreview(payload);
        setPreviewState("ready");
      })
      .catch(() => {
        if (cancelled) return;
        setPreviewState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => stopPolling, []);

  function disconnect(reason?: string) {
    stopPolling();
    window.sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    setToken(null);
    setDraft("");
    setHealth(null);
    setRefresh(null);
    setStats(null);
    setRows(null);
    setDataState("idle");
    setLoadError(null);
    setRunning(false);
    setRunNotice(null);
    setRunError(null);
    setConfirmForce(false);
    setPolledAt(null);
    setGateError(reason ?? null);
  }

  async function load(value: string, quiet = false) {
    if (!quiet) setDataState("loading");
    try {
      const [nextHealth, nextStatus, nextStats, nextUnanswered] = await Promise.all([
        getAdminHealth(),
        getRefreshStatus(value),
        getAdminStats(value),
        getUnanswered(value),
      ]);
      setHealth(nextHealth);
      setRefresh(nextStatus);
      setStats(nextStats);
      setRows(nextUnanswered.unanswered);
      setLoadError(null);
      setDataState("ready");
    } catch (error) {
      if (isTokenRejected(error)) {
        disconnect(
          "The server rejected the stored token, so it was cleared. Enter the current admin token.",
        );
        return;
      }
      if (isAdminDisabled(error)) {
        disconnect(
          "Admin endpoints are disabled: the backend started without ADMIN_TOKEN. Set it, restart the backend, then connect again.",
        );
        return;
      }
      setLoadError(describeError(error, "the admin endpoints"));
      setDataState("error");
    }
  }

  useEffect(() => {
    if (!token) return;
    void load(token);
    // `load` is recreated each render on purpose; it only runs when the token
    // changes, or when a button asks for it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = draft.trim();
    if (!value || connecting) return;
    setConnecting(true);
    setGateError(null);
    try {
      // A protected endpoint is the check: /api/health would accept any token.
      await getAdminStats(value);
      window.sessionStorage.setItem(ADMIN_TOKEN_KEY, value);
      setToken(value);
      setDraft("");
    } catch (error) {
      if (isTokenRejected(error)) {
        setGateError(
          "That token was rejected. It was not stored; check the value the server was started with and try again.",
        );
        setDraft("");
      } else if (isAdminDisabled(error)) {
        setGateError(
          "Admin endpoints are disabled on the server: ADMIN_TOKEN was not set when the backend started. Set it and restart the backend.",
        );
      } else {
        setGateError(describeError(error, "the token check"));
      }
    } finally {
      setConnecting(false);
    }
  }

  async function startRun(force: boolean) {
    if (!token || running) return;
    setConfirmForce(false);
    setRunNotice(null);
    setRunError(null);
    setPolledAt(null);
    setRunning(true);

    const generation = runRef.current + 1;
    runRef.current = generation;
    const startedAt = Date.now();

    const poll = async () => {
      if (runRef.current !== generation) return;
      if (Date.now() - startedAt > POLL_LIMIT_MS) {
        stopPolling();
        setRunning(false);
        setRunNotice(
          "Stopped polling after 5 minutes. The rebuild may still be running on the server; reload the page to read its result.",
        );
        return;
      }
      try {
        const next = await getRefreshStatus(token);
        if (runRef.current !== generation) return;
        setRefresh(next);
        setPolledAt(next.last_checked);
      } catch {
        // A transient read failure is not the run's outcome; keep polling.
      }
    };

    pollRef.current = window.setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);
    void poll();

    let cleared = false;
    try {
      const outcome = await postRefresh(token, force);
      const [nextHealth, nextStatus] = await Promise.all([
        getAdminHealth(),
        getRefreshStatus(token).catch(() => null),
      ]);
      setHealth(nextHealth);
      if (nextStatus) setRefresh(nextStatus);
      setRunNotice(describeOutcome(outcome));
    } catch (error) {
      if (isTokenRejected(error)) {
        cleared = true;
        disconnect("The server rejected the token during the refresh, so it was cleared.");
        return;
      }
      setRunError(describeRunFailure(error));
    } finally {
      stopPolling();
      setRunning(false);
      if (!cleared && token && dataState === "ready") void load(token, true);
    }
  }

  const groups = rows ? groupQuestions(rows) : [];
  const occurrences = rows ? rows.length : 0;
  const changed = refresh?.changed_pages ?? [];
  const busy = running;
  const ready = dataState === "ready";

  return (
    <main className="adm">
      <header className="adm-mast">
        <h1 className="adm-title">What the guide recorded</h1>
        <p className="adm-lede">
          The corpus the answer engine reads, the state of its last refresh, the questions it could
          not answer, and the totals on the session log.
        </p>
      </header>

      {!token ? (
        <>
          <section className="adm-panel adm-panel-public" aria-labelledby="adm-public-title">
            <p className="adm-eyebrow">
              <span className="adm-tick" aria-hidden="true" />
              Corpus
            </p>
            <h2 className="adm-panel-title" id="adm-public-title">
              What the index holds
            </h2>

            {previewState === "loading" ? (
              <p className="adm-note" role="status" aria-live="polite">
                Reading the public health endpoint…
              </p>
            ) : null}

            {previewState === "error" ? (
              <p className="adm-note">
                The API did not answer, so these figures could not be read. The backend may be down.
              </p>
            ) : null}

            {preview ? (
              <>
                <dl className="adm-rows">
                  <div className="adm-row">
                    <dt>Pages</dt>
                    <dd className="adm-num">{formatCount(preview.pages)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Chunks</dt>
                    <dd className="adm-num">{formatCount(preview.chunks)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Prices</dt>
                    <dd className="adm-num">{formatCount(preview.prices)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>FAQ pairs</dt>
                    <dd className="adm-num">{formatCount(preview.faqs)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Model</dt>
                    <dd className="adm-str">{preview.model ?? "—"}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Index built</dt>
                    <dd className="adm-str">{formatDate(preview.last_ingest)}</dd>
                  </div>
                </dl>

                <h3 className="adm-sub">Last refresh</h3>
                <dl className="adm-rows">
                  <div className="adm-row">
                    <dt>Last checked</dt>
                    <dd className="adm-str">{formatDate(preview.refresh?.last_checked)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Result</dt>
                    <dd className="adm-str">{preview.refresh?.last_result ?? "no run recorded"}</dd>
                  </div>
                </dl>

                <p className="adm-note">
                  Read from the public health endpoint, which needs no token. The token below is what
                  unlocks the live panels.
                </p>
              </>
            ) : null}
          </section>

          <section className="adm-gate" aria-labelledby="adm-gate-title">
            <h2 className="adm-gate-title" id="adm-gate-title">
              Admin token
            </h2>
            <p className="adm-note">
              The admin endpoints are protected by the token the backend was started with, so this
              public page carries no secret: the token is typed here, kept in this tab&rsquo;s session
              storage, and never written into the bundle, a URL or a log line.
            </p>
            <form className="adm-form" onSubmit={connect}>
              <label className="adm-label" htmlFor="adm-token">
                Token
              </label>
              <input
                id="adm-token"
                className="adm-field"
                type="password"
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                autoComplete="off"
                spellCheck={false}
                disabled={connecting}
                aria-describedby="adm-gate-note"
              />
              <button
                className="adm-primary"
                type="submit"
                disabled={connecting || draft.trim() === ""}
              >
                {connecting ? "Checking…" : "Connect"}
              </button>
            </form>
            <p className="adm-note" id="adm-gate-note">
              A rejected token is cleared from the field; a server without ADMIN_TOKEN answers 503
              and says so here.
            </p>
            {gateError ? (
              <p className="adm-error" role="alert">
                {gateError}
              </p>
            ) : null}
          </section>
        </>
      ) : (
        <div className="adm-console">
          <div className="adm-bar">
            <p className="adm-bar-state">
              <span className="adm-dot" aria-hidden="true" />
              Connected · token held in this tab only
            </p>
            <button type="button" className="adm-link" onClick={() => disconnect()}>
              Disconnect
            </button>
          </div>

          {dataState === "loading" ? (
            <p className="adm-note" role="status" aria-live="polite">
              Reading the admin endpoints…
            </p>
          ) : null}

          {dataState === "error" ? (
            <div className="adm-banner" role="alert">
              <p>{loadError}</p>
              <button type="button" className="adm-secondary" onClick={() => token && void load(token)}>
                Try again
              </button>
            </div>
          ) : null}

          {ready ? (
            <>
              <section className="adm-panel" aria-labelledby="adm-corpus-title">
                <p className="adm-eyebrow">
                  <span className="adm-tick" aria-hidden="true" />
                  01 · Corpus
                </p>
                <h2 className="adm-panel-title" id="adm-corpus-title">
                  What the index holds
                </h2>

                <dl className="adm-rows">
                  <div className="adm-row">
                    <dt>Pages</dt>
                    <dd className="adm-num">{formatCount(health?.pages)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Chunks</dt>
                    <dd className="adm-num">{formatCount(health?.chunks)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Prices</dt>
                    <dd className="adm-num">{formatCount(health?.prices)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>FAQ pairs</dt>
                    <dd className="adm-num">{formatCount(health?.faqs)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Model</dt>
                    <dd className="adm-str">{health?.model ?? "—"}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Index built</dt>
                    <dd className="adm-str">{formatDate(health?.last_ingest)}</dd>
                  </div>
                </dl>

                <h3 className="adm-sub">Last refresh</h3>
                <dl className="adm-rows">
                  <div className="adm-row">
                    <dt>Last checked</dt>
                    <dd className="adm-str">{formatDate(refresh?.last_checked)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Result</dt>
                    <dd className="adm-str">{refresh?.last_result ?? "no run recorded"}</dd>
                  </div>
                  {refresh?.last_reason ? (
                    <div className="adm-row">
                      <dt>Reason</dt>
                      <dd className="adm-str">{refresh.last_reason}</dd>
                    </div>
                  ) : null}
                </dl>

                <div className="adm-changed">
                  <p className="adm-label">Changed pages</p>
                  {changed.length === 0 ? (
                    <p className="adm-note">No page text changed in the last run.</p>
                  ) : (
                    <ul className="adm-slugs">
                      {changed.map((slug) => (
                        <li key={slug}>{slug}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="adm-actions">
                  <button
                    type="button"
                    className="adm-primary"
                    onClick={() => void startRun(false)}
                    disabled={busy}
                  >
                    {busy ? "Refreshing…" : "Run refresh"}
                  </button>
                  <button
                    type="button"
                    className="adm-secondary"
                    onClick={() => setConfirmForce(true)}
                    disabled={busy || confirmForce}
                  >
                    Force rebuild
                  </button>
                </div>
                <p className="adm-note">
                  Force rebuild bypasses the sanity gate that compares the new corpus with the live
                  one, so a broken fetch could replace a good index.
                </p>

                {confirmForce ? (
                  <div className="adm-confirm" role="group" aria-label="Confirm force rebuild">
                    <p>
                      Rebuild without the sanity gate? The new corpus replaces the live index even if
                      it looks wrong.
                    </p>
                    <div className="adm-actions">
                      <button
                        type="button"
                        className="adm-primary"
                        onClick={() => void startRun(true)}
                      >
                        Rebuild anyway
                      </button>
                      <button
                        type="button"
                        className="adm-secondary"
                        onClick={() => setConfirmForce(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : null}

                <div className="adm-runstate" role="status" aria-live="polite">
                  {busy ? (
                    <p>
                      Refresh running. Reading the server every 3 seconds
                      {polledAt ? ` · last checked ${formatDate(polledAt)}` : ""}. Polling stops when
                      it settles or after 5 minutes.
                    </p>
                  ) : null}
                  {!busy && runNotice ? <p>{runNotice}</p> : null}
                  {!busy && runError ? <p className="adm-error">{runError}</p> : null}
                </div>
              </section>

              <section className="adm-panel" aria-labelledby="adm-gaps-title">
                <p className="adm-eyebrow">
                  <span className="adm-tick" aria-hidden="true" />
                  02 · Gaps
                </p>
                <h2 className="adm-panel-title" id="adm-gaps-title">
                  Questions we could not answer
                </h2>

                {occurrences === 0 ? (
                  <p className="adm-empty">
                    The log is empty. No question has been recorded without an answer.
                  </p>
                ) : (
                  <>
                    <p className="adm-note">
                      {formatCount(groups.length)} distinct question
                      {groups.length === 1 ? "" : "s"} across {formatCount(occurrences)} logged
                      occurrence{occurrences === 1 ? "" : "s"}, most asked first.
                    </p>
                    <div className="adm-table-wrap">
                      <table className="adm-table">
                        <thead>
                          <tr>
                            <th scope="col">Question</th>
                            <th scope="col" className="num">
                              Count
                            </th>
                            <th scope="col" className="num">
                              Most recent
                            </th>
                            <th scope="col">Intent</th>
                            <th scope="col" className="num">
                              Confidence
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {groups.map((group) => (
                            <tr key={group.question}>
                              <td className="adm-q">{group.question}</td>
                              <td className="num adm-strong">{formatCount(group.count)}</td>
                              <td className="num">{formatDate(group.latest)}</td>
                              <td className="adm-intent">{group.intent ?? "—"}</td>
                              <td className="num">{formatConfidence(group)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </section>

              <section className="adm-panel" aria-labelledby="adm-activity-title">
                <p className="adm-eyebrow">
                  <span className="adm-tick" aria-hidden="true" />
                  03 · Activity
                </p>
                <h2 className="adm-panel-title" id="adm-activity-title">
                  Totals on the log
                </h2>

                <dl className="adm-rows">
                  <div className="adm-row">
                    <dt>Sessions</dt>
                    <dd className="adm-num">{formatCount(stats?.sessions)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Messages</dt>
                    <dd className="adm-num">{formatCount(stats?.messages)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Unanswered</dt>
                    <dd className="adm-num">{formatCount(stats?.unanswered)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Leads</dt>
                    <dd className="adm-num">{formatCount(stats?.leads)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Feedback up</dt>
                    <dd className="adm-num">{formatCount(stats?.feedback_up)}</dd>
                  </div>
                  <div className="adm-row">
                    <dt>Feedback down</dt>
                    <dd className="adm-num">{formatCount(stats?.feedback_down)}</dd>
                  </div>
                </dl>
              </section>
            </>
          ) : null}
        </div>
      )}
    </main>
  );
}
