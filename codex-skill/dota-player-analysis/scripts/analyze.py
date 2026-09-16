from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    project = Path(os.getenv("DOTA_PLAYER_ANALYZER_HOME", r"P:\dota-player-analyzer"))
    if not project.is_dir():
        print("Dota Player Analyzer project not found. Set DOTA_PLAYER_ANALYZER_HOME.", file=sys.stderr)
        return 2
    candidate = project / ".venv" / "Scripts" / "python.exe"
    python = candidate if candidate.exists() else Path(sys.executable)
    result = subprocess.run([str(python), "-m", "dota_analyzer", *sys.argv[1:]], cwd=project)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

