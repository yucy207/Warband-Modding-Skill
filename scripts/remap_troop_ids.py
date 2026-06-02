#!/usr/bin/env python3
"""Remap troop ids in generated txt files after troop order changes.

This is meant for full rebuilds where troop ordering changed in
source_res/module_troops.py and all generated txt files need id tokens
rewritten to the new numbering.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TROOP_NAME_RE = re.compile(r'^\["([^"]+)"\s*,', re.M)


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
        return fh.read()


def write_text(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def troop_names(path: Path) -> list[str]:
    text = read_text(path)
    names = TROOP_NAME_RE.findall(text)
    if not names:
        raise SystemExit(f"no troop entries found in {path}")
    return names


def troop_id_map(old_source: Path, new_source: Path) -> dict[int, int]:
    old_names = troop_names(old_source)
    new_names = troop_names(new_source)
    if old_names == new_names:
        return {}

    old_index = {name: idx for idx, name in enumerate(old_names)}
    new_index = {name: idx for idx, name in enumerate(new_names)}

    missing_old = [name for name in old_names if name not in new_index]
    missing_new = [name for name in new_names if name not in old_index]
    if missing_old or missing_new:
        raise SystemExit(
            "troop name sets do not match:\n"
            f"  missing in new source: {', '.join(missing_old) if missing_old else '<none>'}\n"
            f"  missing in old source: {', '.join(missing_new) if missing_new else '<none>'}"
        )

    base = 936748722493063168
    mapping: dict[int, int] = {}
    for name in old_names:
        old_id = base + old_index[name]
        new_id = base + new_index[name]
        if old_id != new_id:
            mapping[old_id] = new_id
    return mapping


def build_pattern(old_id: int) -> re.Pattern[str]:
    return re.compile(rf"(?<!\d){old_id}(?!\d)")


def remap_text(text: str, mapping: dict[int, int]) -> tuple[str, int]:
    replacements = 0
    for old_id, new_id in sorted(mapping.items()):
        pattern = build_pattern(old_id)
        text, count = pattern.subn(str(new_id), text)
        replacements += count
    return text, replacements


def default_txt_files(module_root: Path) -> list[Path]:
    return sorted(
        p for p in module_root.glob("*.txt")
        if p.is_file()
    )


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Remap troop ids in generated txt files.")
    parser.add_argument("--old-source", type=Path, required=True)
    parser.add_argument("--new-source", type=Path, required=True)
    parser.add_argument("--module-root", type=Path, required=True)
    parser.add_argument("--txt", action="append", type=Path, help="Specific txt file to rewrite. Repeatable.")
    parser.add_argument("--all-txt", action="store_true", help="Rewrite every txt file in the module root.")
    parser.add_argument("--write", action="store_true", help="Apply changes in place.")
    parser.add_argument("--dry-run", action="store_true", help="Print a summary without writing.")
    args = parser.parse_args(argv)

    mapping = troop_id_map(args.old_source, args.new_source)
    if not mapping:
        print("No troop id changes detected.")
        return 0

    targets = args.txt if args.txt else default_txt_files(args.module_root) if args.all_txt else []
    if not targets:
        raise SystemExit("no txt targets selected; pass --txt or --all-txt")

    total_replacements = 0
    changed_files: list[tuple[Path, int]] = []
    for path in targets:
        text = read_text(path)
        updated, count = remap_text(text, mapping)
        if count:
            changed_files.append((path, count))
            total_replacements += count
            if args.write:
                write_text(path, updated)

    mode = "applied" if args.write else "preview"
    print(f"{mode}: {len(changed_files)} file(s), {total_replacements} replacement(s)")
    for path, count in changed_files[:20]:
        print(f"  {path}: {count}")
    if len(changed_files) > 20:
        print(f"  ... {len(changed_files) - 20} more file(s)")
    if args.dry_run and args.write:
        print("warning: --dry-run and --write were both set; write took precedence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
