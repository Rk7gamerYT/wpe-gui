"""Per-wallpaper properties (the sliders/switches/colours from project.json) and their saved overrides."""

import json
import re
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from . import library

OVERRIDES_PATH = Path.home() / ".config/wpe-gui/overrides.json"

# Property types we can render and send to the engine with --set-property
EDITABLE = {"bool", "slider", "color", "combo", "textinput"}
LABEL_TYPES = {"text", "group"}

_TAG = re.compile(r"<[^>]+>")
_TOKEN = re.compile(r"\s*(&&|\|\||==|!=|<=|>=|[()!<>]|-?\d+(?:\.\d+)?|true|false|\"[^\"]*\"|'[^']*'|\w+\.value)")


KNOWN_LABELS = {"ui_browse_properties_scheme_color": "Scheme color"}


def clean_label(text: str, key: str) -> str:
    """Property labels are either plain text, HTML or a localisation key like ui_background_color."""
    text = _TAG.sub("", text or "").replace("‎", "").strip()
    if text in KNOWN_LABELS:
        return KNOWN_LABELS[text]
    if not text or text.startswith("ui_"):
        text = (text or key).removeprefix("ui_").replace("_", " ").strip()
        text = text[:1].upper() + text[1:]
    return text


def condition_holds(expr: str, values: dict) -> bool:
    """Evaluates conditions such as 'bg_enable.value && bg_type.value == 1'.

    Only a whitelist of tokens is accepted, so nothing from a project.json is ever executed as arbitrary code.
    """
    if not expr:
        return True
    pos, py = 0, []
    expr = expr.strip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m or m.end() == pos:
            return True  # unknown syntax: show the property rather than hide it
        tok = m.group(1)
        pos = m.end()
        if tok == "&&":
            py.append(" and ")
        elif tok == "||":
            py.append(" or ")
        elif tok == "!":
            py.append(" not ")
        elif tok in ("true", "false"):
            py.append("True" if tok == "true" else "False")
        elif tok.endswith(".value"):
            py.append(f"v.get({tok[:-6]!r})")
        else:
            py.append(tok)
    try:
        return bool(eval("".join(py), {"__builtins__": {}}, {"v": values}))  # noqa: S307 (whitelisted tokens)
    except Exception:
        return True


def _coerce(ptype: str, value):
    if ptype == "bool":
        return value in (True, "true", "1", 1)
    if ptype == "slider":
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
    return value


def serialize(ptype: str, value) -> str:
    """Value in the string form --set-property expects."""
    if ptype == "bool":
        return "true" if value else "false"
    if ptype == "slider":
        f = float(value)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    return str(value)


class PropertiesStore(QObject):
    changed = Signal(str)  # wallpaper path whose overrides changed

    def __init__(self, path: Path = OVERRIDES_PATH, parent=None):
        super().__init__(parent)
        self._path = path
        self._data: dict = {}
        try:
            self._data = json.loads(path.read_text())
        except (OSError, ValueError):
            pass

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def _definitions(self, folder: str) -> dict:
        wp = library.read_wallpaper(Path(folder))
        return wp.properties if wp else {}

    def _values(self, folder: str, defs: dict) -> dict:
        saved = self._data.get(folder, {})
        return {
            k: _coerce(d.get("type"), saved.get(k, d.get("value")))
            for k, d in defs.items()
            if d.get("type") in EDITABLE
        }

    @Slot(str, result="QVariant")
    def load(self, folder):
        """List of dicts, in UI order, with the current value and whether the condition lets it show."""
        defs = self._definitions(folder)
        values = self._values(folder, defs)
        saved = self._data.get(folder, {})
        out = []
        for key, d in sorted(defs.items(), key=lambda kv: kv[1].get("order", 0)):
            ptype = str(d.get("type", "")).lower()
            if ptype not in EDITABLE and ptype not in LABEL_TYPES:
                continue
            if ptype in LABEL_TYPES and not _TAG.sub("", d.get("text", "")).replace("\u200e", "").strip():
                continue  # image-only banners and spacers
            if not condition_holds(d.get("condition", ""), values):
                continue
            item = {
                "key": key,
                "type": ptype,
                "label": clean_label(d.get("text", ""), key),
                "value": values.get(key, ""),
                "modified": key in saved,
            }
            if ptype == "slider":
                item.update(min=d.get("min", 0), max=d.get("max", 100), step=d.get("step", 1))
            if ptype == "combo":
                item["options"] = [
                    {"label": clean_label(str(o.get("label", "")), str(o.get("value"))), "value": str(o.get("value"))}
                    for o in d.get("options", [])
                ]
            out.append(item)
        return out

    @Slot(str, str, "QVariant")
    def setValue(self, folder, key, value):
        defs = self._definitions(folder)
        d = defs.get(key)
        if not d:
            return
        entry = self._data.setdefault(folder, {})
        if _coerce(d.get("type"), value) == _coerce(d.get("type"), d.get("value")):
            entry.pop(key, None)  # back to the default
        else:
            entry[key] = value
        if not entry:
            self._data.pop(folder, None)
        self._save()
        self.changed.emit(folder)

    @Slot(str)
    def reset(self, folder):
        if self._data.pop(folder, None) is not None:
            self._save()
        self.changed.emit(folder)

    # -- per-wallpaper engine options (scaling, clamping), stored beside the property overrides ------

    ENGINE_KEY = "_engine"
    ENGINE_CHOICES = {"scaling": ("default", "stretch", "fit", "fill"), "clamping": ("clamp", "border", "repeat")}

    def engine_options(self, folder: str) -> dict:
        return dict(self._data.get(folder, {}).get(self.ENGINE_KEY, {}))

    @Slot(str, str, result=str)
    def engineOption(self, folder, key):
        """'' means 'use the global setting'."""
        return self.engine_options(folder).get(key, "")

    @Slot(str, str, str)
    def setEngineOption(self, folder, key, value):
        if key not in self.ENGINE_CHOICES or (value and value not in self.ENGINE_CHOICES[key]):
            return
        entry = self._data.setdefault(folder, {})
        options = entry.setdefault(self.ENGINE_KEY, {})
        if value:
            options[key] = value
        else:
            options.pop(key, None)
        if not options:
            entry.pop(self.ENGINE_KEY, None)
        if not entry:
            self._data.pop(folder, None)
        self._save()
        self.changed.emit(folder)

    def engine_args(self, folder: str) -> list[str]:
        """--set-property arguments for the overridden values only."""
        defs = self._definitions(folder)
        args = []
        for key, value in self._data.get(folder, {}).items():
            d = defs.get(key)
            if d and d.get("type") in EDITABLE:
                args += ["--set-property", f"{key}={serialize(d['type'], value)}"]
        return args
