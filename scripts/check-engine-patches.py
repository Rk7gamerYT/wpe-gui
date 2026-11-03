#!/usr/bin/env python3
"""Check the patch series against pristine tracked files, without changing the engine checkout."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('engine_source', type=Path)
    parser.add_argument('--installed', action='store_true', help='Compare installed sources with the complete patch series')
    args = parser.parse_args()
    ref = re.search(r'^ENGINE_REF="([0-9a-f]+)"', (ROOT / 'install.sh').read_text(), re.M).group(1)
    patches = sorted((ROOT / 'patches').glob('*.patch'))
    with tempfile.TemporaryDirectory(prefix='wpe-patches-') as tmp:
        for patch in patches:
            for name in re.findall(r'^--- a/(.+)$', patch.read_text(), re.M):
                path = Path(tmp) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    result = subprocess.run(['git', 'show', f'{ref}:{name}'], cwd=args.engine_source, capture_output=True)
                    if result.returncode == 0:
                        path.write_bytes(result.stdout)
        for patch in patches:
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=tmp, check=True)
            subprocess.run(['git', 'apply', str(patch)], cwd=tmp, check=True)
        if args.installed:
            names = set()
            for patch in patches:
                names.update(re.findall(r'^\+\+\+ b/(.+)$', patch.read_text(), re.M))
            for name in sorted(names):
                installed = args.engine_source / name
                if not installed.is_file() or installed.read_bytes() != (Path(tmp) / name).read_bytes():
                    raise SystemExit(f'Engine source differs: {name}')
        for patch in reversed(patches):
            subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=tmp, check=True)
    print(f'{len(patches)} patches: clean application and already-applied detection OK ({ref})')


if __name__ == '__main__':
    main()
