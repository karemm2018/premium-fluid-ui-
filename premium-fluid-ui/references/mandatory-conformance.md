# Mandatory design-conformance protocol — Premium Fluid UI v1.9.2

## What "mandatory" means

The skill **must repair every confirmed mismatch**, including P2 typography/spacing/rhythm defects even when there is no overflow. The severity number controls the order of work, **never whether a verified mismatch is optional**. Conversely, a static pattern match by itself does **not** prove nonconformance. Do not rewrite a healthy component or override approved colors, identity, imagery, fonts, visual effects, or semantic behavior.

## Contract and measurement order

1. **Confirm existing intent:** identify the accepted desktop visual system, grid counts, header link/CTA visibility, actual content framing, component roles, font families, weights, line heights, and content. Use project profile/approved screenshots first; when undocumented use the v1.9.2 portable reference as the initial contract and record this assumption.
2. **Fix the reference:** `1536×864` CSS layout pixels is the default desktop reference with `html` approximately `16px`. Determine actual CSS available inline and block space, not physical screen pixels. `desktop scale = clamp(0.65, min(scaleW, scaleH), 1.25)`, with the calibrated CSS expression in `assets/desktop-first-scale.css`; record computed font-size and ensure minimum legibility. The root formula is not a mandate to replace an existing design system if it already meets the contract by equivalent tokens.
3. **Desktop `>= 1024px`:** preserve approved number of columns, header navigation/CTAs, proportion and flow; do not collapse based on width alone. For **intended framed inner content** maintain a centered 72–76% viewport-width target (~12–14% left and right, nominal 13.5%); check the individual left and right margins, not only total width. Use `73vw` and `scrollbar-gutter: stable both-edges` for symmetric sides in Chromium with classic scrollbars. An ultra-wide max-width cap can be a documented design-specific exception; do not call it 13.5% if actual margins exceed the range. Approved full-bleed backgrounds, hero media, maps, and intentionally wider headers/footers are explicit exceptions. Never stretch logos/illustrations or hide important labels to make the math pass.
4. **Mobile/tablet `< 1024px`:** fix unusable card widths, clipped labels, excess gaps, inappropriate multicolumn *content* and trapped scroll. Compact statistic pairs or icon grids can stay 2 columns if verified. Check portrait AND landscape and preserve sufficient touch targets and text readability.
5. **Typography:** enforce a consistent role-based hierarchy for titles, subtitles, body, metadata and CTAs. The portable starting reference is H1 `32–42px`, H2 `22–26px`, H3 `18–19px`, body `15px`, metadata `12–13px` at an initial 16px root, with measured 400–700 font-weight ramp. Use the project's approved identity fonts and relative tokens; don't globally convert all `font-black`/`font-extrabold` unless actual role/context fails the contract. Check line wrapping, Arabic glyphs, RTL numbers, and WCAG enlargement.
6. **Spacing:** verify padding/gap/section rhythm by component role and the accepted reference. Correct confirmed overly generous/overly compressed spaces *even without collision*. Do not normalize every section to one fixed padding value; use semantic tokens and available space.
7. **Safety/accessibility:** preserve working behavior. Browser zoom, text zoom, intrinsic layout and minimum readable sizes override a purely proportional objective where the two conflict; record and test the exception instead of hiding content or turning off zoom.

## Findings table — required report per affected component

| Page / component | CSS viewport | Current measured value | Expected contract | Severity | Diagnosis | Change location | After measurement | Status | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `/` / hero header | `1280×720` | e.g. links hidden | desktop links visible | P1 | breakpoint too high | `Navbar.tsx` | after browser test | FIXED / BLOCKED | before/after PNG |

- `FIXED` = deployed/tested in requested environment and matched screenshot + computed geometry.
- `EXCEPTION` = intentional approved composition / accessibility; explicit measured rationale and scope.
- `UNVERIFIED` = no trustworthy runtime/browser result. Never mark PASSED.
- `BLOCKED` = confirmed mismatch not fixed; specify blocker and consequence.
- `CANDIDATE` = static hint awaiting verification; must not be silently dismissed.

## Exit gate

- No confirmed P0/P1/P2 mismatch left silently unresolved.
- All reviewed mismatches either FIXED or EXCEPTION; remaining BLOCKED/UNVERIFIED prominently reported, not called passed.
- Desktop reference and at least `1920×1080`, `1536×864`, `1440×900`, `1366×768`, `1280×720`, `1024×600`; mobile `390×844`, `360×640`, `320×568` and landscape `740×360` checked when a runnable browser is available.
- Record **actual browser zoom** separately from viewport-width proxies, and keep screenshots and build/typecheck/functional results.
- No automatic mass codemod without reviewed, measured scope.
