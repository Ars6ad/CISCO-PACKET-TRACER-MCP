# Native Packet Tracer adapter

This source compiles against the IPC framework included with the user's Cisco Packet Tracer 9 installation. The proprietary Cisco JAR is never copied, committed, or redistributed.

## Build

```powershell
.\native\resolve-dependencies.ps1
.\native\build.ps1
```

The adapter needs a Packet Tracer IPC application registration before it can connect. `pc_ptmp_prepare` generates a per-user `.pta` registration plus a local secret outside the repository. Do not put secrets in source files.

Follow [PTMP_SETUP.md](../PTMP_SETUP.md) to manually authorize the local app and enable Packet Tracer's listener. This configuration changes Packet Tracer's IPC access settings, so it is intentionally not automated.

The initial command protocol is deliberately narrow: `STATUS`, `TOPOLOGY`, and `ADD_DEVICE`. It is a foundation for typed, auditable automation rather than a raw command shell.
