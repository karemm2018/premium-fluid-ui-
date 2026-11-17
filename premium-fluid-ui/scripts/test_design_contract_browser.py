#!/usr/bin/env python3
"""Executable Chromium regression for Premium Fluid UI v1.9.2 2D scale and symmetric desktop framing.

Tests the bundled CSS reference only, NOT an arbitrary client's website. It does not
start a server, touch GitHub or mutate any external project.
"""
import argparse
import shutil
from pathlib import Path


def browser_test(executable=None):
    from playwright.sync_api import sync_playwright

    css = (Path(__file__).resolve().parents[1] / 'assets' / 'desktop-first-scale.css').read_text(encoding='utf-8')
    cases = [
        (1920, 1080, 19.392),
        (1600, 900, 16.56),
        (1536, 864, 15.9936),
        (1440, 900, 15.144),
        (1366, 768, 14.4883),
        (1280, 720, 13.728),
        (1024, 768, 11.4624),
        (1024, 600, 11.4624),
        (960, 600, 16),
        (390, 844, 16),
        (740, 360, 16),
    ]
    exe = executable or shutil.which('chromium') or shutil.which('chromium-browser') or shutil.which('google-chrome')
    with sync_playwright() as pw:
        opts = {'headless': True}
        if exe:
            opts['executable_path'] = exe
        browser = pw.chromium.launch(**opts)
        try:
            for width, height, expected_root in cases:
                page = browser.new_page(viewport={'width': width, 'height': height})
                page.set_content(
                    '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1">'
                    '<style>' + css + '</style></head><body><main class="pf-framed-container"'
                    ' style="height:100px">Framed content</main></body></html>'
                )
                metrics = page.evaluate('''() => {
                    const r = document.querySelector('.pf-framed-container').getBoundingClientRect();
                    return {root: parseFloat(getComputedStyle(document.documentElement).fontSize),
                        left: r.left, right: innerWidth - r.right, innerWidth,
                        centerDelta: Math.abs(r.left - (innerWidth - r.right))};
                }''')
                assert abs(metrics['root'] - expected_root) < 0.07, (width, height, metrics, expected_root)
                if width >= 1024:
                    assert abs(metrics['left'] / width - 0.135) < 0.005, (width, height, 'left framing', metrics)
                    assert abs(metrics['right'] / width - 0.135) < 0.005, (width, height, 'right framing', metrics)
                    assert metrics['centerDelta'] < 1, (width, height, 'asymmetry', metrics)
                print(f'PASS {width}x{height}: root={metrics["root"]:.2f}px '
                      f'left={metrics["left"] / width * 100:.2f}% '
                      f'right={metrics["right"] / width * 100:.2f}%')
                page.close()
        finally:
            browser.close()
    print(f'PASS {len(cases)} browser CSS reference cases; no project URL audited')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-executable', default=None,
                        help='Optional explicit Chromium executable; otherwise use PATH/Playwright install')
    args = parser.parse_args()
    browser_test(args.browser_executable)


if __name__ == '__main__':
    main()
