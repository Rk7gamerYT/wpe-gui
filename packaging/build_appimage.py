#!/usr/bin/env python3
"""Build one AppImage containing Python/Qt, the patched engine, CEF and native dependencies.

Build release artifacts on Ubuntu 24.04; the host glibc/C++ runtime and graphics drivers
are deliberately not bundled. No system package installation is needed on supported desktops.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = json.loads((ROOT / 'packaging/tools.json').read_text())
# Desktop drivers and the C runtime must come from the host, not a different Mesa/glibc build.
HOST_LIB = re.compile(r'^(ld-linux|lib(c|m|pthread|dl|rt|util|resolv|nss_[^.]*)\.so|libstdc\+\+|libgcc_s|lib(GL|EGL|OpenGL|glapi|gbm|drm|vulkan|nvidia|gallium))')


def run(*command, **kwargs):
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def download(name, cache):
    destination = cache / name
    expected = TOOLS[name]['sha256']
    if not destination.exists() or hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
        request = urllib.request.Request(TOOLS[name]['url'], headers={'User-Agent': 'wpe-gui-packager'})
        with urllib.request.urlopen(request, timeout=120) as source, destination.open('wb') as target:
            shutil.copyfileobj(source, target)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != expected:
        raise RuntimeError(f'{name}: SHA-256 mismatch')
    return destination


def elf(path):
    try:
        with path.open('rb') as stream:
            return stream.read(4) == b'\x7fELF'
    except OSError:
        return False


def bundle_dependencies(appdir):
    common = appdir / 'usr/lib'
    queue = [path for path in appdir.rglob('*') if path.is_file() and not path.is_symlink() and elf(path)]
    inspected = set()
    origins = {}
    while queue:
        path = queue.pop()
        if path in inspected:
            continue
        inspected.add(path)
        result = subprocess.run(['ldd', str(path)], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            match = re.match(r'\s*(\S+) => (\S+)', line)
            if not match:
                continue
            name, source = match.groups()
            if HOST_LIB.match(name):
                continue
            target = common / name
            if (path.parent / name).is_file():
                continue
            if source == 'not':
                if target.exists():
                    continue
                raise RuntimeError(f'Missing native dependency {name} required by {path}')
            source = Path(source)
            if not source.is_absolute():
                continue
            if source.is_relative_to(appdir):
                continue
            if not target.exists():
                shutil.copy2(source, target)
                queue.append(target)
                origins[name] = str(source.resolve())
    # Every bundled ELF resolves its own imports; child desktop helpers keep the host environment.
    for path in inspected:
        relative = os.path.relpath(common, path.parent)
        rpath = '$ORIGIN' + (':$ORIGIN/' + relative if relative != '.' else '')
        old = subprocess.run(['patchelf', '--print-rpath', str(path)], capture_output=True, text=True).stdout.strip()
        for entry in old.split(':'):
            if entry.startswith('$ORIGIN') and entry not in rpath.split(':'):
                rpath += ':' + entry
        run('patchelf', '--set-rpath', rpath, path)
    (appdir / 'usr/share/wpe-gui/native-libraries.json').write_text(json.dumps(origins, indent=2))
    return origins


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine-output', type=Path, required=True)
    parser.add_argument('--engine-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    parser.add_argument('--cache', type=Path, default=ROOT / 'build/downloads')
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    output, cache = args.output.resolve(), args.cache.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    appdir = output / 'wpe-gui.AppDir'
    if appdir.exists():
        shutil.rmtree(appdir)
    (appdir / 'usr/app').mkdir(parents=True)
    (appdir / 'usr/share/wpe-gui').mkdir(parents=True)
    engine = appdir / 'usr/lib/wpe-engine'
    engine.mkdir(parents=True)
    python_archive = download('python', cache)
    with tarfile.open(python_archive) as archive:
        archive.extractall(appdir / 'usr', filter='data')
    python = appdir / 'usr/python/bin/python3'
    run(python, '-m', 'pip', 'install', '--disable-pip-version-check', f'PySide6-Essentials=={TOOLS["pyside"]}')
    for directory in ('wpe_gui', 'kde', 'extension', 'packaging'):
        shutil.copytree(ROOT / directory, appdir / 'usr/app' / directory,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'packaging/AppRun', appdir / 'AppRun')
    (appdir / 'AppRun').chmod(0o755)
    shutil.copy2(ROOT / 'packaging/wpe-gui.desktop', appdir / 'wpe-gui.desktop')
    shutil.copy2(ROOT / 'wpe_gui/assets/icons/app.svg', appdir / 'wpe-gui.svg')
    for path in args.engine_output.iterdir():
        if path.name == 'linux-wallpaperengine' or path.name.startswith('lib') or path.suffix in ('.pak', '.dat', '.bin', '.json'):
            if path.is_file():
                shutil.copy2(path, engine / path.name)
        elif path.name == 'locales':
            shutil.copytree(path, engine / path.name)
    # Keep licenses/corresponding-source references with the runtime libraries.
    licenses = appdir / 'usr/share/licenses/wpe-gui'
    licenses.mkdir(parents=True)
    shutil.copy2(ROOT / 'LICENSE', licenses / 'GUI-MIT.txt')
    shutil.copy2(args.engine_source / 'LICENSE', licenses / 'engine-GPL-3.0.txt')
    cef = next((args.engine_source / 'build/cef').glob('cef_binary_*_minimal'), None)
    if cef and (cef / 'LICENSE.txt').exists():
        shutil.copy2(cef / 'LICENSE.txt', licenses / 'CEF-LICENSE.txt')
    (licenses / 'SOURCES.txt').write_text('GUI, patches and build scripts: https://github.com/Rk7gamerYT/wpe-gui\n'
                                       'Engine: https://github.com/Almamu/linux-wallpaperengine\n'
                                       'Python: https://github.com/astral-sh/python-build-standalone\n'
                                       'Qt/PySide: https://code.qt.io/pyside/pyside-setup.git\n'
                                       'Ubuntu runtime library sources: https://archive.ubuntu.com/ubuntu/pool/\n')
    origins = bundle_dependencies(appdir)
    # Include distribution copyright notices for copied native libraries.
    for source in origins.values():
        result = subprocess.run(['dpkg-query', '-S', source], capture_output=True, text=True)
        if result.returncode != 0:
            continue
        package = result.stdout.split(': ', 1)[0].split(':', 1)[0]
        copyright_file = Path('/usr/share/doc') / package / 'copyright'
        if copyright_file.exists():
            shutil.copy2(copyright_file, licenses / (package + '.copyright'))
    if args.prepare_only:
        print(appdir)
        return
    tool, runtime = download('appimagetool', cache), download('runtime', cache)
    tool.chmod(0o755)
    version = re.search(r'__version__ = "([^"]+)"', (ROOT / 'wpe_gui/__init__.py').read_text()).group(1)
    destination = output / f'wpe-gui-{version}-x86_64.AppImage'
    env = dict(os.environ, ARCH='x86_64', APPIMAGE_EXTRACT_AND_RUN='1')
    run(tool, '--runtime-file', runtime, '--comp', 'xz', '--mksquashfs-opt', '-processors',
        '--mksquashfs-opt', '2', appdir, destination, env=env)
    destination.chmod(0o755)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (output / 'SHA256SUMS').write_text(f'{digest}  {destination.name}\n')
    print(destination)


if __name__ == '__main__':
    main()
