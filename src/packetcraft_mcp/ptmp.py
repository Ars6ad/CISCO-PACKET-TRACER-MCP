"""Local setup and process client for the Packet Tracer native PTMP adapter."""

from __future__ import annotations

import json
import os
import secrets
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


APPLICATION_ID = "io.packetcraft.mcp"
PT_ROOT = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Cisco Packet Tracer 9.0.0"
SDK = PT_ROOT / "help" / "default" / "ipc" / "pt-cep-java-framework-9.0.0.0.jar"
META = PT_ROOT / "bin" / "meta.exe"
LOCAL_STATE = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "PacketCraft" / "ptmp"


@dataclass(frozen=True)
class PtmpSettings:
    application_id: str
    secret: str
    host: str = "127.0.0.1"
    port: int = 39000


def configuration_path(state_directory: Path = LOCAL_STATE) -> Path:
    return state_directory / "connection.json"


def load_settings(state_directory: Path = LOCAL_STATE) -> PtmpSettings:
    path = configuration_path(state_directory)
    if not path.exists():
        raise FileNotFoundError("PacketCraft PTMP pairing has not been prepared")
    return PtmpSettings(**json.loads(path.read_text(encoding="utf-8")))


def _registration_xml(settings: PtmpSettings) -> str:
    return f'''<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE PT_APP_META>
<PT_APP_META>
  <PT_VERSION>9.0.0</PT_VERSION>
  <IPC_VERSION>1.0</IPC_VERSION>
  <NAME>PacketCraft MCP</NAME>
  <VERSION>0.1.0</VERSION>
  <ID>{settings.application_id}</ID>
  <DESCRIPTION>Local, typed PacketCraft MCP automation connector.</DESCRIPTION>
  <AUTHOR>PacketCraft</AUTHOR>
  <CONTACT>local-only</CONTACT>
  <EXECUTABLE_PATH>packetcraft-ptmp</EXECUTABLE_PATH>
  <KEY>{settings.secret}</KEY>
  <SECURITY_SETTINGS>
    <PRIVILEGE>GET_NETWORK_INFO</PRIVILEGE>
    <PRIVILEGE>CHANGE_NETWORK_INFO</PRIVILEGE>
    <PRIVILEGE>SIMULATION_MODE</PRIVILEGE>
    <PRIVILEGE>MISC_GUI</PRIVILEGE>
    <PRIVILEGE>FILE</PRIVILEGE>
    <PRIVILEGE>CHANGE_PREFERENCES</PRIVILEGE>
    <PRIVILEGE>CHANGE_GUI</PRIVILEGE>
    <PRIVILEGE>ACTIVITY_WIZARD</PRIVILEGE>
    <PRIVILEGE>MULTIUSER</PRIVILEGE>
    <PRIVILEGE>IPC</PRIVILEGE>
    <PRIVILEGE>APPLICATION</PRIVILEGE>
  </SECURITY_SETTINGS>
  <LOADING>ON_DEMAND</LOADING>
  <SAVING>NEVER</SAVING>
  <INSTANCES>1</INSTANCES>
</PT_APP_META>
'''


def prepare_pairing(state_directory: Path = LOCAL_STATE, application_id: str = APPLICATION_ID) -> dict[str, str]:
    """Create a per-user registration and state file; never writes a secret to the repo."""
    if not SDK.exists() or not META.exists():
        raise FileNotFoundError("Cisco Packet Tracer 9 SDK or meta.exe was not found")
    if not application_id.startswith("io.") or any(character.isspace() for character in application_id):
        raise ValueError("application_id must be a reverse-domain identifier beginning with io.")
    state_directory.mkdir(parents=True, exist_ok=True)
    settings = PtmpSettings(application_id=application_id, secret=secrets.token_urlsafe(32))
    config = configuration_path(state_directory)
    registration_xml = state_directory / "packetcraft.xml"
    registration_pta = state_directory / "packetcraft.pta"
    # Refuse to silently replace a live pairing, so an existing PT registration
    # cannot be invalidated by a second tool call.
    if any(path.exists() for path in (config, registration_xml, registration_pta)):
        raise FileExistsError(f"pairing already exists in {state_directory}")
    config.write_text(json.dumps(asdict(settings), indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(config, 0o600)
    except OSError:
        pass
    registration_xml.write_text(_registration_xml(settings), encoding="iso-8859-1")
    completed = subprocess.run([str(META), str(registration_pta), str(registration_xml)], capture_output=True, text=True, timeout=20, check=False)
    if completed.returncode != 0 or not registration_pta.exists():
        raise RuntimeError("Packet Tracer meta.exe could not create the registration file")
    registration_xml.unlink()
    return {"registration_file": str(registration_pta), "state_directory": str(state_directory), "application_id": application_id}


def refresh_registration(state_directory: Path = LOCAL_STATE) -> dict[str, str]:
    """Stage an updated `.pta` using existing credentials; PT UI registration remains a user action."""
    settings = load_settings(state_directory)
    if not META.exists():
        raise FileNotFoundError("Cisco Packet Tracer meta.exe was not found")
    sequence = 1
    while (state_directory / f"packetcraft-update-{sequence}.pta").exists():
        sequence += 1
    registration_xml = state_directory / f"packetcraft-update-{sequence}.xml"
    registration_pta = state_directory / f"packetcraft-update-{sequence}.pta"
    registration_xml.write_text(_registration_xml(settings), encoding="iso-8859-1")
    try:
        completed = subprocess.run([str(META), str(registration_pta), str(registration_xml)], capture_output=True, text=True, timeout=20, check=False)
        if completed.returncode != 0 or not registration_pta.exists():
            raise RuntimeError("Packet Tracer meta.exe could not create the updated registration file")
    finally:
        registration_xml.unlink(missing_ok=True)
    return {"registration_file": str(registration_pta), "application_id": settings.application_id}


class NativePtmpClient:
    def __init__(self, settings: PtmpSettings, workspace: Path) -> None:
        self.settings = settings
        self.workspace = workspace

    def invoke(self, command: str, *arguments: str) -> dict[str, object]:
        classes = self.workspace / "native" / "build"
        if not classes.exists():
            raise FileNotFoundError("native sidecar has not been compiled; run native/build.ps1")
        if not SDK.exists():
            raise FileNotFoundError("Cisco Packet Tracer IPC SDK not found")
        dependencies = sorted((self.workspace / "native" / "vendor").glob("*.jar"))
        if len(dependencies) < 4:
            raise FileNotFoundError("Cisco IPC runtime dependencies are missing; run native/resolve-dependencies.ps1")
        classpath = os.pathsep.join((str(classes), str(SDK), *(str(path) for path in dependencies)))
        java = self._java_runtime()
        environment = os.environ | {
            "PACKETCRAFT_PTMP_APPLICATION": self.settings.application_id,
            "PACKETCRAFT_PTMP_SECRET": self.settings.secret,
            "PACKETCRAFT_PTMP_HOST": self.settings.host,
            "PACKETCRAFT_PTMP_PORT": str(self.settings.port),
        }
        process = subprocess.run(
            [
                str(java),
                "-Djava.net.preferIPv4Stack=true",
                "-Djava.nio.channels.spi.SelectorProvider=sun.nio.ch.WindowsSelectorProvider",
                "-cp", classpath,
                "io.packetcraft.ptmp.PacketCraftPtmp",
            ],
            input="\t".join((command, *arguments)) + "\nQUIT\n",
            capture_output=True, text=True, timeout=15, env=environment, check=False,
        )
        lines = [line for line in process.stdout.splitlines() if line.strip()]
        if not lines:
            error = process.stderr.strip() or "native sidecar returned no response"
            raise RuntimeError(error)
        response = json.loads(lines[0])
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error", "Packet Tracer rejected the operation")))
        return response

    @staticmethod
    def _java_runtime() -> Path:
        configured = os.environ.get("PACKETCRAFT_JAVA")
        if configured:
            candidate = Path(configured)
            if candidate.exists():
                return candidate
            raise FileNotFoundError("PACKETCRAFT_JAVA does not point to java.exe")
        adoptium = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Eclipse Adoptium"
        # Cisco's IPC SDK itself was built for Java 8. Modern runtimes normally
        # work, but Java 16+ uses an AF_UNIX-backed selector pipe on Windows that
        # is blocked in some managed/AppContainer environments. Prefer Java 8.
        candidates = sorted(adoptium.glob("jdk-8*/bin/java.exe"), reverse=True)
        if candidates:
            return candidates[0]
        portable = LOCAL_STATE.parent / "runtime"
        candidates = sorted(portable.glob("*/bin/java.exe"), reverse=True)
        if candidates:
            return candidates[0]
        candidates = sorted(adoptium.glob("jdk-21*/bin/java.exe"), reverse=True)
        if candidates:
            return candidates[0]
        fallback = shutil.which("java")
        if fallback:
            return Path(fallback)
        raise FileNotFoundError("a Java runtime was not found")
