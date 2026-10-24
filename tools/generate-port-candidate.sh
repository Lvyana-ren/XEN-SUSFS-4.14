#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 4 ]]; then
  echo "Usage: $0 BASE_KERNEL_DIR TARGET_KERNEL_DIR FEATURE_KERNEL_DIR OUTPUT_DIR" >&2
  exit 2
fi

BASE_DIR=$(realpath "$1")
TARGET_DIR=$(realpath "$2")
FEATURE_DIR=$(realpath "$3")
OUT_DIR=$(realpath -m "$4")
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SCOPE_FILE="$REPO_ROOT/patches/susfs-callsite-files.txt"

BASE_COMMIT=$(git -C "$BASE_DIR" rev-parse HEAD)
TARGET_COMMIT=$(git -C "$TARGET_DIR" rev-parse HEAD)
FEATURE_COMMIT=$(git -C "$FEATURE_DIR" rev-parse HEAD)

check_expected_sha() {
  local label="$1"
  local actual="$2"
  local expected="$3"

  if [[ -n "$expected" && "$actual" != "$expected" ]]; then
    echo "::error::Pinned SHA mismatch for $label: expected $expected, got $actual" >&2
    exit 10
  fi
}

check_expected_sha "base" "$BASE_COMMIT" "${EXPECTED_BASE_SHA:-}"
check_expected_sha "target" "$TARGET_COMMIT" "${EXPECTED_TARGET_SHA:-}"
check_expected_sha "feature" "$FEATURE_COMMIT" "${EXPECTED_FEATURE_SHA:-}"

# Never modify a target checkout that already contains work from the user.
if [[ -n "$(git -C "$TARGET_DIR" status --porcelain)" ]]; then
  echo "ERROR: Target checkout is not clean; refusing to generate a candidate." >&2
  exit 11
fi

mkdir -p "$OUT_DIR/reports/conflicts" "$OUT_DIR/reports/merge"
: > "$OUT_DIR/reports/clean-files.txt"
: > "$OUT_DIR/reports/conflicts.txt"
: > "$OUT_DIR/reports/missing-files.txt"

cat > "$OUT_DIR/reports/input-refs.txt" <<EOF
Base repository: ${BASE_REPO:-unknown}
Base ref label: ${BASE_REF:-unknown}
Base commit SHA: $BASE_COMMIT

Target repository: ${TARGET_REPO:-unknown}
Target ref label: ${TARGET_REF:-unknown}
Target commit SHA: $TARGET_COMMIT

Feature repository: ${FEATURE_REPO:-unknown}
Feature ref label: ${FEATURE_REF:-unknown}
Feature commit SHA: $FEATURE_COMMIT
EOF

# Keep a dedicated file for compatibility with the application guide.
printf '%s\n' "$TARGET_COMMIT" > "$OUT_DIR/reports/target-baseline-commit.txt"

while IFS= read -r rel || [[ -n "$rel" ]]; do
  [[ -z "$rel" || "$rel" =~ ^[[:space:]]*# ]] && continue

  base="$BASE_DIR/$rel"
  ours="$TARGET_DIR/$rel"
  theirs="$FEATURE_DIR/$rel"
  missing=0

  for file in "$base" "$ours" "$theirs"; do
    if [[ ! -f "$file" ]]; then
      printf '%s\tmissing input: %s\n' "$rel" "$file" >> "$OUT_DIR/reports/missing-files.txt"
      missing=1
    fi
  done
  [[ "$missing" -eq 1 ]] && continue

  merged=$(mktemp)
  set +e
  git merge-file --diff3 -p "$ours" "$base" "$theirs" > "$merged"
  status=$?
  set -e

  if [[ "$status" -eq 0 ]]; then
    if ! cmp -s "$ours" "$merged"; then
      cp "$merged" "$ours"
      printf '%s\n' "$rel" >> "$OUT_DIR/reports/clean-files.txt"
    fi
  elif [[ "$status" -eq 1 ]]; then
    mkdir -p "$OUT_DIR/reports/conflicts/$(dirname "$rel")"
    cp "$merged" "$OUT_DIR/reports/conflicts/$rel.merge"
    printf '%s\n' "$rel" >> "$OUT_DIR/reports/conflicts.txt"
  else
    printf 'git merge-file failed (%s) for %s\n' "$status" "$rel" >&2
    rm -f "$merged"
    exit "$status"
  fi
  rm -f "$merged"
done < "$SCOPE_FILE"

# SUSFS build wiring: add the object line only when absent.
python3 - "$TARGET_DIR/fs/Makefile" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text()

line = "obj-$(CONFIG_KSU_SUSFS) += susfs.o"
if line in text:
    print("fs/Makefile: SUSFS object line already exists")
else:
    marker = "ifeq ($(CONFIG_BLOCK),y)"
    if marker not in text:
        raise SystemExit("Cannot find safe fs/Makefile insertion point")
    text = text.replace(marker, line + "\n\n" + marker, 1)
    path.write_text(text)
    print("fs/Makefile: added SUSFS object line")
PY

# Candidate patch is a worktree diff against the pinned target commit.
git -C "$TARGET_DIR" diff --binary --no-ext-diff > "$OUT_DIR/xen-susfs-kernel-integration-candidate.patch"

{
  echo "Three-way SUSFS port candidate"
  echo
  echo "Base: ${BASE_REPO:-unknown} @ $BASE_COMMIT (${BASE_REF:-unknown})"
  echo "Target: ${TARGET_REPO:-unknown} @ $TARGET_COMMIT (${TARGET_REF:-unknown})"
  echo "Feature reference: ${FEATURE_REPO:-unknown} @ $FEATURE_COMMIT (${FEATURE_REF:-unknown})"
  echo
  echo "These SHA values are also recorded in reports/input-refs.txt."
  echo "This is a candidate. A clean text merge does not prove semantic correctness or buildability."
  echo "Files with conflicts are unchanged in TARGET_DIR and saved under reports/conflicts/."
  echo "Review the generated patch for unrelated changes before applying."
  echo
  echo "Cleanly merged files:"
  cat "$OUT_DIR/reports/clean-files.txt"
  echo
  echo "Conflicting files:"
  cat "$OUT_DIR/reports/conflicts.txt"
  echo
  echo "Missing-input files:"
  cat "$OUT_DIR/reports/missing-files.txt"
} > "$OUT_DIR/README-CANDIDATE.txt"

# Save applyability/whitespace diagnostics for review.
git -C "$TARGET_DIR" diff --check > "$OUT_DIR/reports/diff-check.txt" 2>&1 || true

echo "Candidate patch: $OUT_DIR/xen-susfs-kernel-integration-candidate.patch"
echo "Base SHA: $BASE_COMMIT"
echo "Target SHA: $TARGET_COMMIT"
echo "Feature SHA: $FEATURE_COMMIT"
echo "Clean files: $(wc -l < "$OUT_DIR/reports/clean-files.txt")"
echo "Conflicts: $(wc -l < "$OUT_DIR/reports/conflicts.txt")"
echo "Review required before use."
