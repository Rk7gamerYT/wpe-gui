"""Opt-in render smoke audit; run with PYTHONPATH=. in a disposable X server.

This checks that a frame renders and records explicit engine/script errors. It does
not prove pixel accuracy or complete compatibility of a wallpaper.
"""
import argparse
import json
import os
from pathlib import Path
import resource
import struct
import subprocess
import time

from wpe_gui.library import default_workshop_dirs, scan


def uses_script_audio(folder):
    try:
        with (folder / 'scene.pkg').open('rb') as stream:
            def integer():
                return struct.unpack('<I', stream.read(4))[0]
            def string():
                return stream.read(integer()).decode()
            string()
            entries = []
            for _ in range(integer()):
                entries.append((string(), integer(), integer()))
            base = stream.tell()
            for name, offset, size in entries:
                if not name.endswith(('.json', '.js')):
                    continue
                stream.seek(base + offset)
                if b'registerAudioBuffers' in stream.read(size):
                    return True
    except (OSError, ValueError, struct.error):
        pass
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--library', type=Path, action='append')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(XDG_SESSION_TYPE='x11', WPE_AUDIO_PROCESSING='1')
    env.pop('WAYLAND_DISPLAY', None)
    rows = []
    for wallpaper in scan(args.library or default_workshop_dirs()):
        if not uses_script_audio(wallpaper.path):
            continue
        logpath = args.output / f'{wallpaper.id}.log'
        screenshot = (args.output / f'{wallpaper.id}.png').resolve()
        screenshot.unlink(missing_ok=True)
        command = [str(args.engine.resolve()), '--window', '0x0x320x180', '--assets-dir',
                   str(args.assets.resolve()), '--bg', str(wallpaper.path), '--silent',
                   '--noautomute', '--no-fullscreen-pause', '--fps', '10',
                   '--screenshot', str(screenshot), '--screenshot-delay', '1']
        with logpath.open('wb') as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=log,
                                       preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            deadline = time.monotonic() + 12
            rendered_at = None
            while process.poll() is None and time.monotonic() < deadline:
                if screenshot.exists():
                    rendered_at = rendered_at or time.monotonic()
                    if time.monotonic() - rendered_at >= .5:
                        break
                time.sleep(.1)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        lines = logpath.read_text(errors='replace').splitlines()
        errors = list(dict.fromkeys(line[:500] for line in lines if any(word in line.lower() for word in
                           ('scriptengine [', 'scenescript timer:', 'not supported', 'not implemented',
                            'failed to setup', 'typeerror', 'referenceerror', 'syntaxerror',
                            '[json.exception', 'framebuffers are not properly set'))))
        row = {'id': wallpaper.id, 'title': wallpaper.title, 'rendered': screenshot.exists(),
               'exit': process.returncode, 'errors': errors[:15]}
        rows.append(row)
        (args.output / 'results.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        print(wallpaper.id, wallpaper.title, 'rendered=' + str(row['rendered']), 'errors=' + str(len(errors)), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
