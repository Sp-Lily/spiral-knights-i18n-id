#!/usr/bin/env python3
"""Remove keys from translated bundles that the English bundle no longer has.

Usage: python3 tools/remove_stale_keys.py [--check] [--lang LANG ...] [--bundle NAME ...] [bundle_dir]

By default every translated bundle is cleaned; --lang (e.g. --lang es) and --bundle (e.g.
--bundle item) limit it the same way they do for check_bundles.py.

The whole entry is removed, including its continuation lines; comments and blank lines are
kept, as are line endings. An unknown key that check_bundles.py thinks is really a piece of the
value above it (a broken "\\" continuation) is left alone and listed, since removing it would lose
part of that translation: fix the continuation by hand. A translated bundle with no English
bundle at all is listed but not deleted.

With --check, nothing is written; the keys that would be removed are listed and the exit status
is 1 if there are any.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_bundles import LANG_SUFFIX, is_fragment, parse, wanted  # noqa: E402


def is_stray(p):
    """Whether check_bundles.py reports p as a broken continuation rather than a key of its own."""
    return bool(p.prev) and (p.indented or re.search(r"\\[ \t]+$", p.prev_text) is not None)


def clean(path, en_keys, check):
    """Remove the stale entries from one file; return (removed keys, skipped fragments)."""
    props, _ = parse(path)
    stale = [p for p in props if p.key not in en_keys]
    remove = [p for p in stale if not (is_fragment(p) or is_stray(p))]
    skipped = [p for p in stale if p not in remove]
    if remove and not check:
        with open(path, "rb") as f:
            text = f.read().decode("latin-1")
        # Pair each line with its line ending, splitting the way parse() does.
        parts = re.split(r"(\r\n|\r|\n)", text)
        lines = [parts[i] + (parts[i + 1] if i + 1 < len(parts) else "") for i in range(0, len(parts), 2)]
        drop = {n for p in remove for n in range(p.line - 1, p.last)}
        out = "".join(line for n, line in enumerate(lines) if n not in drop)
        with open(path, "wb") as f:
            f.write(out.encode("latin-1"))
    return remove, skipped


def main():
    ap = argparse.ArgumentParser(description="Remove keys from translated bundles that the English bundle doesn't have.")
    ap.add_argument("--check", action="store_true", help="only list the keys that would be removed")
    ap.add_argument("--lang", action="append", default=[],
                    help="only clean this language's bundles (e.g. es); may be repeated")
    ap.add_argument("--bundle", action="append", default=[],
                    help="only clean the translations of this bundle (e.g. item); may be repeated")
    ap.add_argument("bundle_dir", nargs="?",
                    default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    args = ap.parse_args()
    root = args.bundle_dir
    names = sorted(n for n in os.listdir(root)
                   if LANG_SUFFIX.match(n) and wanted(n, args.lang, args.bundle))
    if not names:
        print("no translated bundles match")
        sys.exit(1)
    verb = "would remove" if args.check else "removed"
    total, files = 0, 0
    for name in names:
        en_name = LANG_SUFFIX.match(name).group("base") + ".properties"
        en_path = os.path.join(root, en_name)
        if not os.path.isfile(en_path):
            print(f"{name}: no English bundle {en_name}; not touched")
            continue
        en_keys = {p.key for p in parse(en_path)[0]}
        removed, skipped = clean(os.path.join(root, name), en_keys, args.check)
        for p in removed:
            print(f"{name}:{p.line}: {verb} {p.key}")
        for p in skipped:
            print(f"{name}:{p.line}: skipped; looks like a broken continuation of {p.prev.key}, fix it by hand")
        total += len(removed)
        files += bool(removed)
    print(f"{verb} {total} key(s) from {files} file(s)" if total else "nothing to remove")
    sys.exit(1 if args.check and total else 0)


if __name__ == "__main__":
    main()
