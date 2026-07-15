#!/usr/bin/env python3
"""Static preflight for fragile Windows shell commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Finding:
    level: str
    code: str
    message: str
    fix: str


def add(findings: list[Finding], level: str, code: str, message: str, fix: str) -> None:
    findings.append(Finding(level=level, code=code, message=message, fix=fix))


def contains_bash_heredoc(command: str) -> bool:
    return bool(re.search(r"<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?", command))


def has_unix_env_prefix(command: str) -> bool:
    return bool(re.search(r"(^|\s)[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+\S+", command))


def has_probable_unquoted_space_path(command: str) -> bool:
    drive_path = re.compile(r"(?<!['\"])\b[A-Za-z]:\\[^'\"\r\n]*\s+[^'\"\r\n]*(?!['\"])")
    return bool(drive_path.search(command))


def powershell_checks(command: str, findings: list[Finding]) -> None:
    if contains_bash_heredoc(command):
        add(
            findings,
            "ERROR",
            "PS_BASH_HEREDOC",
            "Bash heredoc syntax was found in a PowerShell command.",
            "Use a script file, PowerShell here-string, or python -c; do not use << in PowerShell.",
        )
    if re.search(r"(^|\s)export\s+[A-Za-z_]", command):
        add(
            findings,
            "ERROR",
            "PS_EXPORT",
            "Bash export syntax was found in a PowerShell command.",
            "Use $env:NAME = 'value' before launching the native command.",
        )
    if re.search(r"(^|\s)source\s+\S+", command):
        add(
            findings,
            "ERROR",
            "PS_SOURCE",
            "Bash source syntax was found in a PowerShell command.",
            "Use the PowerShell activation script or call bash.exe -lc explicitly.",
        )
    if has_unix_env_prefix(command):
        add(
            findings,
            "WARN",
            "PS_UNIX_ENV_PREFIX",
            "A VAR=value command prefix may be Unix shell syntax, not PowerShell.",
            "Set $env:VAR first, then call the command.",
        )
    if "&&" in command:
        add(
            findings,
            "WARN",
            "PS_AND_IF",
            "The command uses &&, which requires PowerShell 7+ and can be brittle across hosts.",
            "Prefer separate commands or explicit exit-code checks.",
        )
    if re.search(r"\"\$[A-Za-z_][A-Za-z0-9_]*[:A-Za-z0-9_]", command):
        add(
            findings,
            "WARN",
            "PS_VARIABLE_BOUNDARY",
            "A double-quoted variable is adjacent to punctuation or letters.",
            "Use ${name} for interpolation boundaries or single quotes for literals.",
        )
    if re.search(r"\|\s*cmd(\.exe)?\s+/[cd]\b", command, re.IGNORECASE):
        add(
            findings,
            "WARN",
            "PS_PIPE_TO_CMD",
            "PowerShell output is piped into cmd.exe.",
            "Avoid cross-shell pipelines for file operations; keep one shell end-to-end.",
        )
    if re.search(r"\b(del|erase|rmdir|rd)\b", command, re.IGNORECASE) and re.search(
        r"Get-ChildItem|gci|ls\s", command, re.IGNORECASE
    ):
        add(
            findings,
            "ERROR",
            "PS_CROSS_SHELL_DELETE",
            "The command appears to enumerate in PowerShell and delete through CMD-style verbs.",
            "Use PowerShell Remove-Item with verified resolved paths.",
        )


def generic_checks(command: str, shell: str, findings: list[Finding]) -> None:
    if any(ord(ch) > 127 for ch in command):
        add(
            findings,
            "INFO",
            "COMMAND_HAS_NON_ASCII",
            "The command contains non-ASCII characters, which may include Chinese paths or text.",
            "Use PowerShell -LiteralPath, explicit UTF-8 when reading text, and verify native tools support wide-character paths.",
        )
    if has_probable_unquoted_space_path(command):
        add(
            findings,
            "WARN",
            "UNQUOTED_SPACE_PATH",
            "A Windows path with spaces may be unquoted or embedded in a fragile string.",
            "Use -LiteralPath for PowerShell cmdlets or an argument array for native executables.",
        )
    if re.search(r"\brm\s+-rf\b", command) and shell in {"powershell", "cmd"}:
        add(
            findings,
            "ERROR",
            "UNIX_DELETE_IN_WINDOWS_SHELL",
            "Unix recursive delete syntax was found in a Windows shell command.",
            "Use shell-native deletion after verifying the resolved target path.",
        )
    if re.search(r"\b(find|sort)\b", command) and shell == "powershell":
        add(
            findings,
            "INFO",
            "AMBIGUOUS_NATIVE_TOOL",
            "A command name may resolve differently on Windows than on Unix.",
            "Use Get-Command and pin the full executable path when the exact tool matters.",
        )
    if re.search(r"\b(gdal|ogr|proj)\w*(\.exe)?\b", command, re.IGNORECASE):
        add(
            findings,
            "INFO",
            "GDAL_PROJ_RUNTIME",
            "GDAL/PROJ command detected.",
            "Before large runs, verify proj.db, GDAL_DATA/PROJ_LIB/PROJ_DATA, PATH order, and --help.",
        )
    if re.search(r"\b(msbuild|cmake|cl|dumpbin)\b", command, re.IGNORECASE):
        add(
            findings,
            "INFO",
            "MSVC_TOOLCHAIN",
            "MSVC/CMake command detected.",
            "Verify the developer environment, generator, architecture, and runtime DLL provenance.",
        )
    if re.search(r"\bGet-Content\b", command, re.IGNORECASE) and "-Encoding" not in command:
        add(
            findings,
            "INFO",
            "GET_CONTENT_ENCODING",
            "Get-Content is used without an explicit encoding.",
            "When reading Chinese text or files with uncertain encoding, add -Encoding UTF8 or the known source encoding.",
        )


def path_checks(paths: list[str], findings: list[Finding]) -> None:
    for raw in paths:
        p = Path(raw)
        if not p.exists():
            add(
                findings,
                "WARN",
                "PATH_NOT_FOUND",
                f"Path does not exist: {raw}",
                "Check path style, current machine, drive mapping, quoting, and whether the path is WSL or Windows.",
            )
        if any(ch.isspace() for ch in raw):
            add(
                findings,
                "INFO",
                "PATH_HAS_SPACE",
                f"Path contains whitespace: {raw}",
                "Use LiteralPath or argument arrays; avoid concatenating this path into a shell string.",
            )
        if any(ord(ch) > 127 for ch in raw):
            add(
                findings,
                "INFO",
                "PATH_HAS_NON_ASCII",
                f"Path contains non-ASCII characters: {raw}",
                "Verify UTF-8/wide-character handling for scripts and native tools.",
            )


def environment_checks(findings: list[Finding]) -> None:
    if os.name == "nt":
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        empty = [entry for entry in path_entries if not entry]
        if empty:
            add(
                findings,
                "INFO",
                "PATH_EMPTY_ENTRIES",
                "PATH contains empty entries.",
                "This is usually harmless, but clean PATH when debugging tool resolution.",
            )
        for tool in ("where.exe", "powershell.exe", "cmd.exe"):
            if shutil.which(tool) is None:
                add(
                    findings,
                    "WARN",
                    "BASIC_TOOL_MISSING",
                    f"Could not find {tool} on PATH.",
                    "Check the Windows environment before relying on shell diagnostics.",
                )


def render_text(findings: list[Finding]) -> str:
    if not findings:
        return "OK: no obvious shell hazards detected."
    lines = []
    for item in findings:
        lines.append(f"[{item.level}] {item.code}: {item.message}")
        lines.append(f"  Fix: {item.fix}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Static preflight for fragile Windows shell commands.")
    parser.add_argument("--shell", choices=["powershell", "cmd", "wsl", "bash"], required=True)
    parser.add_argument("--command", default="", help="Command string to inspect.")
    parser.add_argument("--path", action="append", default=[], help="Path to verify; may be repeated.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero on ERROR findings.")
    parser.add_argument("--skip-env", action="store_true", help="Skip local environment checks.")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    command = args.command or ""

    if args.shell == "powershell":
        powershell_checks(command, findings)
    generic_checks(command, args.shell, findings)
    path_checks(args.path, findings)
    if not args.skip_env:
        environment_checks(findings)

    payload = {"ok": not any(f.level == "ERROR" for f in findings), "findings": [asdict(f) for f in findings]}
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(findings))

    if args.strict and not payload["ok"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
