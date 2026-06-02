# MBCodeEditor

`MBCodeEditor.exe` is a redistributable third-party Mount&Blade: Warband code editor/decompiler tool bundled with this skill for convenience.

## Purpose

- Inspect Warband module txt files.
- Generate or inspect decompiled `source_res` style Python files.
- Cross-check compiled txt opcode behavior when the normal module system source is unavailable.

## Bundled File

- File: `MBCodeEditor.exe`
- Size: about 2.3 MiB
- SHA256: `6d7e9fa3f93ed43c76c33f689b92b98ceeb28504fdc1ddd588f0ede8e711daa2`

## Source

Copied from the local module directory:

```text
D:\steam\steamapps\common\MountBlade Warband\Modules\pendro sub 260529\MBCodeEditor.exe
```

The maintainer has confirmed this tool may be redistributed with the skill.

## Usage Notes

On Windows, run `MBCodeEditor.exe` directly.

From WSL, invoke it through the Windows path or copy it into a Windows-accessible directory. Treat generated `source_res` output as decompiled source: inspect changes carefully and validate generated txt with the skill's learning scripts before patching a live module.
