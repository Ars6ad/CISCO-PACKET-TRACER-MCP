"""Authenticated, loopback-only command bridge for a Packet Tracer Script Module.

This is a transport boundary, not a JavaScript execution service. A future Packet
Tracer extension receives only typed actions and returns explicit receipts.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import uuid
from dataclasses import asdict, dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


MAX_BODY_BYTES = 256 * 1024
ALLOWED_ACTIONS = frozenset({
    "create_device", "delete_device", "rename_device", "move_device",
    "connect_ports", "disconnect_port", "run_cli", "query_topology",
    "save_project", "open_project", "ping", "host_command",
})


@dataclass(slots=True)
class Job:
    id: str
    actions: list[dict[str, Any]]
    state: str = "pending"
    receipt: dict[str, Any] | None = None


class Bridge:
    """In-memory job queue with replay-safe, bearer-token authenticated access."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or secrets.token_urlsafe(32)
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    @property
    def token(self) -> str:
        """Return the pairing secret only for local setup, never status output."""
        return self._token

    def authorized(self, candidate: str) -> bool:
        return bool(candidate) and hmac.compare_digest(candidate, self._token)

    def enqueue(self, actions: list[dict[str, Any]]) -> Job:
        if not actions:
            raise ValueError("at least one action is required")
        normalized: list[dict[str, Any]] = []
        for action in actions:
            if not isinstance(action, dict) or set(action) != {"type", "arguments"}:
                raise ValueError("each action requires exactly type and arguments")
            action_type, arguments = action["type"], action["arguments"]
            if action_type not in ALLOWED_ACTIONS:
                raise ValueError(f"unsupported action type: {action_type}")
            if not isinstance(arguments, dict):
                raise ValueError("action arguments must be an object")
            normalized.append({"type": action_type, "arguments": arguments})
        job = Job(id=str(uuid.uuid4()), actions=normalized)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def poll(self) -> Job | None:
        """Dispatch each job once; an extension must submit a receipt to finish it."""
        with self._lock:
            for job in self._jobs.values():
                if job.state == "pending":
                    job.state = "dispatched"
                    return job
        return None

    def record_receipt(self, job_id: str, status: str, result: dict[str, Any]) -> Job:
        if status not in {"succeeded", "failed"}:
            raise ValueError("receipt status must be succeeded or failed")
        if not isinstance(result, dict):
            raise ValueError("receipt result must be an object")
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError("unknown job")
            if job.state != "dispatched":
                raise ValueError("job is not awaiting a receipt")
            job.state = status
            job.receipt = result
            return job

    def status(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError("unknown job")
            return job

    def summary(self) -> dict[str, int]:
        with self._lock:
            states = [job.state for job in self._jobs.values()]
        return {state: states.count(state) for state in ("pending", "dispatched", "succeeded", "failed")}


class BridgeServer:
    """Small HTTP wrapper intended only for a local Packet Tracer extension."""

    def __init__(self, bridge: Bridge | None = None) -> None:
        self.bridge = bridge or Bridge()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def address(self) -> str | None:
        if self._server is None:
            return None
        return f"http://127.0.0.1:{self._server.server_port}"

    def start(self, port: int = 0) -> str:
        if self._server is not None:
            return self.address or ""
        bridge = self.bridge

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def _host_ok(self) -> bool:
                host = self.headers.get("Host", "").split(":", 1)[0].lower().strip("[]")
                return host in {"127.0.0.1", "localhost", "::1"}

            def _token_ok(self) -> bool:
                header = self.headers.get("Authorization", "")
                scheme, _, candidate = header.partition(" ")
                return scheme.lower() == "bearer" and bridge.authorized(candidate)

            def _json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > MAX_BODY_BYTES:
                    raise ValueError("invalid body size")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict):
                    raise ValueError("body must be an object")
                return value

            def _reply(self, code: HTTPStatus, payload: dict[str, Any] | None = None) -> None:
                self.send_response(code)
                if payload is not None:
                    body = json.dumps(payload, separators=(",", ":")).encode()
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                else:
                    # Explicit framing matters for rejected requests on Windows.
                    # Without it some clients observe a reset/WinError 10053 before
                    # parsing the status line instead of receiving the intended 401.
                    body = b""
                    self.send_header("Content-Length", "0")
                    self.send_header("Connection", "close")
                self.end_headers()
                if body:
                    self.wfile.write(body)

            def do_GET(self) -> None:
                if not self._host_ok():
                    self._reply(HTTPStatus.BAD_REQUEST); return
                if self.path == "/v1/status":
                    self._reply(HTTPStatus.OK, {"service": "packetcraft-bridge", "jobs": bridge.summary()}); return
                self._reply(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
                if not self._host_ok() or not self._token_ok():
                    self._reply(HTTPStatus.UNAUTHORIZED); return
                try:
                    data = self._json()
                    if self.path == "/v1/poll":
                        job = bridge.poll()
                        self._reply(HTTPStatus.OK, {"job": None if job is None else asdict(job)}); return
                    if self.path == "/v1/receipt":
                        job = bridge.record_receipt(data["job_id"], data["status"], data["result"])
                        self._reply(HTTPStatus.OK, {"job": asdict(job)}); return
                except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                    self._reply(HTTPStatus.BAD_REQUEST); return
                self._reply(HTTPStatus.NOT_FOUND)

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="packetcraft-bridge")
        self._thread.start()
        return self.address or ""

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            self._thread = None
