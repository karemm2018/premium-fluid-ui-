#!/usr/bin/env python3
"""Review-gated, scoped Fluid UI Codemod (v1.9.2).

Automates repetitive Desktop-First to Two-Tier Fluid UI conversions across
HTML, JSX, TSX, Vue, Svelte, and CSS files:
1. Converts arbitrary Tailwind pixel sizing (e.g., w-[400px], min-w-[320px],
   gap-[24px], p-[32px]) into proportional `rem` values (w-[25rem], min-w-[20rem],
   gap-[1.5rem], p-[2rem]) so Tier 1 desktop scaling works automatically on
   1024x600, 1280x720, and 1366x768 screens.
2. Upgrades standard fixed containers (`max-w-7xl mx-auto`, `max-w-6xl mx-auto`)
   to preserve the ~13.5% desktop side whitespace (`lg:w-[73vw]`).
3. Protects unprefixed multi-column grids (`grid-cols-2`, `grid-cols-3`,
   `grid-cols-4`) by prepending a mobile base while retaining lg desktop counts, only when explicitly requested.
4. Leaves SVG attributes unchanged; use static_css_audit.py to flag candidates
   and convert explicitly after visual verification.
5. Softens extreme Arabic font-weight utilities (`font-black` -> `font-bold`,
   `font-thin` -> `font-normal`) when `--balance-weights` is enabled.

Defaults to a safe dry-run with only arbitrary pixel/rem proposals. For structural
edits use explicit --frame-containers, --reflow-grids and/or --balance-weights
only after verifying a mismatch. --apply additionally requires --reviewed;
limit the positional path to the checked file or carefully reviewed subdirectory.

"""
import argparse
import json
import re
from pathlib import Path

SKIP_DIRS = {
    'node_modules', 'dist', 'build', 'coverage', '.git', '.next',
    'vendor', 'ui-audit', 'ui-before-after', '__pycache__', '.turbo', '.vercel'
}
CODE_EXTS = {'.tsx', '.jsx', '.html', '.vue', '.svelte', '.js', '.ts'}
STYLE_EXTS = {'.css', '.scss', '.sass', '.less'}

# 1. Arbitrary Tailwind pixel classes: w-[400px], min-w-[320px], p-[24px], gap-[32px], top-[40px], etc.
TW_ARB_PX = re.compile(
    r'(?<![\w-])(?P<prefix>(?:(?:sm|md|lg|xl|2xl|hover|focus|group-hover|rtl|ltr):)*)'
    r'(?P<prop>w|min-w|max-w|h|min-h|max-h|basis|size|p|px|py|pt|pb|pl|pr|ps|pe|m|mx|my|mt|mb|ml|mr|ms|me|gap|gap-x|gap-y|inset|top|bottom|left|right|start|end|text)'
    r'-\[(?P<px>\d+(?:\.\d+)?)px\]'
)

# 2. Unprefixed multi-column grid without grid-cols-1
UNPREFIXED_GRID = re.compile(r'(?<![\w:-])grid-cols-(?P<cols>[2-6])\b')

# 3. Standard max-w-7xl / max-w-6xl mx-auto container losing desktop side whitespace
MAX_W_CONTAINER = re.compile(r'\b(?P<mw>max-w-(?:6xl|7xl))\s+mx-auto\b')

# 4. CSS fixed pixel properties (>= 24px for spacing/sizing)
CSS_PX_PROP = re.compile(
    r'(?P<prop>\b(?:width|inline-size|min-width|min-inline-size|max-width|max-inline-size|'
    r'height|block-size|min-height|min-block-size|padding|padding-inline|padding-block|'
    r'padding-top|padding-bottom|padding-left|padding-right|gap|column-gap|row-gap|'
    r'margin-top|margin-bottom|top|bottom|left|right|inset-inline-start|inset-inline-end)\s*:\s*)'
    r'(?P<px>\d+(?:\.\d+)?)px\b',
    re.I
)


def fmt_rem(px_val: float) -> str:
    rem = round(px_val / 16.0, 4)
    s = f'{rem:.4f}'.rstrip('0').rstrip('.')
    return f'{s}rem'


def transform_markup_line(line: str, frame_containers: bool = False, balance_weights: bool = False, reflow_grids: bool = False):
    changes = []
    original = line

    # A. Convert arbitrary Tailwind px -> rem (for values >= 12px, excluding 1px/2px borders)
    def repl_arb(m):
        px = float(m.group('px'))
        prop = m.group('prop')
        if px < 12:
            return m.group(0)
        new_token = f"{m.group('prefix')}{prop}-[{fmt_rem(px)}]"
        changes.append(f"{m.group(0)} -> {new_token}")
        return new_token

    line = TW_ARB_PX.sub(repl_arb, line)

    # B. Only opt-in for a verified framed *inner* content wrapper. Avoid navbar, footer and full-bleed media.
    if frame_containers and ('73vw' not in line) and ('pf-framed-container' not in line):
        def repl_container(m):
            new_cls = "w-full lg:w-[73vw] mx-auto"
            changes.append(f"{m.group(0)} -> {new_cls}")
            return new_cls
        line = MAX_W_CONTAINER.sub(repl_container, line)

    # C. Only opt-in for a verified content-card mobile reflow. Keep intentional 2-up stats and CTAs.
    if reflow_grids and 'grid' in line and 'grid-cols-1' not in line:
        def repl_grid(m):
            cols = int(m.group('cols'))
            bp = 'lg'  # Desktop column counts stay locked at >=1024px; handheld layout reflows
            new_grid = f"grid-cols-1 {bp}:grid-cols-{cols}"
            changes.append(f"{m.group(0)} -> {new_grid}")
            return new_grid
        line = UNPREFIXED_GRID.sub(repl_grid, line, count=1)

    # D. Only opt-in after verifying text role; do not blindly restyle approved identity display.
    if balance_weights:
        if re.search(r'(?<![\w-])font-black(?![\w-])', line):
            line = re.sub(r'(?<![\w-])font-black(?![\w-])', 'font-bold', line)
            changes.append('font-black -> font-bold')
        if re.search(r'(?<![\w-])font-thin(?![\w-])', line):
            line = re.sub(r'(?<![\w-])font-thin(?![\w-])', 'font-normal', line)
            changes.append('font-thin -> font-normal')

    return line, changes if line != original else []


def transform_css_line(line: str):
    changes = []
    original = line
    if '@media' in line or 'clamp(' in line or '12px' in line or '11px' in line:
        return line, []

    def repl_css_px(m):
        px = float(m.group('px'))
        if px < 16:
            return m.group(0)
        rem_str = fmt_rem(px)
        changes.append(f"{px:g}px -> {rem_str}")
        return f"{m.group('prop')}{rem_str}"

    line = CSS_PX_PROP.sub(repl_css_px, line)
    return line, changes if line != original else []


def process_file(path: Path, apply: bool = False, frame_containers: bool = False, balance_weights: bool = False, reflow_grids: bool = False):
    ext = path.suffix.lower()
    if ext not in CODE_EXTS and ext not in STYLE_EXTS:
        return []
    try:
        content = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return []

    lines = content.splitlines(keepends=True)
    new_lines = []
    file_edits = []

    for idx, line in enumerate(lines, 1):
        ending = '\r\n' if line.endswith('\r\n') else ('\n' if line.endswith('\n') else '')
        body = line[:-len(ending)] if ending else line
        if ext in CODE_EXTS:
            updated, changes = transform_markup_line(body, frame_containers=frame_containers, balance_weights=balance_weights, reflow_grids=reflow_grids)
        else:
            updated, changes = transform_css_line(body)
        if changes:
            file_edits.append({
                'file': str(path),
                'line': idx,
                'changes': changes,
                'before': body.strip()[:160],
                'after': updated.strip()[:160],
            })
        new_lines.append(updated + ending)

    if file_edits and apply:
        path.write_text(''.join(new_lines), encoding='utf-8')
    return file_edits


def run_codemod(target: Path, apply: bool = False, frame_containers: bool = False, balance_weights: bool = False, reflow_grids: bool = False, reviewed: bool = False, max_files: int = 5000):
    if apply and not reviewed:
        raise ValueError("--apply requires --reviewed: verify the measured defect and review the dry-run diff first")
    files = [target] if target.is_file() else (f for f in sorted(target.rglob('*')) if f.is_file())
    all_edits = []
    scanned = 0
    modified_files = set()
    for f in files:
        if f.suffix.lower() not in (CODE_EXTS | STYLE_EXTS) or set(f.parts) & SKIP_DIRS:
            continue
        scanned += 1
        if scanned > max_files:
            break
        edits = process_file(f, apply=apply, frame_containers=frame_containers, balance_weights=balance_weights, reflow_grids=reflow_grids)
        if edits:
            modified_files.add(str(f))
            all_edits.extend(edits)
    return {
        'tool': 'premium-fluid-ui/fluid_codemod',
        'version': '1.9.2',
        'mode': 'applied' if apply else 'dry-run',
        'filesScanned': scanned,
        'filesModified': len(modified_files),
        'totalEdits': len(all_edits),
        'edits': all_edits,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', type=Path, help='Project directory or single file to transform')
    p.add_argument('--apply', action='store_true', help='Apply scoped, reviewed transformations; requires --reviewed')
    p.add_argument('--reviewed', action='store_true', help='Explicitly confirm the target file/scope and previewed diff were reviewed against measured defects')
    p.add_argument('--frame-containers', action='store_true', help='Opt-in to converting a VERIFIED inner framed content wrapper (not navbar/hero/full-bleed)')
    p.add_argument('--balance-weights', action='store_true', help='Opt-in to role-verified typography weight replacements')
    p.add_argument('--reflow-grids', action='store_true', help='Opt-in to MOBILE content card grid reflow (not stats/tabs/paired controls)')
    p.add_argument('--json', action='store_true', help='Print machine-readable JSON output')
    args = p.parse_args()
    if not args.path.exists():
        p.error('path does not exist')
    if args.apply and not args.reviewed:
        p.error('--apply requires --reviewed after measuring the defect and reviewing the dry-run diff')
    res = run_codemod(
        args.path,
        apply=args.apply,
        reviewed=args.reviewed,
        frame_containers=args.frame_containers,
        balance_weights=args.balance_weights,
        reflow_grids=args.reflow_grids,
    )
    if args.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print(f"Fluid Codemod ({res['mode']}): scanned {res['filesScanned']} files | "
              f"{res['filesModified']} files with {res['totalEdits']} responsive transformations")
        for e in res['edits'][:60]:
            print(f"- {e['file']}:{e['line']} ({', '.join(e['changes'])})")
        if len(res['edits']) > 60:
            print(f"... and {len(res['edits']) - 60} more transformations (use --json)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
