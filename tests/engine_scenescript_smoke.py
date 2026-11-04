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
from PySide6.QtGui import QColor, QImage

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
    check(shared.groupReady && !shared.propertiesApplied, 'init precedes initial property event');
    check(Math.abs(WEMath.mix(0, 10, 0.5) - 5) < 0.001, 'WEMath import');
    check(Math.abs(WEVector.angleVector2(90).y - 1) < 0.001, 'WEVector import');
    check(Math.abs(WEVector.vectorAngle2(new Vec2(0,1)) - 90) < 0.001, 'WEVector angles');
    let color = WEColor.normalizeColor(new Vec3(255, 128, 0));
    check(color.x === 1 && color.z === 0, 'WEColor import');
    check(new Vec3(1,2).z === 0 && new Vec3(undefined).x === 0, 'partial constructors');
    check(new Vec3(1).hasOwnProperty('x'), 'vector own properties');
    check(new Vec3(3,4,0).lengthSqr() === 25, 'length squared');
    check(new Vec3(1,2,3).dot(new Vec3(4,5,6)) === 32, 'scalar dot product');
    check(new Vec3(8,6,4).subtract(new Vec3(2,3,1)).x === 6, 'subtract order');
    check(new Vec3(8,6,4).divide(new Vec3(2,3,1)).x === 4, 'divide order');
    check(new Vec3(1,0,0).cross(new Vec3(0,1,0)).z === 1, 'cross order');
    check(new Vec3(0).mix(new Vec3(8),0.25).x === 2, 'mix order');
    check(thisLayer.getParent().name === 'Probe group', 'parent lookup');
    check(thisLayer.getTransformMatrix().m.length === 16, 'transform matrix');
    check(thisLayer.color instanceof Vec3, 'layer RGB color type');
    thisLayer.customFlag = 37;
    check(thisScene.getLayer('Probe image') === thisLayer && thisScene.getLayer('Probe image').customFlag === 37, 'stable layer identity and custom fields');
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
    check(shared.propertiesApplied, 'initial property event after init');
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
        failed_model = json.loads(assets[background['image']])
        failed_material = json.loads(assets[failed_model['material']])
        for render_pass in failed_material['passes']:
            render_pass['shader'] = 'smoke_missing_shader'
        assets['materials/smoke-failed.json'] = json.dumps(failed_material).encode()
        failed_model['material'] = 'materials/smoke-failed.json'
        assets['models/smoke-failed.json'] = json.dumps(failed_model).encode()
        scene = dict(original)
        scene['objects'] = [background,
                            {'id': 1000, 'name': 'Probe group', 'origin': '0 0 0',
                             'visible': {'value': True, 'script': GROUP_SCRIPT}},
                            probe,
                            {'id': 1003, 'name': 'Failed probe', 'image': 'models/smoke-failed.json',
                             'visible': {'value': True, 'script': "export function init(){throw new Error('released layer script executed');}"}},
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
        if 'Failed to setup object 1003' not in output:
            failures.append('Failed-layer lifetime regression was not exercised')
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
        # User file properties must decode ordinary PNG images, not search for a .tex named after the property.
        image_path = root / 'user image.png'
        image = QImage(8, 8, QImage.Format_RGBA8888)
        image.fill(QColor('#00ff00')); image.save(str(image_path))
        project['general'].setdefault('properties', {})['smokeImage'] = {
            'type': 'file', 'value': str(image_path), 'text': 'Test image'}
        (root / 'project.json').write_text(json.dumps(project))
        custom_image = dict(background)
        custom_image.update(instance={'usertextures': ['smokeImage']}, color='1.0 1.0 1.0', alpha=1,
                            visible=True, scale='1 1 1')
        custom_image.pop('effects', None)
        original_objects = scene['objects']
        scene['objects'] = [custom_image]
        assets['scene.json'] = json.dumps(scene).encode()
        write_package(root / 'scene.pkg', version, assets)
        image_capture = root / 'user-image.png'
        image_capture.unlink(missing_ok=True)
        image_command = command.copy()
        image_command[image_command.index('--screenshot') + 1] = str(image_capture)
        with (root / 'user-image.log').open('wb') as log:
            image_process = subprocess.Popen(image_command, env=env, stdout=log, stderr=log, preexec_fn=no_core_dump)
            try:
                deadline = time.monotonic() + 10
                while image_process.poll() is None and not image_capture.exists() and time.monotonic() < deadline:
                    time.sleep(.1)
            finally:
                if image_process.poll() is None:
                    image_process.terminate()
                    try: image_process.wait(3)
                    except subprocess.TimeoutExpired: image_process.kill(); image_process.wait()
        captured = QImage(str(image_capture))
        if captured.isNull():
            print('User image: missing screenshot'); return 1
        pixel = captured.pixelColor(captured.width() // 2, captured.height() // 2)
        if pixel.green() < 230 or pixel.red() > 25 or pixel.blue() > 25:
            print('User image: expected green, got', pixel.name()); return 1
        scene['objects'] = original_objects
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
