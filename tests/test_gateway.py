"""The model client against an OpenAI-compatible gateway, without a real key.

A throwaway HTTP server stands in for the gateway. The test checks the parts a
live key would otherwise be the only way to see: the path, the bearer token, the
identifying headers one gateway asks every client to send, and the parsing of
both a normal body and a server-sent event stream.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

seen: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep pytest output clean
        pass

    def do_POST(self):
        length = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        seen.append({"path": self.path, "headers": dict(self.headers), "body": body})

        if body.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for piece in ("18,995", " USD"):
                frame = {"choices": [{"delta": {"content": piece}}]}
                self.wfile.write(f"data: {json.dumps(frame)}\n\n".encode())
            self.wfile.write(b"data: [DONE]\n\n")
            return

        payload = {"choices": [{"message": {"role": "assistant", "content": "The price is 18,995 USD."}}]}
        raw = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class Stub:
    llm_api_key = "test-key"
    llm_model = "deepseek-v4.1-flash"
    llm_temperature = 0.0
    llm_timeout = 5.0
    llm_fallbacks: tuple[str, ...] = ()
    llm_user_agent = "PlacidWayAssessmentBot/1.0"
    llm_session_id = "placidway-guide"
    llm_reasoning_effort = "none"
    llm_base_url = ""


@pytest.fixture()
def gateway(monkeypatch):
    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stub = Stub()
    stub.llm_base_url = f"http://127.0.0.1:{server.server_port}/v1"
    monkeypatch.setattr("app.llm.settings", stub)
    seen.clear()
    yield stub
    server.shutdown()


def test_chat_posts_to_the_compatible_path_with_a_bearer_token(gateway):
    from app.llm import chat

    result = chat([{"role": "user", "content": "price?"}], max_tokens=50)

    assert result.text == "The price is 18,995 USD."
    assert result.model == "deepseek-v4.1-flash"
    request = seen[0]
    assert request["path"] == "/v1/chat/completions"
    headers = {k.lower(): v for k, v in request["headers"].items()}
    assert headers["authorization"] == "Bearer test-key"
    assert headers["user-agent"] == "PlacidWayAssessmentBot/1.0"
    assert headers["x-opencode-session"] == "placidway-guide"
    assert request["body"]["stream"] is False


def test_stream_asks_for_a_stream_and_reads_the_events(gateway):
    from app.llm import chat_stream

    text = "".join(delta.text for delta in chat_stream([{"role": "user", "content": "price?"}]))

    assert text == "18,995 USD"
    assert seen[0]["body"]["stream"] is True
