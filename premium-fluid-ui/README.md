# Premium Fluid UI (v1.9.2)

Cross-client Agent Skill for Antigravity and Codex. Install the whole `premium-fluid-ui` directory in `<project>/.agents/skills/` or globally in Antigravity's `~/.gemini/config/skills/` or Codex's `~/.agents/skills/`.

Core principle: **mandatory correction of every VERIFIED design-contract deviation (P0/P1/P2), preserving approved brand visuals; 1536×864 CSS px baseline; 2D desktop scaling >=1024px; structural handheld reflow <1024px; no global blind codemods**. Read `SKILL.md` for agent instructions and `README_AR.md` for Arabic step-by-step setup.

Optional automation (Python 3.9+, Playwright + Chromium):

```bash
python -m pip install playwright
python -m playwright install chromium
python scripts/responsive_audit.py --url http://localhost:3000 --out ./ui-audit --preset quick
python scripts/responsive_audit.py --fixture healthy --out ./fixture-healthy --preset quick
python scripts/responsive_audit.py --fixture broken --out ./fixture-broken --preset quick
python scripts/static_css_audit.py /path/to/project
# Preview scoped and reviewed changes (does not modify files):
python scripts/fluid_codemod.py /path/to/project/src/components/Hero.tsx --json
# Only after verifying a measured defect and reviewing its diff:
python scripts/fluid_codemod.py /path/to/project/src/components/Hero.tsx --frame-containers --apply --reviewed
python scripts/component_audit.py --fixture healthy --out ./component-healthy
python scripts/component_audit.py --fixture broken --out ./component-broken
python scripts/component_audit.py --url http://localhost:3000 --selector '[data-pf-audit="auction-card"]' --sync-viewport --out ./component-audit
python scripts/test_component_browser.py
python scripts/interaction_smoke.py --fixture healthy --escape-closes --out ./menu-smoke
python scripts/test_interaction_browser.py
python scripts/validate_skill.py
python scripts/test_skill.py
python scripts/test_design_contract_browser.py
python scripts/test_typography_browser.py
```

The default zoom matrix includes viewport-width **reflow proxies**, distinct from `--real-zoom` Chromium CSS/root-font-size experiments. Neither automatically certifies native browser-menu zoom, platform text enlargement, real devices, interactive states or appearance: these require manual evidence.

## v1.9.2 mandatory rules and evidence

- Review the full [must-fix design contract](references/mandatory-conformance.md). **Once an issue is measured and confirmed, the agent must correct it even at P2**, including font size, font weight, whitespace rhythm and exact desktop column/header composition. A static warning is only a candidate.
- Reference: `1536×864 CSS px` (16px root). Desktop `>=1024px` preserves desktop columns/nav and intended `~13.5%` symmetric framing on both sides. `<1024px` uses tested structural reflow. Preserve brand colors, typefaces, images and approved appearance.
- The codemod is conservative, dry-run by default, and only writes with `--apply --reviewed` in a reviewed scope. To fail CI for untriaged browser heuristics, use `responsive_audit.py --strict-review`; exit 3 means review candidates, not proven design defects. Extra structural transformations require explicit flags. Tests: `python scripts/validate_skill.py` and `python scripts/test_skill.py`.

## Historical v1.4 additions: 2D Viewport Matrix (`1024x600`, Low-Res, Landscape), RTL Full-Height Edge Checks & Structural Reflow

- **2D Viewport Coverage (`QUICK` & `FULL`):** automatically tests `1024x600` (WSVGA / compact landscape), low-resolution laptop/desktop (`1366x768`, `1280x720`) and phones (`360x640`, `320x568`), tablet portrait/landscape (`768x1024`, `1024x768`, `820x1180`, `1180x820`, `960x600`), and mobile landscape (`667x375`, `740x360`, `844x390`).
- **Full-Document RTL/LTR Edge & Text Clipping Detection:** `responsive_audit.py` now checks both `rect.left < -3` (critical for RTL negative-margin/overflow bugs) and `rect.right > vw + 3` across the **entire document height** (not just the top viewport fold), plus text-node Range clipping, floating/absolute element overlaps, mobile header crowding, and short-viewport (`<= 640px` height) vertical crush.
- **Enhanced Static Audit (`static_css_audit.py`):** catches fixed widths `>= 260px`, standard Tailwind fixed widths (`w-64`, `w-72`, `w-80`, `w-96`), unprefixed multi-column grids (`grid-cols-2` on mobile), negative horizontal margins (`-mx-*`), unconditional `absolute` positioning, and rigid `100vh`/`h-screen` heights.
- **Breakpoint-Synced Component Sweeps (`component_audit.py --sync-viewport`):** optionally scales the browser viewport alongside the component width so `@media` queries and Tailwind breakpoints trigger realistically.

## Dev server approval policy

Reuse an already-running, verified local development URL. **Never start, stop, restart, or duplicate a dev server or background process without explicit user approval**, including when the agent runtime would otherwise permit a command automatically. Request approval with the proposed command, port, reason, and impact. If declined, perform static checks and mark browser verification as not run.
