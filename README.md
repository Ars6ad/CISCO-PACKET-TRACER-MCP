# PacketCraft MCP

An original, safety-first MCP server for designing, validating, compiling, and eventually deploying Cisco Packet Tracer topologies. It is being built from scratch with the public `Mats2208/MCP-Packet-Tracer` repository used solely as a capability benchmark.

## Current milestone

The first milestone is usable offline: a typed topology format, deterministic address allocation, structural validation, IOS configuration generation, project persistence, and an MCP interface. Live Packet Tracer deployment is deliberately behind a transaction protocol; it will not claim success until an extension reports an acknowledgement.

```powershell
pip install -e .[test]
python -m pytest
packetcraft-mcp
```

For live deployment, end users install one `PacketCraft-Bridge.pts` extension in
Packet Tracer. The portable source and release instructions are in
[`extension/`](extension/); [SCRIPT_MODULE_SETUP.md](SCRIPT_MODULE_SETUP.md)
explains the live check. The clean-room comparison with the reference
architecture is in [REFERENCE_AUDIT.md](REFERENCE_AUDIT.md); the broader delivery
status is in [PARITY.md](PARITY.md). The exhaustive current-reference audit is
in [REFERENCE_FILE_AUDIT.md](REFERENCE_FILE_AUDIT.md).
