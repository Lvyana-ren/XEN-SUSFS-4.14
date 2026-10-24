#!/usr/bin/env python3
"""Sanitize the SUSFS merge candidate for Xen-Kernel's manual-hook workflow."""
from __future__ import annotations

import re
import sys
from pathlib import Path


def normalize_whitespace(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lines = [line.rstrip(" \t") for line in text.splitlines()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def strip_once(text: str, pattern: str, label: str) -> str:
    updated, count = re.subn(pattern, "\n", text, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one matching block; found {count}")
    return updated


def ensure_defconfig_symbol(text: str, symbol: str, value: str) -> str:
    """Set one exact defconfig assignment; avoid invalid CONFIG_FOO=n lines."""
    assign = re.compile(rf"(?m)^(?:# )?{re.escape(symbol)}(?:=.*| is not set)\s*$")
    text = assign.sub("", text)
    wanted = f"{symbol}={value}"
    marker = "CONFIG_TRACEPOINTS=y\n"
    if text.count(marker) != 1:
        raise RuntimeError(f"vayu_defconfig: expected one {marker.strip()} marker")
    text = text.replace(marker, marker + wanted + "\n", 1)
    return text


def main() -> int:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} TARGET_KERNEL_DIR REPORTS_DIR", file=sys.stderr)
        return 2

    target = Path(sys.argv[1]).resolve()
    reports = Path(sys.argv[2]).resolve()
    clean_files = reports / "clean-files.txt"
    if not clean_files.is_file():
        raise RuntimeError(f"Missing merge report: {clean_files}")

    report_lines: list[str] = []

    # Keep SUSFS OPEN_REDIRECT edits in fs/open.c, but remove Anymore's generic
    # faccessat hook. Xen-Kernel inserts that hook with scripts/apply-ksun-manual-hooks.py.
    open_path = target / "fs/open.c"
    open_text = open_path.read_text(encoding="utf-8")
    open_text = strip_once(
        open_text,
        r"\n#ifdef CONFIG_KSU\n"
        r"extern __attribute__\(\(hot\)\) int ksu_handle_faccessat\(int \*dfd,\n"
        r"\s*const char __user \*\*filename_user, int \*mode, int \*flags\);\n"
        r"#endif\n",
        "fs/open.c legacy faccessat declaration",
    )
    open_text = strip_once(
        open_text,
        r"\n#if defined\(CONFIG_KSU\) && !defined\(CONFIG_KSU_TAMPER_SYSCALL_TABLE\)\n"
        r"__attribute__\(\(hot\)\)\n"
        r"extern int ksu_handle_faccessat\(int \*dfd, const char __user \*\*filename_user,\n"
        r"\s*int \*mode, int \*flags\);\n"
        r"#endif\n",
        "fs/open.c generic faccessat declaration",
    )
    open_text = strip_once(
        open_text,
        r"\n#if defined\(CONFIG_KSU\) && !defined\(CONFIG_KSU_TAMPER_SYSCALL_TABLE\)\n"
        r"\s*ksu_handle_faccessat\(&dfd, &filename, &mode, NULL\);\n"
        r"#endif\n",
        "fs/open.c generic faccessat call",
    )
    open_path.write_text(open_text, encoding="utf-8")
    report_lines.append("fs/open.c: removed generic faccessat hook; preserved SUSFS OPEN_REDIRECT changes")

    # Restore the correct ARM64 capability and disabled-hook config. These are
    # deliberately different: HAVE_KPROBES describes platform capability;
    # KPROBES itself remains disabled for Xen-Kernel's manual-hook setup.
    defconfig_path = target / "arch/arm64/configs/vayu_defconfig"
    defconfig = defconfig_path.read_text(encoding="utf-8")
    defconfig = ensure_defconfig_symbol(defconfig, "CONFIG_KPROBES", "not-a-value")
    # Convert the temporary sentinel into the Kconfig "not set" syntax.
    defconfig = defconfig.replace("CONFIG_KPROBES=not-a-value", "# CONFIG_KPROBES is not set")
    defconfig = ensure_defconfig_symbol(defconfig, "CONFIG_HAVE_KPROBES", "y")
    # These were emitted as invalid "=n" assignments by the upstream reference.
    for symbol in ("CONFIG_KPROBE_EVENTS", "CONFIG_KPROBE_EVENT"):
        defconfig = re.sub(rf"(?m)^#?{re.escape(symbol)}(?:=.*| is not set)\s*\n?", "", defconfig)
    # SUSFS features are valid only once the KSUN compatibility overlay declares the symbol.
    for symbol in ("CONFIG_KSU", "CONFIG_KSU_SUSFS"):
        pattern = re.compile(rf"(?m)^(?:# )?{re.escape(symbol)}(?:=.*| is not set)\s*$")
        count = len(pattern.findall(defconfig))
        if count > 1:
            defconfig = pattern.sub("", defconfig)
        if not re.search(rf"(?m)^{re.escape(symbol)}=y$", defconfig):
            if symbol == "CONFIG_KSU":
                raise RuntimeError("vayu_defconfig: CONFIG_KSU=y missing; refusing to guess insertion point")
            marker = "CONFIG_KSU=y\n"
            if defconfig.count(marker) != 1:
                raise RuntimeError("vayu_defconfig: cannot uniquely locate CONFIG_KSU=y")
            defconfig = defconfig.replace(marker, marker + "CONFIG_KSU_SUSFS=y\n", 1)
    defconfig_path.write_text(defconfig, encoding="utf-8")
    report_lines.append("vayu_defconfig: kept CONFIG_KPROBES disabled, restored CONFIG_HAVE_KPROBES=y, removed invalid KPROBE*=n assignments, ensured KSU/SUSFS symbols")

    # Remove trailing whitespace from files changed by the clean three-way merge.
    normalized = 0
    for raw in clean_files.read_text(encoding="utf-8").splitlines():
        rel = raw.strip()
        if not rel:
            continue
        path = target / rel
        if not path.is_file():
            raise RuntimeError(f"Clean merge report references missing file: {rel}")
        before = path.read_text(encoding="utf-8")
        normalize_whitespace(path)
        after = path.read_text(encoding="utf-8")
        if before != after:
            normalized += 1
            report_lines.append(f"{rel}: normalized trailing whitespace")

    reports.mkdir(parents=True, exist_ok=True)
    (reports / "normalization.txt").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    print(f"Normalized candidate; files requiring whitespace cleanup: {normalized}")
    print(f"Actions recorded in {reports / 'normalization.txt'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
