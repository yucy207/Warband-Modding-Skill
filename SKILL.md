---
name: warband-modding
description: Mount&Blade Warband module system and decompiled source workflow for implementing mod features, editing source_res/module_*.py files, avoiding generated txt churn, compiling or hand-checking mission/script txt opcode snippets, and validating Warband operations such as mission triggers, call_script ids, local variables, neg|/this_or_next| flags, agent kill triggers, troop levels, hit points, and item type checks.
---

# Warband Modding

Use this skill for Warband mod work where the user asks to implement or inspect behavior in module source, then optionally compare or output generated txt opcode.

## Workflow

1. Locate the module root and source directory. Prefer `source_res/module_*.py` as the editable source when the user says not to touch txt files.
2. Inspect local patterns with `rg` before editing. Warband mods often contain decompiled source without `header_*.py` or `process_*.py`; rely on nearby compiled txt only for verification, not as the first edit target.
3. Preserve unrelated dirty files. Do not edit generated `.txt` files unless the user explicitly asks for txt output or direct txt patching.
4. Implement the source change conservatively. Add reusable scripts in `module_scripts.py` when logic must be called from several mission templates.
5. Attach mission behavior with the narrowest trigger that works. For kill/wound behavior, use `ti_on_agent_killed_or_wounded`; remember `store_trigger_param_1` is victim agent, `store_trigger_param_2` is killer agent, and `store_trigger_param_3` is wound/kill state when needed.
6. Validate syntax without writing pyc:

```bash
python3 -c "compile(open('source_res/module_scripts.py', encoding='utf-8').read(), 'source_res/module_scripts.py', 'exec')"
```

7. If the user asks to compile a snippet to txt, first say whether it is compiler output, inferred output, or a manual hand-check. Prefer actual compiler output when available.

## Source Rules

- Treat `source_res` as source of truth when the user asks for source edits.
- Do not update `menus.txt`, `scripts.txt`, `mission_templates.txt`, or other generated txt files unless explicitly requested.
- If only decompiled files are present, a full module-system compile may not be available. In that case, syntax-check source and hand-check opcode only for the requested snippet.
- When adding a new script, append it at the end of `module_scripts.py` unless there is a strong reason not to. Script ids in txt use the script id base plus the script index, so inserting in the middle shifts every later script id and breaks partial txt patching against old generated files. If a script must be inserted in the middle, regenerate all txt files that reference scripts.

## Bundled Tools

This skill may include redistributable third-party tools under `tools/`.

- `tools/mb-code-editor/MBCodeEditor.exe`: Warband code editor/decompiler tool used to inspect or generate decompiled `source_res` files from module txt files. See `tools/mb-code-editor/README.md` for source, checksum, and usage notes.
- Prefer skill scripts for deterministic snippet checks. Use bundled GUI/Windows tools only when decompilation or manual inspection is needed.

## Txt Opcode Checks

Use `scripts/compile_snippet.py` before hand-compiling opcode. It supports operation-list snippets and simple mission trigger tuples:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_snippet.py snippet.py
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_snippet.py snippet.py --module-root /path/to/module
```

Pass `--module-root` when the snippet contains `call_script` so script ids can be computed from `source_res/module_scripts.py`.

Read [references/opcode-notes.md](references/opcode-notes.md) when reviewing compiler output or extending the snippet compiler. It includes local variable numbering, common operations, flag math, and the exact mistakes to avoid from the kill-heal workflow.

## Compile Learning

When adding or correcting opcode mappings, run compile learning against the current module root. This builds regression tests from `source_res` source and the existing txt numeric output:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_learning.py --module-root /path/to/module
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_learning.py --module-root /path/to/module --sample-count 100
```

Use this loop:

1. Add or change the mapping in `scripts/compile_snippet.py`.
2. Run `compile_learning.py` against the active Warband module.
3. If a test fails, inspect the source snippet and the matching txt body, then update only the missing or wrong opcode/constant mapping.
4. Repeat until all compile learning tests pass.
5. Add the verified mapping or regression case to [references/opcode-notes.md](references/opcode-notes.md) when it is broadly useful.

Current compile learning coverage includes a real `source_res/module_scripts.py` to `scripts.txt` comparison for `store_intelligence_attribute_level`, the current `player_heal_on_kill` script body, the `ti_on_agent_killed_or_wounded` trigger that calls it, and an automatic source/txt operation sampler. Use `--sample-count 100` to require 100 passing source/txt operation pairs. The sampler skips `call_script` pairs when comparing against an existing txt set because local source may contain newly inserted scripts that shift script ids until txt is regenerated.

## Build Learning

When learning or validating full py-to-txt file changes, run build learning. This checks file-level structure, not just opcode blocks:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/build_learning.py --module-root /path/to/module
```

Use this when adding a script or preparing a txt patch. It verifies:

- `scripts.txt` header text.
- script count field against actual record count.
- source script order against existing `scripts.txt` record order.
- append-only source scripts and the rebuilt count field.
- full script records (`name -1` plus opcode body).
- operation count fields inside script bodies.
- appended script id calculation.

For partial txt compatibility, prefer append-only script changes. If `source_res/module_scripts.py` has one appended script and existing `scripts.txt` is otherwise unchanged, the expected txt change is: increment the count line by one and append a full `script_name -1` record with its compiled body. Existing script records and ids should remain unchanged.

## Txt Implementation Flow

When the user asks to apply a verified source change into generated txt files:

1. Re-run learning first:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_learning.py --module-root /path/to/module --sample-count 100
python3 /home/yucy/.codex/skills/warband-modding/scripts/build_learning.py --module-root /path/to/module
```

2. Patch only the txt files required for the requested feature. Preserve the existing line ending style.
3. For appended scripts in `scripts.txt`, increment the count line and append the full record:

```txt
script_name -1
 <operation_count_and_body>
```

4. For mission trigger insertions in `mission_templates.txt`, parse the mission template structure instead of doing blind text replacement. Entry points may appear as either `0 <trigger_count>` for zero entry points, or as `<entry_count> <first_entry...>` with the trigger count on the line after the final entry point. Increment the trigger count for every template that receives the new trigger.
5. After patching, validate record counts, operation counts, target trigger counts, and exact occurrence counts for the inserted script id or trigger line.
6. If the module root is a git repository, committing the finished txt patch is the standard final step: run `git status --short`, stage only the relevant tracked/generated files for this feature, and commit with a concise message. Leave unrelated dirty files unstaged. If the user explicitly says not to commit, stop after validation instead.

## Kill-Heal Pattern

For player-on-kill healing:

- Filter horses with `agent_is_human` on the victim.
- Match player kills with `get_player_agent_no` and `eq` against `store_trigger_param_2`.
- Use `store_agent_hit_points` / `agent_set_hit_points` with flag `0` for percentage HP. Use `store_agent_hit_points` with flag `1` before and after healing when a display message needs the concrete absolute HP amount restored.
- Estimate target level with `agent_get_troop_id` then `store_character_level`.
- Clip levels with `val_max` and `val_min`.
- Scale percentages with integer arithmetic; for 5% at level 10 to 25% at level 50, use `(level - 10) * 20 / 40 + 5`.
- For remote/ranged half effect, `ti_on_agent_killed_or_wounded` does not provide the damage weapon id. If needed, approximate with `agent_get_wielded_item` and `item_get_type` at trigger time.
- For a healing message with a concrete amount, assign the absolute HP delta to `reg0` and call `display_message` with a normal `str_...` string and color, for example red `0xFF0000`.

## Communication

When reporting results, distinguish:

- Source changed and syntax checked.
- Txt not touched.
- Txt snippet manually compiled for inspection.
- Compiler-generated txt verified.

If manual opcode differs from compiler output, trust the compiler and correct the notes or reasoning.
