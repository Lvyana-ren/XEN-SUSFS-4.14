#!/usr/bin/env python3
"""Apply the Xen-SuSFS v2.3.0 compatibility bridge to the pinned KSUN source.

This is a narrow overlay for the current KSUN pin. It does not replace KSUN,
change hook mode, or enable KPROBES. Run it after checkout of the pinned SHA.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

EXPECTED_KSUN_SHA = "465490a26667ba4cf00b3be975a7e28e53978829"

KCONFIG_BLOCK = r'''
# XEN-SUSFS-KSUN-COMPAT-BEGIN
menu "KernelSU - SUSFS"

config KSU_SUSFS
    bool "KernelSU addon - SUSFS"
    depends on KSU
    depends on THREAD_INFO_IN_TASK
    default y
    help
        Enable the SUSFS v2.3.0 interface in KernelSU-Next.

config KSU_SUSFS_SUS_PATH
    bool "Enable SUS_PATH"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SUS_MOUNT
    bool "Enable SUS_MOUNT"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SUS_KSTAT
    bool "Enable SUS_KSTAT"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_TRY_UMOUNT
    bool "Enable SUSFS try_umount"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SPOOF_UNAME
    bool "Enable uname spoofing"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_ENABLE_LOG
    bool "Enable SUSFS kernel logging"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS
    bool "Hide KernelSU/SUSFS symbols from kallsyms"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
    bool "Enable cmdline/bootconfig spoofing"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_OPEN_REDIRECT
    bool "Enable open redirect"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SUS_MAP
    bool "Enable SUS_MAP"
    depends on KSU_SUSFS
    default y

config KSU_SUSFS_SUS_MEMFD
    bool "Enable SUS_MEMFD (experimental)"
    depends on KSU_SUSFS
    default n

endmenu
# XEN-SUSFS-KSUN-COMPAT-END
'''

REBOOT_BRIDGE = r'''#ifdef CONFIG_KSU_SUSFS
	/*
	 * XEN-SUSFS-KSUN-COMPAT: syscall bridge
	 * Keep the SUSFS_MAGIC ABI used by ksu_susfs userspace while using
	 * this KSUN revision's existing manual-hook entry point.
	 */
	if (magic2 == SUSFS_MAGIC && current_uid().val == 0) {
#ifdef CONFIG_KSU_SUSFS_SUS_PATH
		if (cmd == CMD_SUSFS_ADD_SUS_PATH) {
			susfs_add_sus_path(arg);
			return 0;
		}
		if (cmd == CMD_SUSFS_ADD_SUS_PATH_LOOP) {
			susfs_add_sus_path_loop(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MOUNT
		if (cmd == CMD_SUSFS_HIDE_SUS_MNTS_FOR_NON_SU_PROCS) {
			susfs_set_hide_sus_mnts_for_non_su_procs(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_KSTAT
		if (cmd == CMD_SUSFS_ADD_SUS_KSTAT ||
		    cmd == CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY) {
			susfs_add_sus_kstat(arg);
			return 0;
		}
		if (cmd == CMD_SUSFS_UPDATE_SUS_KSTAT) {
			susfs_update_sus_kstat(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_TRY_UMOUNT
		if (cmd == CMD_SUSFS_ADD_TRY_UMOUNT) {
			susfs_add_try_umount(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_UNAME
		if (cmd == CMD_SUSFS_SET_UNAME) {
			susfs_set_uname(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_ENABLE_LOG
		if (cmd == CMD_SUSFS_ENABLE_LOG) {
			susfs_enable_log(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG
		if (cmd == CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG) {
			susfs_set_cmdline_or_bootconfig(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT
		if (cmd == CMD_SUSFS_ADD_OPEN_REDIRECT) {
			susfs_add_open_redirect(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MAP
		if (cmd == CMD_SUSFS_ADD_SUS_MAP) {
			susfs_add_sus_map(arg);
			return 0;
		}
#endif
#ifdef CONFIG_KSU_SUSFS_SUS_MEMFD
		if (cmd == CMD_SUSFS_ADD_SUS_MEMFD)
			return susfs_add_sus_memfd(arg);
#endif
		if (cmd == CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING) {
			susfs_set_avc_log_spoofing(arg);
			return 0;
		}
		if (cmd == CMD_SUSFS_SHOW_ENABLED_FEATURES) {
			susfs_get_enabled_features(arg);
			return 0;
		}
		if (cmd == CMD_SUSFS_SHOW_VARIANT) {
			susfs_show_variant(arg);
			return 0;
		}
		if (cmd == CMD_SUSFS_SHOW_VERSION) {
			susfs_show_version(arg);
			return 0;
		}
		return 0;
	}
#endif /* CONFIG_KSU_SUSFS */
'''

DISPATCH_BOOT_BRIDGE = r'''#ifdef CONFIG_KSU_SUSFS
				susfs_start_sdcard_monitor_fn(); /* XEN-SUSFS-KSUN-COMPAT: boot monitor */
#endif
'''

KBUILD_BLOCK = r'''
# XEN-SUSFS-KSUN-COMPAT-BEGIN
ifeq ($(CONFIG_KSU_SUSFS),y)
ifeq ($(shell test -f $(srctree)/fs/susfs.c -a -f $(srctree)/include/linux/susfs.h && echo yes),)
$(error CONFIG_KSU_SUSFS=y but SUSFS kernel sources are missing)
endif
SUSFS_VERSION := $(shell sed -n 's/^#define SUSFS_VERSION "\([^"]*\)".*/\1/p' $(srctree)/include/linux/susfs.h)
$(info -- XEN-SUSFS compatibility bridge enabled; SUSFS_VERSION=$(SUSFS_VERSION))
endif
# XEN-SUSFS-KSUN-COMPAT-END
'''


def read_text(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Required KSUN source file is missing: {path}")
    return path.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} /path/to/KernelSU-Next", file=sys.stderr)
        return 2

    root = Path(sys.argv[1]).resolve()
    if not (root / ".git").exists():
        raise RuntimeError(f"Not a Git checkout: {root}")

    actual_sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual_sha != EXPECTED_KSUN_SHA:
        raise RuntimeError(
            "Refusing to patch an unexpected KSUN revision.\n"
            f"Expected: {EXPECTED_KSUN_SHA}\n"
            f"Actual:   {actual_sha}\n"
            "Update the pin and audit compatibility deliberately before retrying."
        )

    kconfig_path = root / "kernel/Kconfig"
    supercall_path = root / "kernel/supercall/supercall.c"
    dispatch_path = root / "kernel/supercall/dispatch.c"
    kbuild_path = root / "kernel/Kbuild"

    kconfig = read_text(kconfig_path)
    supercall = read_text(supercall_path)
    dispatch = read_text(dispatch_path)
    kbuild = read_text(kbuild_path)

    markers = [
        "XEN-SUSFS-KSUN-COMPAT-BEGIN" in kconfig,
        "XEN-SUSFS-KSUN-COMPAT: syscall bridge" in supercall,
        "XEN-SUSFS-KSUN-COMPAT: boot monitor" in dispatch,
        "XEN-SUSFS-KSUN-COMPAT-BEGIN" in kbuild,
    ]
    if all(markers):
        print("XEN-SUSFS KSUN compatibility bridge is already applied.")
        return 0
    if any(markers):
        raise RuntimeError(
            "Partial XEN-SUSFS bridge detected; inspect the working tree before retrying."
        )

    if "CONFIG_KSU_SUSFS" in kconfig or "SUSFS_MAGIC" in supercall:
        raise RuntimeError(
            "Unexpected existing SUSFS integration found; refusing duplicate insertion."
        )

    # Add the SUSFS Kconfig menu before the single top-level endmenu.
    if kconfig.count("\nendmenu") != 1:
        raise RuntimeError("kernel/Kconfig: expected exactly one top-level endmenu")
    kconfig = replace_once(
        kconfig, "\nendmenu", "\n" + KCONFIG_BLOCK + "\nendmenu",
        "kernel/Kconfig SUSFS menu"
    )

    # Export the existing kernel-side SUSFS ABI through KSUN's current reboot hook.
    include_anchor = '#include <linux/utsname.h> // utsname() and uts_sem\n'
    susfs_include = (
        include_anchor
        + "\n#ifdef CONFIG_KSU_SUSFS\n"
        + '#include <linux/susfs.h> /* XEN-SUSFS-KSUN-COMPAT: include */\n'
        + "#endif\n"
    )
    supercall = replace_once(
        supercall, include_anchor, susfs_include, "supercall SUSFS include"
    )
    reboot_anchor = "\t// Check if this is a request to install KSU fd\n"
    supercall = replace_once(
        supercall, reboot_anchor, REBOOT_BRIDGE + "\n" + reboot_anchor,
        "supercall SUSFS syscall bridge"
    )

    # Start the SUSFS sdcard monitor on the normal boot-completed event.
    dispatch_anchor = '#include "uapi/supercall.h"\n'
    dispatch_include = (
        "#ifdef CONFIG_KSU_SUSFS\n"
        '#include <linux/susfs.h> /* XEN-SUSFS-KSUN-COMPAT: include */\n'
        "#endif\n"
        + dispatch_anchor
    )
    dispatch = replace_once(
        dispatch, dispatch_anchor, dispatch_include, "dispatch SUSFS include"
    )
    boot_anchor = r'''				pr_info("boot_complete triggered\n");
				on_boot_completed();
'''
    dispatch = replace_once(
        dispatch, boot_anchor, boot_anchor + DISPATCH_BOOT_BRIDGE,
        "dispatch boot-completed monitor"
    )

    # Make the module build fail early when SUSFS is enabled without kernel-side sources.
    if "XEN-SUSFS-KSUN-COMPAT-BEGIN" in kbuild:
        raise RuntimeError("kernel/Kbuild already contains the XEN-SUSFS bridge")
    kbuild = kbuild.rstrip() + "\n\n" + KBUILD_BLOCK.lstrip() + "\n"

    # All anchors are validated before any file is written.
    kconfig_path.write_text(kconfig, encoding="utf-8")
    supercall_path.write_text(supercall, encoding="utf-8")
    dispatch_path.write_text(dispatch, encoding="utf-8")
    kbuild_path.write_text(kbuild, encoding="utf-8")

    print("Applied XEN-SUSFS v2.3.0 compatibility bridge.")
    print(f"KSUN revision retained: {actual_sha}")
    print("KSU_MANUAL_HOOK and KPROBES settings were not changed.")
    print("Next: verify .config, apply the kernel call-site candidate, then compile.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
