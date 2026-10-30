"""Opt-in integration test using installed wallpaper assets, never modifying the original.

Run under a disposable X server, e.g. DISPLAY=:99 .venv/bin/python
 tests/engine_scenescript_smoke.py --engine /path/to/linux-wallpaperengine
 --wallpaper /path/to/scene-wallpaper --assets /path/to/wallpaper_engine/assets
"""
import argparse
import resource
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time

GROUP_SCRIPT = """
'use strict';
function check(value, message) { if (!value) throw new Error(message); }
// Top-level lookups must work even when the target is later in the scene file.
const sibling = thisScene.getLayer('Probe image');
check(sibling && sibling.name === 'Probe image', 'deferred scene graph lookup');
export function init() {
    shared.groupReady = true;
    check(engine.canvasSize.x > 0 && engine.canvasSize.y > 0, 'canvasSize');
    check(engine.isDesktopDevice() && engine.isWallpaper() && !engine.isMobileDevice(), 'device flags');
    check(typeof engine.userProperties === 'object', 'userProperties');
    console.log('SMOKE_PASS group');
}
"""
IMAGE_SCRIPT = """
'use strict';
import * as WEMath from 'WEMath';
import * as WEColor from 'WEColor';
import * as WEVector from 'WEVector';
function check(value, message) { if (!value) throw new Error(message); }
const defaults = createScriptProperties().addSlider({name:'probeDefault', value:17}).finish();
check(defaults.probeDefault === 17, 'script property defaults');
const buffers = [16, 32, 64].map(r => engine.registerAudioBuffers(r));
let keep = buffers[2].average;
let timerCount = 0;
export function applyUserProperties(values) { shared.propertiesApplied = true; }
export function init(value) {
    check(shared.groupReady && shared.propertiesApplied, 'initialization order');
    check(Math.abs(WEMath.mix(0, 10, 0.5) - 5) < 0.001, 'WEMath import');
    check(Math.abs(WEVector.angleVector2(90).y - 1) < 0.001, 'WEVector import');
    check(Math.abs(WEVector.vectorAngle2(new Vec2(0,1)) - 90) < 0.001, 'WEVector angles');
    let color = WEColor.normalizeColor(new Vec3(255, 128, 0));
    check(color.x === 1 && color.z === 0, 'WEColor import');
    thisLayer.angles = new Vec3(0, 0, 30);
    thisLayer.angles.z = 45;
    check(Math.abs(thisLayer.angles.z - 45) < 0.001, 'degree rotation and vector mutation');
    thisLayer.origin = new Vec3(100, 200, 3);
    check(thisLayer.origin.z === 3, 'Vec3 z');
    check(thisLayer.size.x > 0 && thisLayer.size.y > 0, 'image size');
    thisLayer.alignment = 'bottom';
    check(thisLayer.alignment === 'bottom', 'string alignment');
    check(buffers.every((b, i) => b.average instanceof Float32Array && b.average.length === [16,32,64][i]), 'typed audio buffers');
    try { engine.registerAudioBuffers(17); throw new Error('invalid audio resolution accepted'); }
    catch (error) { check(error instanceof RangeError, 'audio resolution validation'); }
    const config = thisScene.getInitialLayerConfig(thisScene.getLayer('Background'));
    const clone = thisScene.createLayer(config);
    clone.scale = new Vec3(0.001);
    const count = thisScene.getLayerCount();
    check(thisScene.enumerateLayers().length === count, 'scene enumeration');
    thisScene.sortLayer(clone, 1);
    check(thisScene.getLayerIndex(clone) === 1, 'layer order');
    let cancel = engine.setInterval(() => {
        check(thisLayer.name === 'Probe image', 'interval layer context');
        ++timerCount;
        cancel();
    }, 0);
    engine.setTimeout(() => {
        check(timerCount === 1 && thisLayer.name === 'Probe image', 'timer lifetime and cancellation');
        thisLayer.origin = new Vec3(4, 5, 6);
        check(thisLayer.origin.z === 6, 'timer property write');
        shared.timerPassed = true;
        console.log('SMOKE_PASS timer');
    }, 100);
    console.log('SMOKE_PASS image');
    return value;
}
export function update(value) {
    check(keep === buffers[2].average, 'stable audio buffer');
    check(keep.every(x => Number.isFinite(x) && x >= 0 && x <= 1), 'audio range');
    return value;
}
export function destroy() { console.log('SMOKE_PASS destroy'); }
"""
TEXT_SCRIPT = """
'use strict';
import * as WEMath from 'WEMath';
export function update(value) {
    if (!Number.isFinite(WEMath.mix(0, 1, 0.5))) throw new Error('text module import');
    return shared.timerPassed ? 'SMOKE TEXT OK' : 'WAITING';
}
"""


def read_package(path):
    with path.open('rb') as stream:
        def integer():
            return struct.unpack('<I', stream.read(4))[0]
        def string():
            return stream.read(integer()).decode()
        version = string()
        entries = []
        for _ in range(integer()):
            entries.append((string(), integer(), integer()))
        base = stream.tell()
        assets = {}
        for name, offset, size in entries:
            stream.seek(base + offset)
            assets[name] = stream.read(size)
        return version, assets


def write_package(path, version, assets):
    def integer(value):
        return struct.pack('<I', value)
    def string(value):
        encoded = value.encode()
        return integer(len(encoded)) + encoded
    header = string(version) + integer(len(assets))
    payload = bytearray()
    for name, data in assets.items():
        header += string(name) + integer(len(payload)) + integer(len(data))
        payload.extend(data)
    path.write_bytes(header + payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--wallpaper', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='wpe-scenescipt-smoke-') as tmp:
        root = args.output.resolve() if args.output else Path(tmp)
        root.mkdir(parents=True, exist_ok=True)
        version, assets = read_package(args.wallpaper / 'scene.pkg')
        original = json.loads(assets['scene.json'])
        background = next(o.copy() for o in original['objects'] if 'image' in o)
        background.update(id=1, name='Background')
        background.pop('parent', None)
        probe = {'id': 1001, 'name': 'Probe image', 'image': background['image'],
                 'origin': '100 200 0', 'scale': '0.01 0.01 1',
                 'visible': {'value': True, 'script': IMAGE_SCRIPT}, 'parent': 1000}
        scene = dict(original)
        scene['objects'] = [background,
                            {'id': 1000, 'name': 'Probe group', 'origin': '0 0 0',
                             'visible': {'value': True, 'script': GROUP_SCRIPT}},
                            probe,
                            {'id': 1002, 'name': 'Probe text', 'origin': '500 300 0',
                             'text': {'value': 'WAITING', 'script': TEXT_SCRIPT},
                             'font': 'systemfont_consolas', 'pointsize': 24, 'padding': '32 16'}]
        assets['scene.json'] = json.dumps(scene).encode()
        write_package(root / 'scene.pkg', version, assets)
        project = json.loads((args.wallpaper / 'project.json').read_text())
        project.update(file='scene.json', type='scene')
        project.setdefault('general', {})['supportsaudioprocessing'] = True
        (root / 'project.json').write_text(json.dumps(project))
        env = os.environ.copy()
        env['XDG_SESSION_TYPE'] = 'x11'
        env.pop('WAYLAND_DISPLAY', None)
        screenshot = root / 'screenshot.png'
        screenshot.unlink(missing_ok=True)
        command = [str(args.engine.resolve()), '--window', '0x0x640x360', '--bg', str(root),
                   '--assets-dir', str(args.assets.resolve()), '--silent', '--noautomute',
                   '--no-fullscreen-pause', '--fps', '30', '--screenshot', str(screenshot),
                   '--screenshot-delay', '2']
        def no_core_dump():
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

        with (root / 'engine.log').open('wb') as log:
            process = subprocess.Popen(command, env=env, stdout=log, stderr=log, preexec_fn=no_core_dump)
            deadline = time.monotonic() + 12
            while process.poll() is None and time.monotonic() < deadline:
                if screenshot.exists() and 'SMOKE_PASS timer' in (root / 'engine.log').read_text(errors='replace'):
                    break
                time.sleep(.1)
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        output = (root / 'engine.log').read_text(errors='replace')
        failures = [line for line in output.splitlines()
                    if 'ScriptEngine [' in line or 'SceneScript timer:' in line or 'Assertion' in line]
        for marker in ('group', 'image', 'timer', 'destroy'):
            if f'SMOKE_PASS {marker}' not in output:
                failures.append(f'Missing marker: {marker}')
        if process.returncode != 0:
            failures.append(f'Unexpected exit: {process.returncode}')
        if not screenshot.exists():
            failures.append('No rendered screenshot')
        if failures:
            print('\n'.join(failures))
            print(output[-6000:])
            return 1
        # Invalid metadata must return an error instead of aborting in JSON optional().
        scene['objects'][-1]['padding'] = True
        assets['scene.json'] = json.dumps(scene).encode()
        write_package(root / 'scene.pkg', version, assets)
        invalid = subprocess.run([str(args.engine.resolve()), '--bg', str(root), '--assets-dir',
                                  str(args.assets.resolve()), '--list-properties'], env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10,
                                 preexec_fn=no_core_dump)
        (root / 'invalid-metadata.log').write_bytes(invalid.stdout)
        scene['objects'][-1]['padding'] = '32 16'
        assets['scene.json'] = json.dumps(scene).encode()
        write_package(root / 'scene.pkg', version, assets)
        if invalid.returncode != 1:
            print('Invalid metadata should exit 1, got', invalid.returncode)
            return 1
        print('SceneScript lifecycle, imports, groups, vectors, rotation, audio, text, timers and metadata errors: OK')
        if args.output:
            print('Artifacts:', root)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
