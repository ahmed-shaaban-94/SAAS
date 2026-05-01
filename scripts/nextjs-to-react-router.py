"""Convert Next.js page conventions to React Router for the Vite migration.

Targets pos-desktop/src/pages/*.tsx and pos-desktop/src/components/**/*.tsx that
use next/navigation hooks. Sub-PR 2 Phase 1 Task 3.3 step 5.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def convert(text: str) -> tuple[str, list[str]]:
    changes: list[str] = []
    new = text

    # Drop "use client" — Vite is all client.
    if re.search(r'^"use client";?\s*$', new, flags=re.MULTILINE):
        new = re.sub(r'^"use client";?\s*\n', "", new, flags=re.MULTILINE)
        changes.append("dropped 'use client'")

    # Replace next/navigation imports.
    if "next/navigation" in new:
        # useRouter -> useNavigate
        new = re.sub(
            r'import\s*\{\s*useRouter\s*\}\s*from\s*["\']next/navigation["\'];?',
            'import { useNavigate } from "react-router-dom";',
            new,
        )
        # useRouter + useSearchParams (combined)
        new = re.sub(
            r'import\s*\{\s*useRouter\s*,\s*useSearchParams\s*\}\s*from\s*["\']next/navigation["\'];?',
            'import { useNavigate, useSearchParams } from "react-router-dom";',
            new,
        )
        # useSearchParams + useRouter (combined, reversed)
        new = re.sub(
            r'import\s*\{\s*useSearchParams\s*,\s*useRouter\s*\}\s*from\s*["\']next/navigation["\'];?',
            'import { useSearchParams, useNavigate } from "react-router-dom";',
            new,
        )
        # bare useSearchParams
        new = re.sub(
            r'import\s*\{\s*useSearchParams\s*\}\s*from\s*["\']next/navigation["\'];?',
            'import { useSearchParams } from "react-router-dom";',
            new,
        )
        # usePathname -> useLocation
        new = re.sub(
            r'import\s*\{\s*usePathname\s*\}\s*from\s*["\']next/navigation["\'];?',
            'import { useLocation } from "react-router-dom";',
            new,
        )

        # Hook call rename
        new = re.sub(r'\buseRouter\(\)', 'useNavigate()', new)
        new = re.sub(r'const\s+router\s*=\s*useNavigate\(\)', 'const navigate = useNavigate()', new)

        # router.push("/x") -> navigate("/x")
        new = re.sub(r'\brouter\.push\(', 'navigate(', new)
        # router.replace("/x") -> navigate("/x", { replace: true })
        new = re.sub(r'\brouter\.replace\(([^)]+)\)', r'navigate(\1, { replace: true })', new)
        # router.back() -> navigate(-1)
        new = re.sub(r'\brouter\.back\(\)', 'navigate(-1)', new)
        # router.refresh() -> window.location.reload()
        new = re.sub(r'\brouter\.refresh\(\)', 'window.location.reload()', new)

        changes.append("next/navigation -> react-router-dom")

    # Replace next/font/google: drop the import block (handled in layout.tsx separately).
    # Caller will inject `import "@pos/styles/fonts.css"` at top of layout.tsx.
    return new, changes


def main() -> int:
    targets = list(ROOT.glob("pos-desktop/src/pages/*.tsx")) + list(
        ROOT.glob("pos-desktop/src/components/**/*.tsx")
    )
    changed = 0
    for p in targets:
        before = p.read_text(encoding="utf-8")
        after, changes = convert(before)
        if after != before:
            p.write_text(after, encoding="utf-8")
            changed += 1
            print(f'  {p.relative_to(ROOT)}: {", ".join(changes)}')
    print(f"\n{changed} file(s) converted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
