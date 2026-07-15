# Diagnosis Playbook

## First Split

Classify the failure before changing code:

1. Shell syntax: parse errors, heredoc failures, variable expansion surprises.
2. Path or encoding: file exists but command cannot find it, mojibake, spaces, Chinese characters.
3. Environment: missing `PATH`, `CUDA_HOME`, `GDAL_DATA`, `PROJ_LIB`, `PYTHONPATH`, or activated environment.
4. Runtime dependency: DLL entry point, missing DLL, mixed toolchain, wrong Visual C++ runtime.
5. Tool usage: wrong arguments, wrong working directory, wrong shell.
6. Program logic: executable starts correctly but its own code fails.

## Common Windows Failures

| Symptom | Likely cause | Check | Fix |
| --- | --- | --- | --- |
| `The '<' operator is reserved` | Bash heredoc pasted into PowerShell | Look for `<<` | Use a script file, PowerShell here-string, or `python -c` |
| `Variable reference is not valid` | PowerShell parsed `$name:` or `$name_suffix` unexpectedly | Look for `$` inside double quotes | Use `${name}` or single quotes |
| Command works in Git Bash but not Codex | Codex command execution is wrapped by PowerShell on Windows | Re-check actual shell and quoting | Write PowerShell-native invocation or call `bash.exe -lc` explicitly |
| File path exists but tool cannot open it | Spaces, Chinese characters, or wrong path style | Test `Test-Path -LiteralPath` and echo exact argv | Use `-LiteralPath`; for native exe use argument array |
| Text is garbled | Wrong terminal or file encoding | Read with explicit encoding | Use UTF-8 or the source encoding; do not analyze mojibake |
| Chinese path works in PowerShell but not native exe | Native tool does not support wide-character argv or receives mis-encoded string | Try ASCII temp path and inspect exact argv | Prefer tools with Unicode argv support; otherwise stage files in an ASCII path and preserve mapping |
| `proj.db` not found | PROJ search path missing or mismatched runtime | Check `PROJ_LIB`, `PROJ_DATA`, `GDAL_DATA`, executable directory | Set env vars to the matching runtime's `share` directory |
| `The specified procedure could not be found` | DLL version mismatch | Inspect loaded directory and dependency exports | Use one coherent runtime bundle; remove mixed DLLs |
| Tool returns no output and nonzero exit | Missing runtime or GUI subsystem error | Check `$LASTEXITCODE`; run from same directory; inspect stderr | Run `--help` after fixing DLL/PATH |
| `&&` behaves unexpectedly | Windows PowerShell 5.1 vs PowerShell 7 difference | Check `$PSVersionTable.PSVersion` | Use separate commands or explicit `if ($LASTEXITCODE -eq 0)` |
| `where` returns wrong tool | PowerShell alias or PATH order | Use `where.exe` and `Get-Command` | Pin the full executable path |

## Runtime Dependency Checks

Use these in order:

```powershell
Get-Command tool.exe -ErrorAction SilentlyContinue
where.exe tool.exe
$env:PATH -split ';'
```

For a portable executable:

```powershell
Push-Location -LiteralPath $ExeDir
try {
  & .\tool.exe --help
  $code = $LASTEXITCODE
} finally {
  Pop-Location
}
if ($code -ne 0) { throw "smoke test failed: $code" }
```

For suspected DLL mismatch, prefer dependency export/import checks over copying DLLs by guess. If Visual Studio tools are available, use `dumpbin /dependents` and `dumpbin /imports`. Otherwise, check directory provenance and replace the whole runtime bundle from one source.

## Before Large Runs

Run these before full batch or long jobs:

1. `--help` or `--version`.
2. One tiny input or one scene/method.
3. Output existence and nonzero size check.
4. Log keyword check that proves the intended branch ran.
5. Exit code check.
