"""Small stdlib HTTP server for the ACO unified API."""

from __future__ import annotations

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from aco.backend.api_gateway import provider_pool_summary, route_unified_request, simulate_chat_completion
from aco.backend.predictor import DEFAULT_DATA_DIR, generate_prediction_report


class ACORequestHandler(BaseHTTPRequestHandler):
    data_dir = DEFAULT_DATA_DIR
    skills_dir = None
    live = False

    server_version = "ACOUnifiedAPI/0.1"

    def do_OPTIONS(self) -> None:
        self.send_empty(204)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self.send_json({"status": "ok"})
            return
        if path == "/v1/capacity":
            self.send_json(
                {
                    "capacity": provider_pool_summary(data_dir=self.data_dir),
                    "aco": generate_prediction_report(data_dir=self.data_dir),
                }
            )
            return
        self.send_json({"error": {"message": "not found", "code": "not_found"}}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json_body()
        except ValueError as exc:
            self.send_json({"error": {"message": str(exc), "code": "bad_json"}}, status=400)
            return

        if path == "/v1/route":
            self.send_json(route_unified_request(data_dir=self.data_dir, payload=payload, skills_dir=self.skills_dir))
            return
        if path == "/v1/chat/completions":
            response = simulate_chat_completion(
                data_dir=self.data_dir,
                payload=payload,
                skills_dir=self.skills_dir,
                live=self.live,
            )
            status = 400 if "error" in response else 200
            self.send_json(response, status=status)
            return
        self.send_json({"error": {"message": "not found", "code": "not_found"}}, status=404)

    def read_json_body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("request body must be a JSON object")
        return payload

    def send_json(self, payload: dict, *, status: int = 200) -> None:
        encoded = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.add_cors_headers()
        self.end_headers()
        self.wfile.write(encoded)

    def send_empty(self, status: int) -> None:
        self.send_response(status)
        self.add_cors_headers()
        self.end_headers()

    def add_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def log_message(self, format: str, *args) -> None:
        return


def run_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    skills_dir: str | Path | None = None,
    live: bool = False,
) -> None:
    handler = type(
        "ConfiguredACORequestHandler",
        (ACORequestHandler,),
        {
            "data_dir": Path(data_dir),
            "skills_dir": Path(skills_dir) if skills_dir is not None else None,
            "live": live,
        },
    )
    server = ThreadingHTTPServer((host, port), handler)
    print(f"ACO unified API listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
