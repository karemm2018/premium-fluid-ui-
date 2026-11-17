#!/usr/bin/env python3
"""Fast built-in regression checks for Premium Fluid UI v1.9.2."""
import tempfile
import unittest
from pathlib import Path
from responsive_audit import cases
from static_css_audit import audit_file


class SkillTests(unittest.TestCase):
    def test_zoom_and_2d_viewport_matrix(self):
        quick = cases('quick')
        full = cases('full')
        self.assertTrue(any(c[3].startswith('125%') and c[4] == 1.25 for c in quick))
        # Verify 1024x600, mobile-landscape (740x360), and low-res (1366x768, 360x640, 320x568) are present
        dims_quick = {(c[0], c[1], c[2]) for c in quick}
        self.assertIn((1024, 600, 'compact-landscape-1024x600'), dims_quick)
        self.assertIn((740, 360, 'mobile-landscape'), dims_quick)
        self.assertIn((1366, 768, 'laptop-low-res'), dims_quick)
        self.assertIn((360, 640, 'mobile-low-res'), dims_quick)
        self.assertIn((320, 568, 'mobile-tiny'), dims_quick)
        self.assertEqual(len(quick), 12)
        self.assertTrue(all(c[0] >= 320 for c in quick))
        dims_full = {(c[0], c[1], c[2]) for c in full}
        self.assertIn((800, 480, 'low-res-landscape'), dims_full)
        self.assertIn((667, 375, 'mobile-landscape-small'), dims_full)
        self.assertIn((844, 390, 'mobile-landscape-modern'), dims_full)
        self.assertIn((1280, 720, 'low-res-desktop-720p'), dims_full)

    def test_tailwind_jsx_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'page.tsx'
            file.write_text(
                '''<div className="max-w-[1400px] w-[320px] w-80 grid-cols-2 lg:grid-cols-2 -mx-6 absolute h-screen whitespace-nowrap truncate">\n'''
                '''  <button style={{minWidth:'300px'}}>Go</button>\n</div>\n'''
            )
            kinds = {w['kind'] for w in audit_file(file)}
            self.assertIn('tailwind-arbitrary-fixed-dimension', kinds)
            self.assertIn('tailwind-standard-fixed-width', kinds)
            # Responsive prefixed columns (lg:grid-cols-2) are intentionally NOT flagged so desktop column counts stay locked
            self.assertIn('tailwind-unprefixed-multi-col-grid', kinds)
            self.assertIn('tailwind-negative-horizontal-margin', kinds)
            self.assertIn('tailwind-unconditional-absolute', kinds)
            self.assertIn('tailwind-rigid-h-screen-short-viewport-risk', kinds)
            self.assertIn('tailwind-nowrap', kinds)
            self.assertIn('tailwind-truncate', kinds)
            self.assertIn('jsx-inline-fixed-dimension', kinds)

    def test_relative_layout_not_flagged_as_large_fixed(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / 'page.tsx'
            file.write_text('<section className="w-full max-w-full min-w-0 grid grid-cols-1 gap-4 static lg:absolute">ok</section>')
            self.assertFalse(audit_file(file))



    def test_fluid_codemod_transformations(self):
        from fluid_codemod import run_codemod
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'Hero.tsx'
            p.write_text('<div className="max-w-7xl mx-auto w-[400px] gap-[24px] grid grid-cols-3 font-black">Hi</div>\n', encoding='utf-8')
            dry = run_codemod(p, apply=False)
            self.assertEqual(dry['filesModified'], 1)
            self.assertGreaterEqual(dry['totalEdits'], 1)
            with self.assertRaisesRegex(ValueError, '--reviewed'):
                run_codemod(p, apply=True)
            applied = run_codemod(p, apply=True, reviewed=True, frame_containers=True,
                                  reflow_grids=True, balance_weights=True)
            out = p.read_text(encoding='utf-8')
            self.assertIn('lg:w-[73vw]', out)
            self.assertIn('w-[25rem]', out)
            self.assertIn('gap-[1.5rem]', out)
            self.assertIn('grid-cols-1 lg:grid-cols-3', out)
            self.assertIn('font-bold', out)

    def test_real_zoom_cases_option(self):
        rz = cases('quick', include_real_zoom=True)
        kinds = {c[2] for c in rz}
        self.assertIn('real-css-zoom-125', kinds)
        self.assertIn('real-root-font-200', kinds)



    def test_desktop_column_lock_detector(self):
        from responsive_audit import check_desktop_column_lock
        rows = [
            {'requestedViewport': {'width': 1536, 'height': 864}, 'zoomReflowProxy': False,
             'result': {'measuredRegions': [{'element': 'div.grid', 'gridColumns': '300px 300px 300px'}], 'issues': []}},
            {'requestedViewport': {'width': 1280, 'height': 720}, 'zoomReflowProxy': False,
             'result': {'measuredRegions': [{'element': 'div.grid', 'gridColumns': '400px 400px'}], 'issues': []}},
        ]
        check_desktop_column_lock(rows)
        issues = rows[1]['result']['issues']
        self.assertTrue(any(i['kind'] == 'desktop-column-count-changed' and i['level'] == 'high' for i in issues))



    def test_desktop_header_collapse_at_1280_detected(self):
        from responsive_audit import check_desktop_column_lock
        rows = [
            {'requestedViewport': {'width': 1536, 'height': 864}, 'zoomReflowProxy': False,
             'result': {'visibleNavLinks': 6, 'measuredRegions': [], 'issues': []}},
            {'requestedViewport': {'width': 1280, 'height': 800}, 'zoomReflowProxy': False,
             'result': {'visibleNavLinks': 2, 'measuredRegions': [], 'issues': []}},
        ]
        check_desktop_column_lock(rows)
        issues = rows[1]['result']['issues']
        self.assertTrue(any(i['kind'] == 'desktop-header-collapsed-to-drawer' and i['level'] == 'high' for i in issues))
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / 'Nav.tsx'
            f.write_text('<nav className="hidden xl:flex"><button className="xl:hidden">Menu</button></nav>', encoding='utf-8')
            kinds = {w['kind'] for w in audit_file(f)}
            self.assertIn('tailwind-late-desktop-collapse-1280px', kinds)


    def test_static_audit_regex_is_functional(self):
        with tempfile.TemporaryDirectory() as tmp:
            css = Path(tmp) / 'styles.css'
            css.write_text('@media (max-width: 1200px) { h1 { font-weight: 900; }}\n', encoding='utf-8')
            kinds = {x['kind'] for x in audit_file(css)}
            self.assertIn('css-late-desktop-media-collapse', kinds)
            self.assertIn('css-extreme-font-weight', kinds)
            markup = Path(tmp) / 'Markup.tsx'
            markup.write_text('<div className="max-w-7xl mx-auto hidden xl:flex">\n'
                              '<svg width="24" height="24" /></div>', encoding='utf-8')
            kinds = {x['kind'] for x in audit_file(markup)}
            self.assertIn('tailwind-container-loses-desktop-side-whitespace', kinds)
            self.assertIn('tailwind-late-desktop-collapse-1280px', kinds)
            self.assertIn('svg-fixed-pixel-attribute', kinds)

    def test_mandatory_contract_is_not_only_high_severity(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        skill = (root / 'SKILL.md').read_text(encoding='utf-8')
        contract = (root / 'references/mandatory-conformance.md').read_text(encoding='utf-8')
        self.assertIn('version: "1.9.2"', skill)
        self.assertIn('MANDATORY DESIGN-CONTRACT REPAIR (ALL SEVERITIES)', skill)
        self.assertIn('P0/P1/P2', skill)
        self.assertIn('1536×864', skill)
        self.assertIn('CANDIDATE', contract)
        self.assertIn('EXCEPTION', contract)
        self.assertNotIn('only modify a component or layout property when a verified **High-Severity defect** exists', skill)

    def test_codemod_preserves_approved_grid_and_weights_by_default(self):
        from fluid_codemod import run_codemod
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'Card.tsx'
            original = '<div className="grid grid-cols-3 font-black max-w-7xl mx-auto">ok</div>\n'
            path.write_text(original, encoding='utf-8')
            first = run_codemod(path, apply=False)
            self.assertEqual(first['totalEdits'], 0)
            self.assertEqual(path.read_text(encoding='utf-8'), original)
            second = run_codemod(path, apply=True, reviewed=True)
            self.assertEqual(second['totalEdits'], 0)
            self.assertEqual(path.read_text(encoding='utf-8'), original)

    def test_root_scale_reference_and_readability_bounds(self):
        from pathlib import Path
        import math
        css = (Path(__file__).resolve().parents[1] / 'assets/desktop-first-scale.css').read_text(encoding='utf-8')
        self.assertIn('0.885vw', css)
        self.assertIn('1.574dvh', css)
        self.assertIn('65%', css)
        self.assertIn('125%', css)
        def root_font(w, h):
            return max(16 * 0.65, min((0.15 * 16 + 0.00885 * w),
                                      (0.15 * 16 + 0.01574 * h), 16 * 1.25))
        self.assertAlmostEqual(root_font(1536, 864), 16, delta=0.03)
        self.assertGreater(root_font(1024, 600), 11.0)
        self.assertLess(root_font(1024, 600), 11.6)
        self.assertAlmostEqual(root_font(1920, 1080), 19.4, delta=0.05)


if __name__ == '__main__':
    unittest.main(verbosity=2)
