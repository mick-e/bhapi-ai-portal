"""Create a zip with forward-slash paths (cross-platform safe).

Usage:
  python zipdir.py <source_dir> <output.zip> [--exclude .d.ts .map]
  python zipdir.py <root_dir> <output.zip> --include src icons manifest.json ...
"""

import argparse
import os
import sys
import zipfile


def zip_directory(source, dest, excludes):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(source):
            for f in files:
                full = os.path.join(root, f)
                rel = os.path.relpath(full, source).replace("\\", "/")
                if any(rel.endswith(ex) for ex in excludes):
                    continue
                zf.write(full, rel)


def zip_includes(root_dir, dest, includes):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in includes:
            full = os.path.join(root_dir, item)
            if os.path.isfile(full):
                zf.write(full, item.replace("\\", "/"))
            elif os.path.isdir(full):
                for dirpath, _dirs, files in os.walk(full):
                    for f in files:
                        filepath = os.path.join(dirpath, f)
                        arcname = os.path.relpath(filepath, root_dir).replace("\\", "/")
                        zf.write(filepath, arcname)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="Source directory")
    parser.add_argument("output", help="Output zip path")
    parser.add_argument("--exclude", nargs="*", default=[], help="File suffixes to exclude")
    parser.add_argument("--include", nargs="*", default=[], help="Specific files/dirs to include (relative to source)")
    args = parser.parse_args()

    if args.include:
        zip_includes(args.source, args.output, args.include)
    else:
        zip_directory(args.source, args.output, args.exclude)

    size_kb = os.path.getsize(args.output) / 1024
    print(f"  Created: {os.path.basename(args.output)} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()
