#!/usr/bin/env python3
"""Check deterministic M00 command-line prerequisites."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Tool:
    name: str
    version_args: tuple[str, ...]
    required_for_bootstrap: bool = True


TOOLS = (
    Tool("uv", ("--version",)),
    Tool("node", ("--version",)),
    Tool("npm", ("--version",)),
    Tool("ffmpeg", ("-version",), required_for_bootstrap=False),
    Tool("ffprobe", ("-version",), required_for_bootstrap=False),
    Tool("docker", ("--version",), required_for_bootstrap=False),
    Tool("supabase", ("--version",), required_for_bootstrap=False),
)


def inspect(tool: Tool) -> tuple[bool, str]:
    executable = shutil.which(tool.name)
    if executable is None:
        return False, "not found"
    completed = subprocess.run(
        [executable, *tool.version_args],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    first_line = (completed.stdout or completed.stderr).splitlines()
    version = first_line[0] if first_line else f"exit {completed.returncode}"
    return completed.returncode == 0, version


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all",
        action="store_true",
        help="Require media and local-database tools in addition to bootstrap tools.",
    )
    args = parser.parse_args()

    failed: list[str] = []
    for tool in TOOLS:
        ok, version = inspect(tool)
        required = tool.required_for_bootstrap or args.all
        state = "ok" if ok else ("missing" if required else "optional-missing")
        print(f"{tool.name}: {state} ({version})")
        if required and not ok:
            failed.append(tool.name)

    if failed:
        print(f"Missing required M00 tools: {', '.join(failed)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
