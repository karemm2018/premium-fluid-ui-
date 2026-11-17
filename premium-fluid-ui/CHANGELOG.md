# Release history

## 1.9.2 — Mandatory Design Conformance / Safe Review-Gated Automation

- Converted the former high-severity-only exemption into a **must-fix rule for every verified P0/P1/P2** typography, spacing, framing, column-count, header and mobile-flow mismatch. Healthy components must remain unchanged.
- Locked the default 2D design reference at **1536×864 CSS px**, with existing calibrated width/height root scaling and role-specific type/readability checks. Added [`references/mandatory-conformance.md`](references/mandatory-conformance.md) with measurable acceptance matrix, intentional exceptions, and `FIXED / EXCEPTION / BLOCKED / UNVERIFIED / CANDIDATE` evidence statuses.
- Fixed broken regular expressions in `static_css_audit.py` (including the import-crashing media-collapse regex); restored real detection of heavy CSS font weights, SVG pixel attributes, fixed Tailwind containers and late desktop header collapse.
- Made potentially destructive codemod operations **opt-in and review-gated**: no automatic all-site grid collapse, weight normalization, or container replacement. Application requires `--apply --reviewed`, with scoped optional `--frame-containers`, `--balance-weights`, and `--reflow-grids` flags and before/after validation.
- Scoped sample CSS media, font-weight and overflow helpers to opt-in project classes; removed global overflow masking and blanket `h1` / image / video rules that could corrupt third-party brand designs.
- Strengthened desktop side-framing checks toward the documented 12–14% target rather than alerting only on <9% margins; fixed classic-scrollbar asymmetry with `scrollbar-gutter: stable both-edges` and default `73vw` content width (without an implicit ultra-wide cap). Full-bleed backgrounds and documented intentional exceptions are exempt.
- Synchronized top-level README/version reporting and expanded automated tests. This release updates the **reusable skill only**, not any client repository.


## 1.7.0 — Full-Site Automation: Fluid Codemod, Multi-Page Crawler, Real Browser Zoom & RTL Carousel Edge QA

- Added `scripts/fluid_codemod.py` (`--dry-run` / `--apply`): automatically converts arbitrary Tailwind pixel values (`w-[400px]` -> `w-[25rem]`), upgrades `max-w-7xl mx-auto` containers to framed desktop containers (`lg:w-[min(73vw,78rem)]` preserving `~13.5%` side whitespace on all PC monitors), prepends `grid-cols-1` to unprefixed multi-column mobile grids, and balances extreme Arabic font weights across an entire repository in seconds.
- Added `--routes` and `--crawl` (`--max-pages`) flags to `scripts/responsive_audit.py` to audit multiple pages across a site instead of only a single URL.
- Added `--real-zoom` to `scripts/responsive_audit.py` to execute genuine in-browser CSS zoom (`125%`) and root font-size stress tests (`150%` on mobile, `200%` WCAG resize on desktop) automatically inside Chromium.
- Added automated RTL/LTR Carousel Edge Clipping detection (`carousel-card-clipped-at-edge`) to `scripts/responsive_audit.py`.

## 1.6.0 — Mandatory Desktop Side-Whitespace Framing (~13.5% per side across all PC screens)

- Added mandatory desktop side-whitespace framing (`inline-size: min(73vw, 78rem); margin-inline: auto;`) on all computer viewports (`>= 1024px`) so `1024x600`, `1280x720`, `1366x768`, `1440x900`, and `1920x1080` always preserve `~13.5%` empty margin on both right and left sides.
- Added `desktop-insufficient-side-whitespace` browser check in `responsive_audit.py` and `tailwind-container-loses-desktop-side-whitespace` static check in `static_css_audit.py`.

## 1.5.0 — Two-Tier Desktop-First Proportional Scaling & Adaptive Arabic Font Weights

- Added `assets/desktop-first-scale.css` implementing Tier 1 2D proportional root scaling (`60%–100%`) on `>= 1024px` screens and Tier 2 structural reflow on `< 1024px` screens, plus adaptive Arabic font-weight tokens (`400–700`) and 5 anti-distortion guards.

## 1.4.0 — 2D Space Budget, Structural Reflow, RTL Full-Height Audit, Landscape, Low-Res & 1024x600 Support

- Upgraded `scripts/responsive_audit.py` to check **both left (`rect.left < -3`, critical for RTL) and right (`rect.right > vw + 3`) viewport edges across the full document height** (removing the `r.top < vh` first-fold limitation).
- Added full-page text-node Range clipping (`clipped-text-content`) and text-outside-viewport (`text-outside-viewport`) checks to `responsive_audit.py`, upgrading real text clipping from `review` to `high`.
- Added floating/absolute overlay collision detection (`floating-or-absolute-overlap`), mobile header crowding checks (`header-crowding-overflow`, `header-excessive-height`), and short-viewport vertical crush detection (`short-viewport-vertical-crush`, `vertical-overflow-clipped-short-viewport`).
- Expanded `QUICK` and `FULL` test matrices to include **`1024x600` (WSVGA / compact landscape)**, **low-resolution displays** (`1366x768`, `1280x720`, `800x480`, `360x640`, `320x568`), **mobile landscape** (`667x375`, `740x360`, `844x390`), and **tablet portrait/landscape** (`768x1024`, `1024x768`, `820x1180`, `1180x820`, `960x600`, `600x960`).
- Upgraded `scripts/static_css_audit.py` to flag fixed widths `>= 260px`, standard Tailwind fixed widths (`w-64`, `w-72`, `w-80`, `w-96`), unprefixed multi-column grids (`grid-cols-2` without `grid-cols-1` mobile base), negative horizontal margins (`-mx-*`), unconditional `absolute` classes without responsive `static` reset, and rigid `100vh`/`h-screen` heights.
- Added `--sync-viewport` option to `scripts/component_audit.py` so component sweeps can trigger `@media` queries and Tailwind breakpoints (`sm:`, `md:`, `lg:`) alongside short landscape heights.
- Updated `SKILL.md` and `references/` with explicit **Structural Reflow Rules** (collapsing secondary header CTAs into mobile drawers, stacking `position: absolute` hero cards below `1024px` or `680px` height, reserving footer FAB clearance, and gating desktop vertical layouts by both width and height).

## 1.3.0 — Component-aware geometry and evidence

- Added a stand-alone browser component-width sweep (`scripts/component_audit.py`) that holds the viewport fixed, changes card width, and generates PNG screenshots, HTML gallery and JSON diagnostics. No server launch or code mutation.
- Added text-node Range rectangle collision detection, clipped text within internal overflow boundaries, and text outside a component.
- Added optional proportional artwork markers (`data-pf-proportional`, `data-pf-part`) to detect fixed graphics, aspect drift and internal part position/size drift.
- Added four component fixtures (healthy, fixed+colliding, clipped, aspect drift) and executable Chromium regression (`scripts/test_component_browser.py`).
- Added optional permission-gated `interaction_smoke.py` for non-destructive menu click/Escape behavior, paired healthy/broken fixtures and browser regression tests.
- Added on-demand technical reference and proportional-art CSS pattern; mandatory component-level QA gate for nested cards/carousels.
- Preserved v1.2 Personal Luxury type tokens, original CSS/JSX audit and before/after workflow. No FBS repo change.

## 1.2.0 — Personal Luxury typography system

- Adopted the experimentally chosen portable signature: H1 ~32–42, H2 ~22–26, H3 ~18–19, body 15, secondary 12–13 (CSS pixel equivalents only).
- Implemented a reusable `rem` / `clamp()` CSS token and opt-in class file in `assets/luxury-fluid-typography.css`.
- Aligned the older example tokens with this single source of truth; removed conflicting large-font recommendations from typography reference.
- Documented when to apply globally, map existing Tailwind tokens, or preserve an approved site during repair-only tasks.
- Added container-aware proportional artifact guidance, Arabic type readability, and manual genuine browser zoom checks.
- Added browser computed-style regression for the typography token fixture.
- FBS repository and all third-party projects remain unchanged by this archive update.

## 1.1.0 — Evidence-first QA update

- Added a dedicated `visual_compare.py` for matched before/after screenshot matrices, HTML side-by-side gallery and machine-readable findings.
- Replaced arbitrary 175ms screenshot delay with 1500ms default stabilization plus optional `--settle-ms`, `--wait-for`, `--prime-scroll` and font/visible-image readiness checks.
- Added Tailwind arbitrary sizing / responsive columns / JSX inline sizing review to static audit.
- Added measured region snapshots (available inline size, padding, grid columns) in browser audit output.
- Added on-demand design references for available-space budgets and Tailwind component reviews; retained progressive disclosure.
- Added stronger evidence gate: browser zoom proxy is not actual zoom, and a screenshot diff or deployment success is not a design pass.
- Added robust regression tests and updated Arabic/English setup instructions; updated cross-industry primary design references (Apple, Material, Fluent, W3C).
- No code changes to third-party projects; this release is a reusable skill archive only.

## 1.0.0

- Initial modular fluid responsive design skill, CSS/browser heuristics and example fixtures.
