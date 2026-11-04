"""Opt-in CEF bridge test: properties, FPS and 128-bin audio callbacks must paint green."""
import argparse
import json
import os
from pathlib import Path
import resource
import subprocess
import tempfile
import time
from PySide6.QtGui import QImage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='wpe-web-smoke-') as temporary:
        root = Path(temporary) / '9000000001'; root.mkdir()
        (root / 'project.json').write_text(json.dumps({'title': 'Bridge probe', 'type': 'web', 'file': 'index.html',
            'general': {'supportsaudioprocessing': True, 'properties': {
                'speed': {'type': 'slider', 'value': 2.5},
                'enabled': {'type': 'bool', 'value': True},
                'label': {'type': 'textinput', 'value': 'hello'}}}}))
        (root / 'scripts/My Library').mkdir(parents=True)
        (root / 'scripts/My Library/helper.js').write_text('window.bridgeHelper = 123;')
        (root / 'index.html').write_text('''<!doctype html><body style="background:red"><script src="scripts/My Library/helper.js"></script><script>
        let propertiesOK = false, fpsOK = false, received = 0;
        window.wallpaperPropertyListener = {
            applyUserProperties(p) {propertiesOK = p.speed.value === 2.5 && p.enabled.value === true && p.label.value === 'hello' && window.bridgeHelper === 123;},
            applyGeneralProperties(p) {fpsOK = p.fps === 20;}
        };
        wallpaperRegisterAudioListener(data => {
            if (data.length !== 128 || !data.every(Number.isFinite)) return;
            if (++received > 5 && propertiesOK && fpsOK) document.body.style.background = '#00ff00';
        });
        </script></body>''')
        screenshot = args.output.resolve() / 'web.png'; screenshot.unlink(missing_ok=True)
        env = dict(os.environ, XDG_SESSION_TYPE='x11', WPE_CAPTURE_ONLY='1', WPE_AUDIO_PROCESSING='1')
        env.pop('WAYLAND_DISPLAY', None)
        with (args.output / 'web.log').open('wb') as log:
            process = subprocess.Popen([str(args.engine.resolve()), '--window', '0x0x320x180',
                '--bg', str(root), '--assets-dir', str(args.assets.resolve()), '--silent',
                '--noautomute', '--no-fullscreen-pause', '--fps', '20',
                '--screenshot', str(screenshot), '--screenshot-delay', '60'], env=env,
                stdout=log, stderr=log, preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_CORE, (0, 0)))
            try:
                deadline = time.monotonic() + 15
                while process.poll() is None and not screenshot.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
            finally:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(3)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
        picture = QImage(str(screenshot))
        if picture.isNull(): raise SystemExit('Web test failed: no rendered screenshot')
        color = picture.pixelColor(picture.width() // 2, picture.height() // 2)
        if color.green() < 240 or color.red() > 15 or color.blue() > 15:
            raise SystemExit(f'Web bridge failed: expected green, got {color.name()}')
        print('Web properties, general properties and continuous 128-bin audio: OK')


if __name__ == '__main__': main()
