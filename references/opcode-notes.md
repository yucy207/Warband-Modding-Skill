# Warband Txt Opcode Notes

Use this reference when the user asks to compile or inspect a Warband module-system snippet as txt numbers.

## Local Variables

Local variables begin at:

```txt
1224979098644774912
```

Then increment by source encounter order:

```txt
:dead_agent     1224979098644774912
:killer_agent   1224979098644774913
:player_agent   1224979098644774914
```

Registers start at `72057594037927936`.

Global variables from `variables.txt` begin at:

```txt
144115188075855872
```

Then increment by line order in `variables.txt`. For example, line index `1803` compiles to `144115188075857675`.

Normal strings from `strings.txt` begin at:

```txt
216172782113783808
```

Then increment by string record order. Appending one string to a file with 5931 existing records gives the new string id `216172782113789739`.

## Common Operation Encodings

These were verified against compiler output in the kill-heal workflow:

```txt
store_trigger_param_1      2071
store_trigger_param_2      2072
eq                         31
ge                         30
lt                         2147483678
neg|eq                     2147483679
this_or_next|eq            1073741855
try_begin                  4 0
else_try                   5 0
try_end                    3 0
try_for_range              6
try_for_agents             12
call_script                1
store_script_param         23
agent_is_human             1704
agent_is_alive             1702
agent_is_ally              1706
neg|agent_is_ally          2147485354
agent_get_horse            1714
get_player_agent_no        1700
agent_get_troop_id         1718
agent_get_wielded_item     1726
agent_set_division         1783
agent_get_item_slot        1804
agent_get_item_cur_ammo    1977
store_agent_hit_points     1720
agent_set_hit_points       1721
item_get_type              1570
store_character_level      2171
troop_get_slot             520
display_message            1106
store_sub                  2121
val_add                    2105
val_mul                    2107
val_div                    2108
val_min                    2110
val_max                    2111
```

Important: `ge` is `30`, while `lt` compiles as `neg|ge`, `2147483678`. Do not reverse these.

## Item Type Values

For ranged weapon checks:

```txt
itp_type_bow        8
itp_type_crossbow   9
itp_type_thrown     10
```

## Mission Trigger Snippet

This source:

```python
(ti_on_agent_killed_or_wounded, 0.000000, 0.000000,
[
],
[
    (call_script, "script_player_heal_on_kill"),
]),
```

compiles like:

```txt
-26.000000 0.000000 0.000000  0  1 1 1 <script-id>
```

`<script-id>` is `936748722493063168 + script_index`. Recompute it after inserting scripts.

Append new scripts to the end of `module_scripts.py` when partial txt compatibility matters. Inserting a script in the middle changes every later script id; appending preserves all existing script ids and only creates one new id at the end.

## Kill-Heal Action Block Example

Current kill-heal uses 5% at level 10 to 25% at level 50, keeps ranged weapon healing at half effect, and displays the absolute HP restored in red with `display_message`.

For this older source body shape:

```python
(store_trigger_param_1, ":dead_agent"),
(store_trigger_param_2, ":killer_agent"),
(ge, ":dead_agent", 0),
(ge, ":killer_agent", 0),
(agent_is_human, ":dead_agent"),
(neg|agent_is_ally, ":dead_agent"),
(get_player_agent_no, ":player_agent"),
(eq, ":killer_agent", ":player_agent"),
(neg|eq, ":dead_agent", ":player_agent"),
(agent_is_alive, ":player_agent"),
(store_agent_hit_points, ":player_hp", ":player_agent", 0),
(lt, ":player_hp", 75),
(agent_get_troop_id, ":dead_troop", ":dead_agent"),
(store_character_level, ":dead_level", ":dead_troop"),
(val_max, ":dead_level", 10),
(val_min, ":dead_level", 50),
(store_sub, ":heal_percent", ":dead_level", 10),
(val_mul, ":heal_percent", 8),
(val_div, ":heal_percent", 40),
(val_add, ":heal_percent", 2),
(agent_get_wielded_item, ":player_weapon", ":player_agent", 0),
(try_begin),
    (ge, ":player_weapon", 0),
    (item_get_type, ":weapon_type", ":player_weapon"),
    (this_or_next|eq, ":weapon_type", itp_type_bow),
    (this_or_next|eq, ":weapon_type", itp_type_crossbow),
    (eq, ":weapon_type", itp_type_thrown),
    (val_div, ":heal_percent", 2),
(try_end),
(val_add, ":player_hp", ":heal_percent"),
(val_min, ":player_hp", 100),
(agent_set_hit_points, ":player_agent", ":player_hp", 0),
```

the compiler output body is:

```txt
32 2071 1 1224979098644774912 2072 1 1224979098644774913 30 2 1224979098644774912 0 30 2 1224979098644774913 0 1704 1 1224979098644774912 2147485354 1 1224979098644774912 1700 1 1224979098644774914 31 2 1224979098644774913 1224979098644774914 2147483679 2 1224979098644774912 1224979098644774914 1702 1 1224979098644774914 1720 3 1224979098644774915 1224979098644774914 0 2147483678 2 1224979098644774915 75 1718 2 1224979098644774916 1224979098644774912 2171 2 1224979098644774917 1224979098644774916 2111 2 1224979098644774917 10 2110 2 1224979098644774917 50 2121 3 1224979098644774918 1224979098644774917 10 2107 2 1224979098644774918 8 2108 2 1224979098644774918 40 2105 2 1224979098644774918 2 1726 3 1224979098644774919 1224979098644774914 0 4 0 30 2 1224979098644774919 0 1570 2 1224979098644774920 1224979098644774919 1073741855 2 1224979098644774920 8 1073741855 2 1224979098644774920 9 31 2 1224979098644774920 10 2108 2 1224979098644774918 2 3 0 2105 2 1224979098644774915 1224979098644774918 2110 2 1224979098644774915 100 1721 3 1224979098644774914 1224979098644774915 0
```

Use this as a historical regression example when hand-checking similar snippets. The current regression body lives in `scripts/compile_learning.py` and includes the absolute HP delta message.

## Compile Learning Regression

Run:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_learning.py --module-root /path/to/module
python3 /home/yucy/.codex/skills/warband-modding/scripts/compile_learning.py --module-root /path/to/module --sample-count 100
```

The learning test compares:

- `source_res/module_scripts.py` script body against existing `scripts.txt` for `store_intelligence_attribute_level`.
- Current `player_heal_on_kill` source body against the known compiler output.
- The `ti_on_agent_killed_or_wounded` trigger calling `script_player_heal_on_kill`.
- A deterministic sample of supported source operations against existing `scripts.txt`; `--sample-count 100` requires 100 passing pairs.

Use it after changing opcode mappings in `compile_snippet.py`.

When comparing source against old txt after adding a new script, skip `call_script` samples: script ids are table-index based and shift until `scripts.txt` is regenerated.

## Build Learning Regression

Run:

```bash
python3 /home/yucy/.codex/skills/warband-modding/scripts/build_learning.py --module-root /path/to/module
```

This validates complete `scripts.txt` structure:

- Header: `scriptsfile version 1`
- Count line: number of script records.
- Record header: `script_name -1`
- Record body: operation count followed by opcode stream.
- Source/txt script ordering.
- Append-only new scripts and their ids.

For an appended script, the txt-side patch is structurally:

```txt
<old_count + 1>
...
new_script_name -1
 <compiled_operation_count_and_body>
```

Do not insert new scripts in the middle when producing partial txt patches; that changes ids for later scripts.

## Mission Templates Partial Patch

When inserting one compiled trigger into `mission_templates.txt`, update the per-template trigger count as well as adding the trigger line. The file can encode entry points in two common ways:

```txt
0 <trigger_count>
```

for templates with no entry points, or:

```txt
<entry_count> <first_entry_point...>
...
<trigger_count>
```

for templates with one or more entry points. Count the existing entry point lines before reading or changing the trigger count.
