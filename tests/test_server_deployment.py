import json
from pathlib import Path

from packetcraft_mcp import server
from packetcraft_mcp.script_bridge import ScriptMailbox


def test_live_deploy_does_not_queue_when_script_module_is_offline(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(server, "script_mailbox", ScriptMailbox(tmp_path / "bridge"))
    plan = {
        "name": "offline-check",
        "devices": [{"name": "R1", "kind": "router", "model": "2911"}],
    }
    result = json.loads(server.pc_deploy_to_script_module(json.dumps(plan), approve=True))
    assert result["queued"] is False
    assert "not alive" in result["reason"]
