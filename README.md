# XEN-SUSFS-4.14

Porting workspace for **SUSFS v2.3.0** on Xen-Kernel / Poco X3 Pro (vayu), Linux **4.14.357**, with KernelSU-Next manual hooks.

> **Status: staged port, not yet a complete build-ready patch series.** The source-file patch and the source audit are ready. The kernel call-site patch is generated as a candidate by the workflow below; any conflicts and the KernelSU-Next integration gap must be resolved and a build must pass before this is considered usable on-device.

## Pinned references

- Target kernel: [Lvyana-ren/Xen-Kernel, branch `16-KSUN_SuSFS`](https://github.com/Lvyana-ren/Xen-Kernel/tree/16-KSUN_SuSFS)
- Target baseline head at the time this workspace was prepared: `08f4c4761c14f6b30b5efb6b8bd0b817b39eb1c3`
- SUSFS source: [Lvyana-ren/Xen-SuSFS, branch `16-ksu`](https://github.com/Lvyana-ren/Xen-SuSFS/tree/16-ksu)
- SUSFS source head: `67696276f509631e85759d8fdf43e4d90246a281` (declares `SUSFS_VERSION "v2.3.0"`)
- Upstream kernel baseline: [AnymoreProject/android_kernel_vayu, branch `16`](https://github.com/AnymoreProject/android_kernel_vayu/tree/16)
- Upstream SUSFS-enabled reference: [AnymoreProject/android_kernel_vayu, branch `16-ksu`](https://github.com/AnymoreProject/android_kernel_vayu/tree/16-ksu)

## Contents

- `patches/0001-susfs-v2.3.0-source-files.patch` — adds `fs/susfs.c` and the two SUSFS headers to a kernel tree that does **not** already contain them.
- `patches/0002-susfs-fix-ctime-bitmask.patch` — standalone fix for the `KSTAT_SPOOF_CTIME_TV_SEC` flag typo.
- `patches/series.stage1` — source-only bootstrap sequence, not the full feature integration.
- `tools/generate-port-candidate.sh` + [GitHub Actions workflow](https://github.com/Lvyana-ren/XEN-SUSFS-4.14/actions) — perform a three-way merge of SUSFS reference changes onto Xen-Kernel and upload a candidate integration patch plus a conflict report.

## Generate a candidate for Xen-Kernel

1. Open **Actions → Generate Xen SUSFS 4.14 port candidate**.
2. Run the workflow. It uses Anymore `16` as the merge base, Xen-Kernel `16-KSUN_SuSFS` as the target, and Xen-SuSFS `16-ksu` as the feature reference.
3. Download artifact `xen-susfs-4.14-candidate`.
4. Review `reports/clean-files.txt` and `reports/conflicts.txt`. A file listed as conflicted is not modified in the generated candidate.
5. Inspect the generated patch before applying it; run `git apply --check` on the exact target commit, then build the kernel.

The generator never pushes to Xen-Kernel and never changes your target branch. The output is a **candidate**, not an assertion that every feature is complete or that a kernel build has passed.

## Important integration blockers

1. The existing pinned KernelSU-Next commit `465490a26667ba4cf00b3be975a7e28e53978829` does not declare `CONFIG_KSU_SUSFS` in its `kernel/Kconfig`. A kernel-only patch cannot enable manager/SUSFS ioctl support by itself; KSUN-side integration has to be patched and version-matched separately.
2. The target tree previously lacked `obj-$(CONFIG_KSU_SUSFS) += susfs.o` in `fs/Makefile` and did not enable `CONFIG_KSU_SUSFS=y` in `vayu_defconfig`.
3. SUSFS v2.3.0 touches several VFS/proc/mount/stat paths. The upstream comparison includes changes unrelated to SUSFS (including KernelSU syscall hooks and credential-compatibility changes); do **not** cherry-pick the entire `16-ksu` tree wholesale over Xen-Kernel.
4. The upstream `master` patch `50_add_susfs_in_kernel-4.14.patch` belongs to an older frozen SUSFS line. Do not mix it blindly with the v2.3.0 source. Use the branch-pinned source references in this repo.
5. Do not flash the result until the candidate's conflicts are resolved, KSUN support is integrated, `olddefconfig` preserves the required options, and a full kernel build succeeds.

## Applying the source-only bootstrap

On a clean Linux 4.14 kernel tree **without** SUSFS files:

```bash
git apply --check patches/0001-susfs-v2.3.0-source-files.patch
git apply patches/0001-susfs-v2.3.0-source-files.patch
git apply --check patches/0002-susfs-fix-ctime-bitmask.patch
git apply patches/0002-susfs-fix-ctime-bitmask.patch
```

Do **not** run patch 0001 on `Xen-Kernel:16-KSUN_SuSFS` as those three files are already present there. Patch 0002 is standalone and targets `include/linux/susfs.h` in that branch.

See [docs/PORTING-AUDIT.md](docs/PORTING-AUDIT.md) for detailed audit results.
