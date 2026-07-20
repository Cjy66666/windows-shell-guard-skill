# Windows Shell Guard Skill

`windows-shell-guard` is a Codex skill for preventing fragile Windows shell failures before running PowerShell, CMD, WSL, Bash, Python, CMake/MSBuild, SSH, GDAL/PROJ, or DLL-dependent commands.

It is designed for Windows-heavy coding and research workflows where many failures are caused by shell syntax, quoting, path encoding, environment variables, or runtime dependency mismatches rather than the program logic itself.

## What It Catches

- Bash syntax accidentally pasted into PowerShell, such as `python - <<'PY'`, `export`, `source`, or `VAR=value cmd`.
- PowerShell variable-boundary problems, such as `$Drive:` or `$Name_suffix` inside double-quoted strings.
- Fragile command chaining with `&&` across PowerShell hosts.
- Cross-shell filesystem operations that can make deletion or moving unsafe.
- Chinese/non-ASCII paths, whitespace-containing paths, and missing explicit encoding when reading text.
- GDAL/PROJ runtime setup risks, including `proj.db`, `GDAL_DATA`, `PROJ_LIB`, and DLL bundle mismatches.
- CMake/MSBuild/MSVC runtime risks and "compiled but does not run" diagnosis entry points.

## Repository Layout

```text
.
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   ├── command-patterns.md
│   └── diagnosis-playbook.md
├── scripts/
│   └── shell_guard_preflight.py
└── tests/
    └── test_shell_guard_preflight.py
```

## Install

Copy this folder into your Codex skills directory:

```powershell
$SkillsRoot = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $HOME '.codex/skills' }
Copy-Item -Recurse -Force -LiteralPath . -Destination (Join-Path $SkillsRoot 'windows-shell-guard')
```

Then trigger it in Codex with prompts such as:

```text
Use $windows-shell-guard to check this PowerShell command before running it.
```

For stronger default behavior, add a short global rule to your Codex `AGENTS.md`:

```text
On Windows, apply the $windows-shell-guard skill before shell work. For fragile commands involving quoting, redirection, environment variables, PowerShell/CMD/WSL boundaries, Chinese or space-containing paths, destructive operations, DLL/runtime setup, GDAL/PROJ, CMake/MSBuild, SSH, or long-running launches, run the skill's preflight script before executing the command and treat ERROR findings as blockers.
```

## Preflight Usage

Always invoke the checker through Python. Do not execute `.\scripts\shell_guard_preflight.py` directly on Windows, because `.py` file associations may open an editor instead of running Python.

Inspect a PowerShell command:

```powershell
python -B .\scripts\shell_guard_preflight.py --shell powershell --command "python - <<'PY'`nprint(1)`nPY" --strict
```

Expected result:

```text
[ERROR] PS_BASH_HEREDOC: Bash heredoc syntax was found in a PowerShell command.
  Fix: Use a script file, PowerShell here-string, or python -c; do not use << in PowerShell.
```

Inspect a Chinese path and encoding-sensitive read:

```powershell
python -B .\scripts\shell_guard_preflight.py --shell powershell --command "Get-Content -Raw -LiteralPath 'D:\中文 路径\说明.txt'"
```

This should report informational findings about non-ASCII command content and missing explicit encoding.

## Validate

Run the local behavior tests:

```powershell
python -B .\tests\test_shell_guard_preflight.py
```

Expected result:

```text
all shell guard behavior tests passed
```

If the skill-creator validator is available, also run:

```powershell
python -B <path-to-skill-creator>\scripts\quick_validate.py .
```

## Design Notes

This skill intentionally acts as a preflight guard, not as a command runner. It does not execute the command being inspected. It reports obvious hazards so the agent can rewrite the command before touching files or launching long-running work.

The skill is biased toward low false negatives for expensive or risky Windows workflows. `ERROR` findings should block execution; `WARN` and `INFO` findings are prompts to inspect the command shape, not automatic failures.
