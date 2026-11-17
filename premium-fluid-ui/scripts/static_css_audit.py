#!/usr/bin/env python3
"""Heuristic CSS AND Tailwind/JSX sizing audit (v1.9.2).

Flags rigid sizing (>= 260px widths that break 320-360px phones), standard
Tailwind fixed widths (w-64, w-72, w-80, w-96), unprefixed multi-column grids
(grid-cols-2 on mobile), unconditional absolute positioning, negative horizontal
margins (-mx-*), and rigid viewport heights (100vh / h-screen) that crush
1024x600 and mobile landscape screens.
"""
import argparse
import json
import re
from pathlib import Path

PATTERNS = {
    'css-fixed-large-width': re.compile(r'(?<![\w-])(?:width|inline-size|min-width|min-inline-size)\s*:\s*(?:2[6-9]\d|[3-9]\d\d|\d{4,})px\b', re.I),
    'css-fixed-large-height': re.compile(r'(?<![\w-])(?:height|block-size|min-height|min-block-size)\s*:\s*(?:[4-9]\d\d|\d{4,})px\b', re.I),
    'css-rigid-100vh-height': re.compile(r'\b(?:height|block-size)\s*:\s*100(?:d|s|l)?vh\b', re.I),
    'css-viewport-width-100': re.compile(r'\b(?:width|inline-size)\s*:\s*100(?:d|s|l)?vw\b', re.I),
    'css-negative-horizontal-margin': re.compile(r'\bmargin(?:-(?:left|right|inline|inline-start|inline-end))?\s*:\s*-[1-9]\d*(?:px|rem|em|vw)\b', re.I),
    'css-overflow-hidden': re.compile(r'\boverflow-x\s*:\s*hidden\b', re.I),
    'css-nowrap': re.compile(r'\bwhite-space\s*:\s*nowrap\b', re.I),
    'css-zoom': re.compile(r'(?<![\w-])zoom\s*:\s*\d', re.I),
    'css-extreme-font-weight': re.compile(r'\bfont-weight\s*:\s*(?:[12389]00|black|extrabold|ultrabold|thin|extralight|light)\b', re.I),
    'zoom-disabled': re.compile(r'user-scalable\s*=\s*(?:no|0)|maximum-scale\s*=\s*1(?:\.0)?(?:\b|\W)', re.I),
}

# Handle Tailwind arbitrary widths/heights (lowered width threshold to 260px for 320px-360px phones).
ARBITRARY = re.compile(
    r'(?<![\w-])(?:(?:sm|md|lg|xl|2xl|hover|focus|group-hover):)*(?P<prop>w|min-w|max-w|h|min-h|max-h|basis|size)-\[(?P<num>\d+(?:\.\d+)?)px\]'
)
# Standard Tailwind fixed widths >= 256px (w-64=256px, w-72=288px, w-80=320px, w-96=384px)
STANDARD_FIXED_WIDTH = re.compile(r'(?<![\w:-])(?:w|min-w|basis)-(?:64|72|80|96)\b')
# Responsive columns with breakpoint prefix
RESPONSIVE_COLS = re.compile(r'(?<![\w-])(?P<bp>sm|md|lg|xl|2xl):grid-cols-(?P<n>[2-9]|1\d)\b')
# Unprefixed multi-column grid on mobile (e.g., grid-cols-2 without grid-cols-1 base)
UNPREFIXED_MULTI_COLS = re.compile(r'(?<![\w:-])grid-cols-(?P<n>[2-9]|1\d)\b')
# Negative horizontal margins in Tailwind (-mx-4, -ml-6, -mr-6, -ms-4, -me-4)
TAILWIND_NEG_MARGIN = re.compile(r'(?<![\w-])-m[xhlrse]-(?:\d+|\[[^\]]+\])\b')
# Unconditional 'absolute' without responsive reset ('static lg:absolute' or 'max-lg:static')
UNCONDITIONAL_ABSOLUTE = re.compile(r'(?<![\w:-])absolute\b')
RESPONSIVE_STATIC_RESET = re.compile(r'\b(?:static|(?:sm|md|lg|xl):absolute|max-(?:sm|md|lg):static)\b')

SVG_FIXED_ATTR = re.compile(r"<svg[^>]*\b(?:width|height)=['\"](?P<num>[2-9]\d|\d{3,})(?:px)?['\"]", re.I)
DESKTOP_CONTAINER_NO_VW_GUTTER = re.compile(r"\b(?:max-w-(?:6xl|7xl|screen-xl|screen-2xl)|container)\b")
LATE_DESKTOP_COLLAPSE = re.compile(r"\b(?:hidden\s+(?:xl|2xl):(?:flex|inline-flex|block|grid)|(?:xl|2xl):hidden)\b")
CSS_LATE_MEDIA_COLLAPSE = re.compile(r"@media\s*\([^)]*max-(?:width|inline-size)\s*:\s*(?:1[1-4]\d{2}|7[2-9]|8\d)(?:px|rem)\b", re.I)
JSX_FIXED = re.compile(r'(?:width|minWidth|maxWidth|height|minHeight|maxHeight)\s*:\s*[\'\"](?P<num>\d+)px[\'\"]')
TAILWIND_FLAGS = {
    'whitespace-nowrap': 'tailwind-nowrap',
    'truncate': 'tailwind-truncate',
    'overflow-x-hidden': 'tailwind-overflow-x-hidden',
    'h-screen': 'tailwind-rigid-h-screen-short-viewport-risk',
    'w-screen': 'tailwind-w-screen-scrollbar-overflow-risk',
    'font-black': 'tailwind-extreme-heavy-weight-arabic-risk',
    'font-extrabold': 'tailwind-extreme-heavy-weight-arabic-risk',
    'font-thin': 'tailwind-extreme-light-weight-lowres-risk',
    'font-extralight': 'tailwind-extreme-light-weight-lowres-risk',
    'font-light': 'tailwind-extreme-light-weight-lowres-risk',
}
SKIP_DIRS = {'node_modules', 'dist', 'build', 'coverage', '.git', '.next', 'vendor', 'ui-audit', 'ui-before-after', '__pycache__', '.turbo', '.vercel'}
EXTS = {'.css', '.scss', '.sass', '.less', '.html', '.vue', '.svelte', '.jsx', '.tsx', '.js', '.ts'}


def audit_file(path):
    found = []
    try:
        lines = path.read_text(encoding='utf-8').splitlines()
    except (OSError, UnicodeError):
        return found
    for i, line in enumerate(lines, 1):
        text = line.strip()

        def add(kind, detail=''):
            found.append({
                'file': str(path),
                'line': i,
                'kind': kind,
                'detail': detail,
                'text': text[:220],
                'level': 'review',
            })

        for name, rx in PATTERNS.items():
            if rx.search(line):
                add(name)
        # Media queries are CSS, not JSX; inspect all supported text types.
        if CSS_LATE_MEDIA_COLLAPSE.search(line):
            add('css-late-desktop-media-collapse', 'Breakpoints above 1024px may collapse the approved desktop layout or header; verify intent')
        if path.suffix.lower() in {'.tsx', '.jsx', '.html', '.vue', '.svelte', '.js', '.ts'}:
            for m in ARBITRARY.finditer(line):
                prop, value = m.group('prop'), float(m.group('num'))
                threshold = 260 if prop in ('w', 'min-w', 'max-w', 'basis', 'size') else 460
                if value >= threshold:
                    add('tailwind-arbitrary-fixed-dimension', f'{m.group(0)} ({prop} >= {threshold}px)')
            for m in STANDARD_FIXED_WIDTH.finditer(line):
                add('tailwind-standard-fixed-width', f'{m.group(0)} (fixed width >= 256px may overflow 320-360px mobile containers)')
            # Note: Do NOT flag lg:grid-cols-* or md:grid-cols-* as warnings; desktop column counts must be preserved.
            for m in UNPREFIXED_MULTI_COLS.finditer(line):
                if 'grid-cols-1' not in line:
                    add('tailwind-unprefixed-multi-col-grid', m.group(0) + ' — prepend mobile grid-cols-1 (e.g. grid-cols-1 lg:' + m.group(0) + ') while STRICTLY PRESERVING the desktop column count (' + m.group('n') + ' columns)')
            for m in TAILWIND_NEG_MARGIN.finditer(line):
                add('tailwind-negative-horizontal-margin', m.group(0) + ' risks RTL/mobile edge bleed and text clipping')
            if UNCONDITIONAL_ABSOLUTE.search(line) and not RESPONSIVE_STATIC_RESET.search(line):
                add('tailwind-unconditional-absolute', 'absolute without static/responsive reset may overlap content on mobile or 1024x600')
            for m in SVG_FIXED_ATTR.finditer(line):
                add('svg-fixed-pixel-attribute', f'{m.group(0)[:60]} — convert SVG width/height to rem/em so icons scale on 1024px')
            if DESKTOP_CONTAINER_NO_VW_GUTTER.search(line) and not re.search(r"(?:7[0-6]vw|1[1-5]vw|pf-framed-container|page-shell)", line):
                add('tailwind-container-loses-desktop-side-whitespace', 'Fixed max-w-6xl/7xl/container loses side margins on 1024px-1366px screens; use lg:w-[73vw] mx-auto for verified inner content or an approved custom framing token')
            for m in LATE_DESKTOP_COLLAPSE.finditer(line):
                add('tailwind-late-desktop-collapse-1280px', f'{m.group(0)} collapses desktop UI at 1280px/1536px! Use lg:flex / lg:hidden (1024px) or md: (768px) so 1024px and 1280px keep full desktop header/layout')
            for m in JSX_FIXED.finditer(line):
                if float(m.group('num')) >= 260:
                    add('jsx-inline-fixed-dimension', m.group(0))
            for token, kind in TAILWIND_FLAGS.items():
                if re.search(r'(?<![\w-])' + re.escape(token) + r'(?![\w-])', line):
                    add(kind)
    return found


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('path', type=Path)
    p.add_argument('--json', action='store_true')
    p.add_argument('--max-files', type=int, default=5000)
    a = p.parse_args()
    if not a.path.exists():
        p.error('path does not exist')
    files = [a.path] if a.path.is_file() else (f for f in a.path.rglob('*') if f.is_file())
    warnings = []
    count = 0
    for file in files:
        if file.suffix.lower() not in EXTS or set(file.parts) & SKIP_DIRS:
            continue
        count += 1
        if count > a.max_files:
            break
        warnings.extend(audit_file(file))
    result = {
        'files_scanned': min(count, a.max_files),
        'warnings': warnings,
        'note': 'Review hints, NOT confirmed visual defects. Arbitrary px values and responsive grid-cols can be valid.',
    }
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f'Scanned {result["files_scanned"]} files; {len(warnings)} review hints')
        for w in warnings[:80]:
            print(f'- {w["file"]}:{w["line"]} [{w["kind"]}] {w["detail"] or w["text"]}')
        if len(warnings) > 80:
            print(f'... {len(warnings) - 80} more hints (use --json)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
