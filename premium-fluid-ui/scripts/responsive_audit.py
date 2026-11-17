#!/usr/bin/env python3
"""Screenshot and heuristic 2D responsive audit (v1.9.2).

Covers desktop, low-resolution displays (1366x768, 1280x720, 360x640), compact
landscape screens (1024x600, 800x480), tablet portrait/landscape, and mobile
portrait/landscape. Checks bidirectional (RTL left < 0 and LTR right > vw)
overflow across the FULL document height, text-node clipping, floating/absolute
card collisions, header crowding, and short-viewport vertical crush.

Zoom cases are viewport proxies, NOT real zoom.
Requires playwright + Chromium. Returns 0 if no high severity issue is detected,
2 if high severity findings are detected, 1 if an execution error occurs.
"""
import argparse
import html
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
FIXTURES = {"healthy": HERE / "examples" / "healthy.html", "broken": HERE / "examples" / "broken.html"}

# All widths/heights are CSS layout viewport dimensions.
# v1.4 includes 1024x600, low-res (1366x768, 360x640, 320x568), tablet landscape, and mobile landscape.
QUICK = [
    (1536, 864, "desktop-ref-250pct-4k"),
    (1440, 900, "desktop"),
    (1366, 768, "laptop-low-res"),
    (1024, 600, "compact-landscape-1024x600"),
    (1024, 768, "tablet-landscape"),
    (820, 1040, "tablet-portrait"),
    (740, 360, "mobile-landscape"),
    (390, 844, "mobile"),
    (360, 640, "mobile-low-res"),
    (320, 568, "mobile-tiny"),
]

FULL = [
    (1920, 1080, "desktop"),
    (1600, 900, "desktop"),
    (1536, 864, "desktop-ref-250pct-4k"),
    (1440, 900, "desktop"),
    (1366, 768, "laptop-low-res"),
    (1280, 800, "desktop"),
    (1280, 720, "low-res-desktop-720p"),
    (1024, 600, "compact-landscape-1024x600"),
    (1180, 820, "tablet-landscape"),
    (1024, 768, "tablet-landscape"),
    (1024, 1366, "tablet-portrait"),
    (960, 600, "small-tablet-landscape"),
    (820, 1180, "tablet-portrait"),
    (800, 480, "low-res-landscape"),
    (768, 1024, "tablet-portrait"),
    (600, 960, "small-tablet-portrait"),
    (844, 390, "mobile-landscape-modern"),
    (740, 360, "mobile-landscape"),
    (667, 375, "mobile-landscape-small"),
    (480, 900, "mobile"),
    (430, 932, "mobile"),
    (390, 844, "mobile"),
    (375, 667, "mobile-low-res"),
    (360, 640, "mobile-low-res"),
    (320, 568, "mobile-tiny"),
]

JS_AUDIT = r"""() => {
  const de = document.documentElement, body = document.body;
  const vw = de.clientWidth, vh = window.innerHeight;
  const docWidth = Math.max(de.scrollWidth, body?.scrollWidth || 0);
  const issues = [];
  if (docWidth > vw + 2) {
    issues.push({
      kind: 'page-horizontal-overflow',
      level: 'high',
      message: `Scroll width ${docWidth}px exceeds viewport ${vw}px by ${docWidth - vw}px`
    });
  }
  const visible = el => {
    if (!el || !el.isConnected || el.closest('[hidden], [inert], [aria-hidden="true"], [data-pf-ignore]')) return false;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && parseFloat(s.opacity) !== 0 && r.width > 1 && r.height > 1;
  };
  const describe = el => {
    if (!el) return '(none)';
    const id = el.id ? '#' + el.id : '';
    const classes = typeof el.className === 'string' && el.className.trim()
      ? '.' + el.className.trim().split(/\s+/).slice(0, 2).join('.') : '';
    return el.tagName.toLowerCase() + id + classes;
  };
  const hasHorizontalScrollAncestor = el => {
    let cur = el?.parentElement;
    while (cur && cur !== body && cur !== de) {
      const s = getComputedStyle(cur);
      if ((s.overflowX === 'auto' || s.overflowX === 'scroll') && cur.scrollWidth > cur.clientWidth + 4) return true;
      if (cur.matches('[data-pf-carousel], .carousel, .swiper, .splide')) return true;
      cur = cur.parentElement;
    }
    return false;
  };

  const all = [...document.querySelectorAll('body *')].slice(0, 7000);
  let clipped = 0, offCanvas = 0, vClipped = 0;
  const floatingEls = [];

  for (const el of all) {
    if (!visible(el)) continue;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (s.position === 'fixed' || s.position === 'absolute') {
      floatingEls.push({ el, s, r });
    }
    // 1. Content scrollWidth clipping inside overflow-x: hidden/clip
    if (clipped < 24 && (s.overflowX === 'hidden' || s.overflowX === 'clip' || s.textOverflow === 'ellipsis')
      && el.scrollWidth > el.clientWidth + 3 && el.clientWidth > 5 && el.textContent.trim().length > 0) {
      const intentionalEllipsis = s.textOverflow === 'ellipsis' || s.webkitLineClamp !== 'none' || !!el.closest('[data-pf-allow-clip]');
      issues.push({
        kind: 'potential-clipped-content',
        level: intentionalEllipsis ? 'review' : 'high',
        element: describe(el),
        message: `Content scrollWidth ${el.scrollWidth}px > clientWidth ${el.clientWidth}px`
      });
      clipped++;
    }
    // 2. Full-document bidirectional (RTL left < -3 AND LTR right > vw + 3) viewport edge bleeding
    const crossesRight = r.right > vw + 3 && r.left < vw;
    const crossesLeft = r.left < -3 && r.right > 0;
    if (offCanvas < 20 && (crossesRight || crossesLeft) && !hasHorizontalScrollAncestor(el)) {
      const bleedPx = Math.round(Math.max(crossesRight ? r.right - vw : 0, crossesLeft ? -r.left : 0));
      const hasDirectText = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
      const isControl = el.matches('button, a[href], input, select, textarea, [role="button"], h1, h2, h3, p');
      const level = (hasDirectText || isControl || bleedPx > 12) ? 'high' : 'review';
      issues.push({
        kind: 'element-crosses-viewport-edge',
        level,
        element: describe(el),
        message: `${crossesLeft ? `Left edge ${Math.round(r.left)}px < 0 (RTL/left bleed)` : `Right edge ${Math.round(r.right)}px > ${vw}px`} (${bleedPx}px outside viewport)`
      });
      offCanvas++;
    }
    // 3. Short-viewport / 1024x600 / landscape vertical clipping check
    if (vh <= 640 && vClipped < 12 && (s.overflowY === 'hidden' || s.overflowY === 'clip')
      && el.scrollHeight > el.clientHeight + 8 && el.clientHeight >= vh * 0.4 && el.textContent.trim().length > 0) {
      issues.push({
        kind: 'vertical-overflow-clipped-short-viewport',
        level: 'high',
        element: describe(el),
        message: `Vertical scrollHeight ${el.scrollHeight}px clipped inside ${el.clientHeight}px container at short viewport height ${vh}px`
      });
      vClipped++;
    }
  }

  // 4. Text-node Range geometry: catch RTL/LTR clipped text and text outside viewport across full page
  const textNodes = [];
  const tw = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  while (tw.nextNode() && textNodes.length < 1200) {
    const node = tw.currentNode, parent = node.parentElement;
    if (!node.textContent.trim() || !visible(parent)) continue;
    if (parent.closest('script, style, textarea, svg, template')) continue;
    const range = document.createRange();
    range.selectNodeContents(node);
    for (const r of range.getClientRects()) {
      if (r.width > 1 && r.height > 1) {
        textNodes.push({ node, owner: parent, text: node.textContent.trim().slice(0, 45), rect: r });
      }
    }
    range.detach?.();
  }

  let textOutside = 0, textClipped = 0;
  for (const item of textNodes) {
    if (textOutside < 16 && !hasHorizontalScrollAncestor(item.owner)) {
      if (item.rect.left < -2 || item.rect.right > vw + 2) {
        issues.push({
          kind: 'text-outside-viewport',
          level: 'high',
          element: describe(item.owner),
          message: `Text "${item.text}" extends outside viewport (${Math.round(item.rect.left)}px..${Math.round(item.rect.right)}px vs 0..${vw}px)`
        });
        textOutside++;
      }
    }
    if (textClipped < 16) {
      let anc = item.owner;
      while (anc && anc !== body && anc !== de) {
        const s = getComputedStyle(anc);
        const xClip = s.overflowX === 'hidden' || s.overflowX === 'clip';
        if (xClip) {
          const ar = anc.getBoundingClientRect();
          const inLeft = ar.left + anc.clientLeft;
          const inRight = inLeft + anc.clientWidth;
          if (item.rect.left < inLeft - 2 || item.rect.right > inRight + 2) {
            const expected = !!(item.owner.closest('[data-pf-allow-clip]') || s.textOverflow === 'ellipsis' || s.webkitLineClamp !== 'none');
            issues.push({
              kind: 'clipped-text-content',
              level: expected ? 'review' : 'high',
              element: describe(item.owner),
              message: `Text "${item.text}" clipped by ${describe(anc)} (${Math.round(item.rect.left)}..${Math.round(item.rect.right)} vs ${Math.round(inLeft)}..${Math.round(inRight)})`
            });
            textClipped++;
            break;
          }
        }
        anc = anc.parentElement;
      }
    }
  }

  // 5. Interactive controls target size & overlap
  const controls = [...document.querySelectorAll('button,a[href],input:not([type=hidden]),select,textarea,[role=button]')]
    .filter(visible).slice(0, 180);
  let small = 0, overlaps = 0;
  for (let i = 0; i < controls.length; i++) {
    const a = controls[i], ra = a.getBoundingClientRect();
    if (small < 18 && (ra.width < 24 || ra.height < 24)) {
      issues.push({
        kind: 'small-target-review',
        level: 'review',
        element: describe(a),
        message: `${Math.round(ra.width)}x${Math.round(ra.height)}px; inspect target spacing and WCAG exceptions`
      });
      small++;
    }
    for (let j = i + 1; j < controls.length && overlaps < 15; j++) {
      const b = controls[j];
      if (a.contains(b) || b.contains(a)) continue;
      const rb = b.getBoundingClientRect();
      const w = Math.min(ra.right, rb.right) - Math.max(ra.left, rb.left);
      const h = Math.min(ra.bottom, rb.bottom) - Math.max(ra.top, rb.top);
      if (w > 3 && h > 3) {
        issues.push({
          kind: 'interactive-overlap',
          level: 'high',
          element: describe(a),
          message: `Overlaps ${describe(b)} by ~${Math.round(w)}x${Math.round(h)}px`
        });
        overlaps++;
      }
    }
  }

  // 6. Floating / Absolute card & FAB overlap with outside text or controls
  let floatHits = 0;
  for (const f of floatingEls.slice(0, 40)) {
    if (floatHits >= 12) break;
    if (f.el.matches('header, nav, [role="banner"], [data-pf-overlap-ok]')) continue;
    const fr = f.r;
    if (fr.width < 20 || fr.height < 20 || fr.width > vw * 0.95) continue;
    for (const t of textNodes) {
      if (f.el.contains(t.owner) || t.owner.contains(f.el)) continue;
      if (t.owner.closest('header, nav')) continue;
      const w = Math.min(fr.right, t.rect.right) - Math.max(fr.left, t.rect.left);
      const h = Math.min(fr.bottom, t.rect.bottom) - Math.max(fr.top, t.rect.top);
      if (w > 6 && h > 6) {
        const isFooterHit = !!t.owner.closest('footer, [role="contentinfo"]');
        const isAbs = f.s.position === 'absolute';
        issues.push({
          kind: 'floating-or-absolute-overlap',
          level: (isAbs || isFooterHit) ? 'high' : 'review',
          element: describe(f.el),
          message: `${f.s.position} element overlaps text "${t.text}" in ${describe(t.owner)} by ${Math.round(w)}x${Math.round(h)}px`
        });
        floatHits++;
        break;
      }
    }
  }

  // 7. Header / Navbar crowding on mobile & tablet (< 768px)
  const header = document.querySelector('header, [role="banner"], nav');
  if (header && visible(header) && vw <= 768) {
    const hr = header.getBoundingClientRect();
    if (header.scrollWidth > vw + 2) {
      issues.push({
        kind: 'header-crowding-overflow',
        level: 'high',
        element: describe(header),
        message: `Header scrollWidth ${header.scrollWidth}px exceeds mobile viewport ${vw}px`
      });
    }
    if (hr.height > Math.min(130, vh * 0.26)) {
      issues.push({
        kind: 'header-excessive-height',
        level: vh <= 500 ? 'high' : 'review',
        element: describe(header),
        message: `Header height ${Math.round(hr.height)}px consumes ${Math.round(hr.height / vh * 100)}% of viewport height (${vh}px)`
      });
    }
  }

  // 8. Short-viewport / Landscape / 1024x600 sticky chrome budget
  if (vh <= 620) {
    let stickyHeight = 0;
    for (const el of all) {
      if (!visible(el)) continue;
      const s = getComputedStyle(el), r = el.getBoundingClientRect();
      if ((s.position === 'fixed' || s.position === 'sticky') && r.width > vw * 0.5 && r.height < vh * 0.6) {
        stickyHeight += r.height;
      }
    }
    if (stickyHeight > vh * 0.30) {
      issues.push({
        kind: 'short-viewport-vertical-crush',
        level: stickyHeight > vh * 0.38 ? 'high' : 'review',
        element: 'body',
        message: `Fixed/sticky bars consume ${Math.round(stickyHeight)}px (${Math.round(stickyHeight / vh * 100)}%) of short viewport height ${vh}px`
      });
    }
  }

  // 9. Desktop Side-Whitespace Framing Check (vw >= 1024px):
  // Ensure main content / card grids do not slam against the left/right edges on 1024px/1280px/1366px screens.
  // Nominal 13.5% per side; valid 12%-14% for intended framed content.
  // This is a conformance check, including review/P2 deviations with no physical collision.
  if (vw >= 1024) {
    const contentContainers = [...document.querySelectorAll('[data-pf-framed], .pf-framed-container, .page-shell, main .container, main .max-w-7xl, main .max-w-6xl, main .grid, main .cards')]
      .filter(el => visible(el) && !el.closest('header, nav, footer, [data-pf-full-bleed], [data-pf-framing-exception]'));
    let edgeHugCount = 0;
    for (const el of contentContainers) {
      if (edgeHugCount >= 6) break;
      const r = el.getBoundingClientRect();
      const isFullBleedWrapper = r.width >= vw - 4 && [...el.children].some(c => {
        const cr = c.getBoundingClientRect();
        return cr.width > 100 && cr.left >= vw * 0.12 && (vw - cr.right) >= vw * 0.12;
      });
      if (isFullBleedWrapper) continue;
      const leftMarginRatio = r.left / vw;
      const rightMarginRatio = (vw - r.right) / vw;
      const explicitlyFramed = el.matches('[data-pf-framed], .pf-framed-container, .page-shell');
      const sideTooSmall = leftMarginRatio < 0.115 || rightMarginRatio < 0.115;
      const sideTooLarge = leftMarginRatio > 0.145 || rightMarginRatio > 0.145;
      if ((explicitlyFramed && (sideTooSmall || sideTooLarge)) ||
          (!explicitlyFramed && r.width > vw * 0.755 && sideTooSmall)) {
        issues.push({
          kind: sideTooSmall ? 'desktop-insufficient-side-whitespace' : 'desktop-excessive-side-whitespace',
          level: (leftMarginRatio < 0.08 || rightMarginRatio < 0.08) ? 'high' : 'review',
          element: describe(el),
          message: `Desktop content spans ${Math.round(r.width / vw * 100)}% of ${vw}px viewport (left margin ${Math.round(leftMarginRatio * 100)}%, right margin ${Math.round(rightMarginRatio * 100)}%); conformance target 12%-14% empty space on EACH side (nominal 13.5%; 73vw inner content), unless explicitly approved full-bleed`
        });
        edgeHugCount++;
      }
    }
  }

  // 10. RTL/LTR Carousel Edge & Card Clipping Check:
  // Detect horizontal carousels where cards at the start/end are sharply clipped by the track container.
  const carousels = [...document.querySelectorAll('[data-pf-carousel], .carousel, .swiper, .splide')]
    .filter(visible).slice(0, 12);
  for (const car of carousels) {
    const cr = car.getBoundingClientRect();
    const cs = getComputedStyle(car);
    const clipsX = cs.overflowX === 'hidden' || cs.overflowX === 'clip';
    if (!clipsX || cr.width < 120) continue;
    const cards = [...car.children].filter(visible);
    for (const card of cards) {
      const kr = card.getBoundingClientRect();
      const partiallyVisibleLeft = kr.left < cr.left - 4 && kr.right > cr.left + 12;
      const partiallyVisibleRight = kr.right > cr.right + 4 && kr.left < cr.right - 12;
      if (partiallyVisibleLeft || partiallyVisibleRight) {
        issues.push({
          kind: 'carousel-card-clipped-at-edge',
          level: 'high',
          element: describe(car),
          message: `Carousel card ${describe(card)} is sharply clipped at ${partiallyVisibleLeft ? 'left' : 'right'} track edge (${Math.round(kr.left)}..${Math.round(kr.right)} vs track ${Math.round(cr.left)}..${Math.round(cr.right)})`
        });
        break;
      }
    }
  }

  let brokenImages = 0;
  for (const im of [...document.images].slice(0, 300)) {
    if (visible(im) && im.complete && im.naturalWidth === 0 && brokenImages < 15) {
      issues.push({
        kind: 'broken-image',
        level: 'high',
        element: describe(im),
        message: 'Displayed image failed to load'
      });
      brokenImages++;
    }
  }

  const regions = [...document.querySelectorAll('main, main section, section, .grid, [class*="grid-cols"], header, footer, [data-audit-space]')].slice(0, 28)
    .filter(visible).map(el => {
      const r = el.getBoundingClientRect(), parent = el.parentElement?.getBoundingClientRect();
      const cs = getComputedStyle(el);
      return {
        element: describe(el),
        inlineSize: Math.round(r.width),
        blockSize: Math.round(r.height),
        left: Math.round(r.left),
        right: Math.round(r.right),
        containingBlockSize: Math.round(parent?.width || 0),
        paddingInlineStart: cs.paddingInlineStart,
        paddingInlineEnd: cs.paddingInlineEnd,
        gridColumns: cs.gridTemplateColumns,
        flexWrap: cs.flexWrap,
        overflowInline: cs.overflowX
      };
    });

  const headerEl = document.querySelector('header, [role="banner"], nav');
  const visibleNavLinks = headerEl ? [...headerEl.querySelectorAll('a[href], button')].filter(visible).length : 0;
  return {
    visibleNavLinks,
    viewport: { width: vw, height: vh, devicePixelRatio: devicePixelRatio, aspect: Math.round((vw / Math.max(vh, 1)) * 100) / 100 },
    visualViewportScale: window.visualViewport?.scale || 1,
    documentScrollWidth: docWidth,
    examinedElements: all.length,
    examinedControls: controls.length,
    measuredRegions: regions,
    issues
  };
}"""


def cases(preset, include_real_zoom=False):
    base = FULL if preset == 'full' else QUICK
    result = [(w, h, kind, '100%-baseline', None) for w, h, kind in base]
    sources = [(1600, 900), (1440, 900)] if preset == 'quick' else [(1920, 1080), (1600, 900), (1440, 900), (1280, 800)]
    zooms = [1.25] if preset == 'quick' else [1.10, 1.25, 1.50, 2.00]
    for w, h in sources:
        for z in zooms:
            # An approximation of CSS viewport at desktop browser zoom, not actual zoom.
            result.append((round(w / z), round(h / z), 'zoom-reflow-proxy', f'{round(z * 100)}% of {w}px', z))
    if include_real_zoom:
        # Genuine in-browser CSS zoom + WCAG 200% root font-size stress tests
        result.append((1280, 800, 'real-css-zoom-125', 'real-zoom-125%', 1.25))
        result.append((1280, 800, 'real-root-font-200', 'root-font-200%', 2.0))
        result.append((390, 844, 'mobile-root-font-150', 'mobile-font-150%', 1.5))
    return result



def check_desktop_column_lock(rows):
    """Ensure grid column counts on smaller PC screens (1024px-1440px) match the reference desktop (1536px/1600px/1920px)."""
    desktop_rows = [r for r in rows if r.get('result') and r['requestedViewport']['width'] >= 1024 and not r.get('zoomReflowProxy')]
    if len(desktop_rows) < 2:
        return
    # Reference is the widest desktop viewport (or 1536x864 reference)
    ref_row = max(desktop_rows, key=lambda r: r['requestedViewport']['width'])
    ref_cols = {}
    for reg in ref_row['result'].get('measuredRegions', []):
        gtc = reg.get('gridColumns', '')
        if gtc and gtc != 'none':
            cols = len([c for c in gtc.split() if c.strip()])
            if cols >= 2:
                ref_cols[reg['element']] = cols
    for row in desktop_rows:
        if row is ref_row:
            continue
        vw = row['requestedViewport']['width']
        for reg in row['result'].get('measuredRegions', []):
            el = reg['element']
            if el in ref_cols:
                gtc = reg.get('gridColumns', '')
                cols = len([c for c in gtc.split() if c.strip()]) if (gtc and gtc != 'none') else 1
                expected = ref_cols[el]
                if cols != expected:
                    row['result']['issues'].append({
                        'kind': 'desktop-column-count-changed',
                        'level': 'high',
                        'element': el,
                        'message': f'Desktop grid {el} changed from {expected} columns to {cols} columns at {vw}px width; preserve exact desktop column count ({expected} columns) across all >=1024px screens'
                    })
    ref_nav = ref_row['result'].get('visibleNavLinks', 0)
    if ref_nav >= 3:
        for row in desktop_rows:
            if row is ref_row:
                continue
            vw = row['requestedViewport']['width']
            cur_nav = row['result'].get('visibleNavLinks', 0)
            if cur_nav < ref_nav:
                row['result']['issues'].append({
                    'kind': 'desktop-header-collapsed-to-drawer',
                    'level': 'high',
                    'element': 'header/nav',
                    'message': f'Desktop header collapsed from {ref_nav} visible items to {cur_nav} items at {vw}px width! Never switch to a tablet/hamburger menu on >=1024px desktop screens (1024px, 1280px, 1366px).'
                })


def html_report(rows, source, preset):
    cards = []
    for row in rows:
        title = f"{row['label']} · {row['kind']} · {row['requestedViewport']['width']}×{row['requestedViewport']['height']}"
        issues = row['result']['issues'] if row.get('result') else []
        high = sum(i['level'] == 'high' for i in issues)
        details = ''.join('<li><strong>' + html.escape(i['kind']) + '</strong> (' + html.escape(i['level']) + ') — ' +
                          html.escape(i.get('element', '') + ' ' + i['message']) + '</li>' for i in issues[:35])
        if len(issues) > 35:
            details += f'<li>And {len(issues) - 35} more findings (see JSON)</li>'
        screenshot = html.escape(row.get('screenshot', ''))
        cards.append(f'''<article class="card"><h2>{html.escape(title)}</h2><p>{high} high / {len(issues) - high} review flags</p>
          <a href="{screenshot}"><img loading="lazy" src="{screenshot}" alt="Screenshot: {html.escape(title)}"></a>
          <details><summary>Inspection findings ({len(issues)})</summary><ul>{details or '<li>None detected by heuristics</li>'}</ul></details></article>''')
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Premium Fluid UI v1.4 — 2D Responsive Audit v1.9.2</title><style>
:root{font-family:system-ui,sans-serif;color:#17212f;background:#f2f4f7}*{box-sizing:border-box}
body{max-width:90rem;margin:auto;padding:1rem 1.5rem}h1{font-size:1.7rem}.note{max-width:80ch;line-height:1.6}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,22rem),1fr));gap:1.2rem}
.card{min-inline-size:0;background:white;padding:1rem;border:1px solid #dce0e7;border-radius:.75rem}
.card h2{font-size:1.1rem;overflow-wrap:anywhere}.card img{max-width:100%;border:1px solid #ddd;display:block}
li{overflow-wrap:anywhere;margin-block:.4rem}details{margin-block-start:1rem}
</style></head><body><h1>2D Responsive &amp; Landscape Screenshot Audit (v1.9.2)</h1><p class="note">Source: ''' + html.escape(source) + '''. Preset: ''' + html.escape(preset) + '''.
<strong>Includes 1024×600, low-res displays, mobile/tablet landscape, and RTL/LTR full-height edge checks. Zoom cases are viewport-size reflow PROXIES, not genuine browser zoom.</strong>
</p><p class="note">Raw machine-readable results: <a href="results.json">results.json</a></p>
<div class="gallery">''' + '\n'.join(cards) + '</div></body></html>'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument('--url', help='URL of a locally running or accessible site')
    src.add_argument('--fixture', choices=sorted(FIXTURES), help='Use bundled test HTML')
    p.add_argument('--out', type=Path, default=Path('ui-audit'))
    p.add_argument('--preset', choices=['quick', 'full'], default='quick')
    p.add_argument('--timeout', type=int, default=15000, help='Page load timeout in ms')
    p.add_argument('--browser-executable', help='Custom Chromium executable path')
    p.add_argument('--settle-ms', type=int, default=1500, help='Wait for staged content after page/fonts ready; default 1500ms')
    p.add_argument('--wait-for', help='CSS selector that must become visible before screenshot')
    p.add_argument('--prime-scroll', action='store_true', help='Scroll to wake lazy media/reveal content')
    p.add_argument('--routes', help='Comma-separated relative paths to audit (e.g. /,/about,/auctions)')
    p.add_argument('--crawl', action='store_true', help='Automatically discover and audit internal same-origin links')
    p.add_argument('--max-pages', type=int, default=6, help='Maximum internal pages when using --crawl (default 6)')
    p.add_argument('--real-zoom', action='store_true', help='Include CSS zoom (125%%) and root font-size (150%%/200%%) stress tests, not native browser-menu zoom')
    p.add_argument('--strict-review', action='store_true', help='Exit code 3 if review candidates remain after high-severity checks; manual triage still required')
    args = p.parse_args()
    if args.settle_ms < 0:
        p.error('settle-ms must be nonnegative')
    source = FIXTURES[args.fixture].resolve().as_uri() if args.fixture else args.url
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print('Missing dependency: python -m pip install playwright', file=sys.stderr)
        return 1
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'screenshots').mkdir(exist_ok=True)
    rows = []
    try:
        with sync_playwright() as pw:
            opts = {'headless': True, 'args': ['--no-sandbox']}
            if args.browser_executable:
                opts['executable_path'] = args.browser_executable
            try:
                browser = pw.chromium.launch(**opts)
            except Exception as ex:
                if args.browser_executable or not Path('/usr/bin/chromium').exists():
                    raise ex
                opts['executable_path'] = '/usr/bin/chromium'
                browser = pw.chromium.launch(**opts)
            for idx, (width, height, kind, label, zoom) in enumerate(cases(args.preset, include_real_zoom=args.real_zoom), 1):
                is_touch = ('mobile' in kind) or ('tablet' in kind)
                page = browser.new_page(
                    viewport={'width': width, 'height': height},
                    device_scale_factor=1,
                    is_mobile=False,
                    has_touch=is_touch,
                )
                try:
                    if args.fixture:
                        page.set_content(FIXTURES[args.fixture].read_text(encoding='utf-8'), wait_until='domcontentloaded', timeout=args.timeout)
                        response = None
                    else:
                        response = page.goto(source, wait_until='domcontentloaded', timeout=args.timeout)
                    if args.wait_for:
                        page.locator(args.wait_for).first.wait_for(state='visible', timeout=args.timeout)
                    page.evaluate("""async () => {
                      await document.fonts.ready;
                      await Promise.all([...document.images].filter(i=>i.complete && i.naturalWidth>0)
                        .slice(0,100).map(i=>i.decode().catch(()=>{})));
                    }""")
                    if args.prime_scroll:
                        page.evaluate("""async () => {
                          let max=Math.min((document.scrollingElement||document.documentElement).scrollHeight-window.innerHeight,12000);
                          for(let y=0;y<max;y+=Math.max(250,Math.floor(window.innerHeight*.8))){
                            window.scrollTo(0,y); await new Promise(r=>setTimeout(r,65));
                          }
                          window.scrollTo(0,0);
                        }""")
                    if kind == 'real-css-zoom-125':
                        page.add_style_tag(content='html { zoom: 1.25 !important; }')
                    elif kind in ('real-root-font-200', 'mobile-root-font-150'):
                        pct = 200 if '200' in kind else 150
                        page.add_style_tag(content=f'html {{ font-size: {pct}% !important; }}')
                    if args.settle_ms:
                        page.wait_for_timeout(args.settle_ms)
                    result = page.evaluate(JS_AUDIT)
                    shot = f'screenshots/{idx:02d}-{kind}-{width}x{height}.png'
                    page.screenshot(path=str(args.out / shot), full_page=True, animations='disabled', timeout=args.timeout)
                    rows.append({
                        'label': label,
                        'kind': kind,
                        'requestedViewport': {'width': width, 'height': height},
                        'zoomReflowProxy': bool(zoom),
                        'sourceBaseZoom': zoom,
                        'httpStatus': response.status if response else None,
                        'result': result,
                        'screenshot': shot,
                    })
                    flags = result['issues']
                    high = sum(i['level'] == 'high' for i in flags)
                    print(f'{idx:02d} {kind:26} {width:4}×{height:<4} {label:18} high={high} review={len(flags) - high}')
                except Exception as ex:
                    rows.append({
                        'label': label,
                        'kind': kind,
                        'requestedViewport': {'width': width, 'height': height},
                        'zoomReflowProxy': bool(zoom),
                        'error': str(ex),
                        'result': None,
                    })
                    print(f'ERROR {label}, {width}×{height}: {ex}', file=sys.stderr)
                finally:
                    page.close()
            browser.close()
    except Exception as ex:
        print(f'Browser could not run: {ex}', file=sys.stderr)
        return 1
    check_desktop_column_lock(rows)
    n_high = sum(i['level'] == 'high' for r in rows if r['result'] for i in r['result']['issues'])
    n_review = sum(i['level'] == 'review' for r in rows if r['result'] for i in r['result']['issues'])
    n_error = sum('error' in r for r in rows)
    output = {
        'tool': 'premium-fluid-ui/responsive_audit',
        'version': '1.9.2',
        'timestampUTC': datetime.now(timezone.utc).isoformat(),
        'source': source,
        'preset': args.preset,
        'settleMs': args.settle_ms,
        'waitFor': args.wait_for,
        'primeScroll': args.prime_scroll,
        'zoomDisclaimer': 'Equivalent viewport-width reflow proxy, NOT actual browser zoom',
        'summary': {'cases': len(rows), 'highFindings': n_high, 'reviewHints': n_review, 'executionErrors': n_error},
        'cases': rows,
    }
    (args.out / 'results.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.out / 'index.html').write_text(html_report(rows, source, args.preset), encoding='utf-8')
    print(f'Report: {(args.out / "index.html").resolve()}')
    print(f'High findings: {n_high} | Review hints: {n_review} | Errors: {n_error}')
    if n_error:
        return 1
    if n_high:
        return 2
    if args.strict_review and n_review:
        return 3  # Untriaged review candidates: not automatically proven defects.
    return 0  # No high findings; NOT a complete visual contract approval.


if __name__ == '__main__':
    raise SystemExit(main())
