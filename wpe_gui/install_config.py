"""Verify the installed engine and persist its path without losing user settings."""
import subprocess
import sys
from pathlib import Path

from .engine_locator import locate_engine
from .json_store import write_json
from .settings import Settings, CONFIG_PATH


def main():
    settings = Settings()
    engine = locate_engine(sys.argv[1] if len(sys.argv) > 1 else settings.get("enginePath"))
    if not engine:
        raise SystemExit("Motor não encontrado. Execute ./install.sh sem --no-engine para instalá-lo.")
    engine = str(Path(engine).resolve())
    try:
        done = subprocess.run([engine, "--help"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError) as exc:
        raise SystemExit(f"Não foi possível executar o motor: {exc}") from exc
    if done.returncode:
        raise SystemExit(f"O motor não inicia: {done.stderr.strip() or done.stdout.strip()}")
    if "--audio-gain" not in done.stdout:
        raise SystemExit("Motor sem os patches necessários. Execute ./install.sh sem --no-engine.")
    settings._data["enginePath"] = engine
    write_json(CONFIG_PATH, settings._data)
    print(f"Motor verificado e configurado: {engine}")


if __name__ == "__main__":
    main()
