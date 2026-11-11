"""Fail the build if a credential is committed.

The repository is private, but a token in git history is a token you have to
rotate whether or not anyone saw it. This runs on every push, needs no network,
and checks the files git actually tracks — a secret sitting in a local `.env` is
fine, the same string in a tracked file is not.

    python -m tests.check_secrets
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Patterns for the credentials this project actually handles, plus the two
# shapes that show up most often when something is pasted by accident.
PATTERNS: dict[str, re.Pattern[str]] = {
    "Mistral API key": re.compile(r"\bmstrl_[A-Za-z0-9_]{16,}"),
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    "AWS access key id": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "admin token value": re.compile(r"ADMIN_TOKEN\s*=\s*[A-Za-z0-9]{8,}"),
    "bearer token": re.compile(r"Authorization\s*[:=]\s*Bearer\s+[A-Za-z0-9_.-]{20,}"),
}

# Files that legitimately describe the patterns above.
ALLOWED = {
    "tests/check_secrets.py",
    "env.example",
}

TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".json", ".md", ".yml", ".yaml", ".toml", ".txt",
    ".sh", ".ps1", ".css", ".html", ".env", ".example", ".cfg", ".ini", "",
}


def tracked_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=ROOT,
            capture_output=True,
            check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Not a git checkout (a copied build tree, for example): scan the tree.
        return [
            str(path.relative_to(ROOT)).replace("\\", "/")
            for path in ROOT.rglob("*")
            if path.is_file()
            and not any(part in {".git", ".venv", "node_modules", ".next", "out", "__pycache__"}
                        for part in path.parts)
        ]
    return [name for name in out.decode("utf-8").split("\0") if name]


def main() -> int:
    files = tracked_files()
    findings: list[str] = []

    if ".env" in files:
        findings.append(".env is tracked by git; it must not be")

    scanned = 0
    for name in files:
        if name in ALLOWED:
            continue
        path = ROOT / name
        if path.suffix not in TEXT_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{name}:{line}: looks like a {label}")

    print(f"scanned {scanned} tracked text files for {len(PATTERNS)} credential patterns")

    if findings:
        print(f"\n{len(findings)} finding(s):")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("ok - no credentials in tracked files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
