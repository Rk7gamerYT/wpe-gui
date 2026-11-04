#!/usr/bin/env python3
"""Read every installed wallpaper's declared resources and SceneScript usage."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wpe_gui.library import scan, default_workshop_dirs

TEXT = {'.json', '.js', '.html', '.htm', '.frag', '.vert'}


def package_text(path):
    with path.open('rb') as stream:
        length = path.stat().st_size
        def integer():
            data = stream.read(4)
            if len(data) != 4: raise ValueError('Truncated package index')
            return struct.unpack('<I', data)[0]
        def string():
            size = integer()
            if size > 65536: raise ValueError('Invalid package string size')
            return stream.read(size).decode('utf-8')
        if not string().startswith('PKGV'): raise ValueError('Unsupported package header')
        count = integer()
        if count > 100000: raise ValueError('Invalid package entry count')
        entries = [(string(), integer(), integer()) for _ in range(count)]
        base = stream.tell()
        for name, offset, size in entries:
            if Path(name).suffix.lower() not in TEXT: continue
            if base + offset + size > length: raise ValueError('Package entry outside file')
            if size > 16*1024*1024: continue
            stream.seek(base+offset)
            yield name, stream.read(size).decode('utf-8-sig', errors='replace')


def inspect_wallpaper(wallpaper):
    scripts = []; effects = set(); types = Counter(); problems = []
    def walk(value):
        if isinstance(value, dict):
            if isinstance(value.get('script'), str): scripts.append(value['script'])
            if isinstance(value.get('file'), str) and value['file'].startswith('effects/'):
                effects.add(value['file'])
            for item in value.values(): walk(item)
        elif isinstance(value, list):
            for item in value: walk(item)
    def inspect(name, text):
        if name.endswith('.json'):
            try:
                data = json.loads(text); walk(data)
                if name.endswith('scene.json'):
                    for obj in data.get('objects', []):
                        kind = next((key for key in ('image','particle','sound','text','light','volumelight','model') if key in obj), 'group')
                        types[kind] += 1
            except (ValueError, AttributeError) as error: problems.append({'file':name,'error':str(error)})
        elif name.endswith(('.js', '.html', '.htm')): scripts.append(text)
    for file in sorted(wallpaper.path.rglob('*')):
        if not file.is_file(): continue
        try:
            if file.suffix.lower() == '.pkg':
                for name, text in package_text(file): inspect(name, text)
            elif file.suffix.lower() in TEXT and file.stat().st_size <= 16*1024*1024:
                inspect(str(file.relative_to(wallpaper.path)), file.read_text(encoding='utf-8-sig', errors='replace'))
        except (OSError, ValueError, struct.error) as error: problems.append({'file':file.name,'error':str(error)})
    modules = set(); calls = set(); callbacks = set()
    for script in set(scripts):
        script = re.sub(r"\\x([0-9a-fA-F]{2})", lambda match: chr(int(match[1], 16)), script)
        aliases = {}
        for alias, module in re.findall(r'import\s+\*\s+as\s+(\w+)\s+from\s*[\'"]([^\'"]+)', script): aliases[alias] = module
        modules.update(aliases.values())
        modules.update(re.findall(r'\bimport\s+[\'"]([A-Za-z0-9_./-]+)[\'"]', script))
        for receiver, method in re.findall(r'\b([A-Za-z_$][\w$]*)\s*\.\s*([A-Za-z_$][\w$]*)\s*\(', script):
            if receiver in ('engine','thisScene','thisLayer','input','WEMath','WEColor','WEVector') or receiver in aliases:
                calls.add(aliases.get(receiver, receiver)+'.'+method)
        callbacks.update(re.findall(r'export\s+function\s+(\w+)\s*\(', script))
    return {'id':wallpaper.id,'title':wallpaper.title,'type':wallpaper.type,
            'script_count':len(set(scripts)), 'modules':sorted(modules), 'calls':sorted(calls),
            'callbacks':sorted(callbacks),'object_types':dict(types),'effects':sorted(effects),'inspection_errors':problems}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', action='append', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args=parser.parse_args()
    rows=[]; modules=defaultdict(list); calls=defaultdict(list)
    for wallpaper in scan(args.library or default_workshop_dirs()):
        row=inspect_wallpaper(wallpaper);rows.append(row)
        for module in row['modules']:modules[module].append(row['id'])
        for call in row['calls']:calls[call].append(row['id'])
    result={'summary':{'total':len(rows),'types':dict(Counter(r['type'] for r in rows)),
                       'with_scripts':sum(bool(r['script_count']) for r in rows)},
            'modules':dict(sorted(modules.items())), 'calls':dict(sorted(calls.items())), 'wallpapers':rows}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result['summary'],ensure_ascii=False))
    print('Modules:', json.dumps({k:len(v) for k,v in result['modules'].items()}))
    print('Calls:', json.dumps({k:len(v) for k,v in result['calls'].items()}))


if __name__=='__main__': main()
