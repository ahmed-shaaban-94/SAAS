"""POS import codemod — rewrite imports after Phase 1 Task 2.4 mechanical move.

Run: python scripts/pos-import-codemod.py

Idempotent — running multiple times is safe (subsequent runs find nothing to do).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# (pattern, replacement) — Python re semantics, raw strings.
RULES: list[tuple[str, str]] = [
    # @/components/pos/X -> @pos/components/X
    (r"""(['"])@/components/pos/""", r"\1@pos/components/"),
    # @/hooks/use-pos-X -> @pos/hooks/use-pos-X
    (r"""(['"])@/hooks/use-pos-""", r"\1@pos/hooks/use-pos-"),
    # @/store/pos-cart-store -> @pos/store/cart-store  (rename: drop "pos-" prefix)
    (r"""(['"])@/store/pos-cart-store(['"])""", r"\1@pos/store/cart-store\2"),
    # @/contexts/pos-cart-context -> @pos/contexts/pos-cart-context
    (r"""(['"])@/contexts/pos-cart-context""", r"\1@pos/contexts/pos-cart-context"),
    # @/lib/pos/X -> @pos/lib/X
    (r"""(['"])@/lib/pos/""", r"\1@pos/lib/"),
    # @/types/pos -> @pos/types/pos
    (r"""(['"])@/types/pos(['"])""", r"\1@pos/types/pos\2"),
]


def rewrite(text: str) -> tuple[str, int]:
    """Apply all rules, return (new_text, hit_count)."""
    hits = 0
    for pattern, replacement in RULES:
        new_text, n = re.subn(pattern, replacement, text)
        if n:
            text = new_text
            hits += n
    return text, hits


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    targets = [
        *(root / "frontend" / "src").rglob("*.ts"),
        *(root / "frontend" / "src").rglob("*.tsx"),
        *(root / "pos-desktop" / "src").rglob("*.ts"),
        *(root / "pos-desktop" / "src").rglob("*.tsx"),
    ]
    # Skip node_modules, .next, dist, build artefacts.
    skip_parts = {"node_modules", ".next", "dist", "out", ".turbo"}
    targets = [p for p in targets if not any(part in skip_parts for part in p.parts)]

    total_files = 0
    total_hits = 0
    for path in targets:
        try:
            before = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        after, hits = rewrite(before)
        if hits:
            path.write_text(after, encoding="utf-8")
            total_files += 1
            total_hits += hits
            print(f"  {path.relative_to(root)}  ({hits})")

    print(f"\n{total_files} file(s) rewritten, {total_hits} import(s) updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
