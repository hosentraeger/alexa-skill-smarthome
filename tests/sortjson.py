#!/usr/bin/env python3
import json
import sys
import argparse
import os

def get_by_path(root, path_parts):
    """Navigiert durch das Dictionary basierend auf Pfad-Teilen."""
    for part in path_parts:
        if part.endswith('[]'):
            part = part[:-2]
        if part:
            root = root[part]
    return root

def main():
    parser = argparse.ArgumentParser(description='Sortiert JSON: Keys alphabetisch und Arrays nach einem Pfad-Key.')
    parser.add_argument('file', nargs='?', help='JSON-Datei (falls leer, wird von stdin gelesen)')
    parser.add_argument('-k', '--keypath', required=True, 
                        help='Pfad zum Array und Sortier-Key (z.B. .event.payload.endpoints[].endpointId)')
    
    args = parser.parse_args()

    # 1. JSON laden (Datei oder stdin)
    try:
        if args.file and os.path.isfile(args.file):
            with open(args.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            if sys.stdin.isatty() and not args.file:
                parser.print_help()
                sys.exit(1)
            data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Fehler: Ungültiges JSON ({e})", file=sys.stderr)
        sys.exit(1)

    # 2. Key-Pfad parsen (z.B. .event.payload.endpoints[].endpointId)
    parts = args.keypath.strip('.').split('.')
    array_path = []
    sort_key = None

    for i, part in enumerate(parts):
        if '[]' in part:
            array_path = parts[:i+1]
            if i + 1 < len(parts):
                sort_key = parts[i+1]
            break

    # 3. Array sortieren, falls Pfad gefunden wurde
    if array_path and sort_key:
        try:
            parent_path = array_path[:-1]
            array_name = array_path[-1].replace('[]', '')
            
            parent_obj = get_by_path(data, parent_path)
            target_array = parent_obj[array_name]

            # In-place Sortierung des Arrays nach dem angegebenen Key
            target_array.sort(key=lambda x: str(x.get(sort_key, '')).lower())
        except (KeyError, TypeError):
            print(f"Warnung: Pfad '{args.keypath}' im JSON nicht gefunden. Nur Keys werden sortiert.", file=sys.stderr)

    # 4. Ergebnis ausgeben (mit sort_keys=True für die gesamte Struktur)
    print(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()