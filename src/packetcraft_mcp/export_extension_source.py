"""Refresh the checked-in, portable Script Module source for release packaging."""

from pathlib import Path

from .script_bridge import render_script_module


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    path = root / "extension" / "packetcraft-bridge.js"
    path.write_text(render_script_module(), encoding="utf-8", newline="\n")
    print(path)


if __name__ == "__main__":
    main()
