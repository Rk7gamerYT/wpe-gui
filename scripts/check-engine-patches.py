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
    args = parser.parse_args()
    ref = re.search(r'^ENGINE_REF="([0-9a-f]+)"', (ROOT / 'install.sh').read_text(), re.M).group(1)
    patches = sorted((ROOT / 'patches').glob('*.patch'))
    with tempfile.TemporaryDirectory(prefix='wpe-patches-') as tmp:
        for patch in patches:
            for name in re.findall(r'^--- a/(.+)$', patch.read_text(), re.M):
                path = Path(tmp) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                if not path.exists():
                    path.write_bytes(subprocess.check_output(['git', 'show', f'{ref}:{name}'], cwd=args.engine_source))
        for patch in patches:
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=tmp, check=True)
            subprocess.run(['git', 'apply', str(patch)], cwd=tmp, check=True)
        for patch in patches:
            subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=tmp, check=True)
    print(f'{len(patches)} patches: clean application and already-applied detection OK ({ref})')


if __name__ == '__main__':
    main()
