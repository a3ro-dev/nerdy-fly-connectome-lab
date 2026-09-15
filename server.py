"""Loopback-only dashboard and local-model conversation endpoint."""
import json
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tools.reasoning_agent import ollama_chat

ROOT = Path(__file__).with_name("web")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'")
        super().end_headers()

    def do_POST(self):
        if self.path != "/api/talk" or self.headers.get("X-Nerdy-Fly") != "dashboard":
            self.send_error(404); return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 8192: raise ValueError("message size must be 1..8192 bytes")
            user = str(json.loads(self.rfile.read(length))["message"]).strip()[:2000]
            if not user: raise ValueError("empty message")
            reasoning_path = ROOT / "data/reasoning_status.json"
            state = json.loads(reasoning_path.read_text(encoding="utf-8")) if reasoning_path.exists() else {}
            schema = {"type":"object","properties":{"reply":{"type":"string"}},"required":["reply"]}
            system = (
                "You are the local Qwen language module in Nerdy Fly Lab. Speak plainly and briefly. "
                "You are not a biological fly and must not claim consciousness, emotions, resurrection, or suffering. "
                "State uncertainty. The reduced connectome supplies context/attention; Qwen supplies language and reasoning."
            )
            context = f"Latest autonomous reflection: {state.get('summary','none')}\nLatest source: {state.get('source_url','none')}"
            answer = ollama_chat(state.get("model", "qwen3.5:2b"), [{"role":"system","content":system},{"role":"user","content":context},{"role":"user","content":user}], schema)
            record = {"time":datetime.now(timezone.utc).isoformat(),"model":state.get("model", "qwen3.5:2b"),"source_url":state.get("source_url"),"message":user,"reply":str(answer["reply"])[:4000]}
            log_path = ROOT.parent / "work/talk_events.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as stream: stream.write(json.dumps(record,ensure_ascii=False)+"\n")
            payload = json.dumps(record).encode()
            self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)
        except Exception as exc:
            payload = json.dumps({"error":f"{type(exc).__name__}: {exc}"}).encode()
            self.send_response(503); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(payload))); self.end_headers(); self.wfile.write(payload)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8787), Handler)
    print("Nerdy Fly Lab: http://127.0.0.1:8787")
    server.serve_forever()
