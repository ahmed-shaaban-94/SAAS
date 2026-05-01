"""Reverse the POS import codemod — restore @/ imports.

Used to roll back Phase 1 Task 2.4-2.5 when the move turned out to need
deferral to Sub-PR 2 (Vite migration). Idempotent.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RULES: list[tuple[str, str]] = [
    (r"""(['"])@pos/components/""", r"\1@/components/pos/"),
    (r"""(['"])@pos/hooks/use-pos-""", r"\1@/hooks/use-pos-"),
    (r"""(['"])@pos/store/cart-store(['"])""", r"\1@/store/pos-cart-store\2"),
    (r"""(['"])@pos/contexts/pos-cart-context""", r"\1@/contexts/pos-cart-context"),
    (r"""(['"])@pos/lib/""", r"\1@/lib/pos/"),
    (r"""(['"])@pos/types/pos(['"])""", r"\1@/types/pos\2"),
]


def rewrite(text: str) -> tuple[str, int]:
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
    skip = {"node_modules", ".next", "dist", "out", ".turbo"}
    targets = [p for p in targets if not any(part in skip for part in p.parts)]

    files = 0
    hits = 0
    for path in targets:
        try:
            before = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        after, n = rewrite(before)
        if n:
            path.write_text(after, encoding="utf-8")
            files += 1
            hits += n
            print(f"  {path.relative_to(root)}  ({n})")

    print(f"\n{files} file(s) rewritten, {hits} import(s) reverted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
