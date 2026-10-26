import json
from pathlib import Path

import pytest

import packetcraft_mcp.ptmp as ptmp


def test_load_settings_requires_pairing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ptmp.load_settings(tmp_path)


def test_pairing_rejects_existing_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ptmp, "SDK", tmp_path / "sdk.jar")
    monkeypatch.setattr(ptmp, "META", tmp_path / "meta.exe")
    ptmp.SDK.write_text("sdk")
    ptmp.META.write_text("meta")
    (tmp_path / "connection.json").write_text(json.dumps({"application_id": "io.packetcraft.mcp", "secret": "old"}))
    with pytest.raises(FileExistsError):
        ptmp.prepare_pairing(tmp_path)


def test_registration_has_only_required_initial_privileges() -> None:
    xml = ptmp._registration_xml(ptmp.PtmpSettings(application_id="io.packetcraft.mcp", secret="secret"))
    assert "GET_NETWORK_INFO" in xml
    assert "CHANGE_NETWORK_INFO" in xml
    assert "MISC_GUI" in xml
    assert "CHANGE_GUI" in xml
    assert "APPLICATION" in xml
    assert "SIMULATION_MODE" in xml
    assert "FILE" in xml


def test_java_8_is_preferred_over_java_21(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    java8 = tmp_path / "Eclipse Adoptium" / "jdk-8.0.472" / "bin" / "java.exe"
    java = tmp_path / "Eclipse Adoptium" / "jdk-21.0.12" / "bin" / "java.exe"
    java8.parent.mkdir(parents=True)
    java.parent.mkdir(parents=True)
    java8.write_text("java")
    java.write_text("java")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.delenv("PACKETCRAFT_JAVA", raising=False)
    assert ptmp.NativePtmpClient._java_runtime() == java8
