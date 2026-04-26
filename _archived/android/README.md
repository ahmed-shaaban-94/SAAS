# Android (Legacy)

**Status:** Legacy — see [ADR 007](../docs/adr/007-platform-matrix.md) and
[Platform Matrix](../docs/PLATFORM_MATRIX.md).

This directory hosts the earlier Kotlin + Jetpack Compose Android app. It is
**not actively developed**. Future native mobile work ships as React Native
(`mobile/` when scaffolded), reusing the TypeScript contracts and responsive
layout of the canonical web surface.

What still happens here:

- The code continues to build so existing installs are not broken.
- Security patches may land if an advisory forces one.

What does NOT happen here:

- New features.
- API-contract migrations (new backend models aren't wired to Kotlin).
- Responsive/UX redesigns (those live in `frontend/` and flow to React
  Native when it lands).

If you're starting mobile work today, do not extend this directory — scope
the work against React Native and reference the platform matrix for
rationale.
