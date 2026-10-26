# PacketCraft Bridge extension

The user-facing release artifact is `PacketCraft-Bridge.pts`. Like the reference
project's `V5.2.pts`, a user should download that one file and add it in
**Extensions → Scripting → Configure PT Script Modules → Add**.

The checked-in `packetcraft-bridge.js` is the portable, auditable source used to
produce that artifact. Packet Tracer's `.pts` format is encrypted and must be
exported by Packet Tracer itself; the project will never fake the binary format
or distribute another project's extension.

## One-time release build

1. In Packet Tracer, create a new PT Script Module with ID `io.packetcraft.bridge`.
2. Configure **On Startup**, then grant only Get Network, Change Network, Misc GUI,
   Change GUI, and File.
3. Import `packetcraft-bridge.js` in the Script Engine pane.
4. Export it as `PacketCraft-Bridge.pts` into `extension/release/`.
5. Verify it on a clean Packet Tracer installation using the live smoke test in
   `SCRIPT_MODULE_SETUP.md`.

This is a publisher/release step, not an end-user setup step. Once the `.pts`
artifact exists, all future users only install that single `.pts` file.
