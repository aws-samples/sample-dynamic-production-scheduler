#!/bin/bash
# Bundle Lambda dependencies locally (no Docker required)
# Uses Python 3.11 to match Lambda runtime
# Two-pass install: Linux x86_64 binaries first, then pure-python fallbacks

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON="/opt/homebrew/bin/python3.11"
PIP="$PYTHON -m pip"

bundle_lambda() {
    local NAME="$1"
    local REQ_FILE="$2"
    local SRC_DIR="$3"
    local BUNDLE_DIR="$ROOT_DIR/$NAME/.lambda-bundle"

    echo "=== Bundling $NAME Lambda ==="
    rm -rf "$BUNDLE_DIR"
    mkdir -p "$BUNDLE_DIR"

    # Step 1: Install with Linux x86_64 platform targeting
    # This gets correct binary wheels for pydantic-core, etc.
    echo "  Step 1: Installing Linux x86_64 packages..."
    $PIP install \
        -r "$REQ_FILE" \
        -t "$BUNDLE_DIR" \
        --platform manylinux2014_x86_64 \
        --implementation cp \
        --python-version 3.11 \
        --only-binary=:all: \
        --quiet 2>&1 | grep -v "WARNING" || true

    # Step 2: For any pure-python packages that failed --only-binary,
    # install them without platform constraint but skip already-installed ones
    echo "  Step 2: Installing pure-python fallbacks..."
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        # Extract package name (before any version specifier)
        pkg=$(echo "$line" | sed 's/[>=<\[].*//;s/ //g')
        # Check if already installed in bundle
        if [ -d "$BUNDLE_DIR/$pkg" ] || [ -d "$BUNDLE_DIR/${pkg//-/_}" ]; then
            continue
        fi
        echo "    Installing missing: $pkg"
        $PIP install "$line" -t "$BUNDLE_DIR" --quiet 2>/dev/null || true
    done < "$REQ_FILE"

    # Step 3: Remove any macOS Mach-O binaries that leaked in
    local removed=0
    while IFS= read -r sofile; do
        if file "$sofile" 2>/dev/null | grep -q "Mach-O"; then
            rm -f "$sofile"
            removed=$((removed + 1))
        fi
    done < <(find "$BUNDLE_DIR" -name "*.so" -o -name "*.dylib" 2>/dev/null)
    [ $removed -gt 0 ] && echo "  Removed $removed macOS-native binaries"

    # Step 4: Copy application source code
    cp -r "$SRC_DIR" "$BUNDLE_DIR/"

    # Verify
    local count=$(ls "$BUNDLE_DIR" | wc -l | tr -d ' ')
    echo "  -> $count top-level entries in $BUNDLE_DIR"

    # Check pydantic_core specifically
    if ls "$BUNDLE_DIR"/pydantic_core/_pydantic_core*.so 1>/dev/null 2>&1; then
        local arch=$(file "$BUNDLE_DIR"/pydantic_core/_pydantic_core*.so 2>/dev/null | head -1)
        echo "  -> pydantic_core binary: OK"
        echo "     $arch"
    else
        echo "  WARNING: pydantic_core .so NOT found — Lambda will fail!"
    fi
}

bundle_lambda "erp-data-mcp" \
    "$ROOT_DIR/erp-data-mcp/requirements.txt" \
    "$ROOT_DIR/erp-data-mcp/src/erp_data_mcp"

bundle_lambda "audit-mcp" \
    "$ROOT_DIR/audit-mcp/requirements.txt" \
    "$ROOT_DIR/audit-mcp/src/audit_mcp"

echo ""
echo "=== Done. Lambda bundles ready for CDK deploy ==="
