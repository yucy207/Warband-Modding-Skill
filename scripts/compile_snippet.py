#!/usr/bin/env python3
"""Compile small Mount&Blade Warband module-system snippets to txt opcode.

This is a focused snippet compiler, not a full module-system replacement.
It handles operation lists and simple mission triggers commonly needed while
editing decompiled source_res files.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


LOCAL_BASE = 1224979098644774912
REG_BASE = 72057594037927936
GLOBAL_BASE = 144115188075855872
SCRIPT_BASE = 936748722493063168
STRING_BASE = 216172782113783808

FLAGS = {
    "neg": 0x80000000,
    "this_or_next": 0x40000000,
}

OPS = {
    "call_script": 1,
    "try_begin": 4,
    "else_try": 5,
    "try_end": 3,
    "try_for_range": 6,
    "try_for_agents": 12,
    "store_script_param": 23,
    "store_trigger_param_1": 2071,
    "store_trigger_param_2": 2072,
    "store_trigger_param_3": 2073,
    "eq": 31,
    "ge": 30,
    "gt": 32,
    "lt": 0x80000000 | 30,
    "le": 0x80000000 | 32,
    "assign": 2133,
    "store_add": 2120,
    "store_sub": 2121,
    "store_mul": 2122,
    "store_div": 2123,
    "store_mod": 2119,
    "val_add": 2105,
    "val_sub": 2106,
    "val_mul": 2107,
    "val_div": 2108,
    "val_mod": 2109,
    "val_min": 2110,
    "val_max": 2111,
    "get_player_agent_no": 1700,
    "agent_is_alive": 1702,
    "agent_is_human": 1704,
    "agent_is_ally": 1706,
    "agent_get_horse": 1714,
    "agent_get_troop_id": 1718,
    "store_agent_hit_points": 1720,
    "agent_set_hit_points": 1721,
    "agent_get_wielded_item": 1726,
    "agent_set_division": 1783,
    "agent_get_item_slot": 1804,
    "agent_get_item_cur_ammo": 1977,
    "item_get_type": 1570,
    "store_character_level": 2171,
    "troop_get_slot": 520,
    "display_message": 1106,
}

CONSTANTS = {
    "itp_type_horse": 1,
    "itp_type_one_handed_wpn": 2,
    "itp_type_two_handed_wpn": 3,
    "itp_type_polearm": 4,
    "itp_type_arrows": 5,
    "itp_type_bolts": 6,
    "itp_type_shield": 7,
    "itp_type_bow": 8,
    "itp_type_crossbow": 9,
    "itp_type_thrown": 10,
    "ti_on_agent_killed_or_wounded": -26,
}


class CompileError(Exception):
    pass


class Compiler:
    def __init__(self, module_root: Path | None = None) -> None:
        self.locals: dict[str, int] = {}
        self.scripts = self._load_scripts(module_root) if module_root else {}
        self.globals = self._load_globals(module_root) if module_root else {}
        self.strings = self._load_strings(module_root) if module_root else {}

    def _load_scripts(self, module_root: Path) -> dict[str, int]:
        candidates = [
            module_root / "source_res" / "module_scripts.py",
            module_root / "module_scripts.py",
        ]
        for path in candidates:
            if path.exists():
                text = path.read_text(encoding="utf-8", errors="ignore")
                names = re.findall(r'^\("([^"]+)",', text, re.M)
                return {f"script_{name}": SCRIPT_BASE + i for i, name in enumerate(names)}
        return {}

    def _load_globals(self, module_root: Path) -> dict[str, int]:
        candidates = [
            module_root / "variables.txt",
            module_root / "source_res" / "variables.txt",
        ]
        for path in candidates:
            if path.exists():
                names = [line.strip() for line in path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
                return {f"${name}": GLOBAL_BASE + i for i, name in enumerate(names)}
        return {}

    def _load_strings(self, module_root: Path) -> dict[str, int]:
        candidates = [
            module_root / "source_res" / "module_strings.py",
            module_root / "module_strings.py",
            module_root / "strings.txt",
        ]
        for path in candidates:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            if path.name == "strings.txt":
                names = [line.split(maxsplit=1)[0] for line in text.splitlines()[2:] if line.strip()]
            else:
                names = [f"str_{name}" for name in re.findall(r'^\("([^"]+)",', text, re.M)]
            return {name: STRING_BASE + i for i, name in enumerate(names)}
        return {}

    def local_id(self, name: str) -> int:
        if name not in self.locals:
            self.locals[name] = LOCAL_BASE + len(self.locals)
        return self.locals[name]

    def value(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, str):
                return self.string_value(value)
            if isinstance(value, (int, float)):
                return value
            raise CompileError(f"unsupported constant: {value!r}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            value = self.value(node.operand)
            return -value
        if isinstance(node, ast.Name):
            return self.name_value(node.id)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return int(self.value(node.left)) | int(self.value(node.right))
        raise CompileError(f"unsupported expression: {ast.dump(node)}")

    def string_value(self, value: str) -> int:
        if value.startswith(":"):
            return self.local_id(value)
        if value.startswith("$"):
            if value in self.globals:
                return self.globals[value]
            raise CompileError(f"unknown global {value!r}; pass --module-root with variables.txt")
        if value.startswith("reg") and value[3:].isdigit():
            return REG_BASE + int(value[3:])
        if value in self.scripts:
            return self.scripts[value]
        if value in self.strings:
            return self.strings[value]
        if value.startswith("script_"):
            raise CompileError(f"unknown script id {value!r}; pass --module-root with source_res/module_scripts.py")
        if value.startswith("str_"):
            raise CompileError(f"unknown string id {value!r}; pass --module-root with source_res/module_strings.py or strings.txt")
        raise CompileError(f"unsupported quoted identifier {value!r}")

    def name_value(self, name: str) -> int:
        if name in FLAGS:
            return FLAGS[name]
        if name in OPS:
            return OPS[name]
        if name in CONSTANTS:
            return CONSTANTS[name]
        if name.startswith("reg") and name[3:].isdigit():
            return REG_BASE + int(name[3:])
        raise CompileError(f"unknown name {name!r}")

    def op_code(self, node: ast.AST) -> int:
        return int(self.value(node))

    def compile_op(self, node: ast.AST) -> list[str]:
        if not isinstance(node, ast.Tuple):
            code = self.op_code(node)
            return [str(code), "0"]
        if not node.elts:
            raise CompileError("operation must be a tuple")
        code = self.op_code(node.elts[0])
        args = [self.value(arg) for arg in node.elts[1:]]
        return [str(code), str(len(args)), *[fmt(arg) for arg in args]]

    def compile_ops(self, nodes: list[ast.AST]) -> str:
        out: list[str] = [str(len(nodes))]
        for node in nodes:
            out.extend(self.compile_op(node))
        return " ".join(out)

    def compile_trigger(self, node: ast.Tuple) -> str:
        if len(node.elts) != 5:
            raise CompileError("mission trigger tuple must have 5 elements")
        trigger_id = self.value(node.elts[0])
        delay = self.value(node.elts[1])
        rearm = self.value(node.elts[2])
        conditions = as_list(node.elts[3], "conditions")
        consequences = as_list(node.elts[4], "consequences")
        return " ".join([
            f"{float(trigger_id):.6f}",
            f"{float(delay):.6f}",
            f"{float(rearm):.6f}",
            self.compile_ops(conditions),
            self.compile_ops(consequences),
        ])


def fmt(value: int | float) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def as_list(node: ast.AST, label: str) -> list[ast.AST]:
    if not isinstance(node, ast.List):
        raise CompileError(f"{label} must be a list")
    return node.elts


def parse_snippet(text: str) -> list[ast.AST]:
    wrappers = [f"[{text}\n]", text]
    last_error: SyntaxError | None = None
    for wrapped in wrappers:
        try:
            tree = ast.parse(wrapped, mode="eval")
            if isinstance(tree.body, ast.List):
                return tree.body.elts
            return [tree.body]
        except SyntaxError as exc:
            last_error = exc
    raise CompileError(f"syntax error: {last_error}")


def compile_text(text: str, module_root: Path | None = None, mode: str = "auto") -> str:
    compiler = Compiler(module_root)
    nodes = parse_snippet(text)
    if mode == "trigger" or (mode == "auto" and len(nodes) == 1 and isinstance(nodes[0], ast.Tuple) and len(nodes[0].elts) == 5):
        node = nodes[0]
        if not isinstance(node, ast.Tuple):
            raise CompileError("trigger mode requires one tuple")
        return compiler.compile_trigger(node)
    return compiler.compile_ops(nodes)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Compile a Warband module-system snippet to txt opcode.")
    parser.add_argument("file", nargs="?", help="Snippet file. Reads stdin when omitted.")
    parser.add_argument("--module-root", type=Path, help="Module root containing source_res/module_scripts.py for script ids.")
    parser.add_argument("--mode", choices=["auto", "ops", "trigger"], default="auto")
    args = parser.parse_args(argv)

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    try:
        print(compile_text(text, args.module_root, args.mode))
    except CompileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
