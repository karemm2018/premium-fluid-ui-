# Decision engine: select the reference frame, then the CSS mechanism

1. **Determine the problem:** viewport composition? nested component? natural text size? fixed-height overlay? image crop? horizontal reflow? layout state?
2. **Measure the relevant available space:** `document.documentElement.clientWidth` for CSS viewport; layout container `clientWidth` minus padding for a component; account for sidebar, sticky/fixed UI and scrollbars. Use `ResizeObserver` only if JavaScript measurements are truly necessary; prefer CSS.
3. **Select intrinsic behavior first:** `max-inline-size`, `min-inline-size: 0`, `flex-wrap`, `grid-template-columns`, `auto-fit`, `minmax`, natural flow, proper `gap`, logical margins/paddings.
4. **Select a dimension source:** `%` for containing block, `fr` for grid track free space, `rem` for type/consistent spatial tokens, `em` for self-scaled component sizing, `cqi` for container-sensitive scaling **when an eligible ancestor query container exists**. Dynamic viewport height units only for viewport-height tasks.
5. **Add boundaries:** `clamp()` / `min()` / `max()` to avoid microscopic or giant sizes. Do not make base body text shrink to fit narrow devices; preserve reasonable reading size.
6. **Respect the two-tier contract:** for desktop `>=1024px`, preserve the original approved desktop column count and navigation and solve fit with proportional tokens, gaps and available-space corrections; do not drop desktop columns. Only on `<1024px` handheld/tablet layouts use reflow (fewer columns, stacked controls, secondary chrome drawer) and accessible alternate representations for tables. If the desktop contract is physically inaccessible with larger text/zoom, prioritize accessibility and document the exception.
7. **Test content edge cases:** Arabic diacritics, mixed Arabic-English numerals, long auction plate IDs, localization, user-entered text, enlarged system fonts, empty states.
8. **Confirm and repair all design-contract deviations, including P2:** static suspicious styles need measurement; confirmed typography/weight/spacing/framing errors still require a fix even when there is no overflow. Small non-fluid `px` values may be correct as an approved exception.

## Priorities
P0: lost access to action/content, blocked scrolling, overlapping controls, unreadable text, keyboard trap.
P1: accidental page overflow, clipped meaningful images/labels, unstable reflow at common zoom/widths.
P2: uneven visual rhythm, excessive whitespace, typographic hierarchy/weight mismatch, edge-case text wrapping. **P2 is mandatory to address once verified**, not optional.

Never solve P1 by adding `overflow-x: hidden` to the whole page: this may conceal the underlying defect. Fix the overflowing component. Likewise don't use browser-zoom detection scripts to undo enlargement.
