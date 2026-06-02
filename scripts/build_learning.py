#!/usr/bin/env python3
"""Learn full source-to-txt build structure from local Warband files.

This validates more than opcode blocks: file headers, count fields, script
record names, record markers, body operation counts, and append-only script
changes against the current module source_res and txt files.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from compile_learning import KILL_HEAL_EXPECTED, assert_equal, source_script, txt_script
from compile_snippet import SCRIPT_BASE, compile_text


def source_script_names(module_root: Path) -> list[str]:
    text = (module_root / "source_res" / "module_scripts.py").read_text(encoding="utf-8", errors="ignore")
    return re.findall(r'^\("([^"]+)",', text, re.M)


def txt_scripts(module_root: Path) -> tuple[str, int, list[tuple[str, str]]]:
    lines = (module_root / "scripts.txt").read_text(encoding="utf-8", errors="ignore").splitlines()
    if len(lines) < 2:
        raise AssertionError("scripts.txt is too short")
    header = lines[0].strip()
    count = int(lines[1].strip())
    records: list[tuple[str, str]] = []
    pos = 2
    while pos < len(lines):
        line = lines[pos].strip()
        if not line:
            pos += 1
            continue
        if not line.endswith(" -1"):
            raise AssertionError(f"unexpected script header line: {lines[pos]!r}")
        name = line[:-3]
        if pos + 1 >= len(lines):
            raise AssertionError(f"missing body for script {name}")
        records.append((name, " ".join(lines[pos + 1].split())))
        pos += 2
    return header, count, records


def body_count(body: str) -> int:
    tokens = body.split()
    if not tokens:
        raise AssertionError("empty operation body")
    return int(tokens[0])


def script_id(names: list[str], name: str) -> int:
    if name not in names:
        raise AssertionError(f"script not found: {name}")
    return SCRIPT_BASE + names.index(name)


def build_script_record(module_root: Path, name: str) -> str:
    body = compile_text(source_script(module_root, name), module_root, "ops")
    return f"{name} -1\n {body}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run full txt build-structure learning tests.")
    parser.add_argument("--module-root", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.module_root

    source_names = source_script_names(root)
    header, txt_count, txt_records = txt_scripts(root)
    txt_names = [name for name, _ in txt_records]

    assert_equal("scripts.txt header", header, "scriptsfile version 1")
    assert_equal("scripts.txt count matches record count", str(txt_count), str(len(txt_records)))

    if source_names[:len(txt_names)] != txt_names:
        for index, (src, txt) in enumerate(zip(source_names, txt_names)):
            if src != txt:
                raise AssertionError(f"script order diverges at {index}: source={src} txt={txt}")
        raise AssertionError("script name prefix mismatch")
    print(f"PASS source script order matches existing scripts.txt prefix ({len(txt_names)} records)")

    appended = source_names[len(txt_names):]
    print(f"PASS detected {len(appended)} appended source script(s): {', '.join(appended) if appended else '<none>'}")
    assert_equal("rebuilt scripts.txt count after source append", str(len(source_names)), str(txt_count + len(appended)))

    stable_name = "store_intelligence_attribute_level"
    stable_record = build_script_record(root, stable_name)
    assert_equal(
        f"full script record build: {stable_name}",
        stable_record,
        f"{stable_name} -1\n {txt_script(root, stable_name)}",
    )
    assert_equal(f"{stable_name} operation count field", str(body_count(txt_script(root, stable_name))), "3")

    if "player_heal_on_kill" in source_names:
        heal_record = build_script_record(root, "player_heal_on_kill")
        if "player_heal_on_kill" in txt_names:
            expected_heal_record = f"player_heal_on_kill -1\n {txt_script(root, 'player_heal_on_kill')}"
            id_check_name = "player_heal_on_kill script id"
        else:
            expected_heal_record = f"player_heal_on_kill -1\n {KILL_HEAL_EXPECTED}"
            id_check_name = "player_heal_on_kill append script id"
        assert_equal(
            "full script record build: player_heal_on_kill",
            heal_record,
            expected_heal_record,
        )
        expected_body = txt_script(root, "player_heal_on_kill") if "player_heal_on_kill" in txt_names else KILL_HEAL_EXPECTED
        assert_equal("player_heal_on_kill operation count field", str(body_count(expected_body)), "38")
        expected_id = SCRIPT_BASE + source_names.index("player_heal_on_kill")
        assert_equal(id_check_name, str(script_id(source_names, "player_heal_on_kill")), str(expected_id))

    print("build learning ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
