import json
from pathlib import Path

import pytest

from packetcraft_mcp.script_bridge import ScriptBridgeError, ScriptMailbox, render_script_module, validate_actions
from packetcraft_mcp.catalog import list_models


def create_action() -> dict:
    return {
        "type": "create_device",
        "arguments": {"kind": "router", "model": "2911", "name": "R1", "x": 100, "y": 200},
    }


def test_prepare_writes_a_typed_script_without_eval(tmp_path: Path) -> None:
    mailbox = ScriptMailbox(tmp_path / "bridge")
    script = mailbox.prepare()
    source = script.read_text(encoding="utf-8")
    assert "ipc.systemFileManager()" in source
    assert "getActiveWorkspace().getLogicalWorkspace()" in source
    assert "getUserFolder()" in source
    assert str(tmp_path) not in source
    assert "packetcraftAction" in source
    assert "'Laptop-PT': 17" in source
    assert "eval(" not in source
    assert "new Function" not in source


def test_queue_and_correlated_receipt(tmp_path: Path) -> None:
    mailbox = ScriptMailbox(tmp_path / "bridge")
    job_id = mailbox.queue([create_action()])
    assert mailbox.status(job_id)["state"] == "pending"
    receipt = {"protocol": 1, "job_id": job_id, "status": "succeeded", "results": [{"type": "create_device", "result": {"created": "R1"}}]}
    (mailbox.results_dir / f"{job_id}.json").write_text(json.dumps(receipt), encoding="utf-8")
    result = mailbox.status(job_id)
    assert result["state"] == "succeeded"
    assert result["receipt"] == receipt


def test_script_bridge_rejects_raw_code_and_bad_model(tmp_path: Path) -> None:
    with pytest.raises(ScriptBridgeError, match="unsupported"):
        validate_actions([{"type": "run_cli", "arguments": {"command": "erase startup-config"}}])
    bad = create_action()
    bad["arguments"]["model"] = "2911;evil"
    with pytest.raises(ScriptBridgeError, match="invalid"):
        ScriptMailbox(tmp_path).queue([bad])


def test_heartbeat_diagnostics(tmp_path: Path) -> None:
    mailbox = ScriptMailbox(tmp_path / "bridge")
    mailbox.prepare()
    mailbox.heartbeat_path.write_text('{"protocol":1}', encoding="utf-8")
    assert mailbox.diagnostics()["script_module_alive"] is True


def test_checked_in_extension_source_is_the_generated_portable_source() -> None:
    source = Path(__file__).parents[1] / "extension" / "packetcraft-bridge.js"
    assert source.read_text(encoding="utf-8") == render_script_module()


def test_extension_device_types_match_the_owned_catalog() -> None:
    source = render_script_module()
    for model in list_models():
        assert f"'{model['model']}': {model['device_type']}" in source
