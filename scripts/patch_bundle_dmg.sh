#!/bin/bash
# Patches bundle_dmg.sh to use --skip-jenkins (avoids AppleScript Finder timeout in non-interactive environments)
# This works because the script is regenerated on each build, so we patch it after generation

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUNDLE_DMG="$PROJECT_ROOT/frontend/src-tauri/target/release/bundle/dmg/bundle_dmg.sh"

if [ -f "$BUNDLE_DMG" ]; then
    if grep -q "SKIP_JENKINS=0" "$BUNDLE_DMG" 2>/dev/null; then
        sed -i '' 's/SKIP_JENKINS=0/SKIP_JENKINS=1/' "$BUNDLE_DMG"
        echo "Patched bundle_dmg.sh to skip Jenkins (SKIP_JENKINS=1)"
    fi
else
    echo "bundle_dmg.sh not found at $BUNDLE_DMG"
    exit 1
fi
