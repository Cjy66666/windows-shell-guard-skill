---
name: windows-shell-guard
description: Prevent fragile Windows command failures before running PowerShell, CMD, WSL, Bash, Python, CMake/MSBuild, SSH, GDAL/PROJ, DLL-dependent tools, or scripts with Windows paths. Use when a task involves Windows shell execution, quoting or variable expansion, Chinese or space-containing paths, environment variables, PATH/DLL/runtime issues, PowerShell-vs-Bash syntax, heredocs, command chaining, destructive filesystem operations, long-running command launch, or "compiled but does not run" diagnosis.
---

# Windows Shell Guard

Use this skill before running fragile commands on Windows. Treat it as a preflight layer: identify the active shell, choose the safest invocation pattern, check paths and environment, then run the smallest command that proves the setup is correct.

## Workflow

1. Identify the shell and boundary.
   - Confirm whether the command is PowerShell, CMD, WSL/Linux shell, Git Bash, or a native executable launched from PowerShell.
   - Do not translate syntax by habit. Bash heredocs, `export`, `source`, `VAR=value cmd`, and many Unix pipelines are not PowerShell syntax.
   - For destructive file operations, stay in one shell end-to-end and use native path-safe commands.

2. Run static preflight for nontrivial commands.
   - Use `scripts/shell_guard_preflight.py` when a command contains nested quoting, shell redirection, environment setup, path-heavy arguments, `cmd /c`, WSL, DLL/runtime setup, or destructive verbs.
   - Pass the intended shell with `--shell powershell`, `--shell cmd`, `--shell wsl`, or `--shell bash`.
   - Treat `ERROR` findings as blockers; fix the command before execution.

3. Use the safe PowerShell defaults.
   - Use `-LiteralPath` for file cmdlets.
   - Use single quotes for literal strings, especially strings containing `$`, `\`, `{}`, or JSON.
   - Use `${name}` when interpolating variables next to punctuation or letters.
   - Launch native executables with the call operator and an argument array for complex paths: `& $Exe @Args`.
   - Prefer separate tool calls for setup, execution, and inspection when output clarity matters.

4. Verify runtime before full work.
   - Run `--help`, `--version`, or one tiny smoke test before large jobs.
   - For compiled Windows tools, verify DLL loading from the intended directory before assuming source logic is wrong.
   - For GDAL/PROJ tools, verify `proj.db`, `GDAL_DATA`, `PROJ_LIB` or `PROJ_DATA`, and DLL versions as a runtime group.

5. Record the command shape when fixing failures.
   - Save the failing command, shell, exit code, and first meaningful error.
   - Classify failures as shell syntax, path/encoding, environment, runtime dependency, tool usage, or program logic.

## Resource Loading

- Read `references/command-patterns.md` when constructing or translating commands.
- Read `references/diagnosis-playbook.md` when a command fails, exits silently, shows garbled text, cannot find DLLs, cannot find `proj.db`, or behaves differently across PowerShell/CMD/WSL.
- Run `scripts/shell_guard_preflight.py --help` to inspect available checks.

## Hard Rules

- Do not use Bash heredoc syntax such as `python - <<'PY'` in PowerShell.
- Do not compose recursive delete or move operations across shells.
- Do not assume Codex Desktop's visible terminal shell is the exact shell used for command execution on Windows.
- Do not copy random DLLs from multiple toolchains into one executable directory without checking dependency compatibility.
- Do not treat mojibake as source text; reread with explicit UTF-8 or the file's real encoding.
