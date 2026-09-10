set shell := ["bash", "-uc"]

sync:
    #!/usr/bin/env bash
    set -euo pipefail
    out=$(python generate.py 2>&1)
    printf '%s\n' "$out"
    if grep -q "Warning: failed to download" <<<"$out"; then
        echo "Jacket download failed; aborting before push." >&2
        exit 1
    fi
    git add -f data/
    git commit -m "data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    git push
