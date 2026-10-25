"""Small privileged helper for Ubuntu GDM. Run only after explicit authentication."""

import os
import stat
import subprocess
import sys
from pathlib import Path

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
PNG_END = b"\x00\x00\x00\x00IEND\xaeB`\x82"


def read_png(source: Path) -> bytes:
    fd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or not 20 <= info.st_size <= 64 * 1024 * 1024:
            raise ValueError("Arquivo de imagem inválido ou maior que 64 MiB.")
        data = stream.read(64 * 1024 * 1024 + 1)
    if len(data) > 64 * 1024 * 1024 or not data.startswith(PNG_HEADER) or not data.endswith(PNG_END):
        raise ValueError("A captura PNG não está completa.")
    return data


def configure(source: Path | None, root: Path = Path("/"), runner=subprocess.run):
    """Install/remove only our own override; restore it if GDM compilation fails."""
    image = root / "var/lib/wpe-gui/login.png"
    override = root / "usr/share/gdm/dconf/99-wpe-gui"
    generate = root / "usr/share/gdm/generate-config"
    if not generate.is_file() or not override.parent.is_dir():
        raise RuntimeError("Esta integração requer o GDM do Ubuntu.")
    data = read_png(source) if source is not None else None
    previous = {p: (p.read_bytes(), stat.S_IMODE(p.stat().st_mode)) if p.exists() else None
                for p in (image, override)}

    def write(path, content, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        temporary = path.with_suffix(".tmp")
        # Never follow a pre-existing temporary symlink as root.
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                os.fchmod(stream.fileno(), mode)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)

    try:
        if data is None:
            override.unlink(missing_ok=True)
        else:
            write(image, data)
            write(override, (
                "# Managed by wpe-gui. Remove through the app to restore the previous background.\n"
                "[com/ubuntu/login-screen]\n"
                "background-picture-uri='file:///var/lib/wpe-gui/login.png'\n"
                "background-size='cover'\n"
                "background-repeat='no-repeat'\n"
            ).encode())
        runner([str(generate)], check=True, capture_output=True, timeout=30)
        if data is None:
            image.unlink(missing_ok=True)
    except Exception:
        for path, old in previous.items():
            if old is None:
                path.unlink(missing_ok=True)
            else:
                write(path, *old)
        runner([str(generate)], check=False, capture_output=True, timeout=30)
        raise


def main():
    if os.geteuid() != 0:
        raise RuntimeError("É necessária autenticação de administrador.")
    if len(sys.argv) == 2 and sys.argv[1] == "--reset":
        configure(None)
    elif len(sys.argv) == 3 and sys.argv[1] == "--apply":
        configure(Path(sys.argv[2]))
    else:
        raise ValueError("Uso: login_helper.py --apply captura.png | --reset")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
