#!/usr/bin/env python3
"""Learn and regression-test compile_snippet.py against local Warband source/txt.

This builds small tests from the current module's source_res and txt files.
It intentionally tests supported snippets, not the complete module system.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

from compile_snippet import CompileError, Compiler, compile_text, parse_snippet


KILL_HEAL_EXPECTED = (
    '38 2071 1 1224979098644774912 2072 1 1224979098644774913 30 2 1224979098644774912 0 30 2 1224979098644774913 0 1704 1 1224979098644774912 2147485354 1 1224979098644774912 1700 1 1224979098644774914 31 2 1224979098644774913 1224979098644774914 2147483679 2 1224979098644774912 1224979098644774914 1702 1 1224979098644774914 1720 3 1224979098644774915 1224979098644774914 0 2147483678 2 1224979098644774915 75 1720 3 1224979098644774916 1224979098644774914 1 1718 2 1224979098644774917 1224979098644774912 2171 2 1224979098644774918 1224979098644774917 2111 2 1224979098644774918 10 2110 2 1224979098644774918 50 2121 3 1224979098644774919 1224979098644774918 10 2107 2 1224979098644774919 20 2108 2 1224979098644774919 40 2105 2 1224979098644774919 5 1726 3 1224979098644774920 1224979098644774914 0 4 0 30 2 1224979098644774920 0 1570 2 1224979098644774921 1224979098644774920 1073741855 2 1224979098644774921 8 1073741855 2 1224979098644774921 9 31 2 1224979098644774921 10 2108 2 1224979098644774919 2 3 0 2120 3 1224979098644774922 1224979098644774915 1224979098644774919 2110 2 1224979098644774922 100 1721 3 1224979098644774914 1224979098644774922 0 1720 3 1224979098644774923 1224979098644774914 1 2121 3 1224979098644774924 1224979098644774923 1224979098644774916 32 2 1224979098644774924 0 2133 2 72057594037927936 1224979098644774924 1106 2 216172782113789739 16711680'
)

def source_script(module_root: Path, name: str) -> str:
    path = module_root / "source_res" / "module_scripts.py"
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r'^\("' + re.escape(name) + r'",\n\[(.*?)\n\]\),', text, re.M | re.S)
    if not match:
        raise AssertionError(f"source script not found: {name}")
    return match.group(1).strip()


def txt_script(module_root: Path, name: str) -> str:
    path = module_root / "scripts.txt"
    text = path.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"^" + re.escape(name) + r" -1\n ([^\n]+)", text, re.M)
    if not match:
        raise AssertionError(f"txt script not found: {name}")
    return " ".join(match.group(1).split())


def assert_equal(label: str, actual: str, expected: str) -> None:
    actual = " ".join(actual.split())
    expected = " ".join(expected.split())
    if actual != expected:
        raise AssertionError(f"{label} mismatch\nactual:   {actual}\nexpected: {expected}")
    print(f"PASS {label}")


def script_id(module_root: Path, name: str) -> int:
    names = all_script_names(module_root)
    if name not in names:
        raise AssertionError(f"script not found: {name}")
    return 936748722493063168 + names.index(name)


def all_script_names(module_root: Path) -> list[str]:
    text = (module_root / "source_res" / "module_scripts.py").read_text(encoding="utf-8", errors="ignore")
    return re.findall(r'^\("([^"]+)",', text, re.M)


def parse_txt_ops(body: str) -> list[list[str]]:
    tokens = body.split()
    if not tokens:
        return []
    count = int(tokens[0])
    ops: list[list[str]] = []
    pos = 1
    for _ in range(count):
        if pos + 1 >= len(tokens):
            raise AssertionError("truncated txt operation stream")
        code = tokens[pos]
        argc = int(tokens[pos + 1])
        end = pos + 2 + argc
        ops.append(tokens[pos:end])
        pos = end
    if pos != len(tokens):
        raise AssertionError("extra tokens after txt operation stream")
    return ops


def touch_locals(compiler: Compiler, node: ast.AST) -> None:
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str) and child.value.startswith(":"):
            compiler.local_id(child.value)


def op_name(node: ast.AST) -> str | None:
    target = node.elts[0] if isinstance(node, ast.Tuple) and node.elts else node
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.BinOp):
        while isinstance(target, ast.BinOp):
            target = target.right
        if isinstance(target, ast.Name):
            return target.id
    return None


def sample_supported_operation_pairs(module_root: Path, limit: int) -> list[tuple[str, str, str, str]]:
    samples: list[tuple[str, str, str, str]] = []
    for script_name in all_script_names(module_root):
        if len(samples) >= limit:
            break
        try:
            source_body = source_script(module_root, script_name)
            source_ops = parse_snippet(source_body)
            txt_ops = parse_txt_ops(txt_script(module_root, script_name))
        except Exception:
            continue
        if len(source_ops) != len(txt_ops):
            continue
        compiler = Compiler(module_root)
        for index, (source_op, txt_op) in enumerate(zip(source_ops, txt_ops)):
            touch_locals(compiler, source_op)
            if len(samples) >= limit:
                break
            if op_name(source_op) == "call_script":
                # Existing txt may be older than source_res after inserting scripts.
                # Skip script-id-sensitive samples unless the whole txt was regenerated.
                continue
            try:
                compiled = " ".join(compiler.compile_op(source_op))
            except CompileError:
                continue
            expected = " ".join(txt_op)
            if compiled != expected:
                raise AssertionError(
                    f"sample mismatch in {script_name}[{index}]\n"
                    f"source:   {ast.unparse(source_op)}\n"
                    f"actual:   {compiled}\n"
                    f"expected: {expected}"
                )
            samples.append((script_name, str(index), ast.unparse(source_op), expected))
    if len(samples) < limit:
        raise AssertionError(f"only collected {len(samples)} supported samples, wanted {limit}")
    return samples


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run compile learning regression tests.")
    parser.add_argument("--module-root", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=100)
    args = parser.parse_args(argv)
    root = args.module_root

    body = source_script(root, "store_intelligence_attribute_level")
    expected = txt_script(root, "store_intelligence_attribute_level")
    assert_equal("source_res/module_scripts.py -> scripts.txt: store_intelligence_attribute_level", compile_text(body, root, "ops"), expected)

    heal_body = source_script(root, "player_heal_on_kill")
    assert_equal("current source_res player_heal_on_kill body", compile_text(heal_body, root, "ops"), KILL_HEAL_EXPECTED)

    trigger = '''(ti_on_agent_killed_or_wounded, 0.000000, 0.000000,
[
],
[
    (call_script, "script_player_heal_on_kill"),
]),'''
    assert_equal(
        "player_heal_on_kill trigger",
        compile_text(trigger, root, "trigger"),
        f"-26.000000 0.000000 0.000000 0 1 1 1 {script_id(root, 'player_heal_on_kill')}",
    )

    samples = sample_supported_operation_pairs(root, args.sample_count)
    print(f"PASS sampled {len(samples)} source/txt operation pairs")
    for script_name, index, source, expected in samples[:10]:
        print(f"  sample {script_name}[{index}]: {source} -> {expected}")
    if len(samples) > 10:
        print(f"  ... {len(samples) - 10} more samples")

    print("compile learning ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
