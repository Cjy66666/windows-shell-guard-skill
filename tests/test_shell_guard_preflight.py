from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "shell_guard_preflight.py"


def run_case(*args: str) -> tuple[int, set[str], str]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--json", "--skip-env"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.stdout:
        payload = json.loads(proc.stdout)
        codes = {item["code"] for item in payload["findings"]}
    else:
        codes = set()
    return proc.returncode, codes, proc.stderr


def assert_case(name: str, condition: bool, detail: str) -> None:
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def main() -> int:
    code, findings, stderr = run_case(
        "--shell",
        "powershell",
        "--command",
        "python - <<'PY'\nprint(1)\nPY",
        "--strict",
    )
    assert_case("bash heredoc", code == 2, f"expected exit 2, got {code}; {stderr}")
    assert_case("bash heredoc", "PS_BASH_HEREDOC" in findings, f"missing PS_BASH_HEREDOC in {findings}")

    code, findings, _ = run_case(
        "--shell",
        "powershell",
        "--command",
        "export GDAL_DATA=/tmp && gdalinfo a.tif",
    )
    assert_case("export", code == 0, f"expected exit 0, got {code}")
    assert_case("export", {"PS_EXPORT", "PS_AND_IF", "GDAL_PROJ_RUNTIME"} <= findings, f"got {findings}")

    code, findings, _ = run_case(
        "--shell",
        "powershell",
        "--command",
        'Write-Host "$Drive:$Path"',
    )
    assert_case("variable boundary", code == 0, f"expected exit 0, got {code}")
    assert_case("variable boundary", "PS_VARIABLE_BOUNDARY" in findings, f"got {findings}")

    code, findings, _ = run_case(
        "--shell",
        "powershell",
        "--command",
        "$Path = 'C:\\Temp\\a b.txt'; Get-Content -Raw -LiteralPath $Path",
    )
    assert_case("safe literal path", code == 0, f"expected exit 0, got {code}")
    assert_case("safe literal path", "PS_BASH_HEREDOC" not in findings, f"got {findings}")

    code, findings, _ = run_case(
        "--shell",
        "powershell",
        "--command",
        "Get-Content -Raw -LiteralPath 'D:\\中文 路径\\说明.txt'",
    )
    assert_case("Chinese path", code == 0, f"expected exit 0, got {code}")
    assert_case("Chinese path", {"COMMAND_HAS_NON_ASCII", "GET_CONTENT_ENCODING"} <= findings, f"got {findings}")

    code, findings, _ = run_case(
        "--shell",
        "cmd",
        "--command",
        "echo hello && where python",
    )
    assert_case("cmd isolation", code == 0, f"expected exit 0, got {code}")
    assert_case("cmd isolation", not {"PS_AND_IF", "PS_BASH_HEREDOC"} & findings, f"got {findings}")

    print("all shell guard behavior tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
