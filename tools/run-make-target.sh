#!/usr/bin/env bash
set -u

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
REPO_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"

TARGET="${1:-}"
ACTION_LABEL="${2:-$TARGET}"

if [[ -z "$TARGET" ]]; then
    echo "Usage: $(basename "$0") <make-target> [label]"
    echo
    read -r -p "Press Enter to close..."
    exit 1
fi

cd "$REPO_DIR" || exit 1

echo "${ACTION_LABEL}..."

if command -v make >/dev/null 2>&1; then
    make "$TARGET"
    EXIT_CODE=$?
else
    echo "Error: 'make' is not available in PATH."
    echo "Install GNU Make and try again."
    EXIT_CODE=127
fi

echo
if [[ "$EXIT_CODE" -eq 0 ]]; then
    echo "Finished successfully."
else
    echo "The command failed with exit code $EXIT_CODE."
fi

echo
read -r -p "Press Enter to close..."
exit "$EXIT_CODE"
