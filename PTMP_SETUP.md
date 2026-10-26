# One-time Packet Tracer PTMP setup

PacketCraft has generated a local registration file at:

`C:\Users\Dudekula arshad\AppData\Local\PacketCraft\ptmp\packetcraft.pta`

The pairing secret is kept separately in the same local state folder and is not stored in this repository or printed by the MCP tools.

## Required manual Packet Tracer actions

1. In Cisco Packet Tracer, open **Extensions → IPC → Configure Apps**.
2. Select **Add** and choose the `packetcraft.pta` file above.
3. Set its load mode to **On Demand** and save the configuration.
4. Open **Extensions → IPC → Options**.
5. Enable **Listening**, set port **39000**, and enable **Always Listen On Start**.
6. Restart Packet Tracer.

Then return here and say **“PTMP configured.”** PacketCraft will authenticate, read the live topology, and run a non-destructive connection test before any mutation tools are enabled.

## Updating the registration

The full-automation profile requests Packet Tracer privileges for topology reads/writes, GUI workspace access, project files, simulation, activities, preferences, multiuser features, IPC, and application access. It is local-only and can reach only the Packet Tracer listener you enabled. Remove its entry in **Configure Apps** at any time to revoke it.

## Troubleshooting

- PacketCraft always targets `127.0.0.1:39000`; do not expose the listener to a LAN.
- The native sidecar prefers Eclipse Temurin Java 8 (the Cisco IPC SDK's build target), then Java 21. The globally selected Java 23 is not used.
- If the status test still cannot start due to a Java `PipeImpl` / `UnixDomainSockets` error, tell PacketCraft the full error. Some managed Windows environments block the JVM's required local loopback pipe; the fallback bridge can then be used instead.
