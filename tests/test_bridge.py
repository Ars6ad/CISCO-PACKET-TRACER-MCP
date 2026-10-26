import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from packetcraft_mcp.bridge import Bridge, BridgeServer


def post(url: str, token: str, payload: dict) -> tuple[int, dict]:
    request = Request(url, data=json.dumps(payload).encode(), method="POST", headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urlopen(request, timeout=2) as response:
        return response.status, json.loads(response.read())


def test_bridge_dispatches_once_and_requires_receipt() -> None:
    bridge = Bridge(token="test-secret")
    job = bridge.enqueue([{"type": "query_topology", "arguments": {}}])
    assert bridge.poll().id == job.id
    assert bridge.poll() is None
    assert bridge.record_receipt(job.id, "succeeded", {"devices": []}).state == "succeeded"
    with pytest.raises(ValueError):
        bridge.record_receipt(job.id, "succeeded", {})


def test_bridge_rejects_arbitrary_javascript() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        Bridge().enqueue([{"type": "send_raw", "arguments": {"javascript": "evil()"}}])


def test_http_bridge_requires_token_and_returns_receipt() -> None:
    server = BridgeServer(Bridge(token="test-secret"))
    address = server.start()
    try:
        with pytest.raises(HTTPError) as error:
            post(f"{address}/v1/poll", "wrong", {})
        assert error.value.code == 401
        job = server.bridge.enqueue([{"type": "query_topology", "arguments": {}}])
        status, polled = post(f"{address}/v1/poll", "test-secret", {})
        assert status == 200 and polled["job"]["id"] == job.id
        status, receipt = post(f"{address}/v1/receipt", "test-secret", {"job_id": job.id, "status": "succeeded", "result": {"devices": []}})
        assert status == 200 and receipt["job"]["state"] == "succeeded"
    finally:
        server.stop()
