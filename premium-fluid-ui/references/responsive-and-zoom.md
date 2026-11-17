# Two-Tier Desktop-First Scaling, 1024x600, Low-Res, Landscape + Zoom Protocol (v1.9.2)

## 1. The Core Problem with Desktop-First Projects
When a UI is designed **Desktop-First** on a large monitor (`1920×1080` or `1600×900`), two distinct failures occur if you only use standard media queries:
1. **On Smaller Computer Screens (`1440×900`, `1366×768`, `1280×720`, `1024×600`, or Windows 125%/150% display scaling):**
   - If `1rem` stays fixed at `16px` (or elements use hardcoded `px`), a layout designed for `1920×1080` is physically too large for a `1366×768`, `1280×720`, or `1024×600` screen.
   - Standard responsive rules try to fix this by **breaking the desktop design** (dropping 4 columns down to 2, or turning floating hero cards into stacked mobile blocks), which ruins the desktop look on smaller laptops and `1024×600` screens!
2. **On Handheld Mobile & Portrait Tablet Screens (`< 1024px` width, especially `320px–430px` phones):**
   - Here the screen loses up to **75% of its width** and changes aspect ratio from landscape (`16:9`) to tall portrait (`9:19.5`). Simply shrinking the desktop layout onto a `360px` phone would shrink text to an unreadable `4px`! Here, **Structural Reflow** is mandatory.

## 2. The Solution: Two-Tier Responsive Architecture (`assets/desktop-first-scale.css`)

### Tier 1 — Smaller Computer Screens (`>= 1024px` width, including `1440×900`, `1366×768`, `1280×720`, and `1024×600`)
**Goal:** Keep the **exact desktop layout, column counts, navbar, and floating cards as-is**, scaled down proportionally in 2D (both width and height).
1. **Convert Desktop-First hardcoded `px` to `rem`:**
   - Replace fixed pixel widths, heights, paddings, gaps, and `inset` coordinates with `rem` (`px / 16`, e.g., `w-[400px]` -> `w-[25rem]`, `gap-[32px]` -> `gap-8` / `2rem`).
   - Because Tailwind's default spacing and sizing scale (`p-4`, `gap-6`, `w-80`, `max-w-7xl`, `text-xl`) is **already built in `rem`**, converting remaining arbitrary `[...px]` values to `rem` makes the entire UI scale automatically with the root `html` font size!
2. **Apply 2D Proportional Root Scaling (`min(width, height)`):**
   ```css
   /* v1.9.2 canonical: 1536×864 CSS px corresponds to ~16px root */
   @media (min-width: 64rem) {
     html {
       font-size: clamp(
         65%,
         min(calc(0.15rem + 0.885vw), calc(0.15rem + 1.574dvh)),
         125%
       );
     }
   }
   ```
   - Chromium measured values with this exact expression: `1920×1080` ≈ `19.39px`, `1536×864` ≈ `15.99px`, `1440×900` ≈ `15.14px`, `1366×768` ≈ `14.49px`, `1280×720` ≈ `13.73px`, `1024×600` ≈ `11.46px`.
   - **Desktop section framing**: use `inline-size: 73vw; margin-inline: auto` with `scrollbar-gutter: stable both-edges` to preserve symmetrical ~13.5% side margins. Max-width caps are explicit exceptions if the approved ultra-wide composition needs them.
   - Do not assume shrinking text alone resolves short-height layout issues. Preserve text legibility; adapt height/gaps locally and document accessibility exceptions under zoom.
   - On an existing approved site, map the formula into its actual design tokens rather than importing global CSS indiscriminately.

### Tier 2 — Tablet Portrait & Mobile (`< 1024px` width)
**Goal:** Restore `html { font-size: 100%; }` (`16px` base) for crisp legibility and automatically reflow the structure:
- **Headers (`< 1024px` where needed):** keep Logo + 1–2 icons on the bar; move secondary action buttons ("تسجيل الدخول", "اعرض لوحتك") into the mobile drawer (`hidden lg:inline-flex`).
- **Floating Hero Cards (`< 1024px`):** use `static lg:absolute` so the card stays floating on all computer screens (`>= 1024px`, including `1024×600`) and stacks cleanly in normal flow below `1024px`.
- **Grids (`< 640px`):** stack to a single column (`grid-cols-1 sm:grid-cols-2 lg:grid-cols-4`).
- **Steppers (`< 768px`):** switch horizontal process steps to vertical (`flex-col md:flex-row`).
- **Mobile Landscape (`< 960px` wide and `<= 500px` tall, e.g., `740×360`, `844×390`):** use a compact 2-column side-by-side grid (`grid-template-columns: 1.15fr 0.85fr`), unstick the header (`position: relative`), and cap image height (`max-block-size: 48dvh`).

## 3. Test matrix (v1.5 mandatory coverage)
- **Large Desktop:** `1920×1080`, `1600×900`.
- **Smaller PC / Laptop & `1024×600` (Tier 1 Proportional Desktop Preservation):** `1440×900`, `1366×768`, `1280×800`, `1280×720`, `1024×600`.
- **Tablet Portrait & Landscape:** `768×1024`, `1024×768`, `820×1180`, `1180×820`, `960×600`, `600×960`.
- **Mobile Portrait (Modern + Low-Res):** `480×900`, `430×932`, `390×844`, `375×667`, `360×640`, `320×568`.
- **Mobile Landscape:** `844×390`, `740×360`, `667×375`, `800×480`.
