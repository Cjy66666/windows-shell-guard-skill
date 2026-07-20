# Command Patterns

## PowerShell File Paths

Use `-LiteralPath` for local filesystem paths:

```powershell
Get-Content -Raw -LiteralPath $Path
Copy-Item -LiteralPath $Source -Destination $Dest -Force
Remove-Item -LiteralPath $Target -Recurse -Force
```

Before recursive delete or move, resolve and inspect the absolute target:

```powershell
$Root = (Resolve-Path -LiteralPath $ExpectedRoot).Path
$Target = (Resolve-Path -LiteralPath $Candidate).Path
if (-not $Target.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
  throw "Target is outside expected root: $Target"
}
```

## PowerShell Quoting

Use single quotes for literal strings:

```powershell
$Json = '{"name":"$literal","enabled":true}'
```

Use `${var}` when a variable touches punctuation or letters:

```powershell
"${Drive}:`n$Path"
"${Name}_suffix"
```

Use a here-string only when PowerShell is the shell:

```powershell
$Text = @'
literal text with $ and "quotes"
'@
```

Do not paste Bash heredocs into PowerShell. For multi-line Python, prefer a script file or `python -c` for small probes.

## Native Executables From PowerShell

Use the call operator with an argument array when paths or quotes are complex:

```powershell
$Exe = 'C:\Tools\tool.exe'
$Args = @('--input', $InputPath, '--output', $OutputPath, '--flag')
& $Exe @Args
if ($LASTEXITCODE -ne 0) { throw "tool.exe failed with $LASTEXITCODE" }
```

Avoid building one giant quoted string unless the target really requires shell parsing.

## Preflight Checker Invocation

On Windows, call the preflight checker through Python rather than executing the `.py` path directly:

```powershell
$Guard = '<skill-dir>\scripts\shell_guard_preflight.py'
$Command = "& 'C:\Tools\tool.exe' --input 'C:\data\input.tif'"
& python -B $Guard --shell powershell --command $Command --strict
```

If `python` is not the intended interpreter, use an explicit interpreter path or `py -3`.
Do not run `& '<skill-dir>\scripts\shell_guard_preflight.py' ...`; direct `.py` execution can follow Windows file associations and open an editor such as VS Code.

## Environment Variables

For the current PowerShell process:

```powershell
$env:PROJ_LIB = $ProjDir
$env:GDAL_DATA = $GdalDataDir
```

For a single native command, set the variables in PowerShell before calling it, then restore if needed:

```powershell
$oldPath = $env:PATH
try {
  $env:PATH = "$DllDir;$env:PATH"
  & $Exe @Args
} finally {
  $env:PATH = $oldPath
}
```

Use persistent environment changes only when the user asks for a machine-level setup.

## CMD and WSL Boundaries

Use CMD only for commands that require CMD syntax:

```powershell
cmd.exe /d /c "where cl.exe"
```

Use WSL path conversion when crossing Windows/Linux boundaries:

```powershell
wsl.exe wslpath -a "C:\data\input.tif"
```

Do not pass `/mnt/c/...` paths to Windows native tools unless that tool explicitly accepts them.

## Encoding

When reading text that may contain Chinese paths or prose:

```powershell
Get-Content -Raw -Encoding UTF8 -LiteralPath $Path
```

For Python:

```python
Path(path).read_text(encoding="utf-8", errors="replace")
```

For PowerShell console output before running probes:

```powershell
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
```
