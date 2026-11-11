/* ==========================================================================
   PlacidWay treatment guide — chat client
   Plain browser JavaScript. No build step, no dependencies.

   API contract (fixed):
     POST /api/chat  {session_id, message}
       -> {session_id, answer, sources[], language, intent, grounded,
           show_disclaimer, show_lead_form, latency_ms}
     POST /api/lead  {session_id, name, email, message} -> {ok: true}
     GET  /api/health -> {status, pages, chunks, model, last_ingest}
   ========================================================================== */

(function () {
  "use strict";

  /* ---------- Elements ---------- */

  var transcript = document.getElementById("transcript");
  var emptyState = document.getElementById("empty-state");
  var starters = document.getElementById("starters");
  var form = document.getElementById("composer");
  var input = document.getElementById("message");
  var sendBtn = document.getElementById("send");
  var newChatBtn = document.getElementById("new-chat");
  var disclaimer = document.getElementById("disclaimer");
  var disclaimerClose = document.getElementById("disclaimer-close");
  var footerStatus = document.getElementById("footer-status");
  var footerDot = document.querySelector(".footer-dot");

  /* ---------- Constants ---------- */

  var SESSION_KEY = "placidway.session_id";
  var DISCLAIMER_KEY = "placidway.disclaimer_dismissed";
  var MAX_MESSAGE = 1000;
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

  var ICONS = {
    spark:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M10 2.8v14.4M2.8 10h14.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    link:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M7.5 4.5h8v8M15.5 4.5 5 15" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    book:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M3.5 4.5h4.2a2.3 2.3 0 0 1 2.3 2.3v8.7a1.8 1.8 0 0 0-1.8-1.8H3.5Zm13 0h-4.2a2.3 2.3 0 0 0-2.3 2.3v8.7a1.8 1.8 0 0 1 1.8-1.8h4.7Z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/></svg>',
    search:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="9" cy="9" r="5.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path d="m13 13 3.5 3.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>',
    check:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="m4.5 10.5 3.6 3.6 7.4-8" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    alert:
      '<svg viewBox="0 0 20 20" aria-hidden="true" focusable="false"><circle cx="10" cy="10" r="7.2" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M10 6.2v4.6" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/><circle cx="10" cy="13.6" r="0.9" fill="currentColor"/></svg>'
  };

  /* ---------- State ---------- */

  var state = {
    sessionId: readSession(),
    busy: false,
    resumeNoted: false,
    disclaimerShown: false
  };

  /* ---------- Storage helpers ---------- */

  function readSession() {
    try {
      return sessionStorage.getItem(SESSION_KEY) || null;
    } catch (err) {
      return null;
    }
  }

  function writeSession(id) {
    state.sessionId = id || null;
    try {
      if (id) sessionStorage.setItem(SESSION_KEY, id);
      else sessionStorage.removeItem(SESSION_KEY);
    } catch (err) {
      /* Private mode or storage disabled: the conversation still works in memory. */
    }
  }

  function disclaimerDismissed() {
    try {
      return sessionStorage.getItem(DISCLAIMER_KEY) === "1";
    } catch (err) {
      return false;
    }
  }

  function rememberDisclaimer() {
    try {
      sessionStorage.setItem(DISCLAIMER_KEY, "1");
    } catch (err) {
      /* ignore */
    }
  }

  /* ---------- Small DOM helpers ---------- */

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function svgIcon(markup) {
    var holder = el("span");
    holder.innerHTML = markup;
    return holder.firstElementChild;
  }

  function scrollToBottom(smooth) {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    transcript.scrollTo({
      top: transcript.scrollHeight,
      behavior: smooth && !reduce ? "smooth" : "auto"
    });
  }

  /* ---------- Markdown-lite renderer ----------
     Supports: paragraphs, **bold**, "- " bullets, [n] citation markers.
     Everything is built with DOM nodes and textContent, so model output can
     never inject HTML. */

  function renderInline(text, sources, answerEl) {
    var frag = document.createDocumentFragment();
    var pattern = /(\*\*[^*]+\*\*)|(\[(\d{1,2})\])/g;
    var last = 0;
    var match;

    while ((match = pattern.exec(text)) !== null) {
      if (match.index > last) {
        frag.appendChild(document.createTextNode(text.slice(last, match.index)));
      }

      if (match[1]) {
        var strong = el("strong", null, match[1].slice(2, -2));
        frag.appendChild(strong);
      } else {
        var num = parseInt(match[3], 10);
        var source = sources[num - 1];
        if (source) {
          frag.appendChild(makeCitation(num, answerEl));
        } else {
          /* A marker with no matching source is shown as plain text, not a dead link. */
          frag.appendChild(document.createTextNode(match[0]));
        }
      }

      last = pattern.lastIndex;
    }

    if (last < text.length) {
      frag.appendChild(document.createTextNode(text.slice(last)));
    }

    return frag;
  }

  function makeCitation(num, answerEl) {
    var chip = el("a", "cite", String(num));
    chip.href = "#source-" + answerEl.dataset.answerId + "-" + num;
    chip.setAttribute("aria-label", "Source " + num);
    chip.addEventListener("click", function (event) {
      event.preventDefault();
      highlightSource(answerEl, num, true);
    });
    return chip;
  }

  function renderAnswer(markdown, sources, answerEl) {
    var lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
    var block = null;
    var list = null;

    function flush() {
      block = null;
      list = null;
    }

    lines.forEach(function (raw) {
      var line = raw.trim();

      if (!line) {
        flush();
        return;
      }

      var bullet = line.match(/^[-*•]\s+(.*)$/);
      if (bullet) {
        if (!list) {
          list = el("ul");
          answerEl.appendChild(list);
          block = null;
        }
        var item = el("li");
        item.appendChild(renderInline(bullet[1], sources, answerEl));
        list.appendChild(item);
        return;
      }

      if (list) list = null;

      if (!block) {
        block = el("p");
        answerEl.appendChild(block);
      } else {
        block.appendChild(document.createTextNode(" "));
      }
      block.appendChild(renderInline(line, sources, answerEl));
    });

    if (!answerEl.childNodes.length) {
      answerEl.appendChild(el("p", null, "No answer text was returned."));
    }
  }

  /* ---------- Source cards ---------- */

  function highlightSource(answerEl, num, scroll) {
    var cards = answerEl.querySelectorAll(".source-card");
    var chips = answerEl.querySelectorAll(".cite");

    Array.prototype.forEach.call(cards, function (card) {
      card.classList.toggle("is-active", card.dataset.num === String(num));
    });
    Array.prototype.forEach.call(chips, function (chip) {
      chip.classList.toggle("is-active", chip.textContent === String(num));
    });

    if (scroll) {
      var target = answerEl.querySelector('.source-card[data-num="' + num + '"]');
      if (target) {
        var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        target.scrollIntoView({ block: "nearest", behavior: reduce ? "auto" : "smooth" });
        target.focus({ preventScroll: true });
      }
    }
  }

  function renderSources(sources, answerEl) {
    if (!sources || !sources.length) return;

    var wrap = el("div", "sources");
    var title = el("p", "sources-title");
    title.appendChild(svgIcon(ICONS.book));
    title.appendChild(document.createTextNode(sources.length === 1 ? "Source page" : "Source pages"));
    wrap.appendChild(title);

    var list = el("ul", "source-list");

    sources.forEach(function (source, index) {
      var num = index + 1;
      var card = el("li", "source-card");
      card.dataset.num = String(num);
      card.id = "source-" + answerEl.dataset.answerId + "-" + num;
      card.tabIndex = -1;

      var number = el("span", "source-num", String(num));
      number.setAttribute("aria-hidden", "true");

      var head = el("div", "source-head");
      head.appendChild(el("span", "source-title", source.title || "Untitled page"));
      if (source.page_type) head.appendChild(el("span", "badge", source.page_type));

      var link = el("a", "source-url");
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.appendChild(document.createTextNode(prettyUrl(source.url)));
      link.appendChild(svgIcon(ICONS.link));
      link.appendChild(el("span", "sr-only", " (opens in a new tab)"));

      card.appendChild(number);
      card.appendChild(head);
      card.appendChild(link);
      list.appendChild(card);
    });

    wrap.appendChild(list);
    answerEl.appendChild(wrap);
  }

  function prettyUrl(url) {
    try {
      var parsed = new URL(url);
      var path = decodeURIComponent(parsed.pathname);
      if (path.length > 64) path = path.slice(0, 61) + "…";
      return parsed.hostname.replace(/^www\./, "") + path;
    } catch (err) {
      return url;
    }
  }

  /* ---------- Not-found state ---------- */

  function renderNotFound(answerEl) {
    var box = el("div", "notfound");

    var head = el("p", "notfound-head");
    head.appendChild(svgIcon(ICONS.search));
    head.appendChild(document.createTextNode("This is not in the pages I can read"));
    box.appendChild(head);

    box.appendChild(
      el(
        "p",
        null,
        "I only answer from seven PlacidWay pages about the ITC clinic in Tijuana and its cancer treatment packages. " +
          "For anything else, a PlacidWay coordinator can help you directly."
      )
    );

    var actions = el("div", "notfound-actions");
    var quote = el("a", "btn btn-primary");
    quote.href = "https://www.placidway.com/";
    quote.target = "_blank";
    quote.rel = "noopener noreferrer";
    quote.appendChild(document.createTextNode("Request a free quote"));
    quote.appendChild(svgIcon(ICONS.link));
    quote.appendChild(el("span", "sr-only", " (opens in a new tab)"));

    var retry = el("button", "btn btn-quiet", "Ask something else");
    retry.type = "button";
    retry.addEventListener("click", function () {
      input.focus();
    });

    actions.appendChild(quote);
    actions.appendChild(retry);
    box.appendChild(actions);
    answerEl.appendChild(box);
  }

  /* ---------- Lead form ---------- */

  function renderLeadForm(answerEl) {
    var box = el("div", "lead");
    box.appendChild(el("p", "lead-title", "Want a price for your case?"));
    box.appendChild(
      el("p", "lead-sub", "Leave your name and email. A PlacidWay coordinator will reply with a free quote.")
    );

    var leadForm = el("form", "lead-form");
    leadForm.noValidate = true;

    var nameField = makeField("lead-name", "Your name", "text", "name", true);
    var emailField = makeField("lead-email", "Email", "email", "email", true);
    var messageField = makeField("lead-message", "What would you like to ask?", "textarea", "message", false);

    leadForm.appendChild(nameField.wrap);
    leadForm.appendChild(emailField.wrap);
    leadForm.appendChild(messageField.wrap);

    var actions = el("div", "lead-actions");
    var submit = el("button", "btn btn-primary", "Send my details");
    submit.type = "submit";
    var note = el("span", "lead-note", "We use these details only to answer your question.");
    actions.appendChild(submit);
    actions.appendChild(note);
    leadForm.appendChild(actions);

    leadForm.addEventListener("submit", function (event) {
      event.preventDefault();
      submitLead(leadForm, box, nameField, emailField, messageField, submit);
    });

    box.appendChild(leadForm);
    answerEl.appendChild(box);
  }

  function makeField(id, labelText, type, name, required) {
    var wrap = el("div", "field");
    var label = el("label");
    label.htmlFor = id;
    label.appendChild(document.createTextNode(labelText));
    if (!required) label.appendChild(el("span", "optional", " (optional)"));

    var control;
    if (type === "textarea") {
      control = el("textarea");
      control.rows = 3;
      control.placeholder = "For example: my mother was diagnosed last month.";
    } else {
      control = el("input");
      control.type = type;
      control.autocomplete = name === "email" ? "email" : "name";
      control.placeholder = name === "email" ? "you@example.com" : "First and last name";
    }
    control.id = id;
    control.name = name;
    if (required) control.setAttribute("aria-required", "true");

    var error = el("p", "field-error");
    error.id = id + "-error";
    control.setAttribute("aria-describedby", error.id);

    wrap.appendChild(label);
    wrap.appendChild(control);
    wrap.appendChild(error);

    return { wrap: wrap, control: control, error: error };
  }

  function setFieldError(field, message) {
    field.wrap.classList.toggle("has-error", Boolean(message));
    field.error.textContent = message || "";
    field.control.setAttribute("aria-invalid", message ? "true" : "false");
  }

  function validateLead(nameField, emailField) {
    var ok = true;
    var name = nameField.control.value.trim();
    var email = emailField.control.value.trim();

    if (!name) {
      setFieldError(nameField, "Please enter your name.");
      ok = false;
    } else {
      setFieldError(nameField, "");
    }

    if (!email) {
      setFieldError(emailField, "Please enter your email address.");
      ok = false;
    } else if (!EMAIL_RE.test(email)) {
      setFieldError(emailField, "That email address looks incomplete. Check for a missing @ or dot.");
      ok = false;
    } else {
      setFieldError(emailField, "");
    }

    return ok;
  }

  function submitLead(leadForm, box, nameField, emailField, messageField, submit) {
    if (!validateLead(nameField, emailField)) {
      var firstBad = leadForm.querySelector(".has-error input, .has-error textarea");
      if (firstBad) firstBad.focus();
      return;
    }

    submit.disabled = true;
    submit.textContent = "Sending…";

    postJson("/api/lead", {
      session_id: state.sessionId,
      name: nameField.control.value.trim(),
      email: emailField.control.value.trim(),
      message: messageField.control.value.trim()
    })
      .then(function (data) {
        if (!data || data.ok !== true) throw new Error("Lead was not accepted");
        var success = el("div", "lead-success");
        success.setAttribute("role", "status");
        success.appendChild(svgIcon(ICONS.check));
        success.appendChild(
          el(
            "span",
            null,
            "Thank you. Your details are with PlacidWay, and a coordinator will reply to " +
              emailField.control.value.trim() +
              "."
          )
        );
        box.replaceChildren(success);
      })
      .catch(function () {
        submit.disabled = false;
        submit.textContent = "Send my details";
        var note = leadForm.querySelector(".lead-note");
        if (note) {
          note.textContent = "That did not send. Check your connection and try again.";
          note.style.color = "#8f3a27";
        }
      });
  }

  /* ---------- Messages ---------- */

  var answerCounter = 0;

  function addUserMessage(text) {
    var msg = el("div", "msg msg-user");
    var bubble = el("div", "bubble", text);
    msg.appendChild(bubble);
    transcript.appendChild(msg);
    scrollToBottom(true);
  }

  function addAssistantShell() {
    answerCounter += 1;
    var msg = el("div", "msg msg-assistant");
    var label = el("p", "msg-label");
    label.appendChild(svgIcon(ICONS.spark));
    label.appendChild(document.createTextNode("PlacidWay guide"));

    var bubble = el("div", "bubble");
    var answer = el("div", "answer");
    answer.dataset.answerId = "a" + answerCounter;

    bubble.appendChild(answer);
    msg.appendChild(label);
    msg.appendChild(bubble);
    transcript.appendChild(msg);
    scrollToBottom(true);

    return { msg: msg, answer: answer };
  }

  function addTyping() {
    var msg = el("div", "msg msg-assistant");
    msg.id = "typing-row";
    var label = el("p", "msg-label");
    label.appendChild(svgIcon(ICONS.spark));
    label.appendChild(document.createTextNode("PlacidWay guide"));

    var bubble = el("div", "bubble");
    var typing = el("div", "typing");
    typing.setAttribute("role", "status");
    typing.appendChild(el("span"));
    typing.appendChild(el("span"));
    typing.appendChild(el("span"));
    typing.appendChild(el("span", "typing-text", "Reading the pages…"));

    bubble.appendChild(typing);
    msg.appendChild(label);
    msg.appendChild(bubble);
    transcript.appendChild(msg);
    scrollToBottom(true);
    return msg;
  }

  function removeTyping() {
    var row = document.getElementById("typing-row");
    if (row) row.remove();
  }

  function addErrorMessage(text, retryText) {
    var msg = el("div", "msg msg-assistant");
    var box = el("div", "msg-error");
    box.appendChild(svgIcon(ICONS.alert));

    var body = el("div");
    body.appendChild(el("p", null, text));

    if (retryText) {
      var retry = el("button", "retry", "Try again");
      retry.type = "button";
      retry.addEventListener("click", function () {
        msg.remove();
        send(retryText);
      });
      body.appendChild(retry);
    }

    box.appendChild(body);
    msg.appendChild(box);
    transcript.appendChild(msg);
    scrollToBottom(true);
  }

  /* ---------- Disclaimer ---------- */

  function maybeShowDisclaimer(flag) {
    if (!flag || state.disclaimerShown || disclaimerDismissed()) return;
    state.disclaimerShown = true;
    disclaimer.hidden = false;
  }

  disclaimerClose.addEventListener("click", function () {
    disclaimer.hidden = true;
    rememberDisclaimer();
    input.focus();
  });

  /* ---------- Composer behaviour ---------- */

  function autoGrow() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 144) + "px";
  }

  function setBusy(busy) {
    state.busy = busy;
    input.disabled = busy;
    sendBtn.disabled = busy;
    form.classList.toggle("is-busy", busy);
    transcript.setAttribute("aria-busy", busy ? "true" : "false");
  }

  input.addEventListener("input", autoGrow);

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    var text = input.value.trim();
    if (!text || state.busy) return;
    input.value = "";
    autoGrow();
    send(text);
  });

  starters.addEventListener("click", function (event) {
    var button = event.target.closest(".starter");
    if (!button) return;
    input.value = button.dataset.question || "";
    autoGrow();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
  });

  newChatBtn.addEventListener("click", function () {
    if (state.busy) return;
    writeSession(null);
    state.resumeNoted = false;
    Array.prototype.forEach.call(transcript.querySelectorAll(".msg"), function (node) {
      node.remove();
    });
    emptyState.hidden = false;
    newChatBtn.hidden = true;
    input.value = "";
    autoGrow();
    input.focus();
  });

  /* ---------- Network ---------- */

  function postJson(url, body) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body)
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("HTTP " + response.status);
      }
      return response.json();
    });
  }

  function send(text) {
    if (state.busy) return;

    if (text.length > MAX_MESSAGE) {
      addErrorMessage("That question is too long. Please shorten it to " + MAX_MESSAGE + " characters.");
      return;
    }

    if (state.sessionId && !state.resumeNoted) {
      state.resumeNoted = true;
      addResumeNote();
    }

    emptyState.hidden = true;
    newChatBtn.hidden = false;
    addUserMessage(text);
    setBusy(true);
    var typing = addTyping();

    postJson("/api/chat", { session_id: state.sessionId, message: text })
      .then(function (data) {
        removeTyping();
        if (data && data.session_id) writeSession(data.session_id);
        renderReply(data || {});
      })
      .catch(function () {
        removeTyping();
        addErrorMessage(
          "I could not reach the server. Check your connection, then try again.",
          text
        );
      })
      .then(function () {
        setBusy(false);
        input.focus();
      });
  }

  function renderReply(data) {
    var shell = addAssistantShell();
    var answerEl = shell.answer;
    var sources = Array.isArray(data.sources) ? data.sources : [];
    var grounded = data.grounded !== false;

    if (grounded) {
      renderAnswer(data.answer, sources, answerEl);
    } else {
      /* The server's own wording is kept when it exists, so the refusal reads
         the way the backend wrote it. The calm panel follows underneath. */
      if (data.answer && String(data.answer).trim()) {
        renderAnswer(data.answer, [], answerEl);
      }
      renderNotFound(answerEl);
    }

    renderSources(sources, answerEl);

    if (data.show_lead_form) {
      renderLeadForm(answerEl);
    }

    maybeShowDisclaimer(data.show_disclaimer);
    scrollToBottom(true);
  }

  /* ---------- Health footer ---------- */

  function loadHealth() {
    fetch("/api/health", { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        var pages = Number(data.pages);
        var model = data.model ? String(data.model) : "unknown model";
        var parts = [];
        parts.push("Model: " + model);
        parts.push(
          Number.isFinite(pages) && pages > 0
            ? pages + (pages === 1 ? " page" : " pages") + " in the knowledge base"
            : "Page count unavailable"
        );
        if (data.last_ingest) parts.push("Last updated " + formatDate(data.last_ingest));
        footerStatus.textContent = parts.join(" · ");
        footerDot.classList.add("is-ok");
      })
      .catch(function () {
        footerStatus.textContent = "Knowledge base status unavailable right now";
        footerDot.classList.add("is-down");
      });
  }

  function formatDate(value) {
    var date = new Date(value);
    if (isNaN(date.getTime())) return String(value);
    try {
      return date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
    } catch (err) {
      return date.toISOString().slice(0, 10);
    }
  }

  /* A reload keeps the session id but not the transcript, so the first message
     after a reload says plainly that earlier messages are gone. */
  function addResumeNote() {
    var note = el("div", "msg msg-assistant");
    var box = el("div", "msg-error");
    box.appendChild(svgIcon(ICONS.alert));
    var body = el("div");
    body.appendChild(
      el(
        "p",
        null,
        "Welcome back. Your earlier messages are not shown after a reload, but I still remember the conversation, so you can carry on with a follow-up question."
      )
    );
    box.appendChild(body);
    note.appendChild(box);
    transcript.appendChild(note);
  }

  /* ---------- Start ---------- */

  autoGrow();
  loadHealth();
  if (state.sessionId) newChatBtn.hidden = false;
})();
