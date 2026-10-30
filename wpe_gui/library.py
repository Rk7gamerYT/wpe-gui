"""Finds installed Wallpaper Engine wallpapers and reads their project.json."""

import functools
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

WORKSHOP_APP_ID = "431960"

STEAM_ROOTS = [
    Path.home() / ".steam/steam",
    Path.home() / ".local/share/Steam",
    Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
]


@dataclass
class Wallpaper:
    path: Path
    title: str
    type: str
    preview: Path | None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.path.name


def steam_library_roots() -> list[Path]:
    """Every Steam install plus the extra libraries listed in libraryfolders.vdf."""
    roots = [r for r in STEAM_ROOTS if r.is_dir()]
    for root in list(roots):
        vdf = root / "steamapps/libraryfolders.vdf"
        try:
            text = vdf.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in re.finditer(r'"path"\s+"([^"]+)"', text):
            p = Path(m.group(1).replace("\\\\", "\\"))
            if p.is_dir():
                roots.append(p)
    # Libraries on secondary drives that this Steam install doesn't know about
    uid = Path.home().name
    for pattern in ("/mnt/*", "/media/*", f"/media/{uid}/*", f"/run/media/{uid}/*"):
        for mount in Path("/").glob(pattern.lstrip("/")):
            for cand in (mount, *[c for c in mount.glob("*Steam*") if c.is_dir()]):
                if (cand / "steamapps").is_dir():
                    roots.append(cand)
    unique = []
    for r in roots:
        if r.resolve() not in [u.resolve() for u in unique]:
            unique.append(r)
    return unique


def default_workshop_dirs() -> list[Path]:
    return [
        d
        for root in steam_library_roots()
        if (d := root / "steamapps/workshop/content" / WORKSHOP_APP_ID).is_dir()
    ]


def default_assets_dir() -> Path | None:
    for root in steam_library_roots():
        d = root / "steamapps/common/wallpaper_engine/assets"
        if d.is_dir():
            return d
    return None


def read_wallpaper(folder: Path) -> Wallpaper | None:
    try:
        data = json.loads((folder / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    preview = folder / data["preview"] if data.get("preview") else None
    if preview is not None and not preview.is_file():
        preview = None
    props = data.get("general", {}).get("properties", {})
    return Wallpaper(
        path=folder,
        title=data.get("title") or folder.name,
        type=str(data.get("type", "unknown")).lower(),
        preview=preview,
        description=data.get("description", ""),
        tags=list(data.get("tags", [])),
        properties=props if isinstance(props, dict) else {},
    )


def scan(dirs: list[Path]) -> list[Wallpaper]:
    found = []
    for d in dirs:
        if not d.is_dir():
            continue
        for sub in sorted(d.iterdir()):
            if sub.is_dir() and (wp := read_wallpaper(sub)):
                found.append(wp)
    return found


@functools.lru_cache(maxsize=None)
def audio_responsive(folder: str) -> bool:
    """Whether the wallpaper reacts to the sound playing on the computer (visualizers, pulsing scenes...).

    Wallpapers declare it with `supportsaudioprocessing` in project.json, but many only use the audio spectrum in
    their shaders, so the scene package is searched too (in chunks, the packages can be large).
    """
    root = Path(folder)
    try:
        data = json.loads((root / "project.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    if data.get("general", {}).get("supportsaudioprocessing"):
        return True
    needles = (b"g_AudioSpectrum", b"registerAudioBuffers", b"audioprocessingmode")
    overlap = max(map(len, needles)) - 1
    try:
        with open(root / "scene.pkg", "rb") as f:
            tail = b""
            while chunk := f.read(8 << 20):
                if any(needle in tail + chunk for needle in needles):
                    return True
                tail = chunk[-overlap:]
    except OSError:
        pass
    return False
