#!/usr/bin/env python3
"""Verify Arcanum Android ARM64 binaries and their advertised SIMD backend."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> str:
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return result.stdout + result.stderr


def find_tool(env_name: str, candidates: tuple[str, ...]) -> str:
    import os

    override = os.environ.get(env_name)
    if override:
        return override
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise FileNotFoundError(f"None of these tools were found: {', '.join(candidates)}")


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <binary> <neon|dotprod>", file=sys.stderr)
        return 2

    binary = Path(sys.argv[1])
    mode = sys.argv[2].lower()
    if mode not in {"neon", "dotprod"}:
        print("Backend must be 'neon' or 'dotprod'.", file=sys.stderr)
        return 2
    if not binary.is_file():
        print(f"Missing binary: {binary}", file=sys.stderr)
        return 1

    readelf_tool = find_tool("LLVM_READELF", ("llvm-readelf", "readelf"))
    objdump_tool = find_tool("LLVM_OBJDUMP", ("llvm-objdump", "aarch64-linux-gnu-objdump"))
    readelf = run([readelf_tool, "-h", str(binary)])
    if "ELF64" not in readelf or "AArch64" not in readelf:
        print("FAIL: expected an ELF64 AArch64 binary.", file=sys.stderr)
        return 1
    if not re.search(r"Type:\s+(EXEC|DYN)\b", readelf):
        print("FAIL: expected a linked executable, not a relocatable object.", file=sys.stderr)
        return 1
    print("PASS: linked ELF64 AArch64 executable.")

    objdump = run([objdump_tool, "-d", str(binary)]).lower()
    neon_patterns = (
        r"\b(add|sub|smax|smin|smull|umov|shll|sadalp|sqadd)\s+v\d+",
        r"\b(ld1|st1)\s+\{?v\d+",
    )
    if not any(re.search(pattern, objdump) for pattern in neon_patterns):
        print("FAIL: no recognizable AArch64 Advanced SIMD instructions found.", file=sys.stderr)
        return 1
    print("PASS: AArch64 NEON instructions are present.")

    has_sdot = re.search(r"\bsdot\s+v\d+", objdump) is not None
    if mode == "dotprod":
        if not has_sdot:
            print("FAIL: DotProd build contains no SDOT instruction.", file=sys.stderr)
            return 1
        print("PASS: SDOT instructions are present in the DotProd backend.")
    elif has_sdot:
        print("FAIL: baseline NEON binary unexpectedly contains SDOT instructions.", file=sys.stderr)
        return 1
    else:
        print("PASS: baseline NEON binary contains no DotProd-only instructions.")

    print(f"PASS: {binary} ({binary.stat().st_size:,} bytes).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
