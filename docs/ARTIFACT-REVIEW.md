# Artifact review: `xen-susfs-4.14-candidate`

## Verdict

**Do not apply this artifact to Xen-Kernel yet.** The archive is structurally readable and its revision pins are consistent, but it is not compatible with the current Xen-Kernel build workflow without further integration work.

## Artifact and source integrity

- Target SHA: `08f4c4761c14f6b30b5efb6b8bd0b817b39eb1c3`
- Base SHA: `0f8b1c04302094439718fa5d8d9122d9f89a730b`
- Feature SHA: `67696276f509631e85759d8fdf43e4d90246a281`
- `reports/clean-files.txt`: 32 files
- `reports/conflicts.txt`: empty
- `reports/missing-files.txt`: empty
- `git apply --stat`: parses a 32-file patch, 1,733 insertions and 422 deletions
- `reports/diff-check.txt`: five trailing-whitespace diagnostics

Zero textual merge conflicts means `git merge-file` found no overlapping text edits it could not reconcile. It does **not** validate semantic compatibility or guarantee a successful build.

## Blocking issue 1: duplicate manual-hook guards

The candidate adds KernelSU hook code to `fs/open.c` (`ksu_handle_faccessat`) and `fs/stat.c` (`ksu_handle_stat`).

The target build workflow runs `scripts/apply-ksun-manual-hooks.py` before compiling. Its `patch_open()` and `patch_stat()` functions explicitly raise an error whenever those hook names already exist. Applying this candidate unchanged will therefore make the existing manual-hook step abort, unless either the candidate is curated to keep the manual hook implementation authoritative or the hook script is deliberately adapted to verify and skip already-integrated hooks.

Do not bypass this check blindly: the reference `fs/stat.c` contains more syscall variants than the current manual hook script's native-only insertion, so their intended coverage needs review.

## Blocking issue 2: KernelSU-Next SUSFS version mismatch

The current Xen-Kernel build workflow pins `Lvyana-ren/KernelSU-Next` at `465490a26667ba4cf00b3be975a7e28e53978829`. That commit's `kernel/Kconfig` does **not** declare `CONFIG_KSU_SUSFS` or its feature options.

However, `Xen-SuSFS:16-ksu` has a KernelSU-Next submodule gitlink at `68f01be106d5fe4f28177b1d1d45e69beebbb002`; that commit's Kconfig *does* define `CONFIG_KSU_SUSFS` and the feature symbols. These are different KSUN revisions. The target's current pin and the feature tree's KSUN interface must be reconciled deliberately, including manager/userspace API compatibility. Do not assume adding `CONFIG_KSU_SUSFS=y` to `vayu_defconfig` enables SUSFS while Kconfig does not define the symbol; `olddefconfig` may drop it.

## Other items to review

- `fs/proc/task_mmu.c` has a large refactor (567 changed lines by the patch summary); inspect it as a functional port, not merely as a clean merge.
- `fs/proc/task_nommu.c` has removed TID-specific map operations but has no SUSFS-specific symbols in the candidate's changed lines. Review whether this inherited refactor is necessary for this ARM64 target.
- `fs/namespace.c` and `fs/super.c` contain IDA API/backport changes in addition to SUSFS mount handling. These may be required by the v2.3.0 port, but need to remain in the dependency audit.
- The defconfig comment says `SuSFS 1.5.3+`, while the source header declares `v2.3.0`; update the wording when curating the config patch.
- Remove the five trailing-whitespace lines before finalizing the patch series.

## Safe next sequence

1. Reconcile the exact KernelSU-Next revision and its manager/userspace interface with the `Xen-SuSFS` source submodule.
2. Resolve the duplicate-hook workflow failure without losing required syscall coverage.
3. Decide which inherited backports are required; discard unrelated source-ref changes.
4. Normalize whitespace and regenerate the candidate.
5. Apply-check against the exact target SHA, run `olddefconfig`, inspect the resulting symbols, then run a full kernel build.
6. Only proceed to device testing after a successful build. This artifact has not been compile-tested.
