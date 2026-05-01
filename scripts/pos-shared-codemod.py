"""Rewrite POS-side imports of cross-cut frontend modules to use @shared/* alias.

Run after the file move (Sub-PR 2). For files now under pos-desktop/src/,
the @/* alias still points at frontend/src/ (frontend's tsconfig). To make
those imports survive, rewrite them to @shared/* which is configured in
pos-desktop's tsconfig.app.json + frontend's vitest.config.ts to resolve to
frontend/src/.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Each rule is (pattern, replacement) — pattern matches the part AFTER the quote.
RULES: list[tuple[str, str]] = [
    # Relative ../api-client (from pos-desktop/src/lib/) — goes to @shared/lib/api-client
    (r'\.\./api-client', '@shared/lib/api-client'),
    # @/-prefixed cross-cuts → @shared/-prefixed
    (r'@/lib/api-client', '@shared/lib/api-client'),
    (r'@/lib/utils', '@shared/lib/utils'),
    (r'@/lib/auth-bridge', '@shared/lib/auth-bridge'),
    (r'@/lib/swr-config', '@shared/lib/swr-config'),
    (r'@/components/empty-state', '@shared/components/empty-state'),
    (r'@/components/auth-provider', '@shared/components/auth-provider'),
    (r'@/components/branding/brand-provider', '@shared/components/branding/brand-provider'),
    (r'@/components/error-boundary', '@shared/components/error-boundary'),
    (r'@/components/ui/toast', '@shared/components/ui/toast'),
    (r'@/components/ui/', '@shared/components/ui/'),
    (r'@/hooks/use-active-shift', '@shared/hooks/use-active-shift'),
    (r'@/hooks/use-branding', '@shared/hooks/use-branding'),
    (r'@/hooks/use-drug-search', '@shared/hooks/use-drug-search'),
    (r'@/hooks/use-eligible-promotions', '@shared/hooks/use-eligible-promotions'),
    (r'@/hooks/use-jwt-bridge', '@shared/hooks/use-jwt-bridge'),
    (r'@/hooks/use-manager-override', '@shared/hooks/use-manager-override'),
    (r'@/hooks/use-offline-state', '@shared/hooks/use-offline-state'),
    (r'@/hooks/use-renderer-crash-bridge', '@shared/hooks/use-renderer-crash-bridge'),
    (r'@/hooks/use-voucher-validate', '@shared/hooks/use-voucher-validate'),
    # POS-only CSS path changed
    (r'@/styles/pos-globals\.css', '@pos/styles/globals.css'),
]


def rewrite(text: str) -> tuple[str, int]:
    hits = 0
    for pattern, replacement in RULES:
        # Match within an import string: from "<pattern>" or from '<pattern>'
        # and also: import "<pattern>"
        regex = r'(["\'])' + pattern + r'(["\'])'
        new = re.sub(regex, lambda m, r=replacement: m.group(1) + r + m.group(2), text)
        if new != text:
            hits += text.count(pattern)
            text = new
    return text, hits


def main() -> int:
    targets = list(ROOT.glob("pos-desktop/src/**/*.ts")) + list(
        ROOT.glob("pos-desktop/src/**/*.tsx")
    )
    files = 0
    total = 0
    for p in targets:
        try:
            before = p.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        after, hits = rewrite(before)
        if after != before:
            p.write_text(after, encoding='utf-8')
            files += 1
            total += hits
            print(f'  {p.relative_to(ROOT)}  ({hits})')
    print(f'\n{files} file(s) rewritten, {total} import(s) updated')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
