Three-way SUSFS port candidate

Base: AnymoreProject/android_kernel_vayu @ 0f8b1c04302094439718fa5d8d9122d9f89a730b (16)
Target: Lvyana-ren/Xen-Kernel @ 08f4c4761c14f6b30b5efb6b8bd0b817b39eb1c3 (16-KSUN_SuSFS)
Feature reference: Lvyana-ren/Xen-SuSFS @ 67696276f509631e85759d8fdf43e4d90246a281 (16-ksu)

These SHA values are also recorded in reports/input-refs.txt.
This is a candidate. A clean text merge does not prove semantic correctness or buildability.
Files with conflicts are unchanged in TARGET_DIR and saved under reports/conflicts/.
Review the generated patch for unrelated changes before applying.

Cleanly merged files:
fs/Makefile
fs/internal.h
fs/namei.c
fs/namespace.c
fs/notify/fdinfo.c
fs/open.c
fs/proc/base.c
fs/proc/cmdline.c
fs/proc/fd.c
fs/proc/internal.h
fs/proc/task_mmu.c
fs/proc/task_nommu.c
fs/proc_namespace.c
fs/readdir.c
fs/seq_file.c
fs/stat.c
fs/statfs.c
fs/super.c
include/linux/kernel.h
include/linux/mount.h
include/linux/pkeys.h
include/linux/sched.h
include/linux/seq_file.h
kernel/kallsyms.c
kernel/sys.c
lib/idr.c
lib/vsprintf.c
mm/memory.c
mm/shmem.c
security/selinux/avc.c
security/selinux/hooks.c
arch/arm64/configs/vayu_defconfig

Conflicting files:

Missing-input files:
