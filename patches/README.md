# Patch status

This directory is deliberately staged; these patches alone do not make the kernel build-ready.

- `0001-susfs-v2.3.0-source-files.patch`: source-only bootstrap for a kernel tree that has no SUSFS source files yet.
- `0002-susfs-fix-ctime-bitmask.patch`: fixes the ctime spoof flag constant; verify the matching userspace version before using the feature.
- `series.stage1`: applies those two patches in order on a clean baseline.

For the current `Xen-Kernel:16-KSUN_SuSFS` branch, do not apply patch 0001 because the source files are already present. The call-site changes are generated as a candidate by the workflow and must be reviewed/applied as documented in [docs/APPLY-TO-XEN-KERNEL.md](../docs/APPLY-TO-XEN-KERNEL.md). Textual conflicts are reported separately and must be ported manually. KSUN-side config/API/ioctl support and full build validation are still required.
