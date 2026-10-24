# XEN-SUSFS-4.14

Porting workspace for **SUSFS v2.3.0** on Xen-Kernel / Poco X3 Pro (vayu), Linux **4.14.357**, with KernelSU-Next manual hooks.

> **Status: staged port, not yet a complete build-ready patch series.** The source-file patch and source audit are available. The kernel call-site patch is generated as a candidate; textual conflicts, KSUN-side SUSFS support, and config integration must be resolved and a full build must pass before this is usable on a device.

## Pinned references

The candidate workflow reads all repository references from [`config/port-refs.env`](config/port-refs.env). It fetches and verifies the exact commit SHA; it does **not** silently use the latest branch tip.

- Base SHA (`AnymoreProject/android_kernel_vayu:16`): `0f8b1c04302094439718fa5d8d9122d9f89a730b`
- Target SHA (`Lvyana-ren/Xen-Kernel:16-KSUN_SuSFS`): `08f4c4761c14f6b30b5efb6b8bd0b817b39eb1c3`
- Feature SHA (`Lvyana-ren/Xen-SuSFS:16-ksu`): `67696276f509631e85759d8fdf43e4d90246a281`

Update these pins deliberately in the config file when you intend to change the reference versions; review the resulting diff and artifact afterward.

- Target kernel: [Lvyana-ren/Xen-Kernel, branch `16-KSUN_SuSFS`](https://github.com/Lvyana-ren/Xen-Kernel/tree/16-KSUN_SuSFS)
- Target baseline head at the time of the initial import: `08f4c4761c14f6b30b5efb6b8bd0b817b39eb1c3`
- SUSFS source: [Lvyana-ren/Xen-SuSFS, branch `16-ksu`](https://github.com/Lvyana-ren/Xen-SuSFS/tree/16-ksu)
- SUSFS source head: `67696276f509631e85759d8fdf43e4d90246a281` (declares `SUSFS_VERSION "v2.3.0"`)
- Upstream kernel baseline: [AnymoreProject/android_kernel_vayu, branch `16`](https://github.com/AnymoreProject/android_kernel_vayu/tree/16)
- Upstream SUSFS-enabled reference: [AnymoreProject/android_kernel_vayu, branch `16-ksu`](https://github.com/AnymoreProject/android_kernel_vayu/tree/16-ksu)

## Repository contents

- `patches/0001-susfs-v2.3.0-source-files.patch` — adds `fs/susfs.c` and the SUSFS headers to a tree that does not already contain them.
- `patches/0002-susfs-fix-ctime-bitmask.patch` — standalone correction for the `KSTAT_SPOOF_CTIME_TV_SEC` bit flag typo; pair it with a compatible userspace audit.
- `patches/series.stage1` — source-only bootstrap sequence, not the full feature integration.
- `tools/generate-port-candidate.sh` and the [Actions workflow](https://github.com/Lvyana-ren/XEN-SUSFS-4.14/actions/workflows/generate-port-candidate.yml) — create a candidate call-site integration patch plus merge/conflict reports.

## How to integrate the candidate into Xen-Kernel

1. Open [Actions → Generate Xen SUSFS 4.14 port candidate](https://github.com/Lvyana-ren/XEN-SUSFS-4.14/actions/workflows/generate-port-candidate.yml) and run it on `main`.
2. Download and extract the `xen-susfs-4.14-candidate` artifact from the completed run.
3. Read `reports/target-baseline-commit.txt`, `reports/clean-files.txt`, and `reports/conflicts.txt`. Resolve every conflicted file manually; those files are not automatically included as resolved changes.
4. Apply `xen-susfs-kernel-integration-candidate.patch` on a **separate review branch** at the exact target commit, first with `git apply --check`, then with `git apply`. Run `git diff --check` and review the diff.

The complete shell commands, conflict handling, and next steps are documented in **[docs/APPLY-TO-XEN-KERNEL.md](docs/APPLY-TO-XEN-KERNEL.md)**.

The generator does not push to Xen-Kernel or modify the remote target branch. It verifies and reports the exact base, target, and feature commit SHAs in `reports/input-refs.txt`. Its output is only a candidate patch; it does not claim that every SUSFS feature is integrated or that a kernel build has passed.

## Current blockers — read before building

1. The KernelSU-Next commit pinned in the current Xen-Kernel workflow, `465490a26667ba4cf00b3be975a7e28e53978829`, does not declare `CONFIG_KSU_SUSFS` in `kernel/Kconfig`. The matching KSUN config/API/ioctl/userspace interface must be integrated and version-matched.
2. The target branch at the time of the audit lacked `obj-$(CONFIG_KSU_SUSFS) += susfs.o` in `fs/Makefile` and lacked SUSFS config symbols in `vayu_defconfig`. The generator adds the object line to its candidate; it does not finish the KSUN-side Kconfig or config work.
3. The reference comparison includes unrelated changes (including generic KernelSU syscall hooks and credential-compatibility changes). Do not transplant the entire `16-ksu` tree wholesale; preserve Xen-Kernel's manual hooks.
4. The upstream `master` patch `50_add_susfs_in_kernel-4.14.patch` is from an older SUSFS line. Do not mix it blindly with the v2.3.0 source.
5. Do not flash the candidate. Resolve conflicts, complete KSUN/config integration, verify `make olddefconfig`, and get a successful full build first.

## Applying the source-only bootstrap

Only use this on a clean Linux 4.14 tree that **does not have** the three SUSFS source files:

```bash
git apply --check patches/0001-susfs-v2.3.0-source-files.patch
git apply patches/0001-susfs-v2.3.0-source-files.patch
git apply --check patches/0002-susfs-fix-ctime-bitmask.patch
git apply patches/0002-susfs-fix-ctime-bitmask.patch
```

Do **not** apply patch 0001 on `Xen-Kernel:16-KSUN_SuSFS`, because the three SUSFS source files are already present there. Patch 0002 is independent, but coordinate the bitmask correction with the matching userspace implementation.

See [docs/PORTING-AUDIT.md](docs/PORTING-AUDIT.md) for the audit details.
