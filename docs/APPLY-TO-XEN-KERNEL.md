# Applying the SUSFS 4.14 candidate to Xen-Kernel

> **Important:** this is a review workflow, not a ready-to-flash integration. The candidate patch does not yet include the matching KernelSU-Next SUSFS config/ioctl/API implementation, and any conflicted files still need a manual port.

## 1. Generate the candidate artifact

1. Open [XEN-SUSFS-4.14 Actions](https://github.com/Lvyana-ren/XEN-SUSFS-4.14/actions).
2. Select **Generate Xen SUSFS 4.14 port candidate**.
3. Click **Run workflow** on branch `main`.
4. Open the completed workflow run and download artifact `xen-susfs-4.14-candidate`.
5. Extract the ZIP. The useful files are:
   - `xen-susfs-kernel-integration-candidate.patch` — changes merged without textual conflicts.
   - `reports/target-baseline-commit.txt` — exact Xen-Kernel commit used as the patch base.
   - `reports/input-refs.txt` — exact base, target, and Xen-SuSFS commit SHAs used for this artifact.
   - `reports/clean-files.txt` — files merged without textual conflicts.
   - `reports/conflicts.txt` and `reports/conflicts/` — files that require manual integration.
   - `README-CANDIDATE.txt` — report generated for that run.

If `reports/conflicts.txt` is not empty, those conflicted files are **not** included as a resolved change in the candidate patch. Review each corresponding `.merge` file and integrate the SUSFS changes into the target file manually; never copy conflict markers into the kernel source.

## 2. Apply to a separate local review branch

Run these commands in a clean checkout on a Linux build machine. Replace `/path/to/xen-susfs-4.14-candidate` with the directory where you extracted the artifact.

```bash
git clone --branch 16-KSUN_SuSFS --single-branch \
  https://github.com/Lvyana-ren/Xen-Kernel.git Xen-Kernel
cd Xen-Kernel

# Use the exact SHA recorded in the artifact, not a possibly newer branch tip.
TARGET_SHA=$(cat /path/to/xen-susfs-4.14-candidate/reports/target-baseline-commit.txt)
git checkout --detach "$TARGET_SHA"
git switch -c susfs-4.14-review

PATCH=/path/to/xen-susfs-4.14-candidate/xen-susfs-kernel-integration-candidate.patch

# First check that every hunk applies to this exact baseline.
git apply --check "$PATCH"

# Only apply after the check succeeds.
git apply "$PATCH"

# Review the changes; this does not build or flash the kernel.
git diff --check
git status --short
git diff --stat
```

If `git apply --check` fails, stop. Confirm that `TARGET_SHA` matches the artifact report and that the checkout has no local changes. Do not force the patch or use `git apply --reject` as a shortcut.

## 3. Know what is—and is not—in the patch

- The generated candidate contains the three-way merged call-site changes for files listed as clean and a safe `fs/Makefile` object-line addition.
- Files listed in `reports/conflicts.txt` need a manual port and review.
- The candidate generator does not yet complete KSUN's SUSFS config, ioctl, userspace API, or all required `vayu_defconfig` changes.
- The target branch already contains `fs/susfs.c`, `include/linux/susfs.h`, and `include/linux/susfs_def.h`. **Do not apply** `patches/0001-susfs-v2.3.0-source-files.patch` on top of that branch; it is only for a clean kernel tree without those files.
- `patches/0002-susfs-fix-ctime-bitmask.patch` changes `KSTAT_SPOOF_CTIME_TV_SEC` from the comparison `(1 < 8)` to the bit flag `(1 << 8)`. The matching `ksu_susfs` userspace constants and behavior must be audited/version-matched before enabling SUS_KSTAT for device testing.

## 4. Complete the missing KSUN/config integration before building

The KernelSU-Next commit currently pinned in the Xen-Kernel workflow is `465490a26667ba4cf00b3be975a7e28e53978829`. Its `kernel/Kconfig` does not define `CONFIG_KSU_SUSFS` or the SUSFS feature symbols. Therefore, do not just append `CONFIG_KSU_SUSFS=y` to `vayu_defconfig`: `olddefconfig` cannot retain a symbol that the integrated KSUN Kconfig does not declare.

Before calling the port complete:

1. Integrate and pin a KSUN revision that actually implements the SUSFS v2.3.0 config/API/ioctl interface expected by this kernel source.
2. Add the corresponding feature Kconfig symbols and source dependencies; check every symbol referenced by `fs/susfs.c` and `include/linux/susfs*.h`.
3. Port all conflicted VFS/proc/mount/stat call sites by hand, preserving Xen-Kernel's KSUN manual-hook edits. Do not blindly import generic KSUN syscall-hook changes or unrelated credential changes from the reference tree.
4. Add the proper build wiring and config options, run `make olddefconfig`, and inspect `.config` to ensure the intended symbols remain enabled and `KPROBES` stays disabled.
5. Run the full kernel build and inspect the logs. Only after a successful build should you plan device tests; do not flash a kernel from the candidate artifact alone.

## 5. Keep the review reproducible

Keep the original `16-KSUN_SuSFS` branch unchanged while reviewing. After the call sites, KSUN integration, configuration, and build all pass review, commit the changes on your own review branch and open a separate PR or merge them deliberately. The candidate workflow itself never pushes to Xen-Kernel.
