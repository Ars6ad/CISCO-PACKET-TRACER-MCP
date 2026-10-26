"""Typed file-mailbox bridge for a Packet Tracer Script Module.

The Packet Tracer Script Engine has access to the documented ``ipc`` API and
local-file API, but it cannot make HTTP requests.  This module deliberately
uses a one-job-per-file mailbox instead of passing JavaScript over a socket.
Only a small, validated action vocabulary reaches Packet Tracer.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = 1
HEARTBEAT_TTL_SECONDS = 6.0
DEVICE_KINDS = frozenset({"router", "switch", "host", "server", "access_point"})
SCRIPT_ACTIONS = frozenset({
    "ping", "query_topology", "create_device", "delete_device", "rename_device",
    "move_device", "connect_ports", "disconnect_port",
})
_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,31}$")
_MODEL = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")
_PORT = re.compile(r"^[A-Za-z][A-Za-z0-9/_.-]{0,63}$")
_CABLES = frozenset({"auto", "copper_straight", "copper_cross", "fiber", "serial"})


class ScriptBridgeError(ValueError):
    """The requested typed action cannot be passed to Packet Tracer."""


@dataclass(frozen=True, slots=True)
class ScriptMailbox:
    """Persistent mailbox shared by the MCP process and one PT Script Module."""

    root: Path

    @classmethod
    def default(cls) -> "ScriptMailbox":
        # Cisco's Script Module API exposes this same OS user folder through
        # ipc.appWindow().getUserFolder().  Keeping the mailbox below it makes
        # an exported .pts portable across Windows user profiles; an extension
        # must never embed the profile path of the machine that built it.
        return cls(Path.home() / "PacketCraft" / "script-bridge")

    @property
    def jobs_dir(self) -> Path:
        return self.root / "jobs"

    @property
    def results_dir(self) -> Path:
        return self.root / "results"

    @property
    def heartbeat_path(self) -> Path:
        return self.root / "heartbeat.json"

    @property
    def script_path(self) -> Path:
        return self.root / "packetcraft-bridge.js"

    def prepare(self) -> Path:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self._write_atomic(self.script_path, render_script_module())
        return self.script_path

    def queue(self, actions: list[dict[str, Any]]) -> str:
        normalized = validate_actions(actions)
        self.prepare()
        job_id = uuid.uuid4().hex
        payload = {
            "protocol": PROTOCOL_VERSION,
            "job_id": job_id,
            "created_at": time.time(),
            "actions": normalized,
        }
        self._write_atomic(self.jobs_dir / f"{job_id}.json", json.dumps(payload, separators=(",", ":")))
        return job_id

    def status(self, job_id: str) -> dict[str, Any]:
        if not re.fullmatch(r"[0-9a-f]{32}", job_id):
            raise ScriptBridgeError("job_id must be a PacketCraft job id")
        result = self._read_json(self.results_dir / f"{job_id}.json")
        if result is not None:
            return {"job_id": job_id, "state": result.get("status", "failed"), "receipt": result}
        if (self.jobs_dir / f"{job_id}.json").exists():
            return {"job_id": job_id, "state": "pending", "receipt": None}
        return {"job_id": job_id, "state": "unknown", "receipt": None}

    def diagnostics(self) -> dict[str, Any]:
        heartbeat = self._read_json(self.heartbeat_path)
        try:
            age = round(time.time() - self.heartbeat_path.stat().st_mtime, 2)
        except OSError:
            age = None
        return {
            "prepared": self.script_path.exists(),
            "mailbox": str(self.root),
            "script_module_alive": age is not None and age < HEARTBEAT_TTL_SECONDS,
            "heartbeat_age_seconds": age,
            "heartbeat": heartbeat,
            "pending_jobs": len(list(self.jobs_dir.glob("*.json"))) if self.jobs_dir.exists() else 0,
        }

    @staticmethod
    def _write_atomic(path: Path, text: str) -> None:
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None


def validate_actions(actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Validate and normalize actions before they are written to the mailbox."""
    if not isinstance(actions, list) or not actions:
        raise ScriptBridgeError("actions must be a non-empty JSON array")
    if len(actions) > 100:
        raise ScriptBridgeError("at most 100 actions may be in one job")
    normalized: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict) or set(action) != {"type", "arguments"}:
            raise ScriptBridgeError("each action requires exactly type and arguments")
        kind, args = action["type"], action["arguments"]
        if kind not in SCRIPT_ACTIONS or not isinstance(args, dict):
            raise ScriptBridgeError(f"unsupported Script Module action: {kind}")
        _validate_arguments(kind, args)
        normalized.append({"type": kind, "arguments": args})
    return normalized


def _validate_arguments(kind: str, args: dict[str, Any]) -> None:
    def name(key: str) -> None:
        if not isinstance(args.get(key), str) or not _NAME.fullmatch(args[key]):
            raise ScriptBridgeError(f"{kind}.{key} must be a Packet Tracer-safe device name")

    def port(key: str) -> None:
        if not isinstance(args.get(key), str) or not _PORT.fullmatch(args[key]):
            raise ScriptBridgeError(f"{kind}.{key} must be a safe port name")

    if kind in {"ping", "query_topology"}:
        if args:
            raise ScriptBridgeError(f"{kind} does not accept arguments")
    elif kind == "create_device":
        if set(args) != {"kind", "model", "name", "x", "y"}:
            raise ScriptBridgeError("create_device needs kind, model, name, x, and y")
        if args["kind"] not in DEVICE_KINDS or not isinstance(args["model"], str) or not _MODEL.fullmatch(args["model"]):
            raise ScriptBridgeError("create_device kind or model is invalid")
        name("name")
        if any(not isinstance(args[key], (int, float)) or isinstance(args[key], bool) or abs(args[key]) > 100000 for key in ("x", "y")):
            raise ScriptBridgeError("create_device coordinates must be finite workspace numbers")
    elif kind in {"delete_device", "disconnect_port"}:
        expected = {"name"} if kind == "delete_device" else {"name", "port"}
        if set(args) != expected:
            raise ScriptBridgeError(f"{kind} has unexpected arguments")
        name("name")
        if kind == "disconnect_port":
            port("port")
    elif kind == "rename_device":
        if set(args) != {"name", "new_name"}:
            raise ScriptBridgeError("rename_device needs name and new_name")
        name("name"); name("new_name")
    elif kind == "move_device":
        if set(args) != {"name", "x", "y"}:
            raise ScriptBridgeError("move_device needs name, x, and y")
        name("name")
        if any(not isinstance(args[key], (int, float)) or isinstance(args[key], bool) or abs(args[key]) > 100000 for key in ("x", "y")):
            raise ScriptBridgeError("move_device coordinates must be finite workspace numbers")
    elif kind == "connect_ports":
        if set(args) != {"a", "a_port", "b", "b_port", "cable"}:
            raise ScriptBridgeError("connect_ports needs a, a_port, b, b_port, and cable")
        name("a"); name("b"); port("a_port"); port("b_port")
        if args["a"] == args["b"] or args["cable"] not in _CABLES:
            raise ScriptBridgeError("connect_ports endpoints or cable are invalid")


def render_script_module() -> str:
    """Render a self-contained ES5 Script Engine file for this mailbox.

    This is original code based on Cisco's documented Script Module IPC API.
    It never evaluates data delivered through the mailbox as source code.
    """
    return f'''// PacketCraft Script Module bridge; generated locally. Do not edit MAILBOX.
// Uses typed JSON jobs only. It never evaluates job text as JavaScript.
var PACKETCRAFT_PROTOCOL = {PROTOCOL_VERSION};
// getUserFolder() is Packet Tracer's documented OS-user folder. This makes a
// compiled .pts portable: no Windows username is baked into the extension.
var MAILBOX = String(ipc.appWindow().getUserFolder()).replace(/\\\\/g, '/') + '/PacketCraft/script-bridge';
var POLL_MS = 500;
var packetcraftTimer = null;

function packetcraftPath(part) {{ return MAILBOX + '/' + part; }}
function packetcraftFiles() {{ return ipc.systemFileManager(); }}
function packetcraftWorkspace() {{ return ipc.appWindow().getActiveWorkspace().getLogicalWorkspace(); }}
function packetcraftWriteAtomic(path, text) {{
  var files = packetcraftFiles();
  var temp = path + '.tmp';
  if (!files.writeTextToFile(temp, text)) throw new Error('unable to write ' + temp);
  if (!files.moveSrcFileToDestFile(temp, path, true)) throw new Error('unable to move ' + path);
}}
function packetcraftHeartbeat() {{
  packetcraftWriteAtomic(packetcraftPath('heartbeat.json'), JSON.stringify({{protocol: PACKETCRAFT_PROTOCOL, at: new Date().getTime()}}));
}}
function packetcraftType(kind, model) {{
  // PT's documented DeviceType enum, with model-specific values where the
  // broad category is not sufficient (for example multilayer switches).
  // Keep this in lockstep with packetcraft_mcp.catalog.  Values are verified
  // against the PT 9 Script Module DeviceType documentation.
  var models = {{
    '1941': 0, '2901': 0, '2911': 0, 'ISR4321': 0, 'ISR4331': 0, 'Router-PT': 0,
    '2960-24TT': 1, '3560-24PS': 16, 'Switch-PT': 1,
    'PC-PT': 8, 'Laptop-PT': 17, 'Server-PT': 9, 'AccessPoint-PT': 7
  }};
  var kinds = {{router: 0, switch: 1, host: 8, server: 9, access_point: 7}};
  if (models[model] !== undefined) return models[model];
  if (kinds[kind] === undefined) throw new Error('unsupported device kind');
  return kinds[kind];
}}
function packetcraftCable(kind) {{
  var cables = {{copper_straight: 8100, copper_cross: 8101, fiber: 8103, serial: 8106, auto: 8107}};
  if (cables[kind] === undefined) throw new Error('unsupported cable');
  return cables[kind];
}}
function packetcraftTopology() {{
  var network = ipc.network(), devices = [], i, device;
  for (i = 0; i < network.getDeviceCount(); i++) {{
    device = network.getDeviceAt(i);
    devices.push({{name: String(device.getName()), model: String(device.getModel()), ports: device.getPorts()}});
  }}
  return {{devices: devices, device_count: devices.length, link_count: network.getLinkCount()}};
}}
function packetcraftAction(action) {{
  var a = action.arguments, ws, device, created;
  if (action.type === 'ping') return {{pong: true}};
  if (action.type === 'query_topology') return packetcraftTopology();
  ws = packetcraftWorkspace();
  if (action.type === 'create_device') {{
    if (ipc.network().getDevice(a.name)) throw new Error('device already exists: ' + a.name);
    created = String(ws.addDevice(packetcraftType(a.kind, a.model), a.model, a.x, a.y));
    device = ipc.network().getDevice(created); device.setName(a.name);
    return {{created: a.name, packet_tracer_name: created}};
  }}
  if (action.type === 'delete_device') return {{deleted: a.name, ok: ws.removeDevice(a.name)}};
  if (action.type === 'rename_device') {{ ipc.network().getDevice(a.name).setName(a.new_name); return {{renamed: a.name, new_name: a.new_name}}; }}
  if (action.type === 'move_device') {{ ipc.network().getDevice(a.name).moveToLocation(a.x, a.y); return {{moved: a.name}}; }}
  if (action.type === 'connect_ports') return {{connected: ws.createLink(a.a, a.a_port, a.b, a.b_port, packetcraftCable(a.cable))}};
  if (action.type === 'disconnect_port') return {{disconnected: ws.deleteLink(a.name, a.port)}};
  throw new Error('unsupported action');
}}
function packetcraftProcess(fileName) {{
  var files = packetcraftFiles(), source = packetcraftPath('jobs/' + fileName), request, reply, i, one;
  try {{
    request = JSON.parse(String(files.getFileContents(source)));
    if (request.protocol !== PACKETCRAFT_PROTOCOL || !request.job_id || !request.actions) throw new Error('invalid job envelope');
    reply = {{protocol: PACKETCRAFT_PROTOCOL, job_id: request.job_id, status: 'succeeded', results: []}};
    for (i = 0; i < request.actions.length; i++) {{
      one = request.actions[i];
      reply.results.push({{type: one.type, result: packetcraftAction(one)}});
    }}
  }} catch (error) {{
    reply = {{protocol: PACKETCRAFT_PROTOCOL, job_id: request && request.job_id ? request.job_id : fileName.replace('.json', ''), status: 'failed', error: String(error)}};
  }}
  packetcraftWriteAtomic(packetcraftPath('results/' + reply.job_id + '.json'), JSON.stringify(reply));
  files.removeFile(source);
}}
function packetcraftTick() {{
  var files, names, i;
  try {{
    packetcraftHeartbeat(); files = packetcraftFiles(); names = files.getFilesInDirectory(packetcraftPath('jobs'));
    for (i = 0; i < names.length; i++) if (/^[0-9a-f]{{32}}\\.json$/.test(String(names[i]))) packetcraftProcess(String(names[i]));
  }} catch (error) {{ dprint('PacketCraft bridge error: ' + String(error)); }}
}}
function main() {{ packetcraftTick(); packetcraftTimer = setInterval(packetcraftTick, POLL_MS); }}
function cleanUp() {{ if (packetcraftTimer !== null) clearInterval(packetcraftTimer); }}
'''
