# Phase 4 -- Public Website

**Status**: DONE
**Scope**: Marketing/landing page for the DataPulse SaaS platform

## Overview

Phase 4 delivers a public-facing marketing website within the existing Next.js 14 frontend. The implementation uses a route group restructure to separate marketing pages from the authenticated app, with zero new dependencies and zero image assets.

## Architecture Decision

The frontend was restructured into two route groups:

| Route Group | Purpose | Layout |
|-------------|---------|--------|
| `(marketing)` | Public pages -- landing, pricing, legal | Navbar + Footer |
| `(app)` | Authenticated dashboard pages | Sidebar + Header |

This keeps a single Next.js deployment while cleanly separating public and private concerns.

## Sub-Phases

| Sub-Phase | Title | Status |
|-----------|-------|--------|
| [4.1](./4.1-setup-and-hero.md) | Setup and Hero Section | DONE |
| [4.2](./4.2-features-and-pipeline.md) | Features and Pipeline Visualization | DONE |
| [4.3](./4.3-pricing-and-faq.md) | Pricing and FAQ | DONE |
| [4.4](./4.4-auth-and-waitlist.md) | Auth Pages and Waitlist | DONE |
| [4.5](./4.5-seo-and-performance.md) | SEO and Performance | DONE |
| [4.6](./4.6-polish-and-testing.md) | Polish and Testing | DONE |

## Key Constraints

- **Zero new dependencies** -- everything built with Next.js 14, Tailwind CSS, and native browser APIs
- **Zero images** -- all visuals are CSS-only (dashboard mockup, pipeline diagram, icons)
- **Dark/light mode** -- inherits the existing `next-themes` setup
- **Accessible** -- skip-to-content link, ARIA attributes, keyboard navigation, reduced motion support

## Deliverables Summary

- Route group restructure with marketing and app layouts
- Hero section with CSS-only dashboard mockup
- Features grid (6 cards) and pipeline visualization (4 steps)
- Stats banner with animated count-up
- 3 pricing cards and FAQ accordion (8 questions)
- Tech badges section
- Waitlist form with API route
- Privacy policy and terms of service pages
- CTA section
- Full SEO: meta tags, Open Graph, Twitter cards, JSON-LD, sitemap.xml, robots.txt, OG image generation
- 18 E2E tests
- Accessibility: skip-to-content, ARIA, keyboard nav, reduced motion
