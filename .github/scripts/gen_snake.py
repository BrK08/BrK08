#!/usr/bin/env python3
"""Space 3D — Self-hosted contribution constellation generator.

Runs inside the Space Autopilot GitHub Actions workflow (or locally with a
token). Fetches the REAL contribution calendar from the GitHub GraphQL API
and renders assets/snake.svg in the Space 3D style: extruded contribution
cells as glowing stars, a nebula-gradient snake weaving through the active
days with SMIL motion.

Pure stdlib (urllib + json). Exits non-zero on API failure so the workflow
never commits a blank or wrong panel.
"""
import datetime
import json
import os
import sys
import urllib.request

# ---------------- palette (Space design system) ----------------
VIOLET = '#8B5CF6'; CYAN = '#22D3EE'; ICE = '#7DD3FC'; AQUA = '#2DD4BF'
MAGENTA = '#FF3D9A'; PINK = '#F472B6'; GOLD = '#FBBF24'; GREEN_OK = '#4ADE9B'
TXT = '#EEF2FF'; SUB = '#A6B4D8'; FAINT = '#7E8BB3'
SANS = "Segoe UI, -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace"
W = 1012
H = 396

LADDER = ['#2B3168', '#4C4FC4', '#8B5CF6', '#FF3D9A']  # intensity levels

_uid = [0]


def uid(p='sn'):
    _uid[0] += 1
    return f'{p}{_uid[0]}'


def esc(s):
    A = chr(38)
    return (str(s).replace(A, A + 'amp;')
            .replace('<', A + 'lt;').replace('>', A + 'gt;'))


def rgba(hexc, a):
    h = hexc.lstrip('#')
    return f'rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})'


def lighten(hexc, t):
    h = hexc.lstrip('#')
    r = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(round(v + (255 - v) * t) for v in r)


def nebula_grad(gid):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="{ICE}"/>'
            f'<stop offset="0.32" stop-color="{CYAN}"/>'
            f'<stop offset="0.62" stop-color="{VIOLET}"/>'
            f'<stop offset="1" stop-color="{MAGENTA}"/></linearGradient>')


def T(x, y, s, fs=16, fill=TXT, w=400, anchor='start', ls=None, font=SANS):
    a = (f'x="{x}" y="{y}" font-family="{font}" font-size="{fs}" '
         f'font-weight="{w}" fill="{fill}"')
    if anchor != 'start':
        a += f' text-anchor="{anchor}"'
    if ls is not None:
        a += f' letter-spacing="{ls}"'
    return f'<text {a}>{esc(s)}</text>'


def grad_text(defs, x, y, s, fs, w=800, anchor='middle', glow_color=None):
    gt = uid('gt')
    defs += nebula_grad(gt)
    gf = ''
    if glow_color:
        gf = uid('gf')
        defs += (f'<filter id="{gf}" x="-70%" y="-70%" width="240%" height="240%">'
                 f'<feGaussianBlur stdDeviation="{max(5, fs * 0.13)}"/></filter>')
    m = ''
    anc = (f' text-anchor="{anchor}"' if anchor != 'start' else '')
    if glow_color:
        m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
              f'font-weight="{w}" fill="{glow_color}" opacity="0.9"{anc} '
              f'filter="url(#{gf})">{esc(s)}</text>')
    m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
          f'font-weight="{w}"{anc} fill="url(#{gt})">{esc(s)}</text>')
    return defs, m


def chip(defs, x, y, label, value, color, fs=13):
    wdt = len(label) * fs * 0.62 + len(str(value)) * fs * 0.68 + 42
    m = (f'<rect x="{x:.0f}" y="{y}" width="{wdt:.0f}" height="29" rx="14.5" '
         f'fill="{rgba(color, 0.13)}" stroke="{rgba(color, 0.55)}" stroke-width="1"/>'
         f'<circle cx="{x + 15:.0f}" cy="{y + 14.5}" r="3.2" fill="{color}">'
         f'<animate attributeName="opacity" values="0.35;1;0.35" dur="2.2s" '
         f'repeatCount="indefinite"/></circle>'
         + T(x + 26, y + 19.5, label, fs=fs, fill=SUB, font=MONO, w=600)
         + T(x + 26 + len(label) * fs * 0.62 + 10, y + 19.5, str(value),
             fs=fs, fill=lighten(color, 0.35), font=MONO, w=700))
    return defs, m, wdt


def hud_corners(x, y, w, h, c, L=13):
    st = f'stroke="{rgba(c, 0.8)}" stroke-width="2" fill="none" stroke-linecap="round"'
    return (f'<path d="M{x},{y + L} V{y} H{x + L}" {st}/>'
            f'<path d="M{x + w - L},{y} H{x + w} V{y + L}" {st}/>'
            f'<path d="M{x},{y + h - L} V{y + h} H{x + L}" {st}/>'
            f'<path d="M{x + w - L},{y + h} H{x + w} V{y + h - L}" {st}/>')


# ---------------- data ----------------
def fetch_calendar(owner, token):
    q = ('query{user(login:"%s"){contributionsCollection{contributionCalendar{'
         'totalContributions weeks{contributionDays{date contributionCount}}}}}}'
         % owner)
    body = json.dumps({'query': q}).encode()
    req = urllib.request.Request('https://api.github.com/graphql', data=body,
                                 headers={
                                     'Authorization': f'Bearer {token}',
                                     'Content-Type': 'application/json',
                                     'User-Agent': 'space-autopilot',
                                 })
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode())
    cal = data['data']['user']['contributionsCollection']['contributionCalendar']
    days = [d for w in cal['weeks'] for d in w['contributionDays']]
    return cal['totalContributions'], days


def level(count):
    if count >= 10:
        return 4
    if count >= 5:
        return 3
    if count >= 3:
        return 2
    return 1


# ---------------- render ----------------
def render(total, days, date_str):
    # grid geometry: 53 weeks x 7 days
    GX, GY = 56, 128
    PITCH, CS = 16.4, 13.6
    defs = (f'<filter id="softShadow" x="-40%" y="-40%" width="180%" '
            f'height="180%"><feGaussianBlur stdDeviation="10"/></filter>')
    body = ''

    # glass panel
    px, py, pw, ph = 30, 26, 952, 344
    pg = uid('pg')
    defs += (f'<linearGradient id="{pg}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0A0E28" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#080B20" stop-opacity="0.96"/>'
             f'</linearGradient>')
    body += (f'<rect x="{px}" y="{py + 10}" width="{pw}" height="{ph}" rx="20" '
             f'fill="rgba(4,2,18,0.55)" filter="url(#softShadow)"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" '
             f'fill="url(#{pg})" stroke="{rgba(MAGENTA, 0.5)}" stroke-width="1.4"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="4" rx="2" '
             f'fill="{rgba(MAGENTA, 0.8)}"/>'
             + hud_corners(px + 10, py + 10, pw - 20, ph - 20, MAGENTA, 13))

    # nebulae
    for cx, cy, rx, ry, col, op, dx, dy, dur, beg in [
            (-40, 100, 300, 120, MAGENTA, 0.13, 26, 8, 12, 0),
            (1050, 300, 280, 110, VIOLET, 0.15, -26, 6, 13, 2)]:
        bg = uid('bl')
        defs += (f'<radialGradient id="{bg}" cx="0.5" cy="0.5" r="0.5">'
                 f'<stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                 f'<stop offset="1" stop-color="{col}" stop-opacity="0"/>'
                 f'</radialGradient>')
        body += (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                 f'fill="url(#{bg})">'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'values="0 0;{dx} {dy};0 0" dur="{dur}s" begin="{beg}s" '
                 f'repeatCount="indefinite" calcMode="spline" '
                 f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/></ellipse>')

    # title
    defs, m = grad_text(defs, W / 2, 78, 'CONTRIBUTION CONSTELLATION', 30,
                        w=800, anchor='middle', glow_color=MAGENTA)
    body += m
    active = [d for d in days if d['contributionCount'] > 0]
    body += (f'<circle cx="{W / 2 + 266}" cy="70" r="5" fill="{GREEN_OK}">'
             f'<animate attributeName="opacity" values="0.35;1;0.35" dur="1.6s" '
             f'repeatCount="indefinite"/></circle>'
             + T(W / 2 + 280, 75, 'LIVE DATA', fs=12.5, fill=GREEN_OK,
                 font=MONO, w=700, ls=1.6))
    body += T(W / 2, 104, f'last 365 days — regenerated daily by Space Autopilot '
             f'({date_str})', fs=12.5, fill=FAINT, anchor='middle', font=MONO)

    # ---- contribution cells ----
    adates = sorted(d['date'] for d in active)
    longest = cur = 1 if adates else 0
    for i in range(1, len(adates)):
        prev = (datetime.date.fromisoformat(adates[i - 1])
                + datetime.timedelta(days=1)).isoformat()
        cur = cur + 1 if adates[i] == prev else 1
        longest = max(longest, cur)

    cells = {}
    for i, d in enumerate(days):
        col, row = i // 7, i % 7
        cells[(col, row)] = d

    # base faint cells
    body += '<g>'
    for (col, row), d in sorted(cells.items()):
        x, y = GX + col * PITCH, GY + row * PITCH
        body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{CS}" height="{CS}" '
                 f'rx="3" fill="rgba(255,255,255,0.045)"/>')
    body += '</g>'

    # active cells with 3D extrusion + glow (glowing stars)
    for (col, row), d in sorted(cells.items()):
        c = d['contributionCount']
        if c <= 0:
            continue
        x, y = GX + col * PITCH, GY + row * PITCH
        lv = level(c)
        colr = LADDER[lv - 1]
        body += (f'<rect x="{x + 2:.1f}" y="{y + 2:.1f}" width="{CS}" '
                 f'height="{CS}" rx="3" fill="rgba(3,2,15,0.55)"/>')
        if lv >= 3:
            gl = uid('gl')
            defs += (f'<radialGradient id="{gl}" cx="0.5" cy="0.5" r="0.5">'
                     f'<stop offset="0" stop-color="{colr}" '
                     f'stop-opacity="{0.6 if lv == 4 else 0.32}"/>'
                     f'<stop offset="1" stop-color="{colr}" '
                     f'stop-opacity="0"/></radialGradient>')
            body += (f'<ellipse cx="{x + CS / 2:.1f}" cy="{y + CS / 2:.1f}" '
                     f'rx="{CS * 0.95:.1f}" ry="{CS * 0.95:.1f}" fill="url(#{gl})">'
                     f'<animate attributeName="opacity" values="0.6;1;0.6" '
                     f'dur="{2.4 + (col % 5) * 0.3}s" '
                     f'begin="{(col * 0.11):.2f}s" repeatCount="indefinite"/>'
                     f'</ellipse>')
        body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{CS}" height="{CS}" '
                 f'rx="3" fill="{colr}" '
                 f'stroke="{rgba("#FFFFFF", 0.22)}" stroke-width="0.7">'
                 f'<animate attributeName="opacity" values="0.82;1;0.82" '
                 f'dur="{3.2 + (row % 4) * 0.4}s" '
                 f'begin="{(col * 0.07 + row * 0.05):.2f}s" '
                 f'repeatCount="indefinite"/></rect>')

    # ---- snake path: column scan weaving through active cells ----
    act_by_col = {}
    for (col, row), d in cells.items():
        if d['contributionCount'] > 0:
            act_by_col.setdefault(col, []).append(row)
    path = []
    prev_row = 0
    for col in sorted(act_by_col):
        rows = sorted(act_by_col[col])
        order = rows if prev_row <= 3 else list(reversed(rows))
        for r in order:
            path.append((col, r))
        prev_row = order[-1]
    if path:
        cx0 = lambda c: GX + c * PITCH + CS / 2  # noqa: E731
        cy0 = lambda r: GY + r * PITCH + CS / 2  # noqa: E731
        pts = [(cx0(c), cy0(r)) for c, r in path]
        dstr = (f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
                + ''.join(f' L{x:.1f},{y:.1f}' for x, y in pts[1:]))
        # halo
        body += (f'<path d="{dstr}" fill="none" stroke="{rgba(CYAN, 0.20)}" '
                 f'stroke-width="10" stroke-linecap="round" '
                 f'stroke-linejoin="round"/>')
        # nebula-gradient flowing dashes
        sg = uid('sg')
        defs += nebula_grad(sg)
        body += (f'<path d="{dstr}" fill="none" stroke="url(#{sg})" '
                 f'stroke-width="6.4" stroke-linecap="round" '
                 f'stroke-linejoin="round" stroke-dasharray="26 18">'
                 f'<animate attributeName="stroke-dashoffset" '
                 f'values="0;-88" dur="2.6s" repeatCount="indefinite"/>'
                 f'</path>')
        # tail fade dot
        body += (f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="4" '
                 f'fill="{AQUA}" opacity="0.85"/>')
        # head follows the path (gold-white comet)
        hb = uid('hb')
        defs += (f'<radialGradient id="{hb}" cx="0.5" cy="0.5" r="0.5">'
                 f'<stop offset="0" stop-color="#FFFFFF" '
                 f'stop-opacity="0.95"/>'
                 f'<stop offset="0.4" stop-color="{GOLD}" '
                 f'stop-opacity="0.6"/>'
                 f'<stop offset="1" stop-color="{GOLD}" '
                 f'stop-opacity="0"/></radialGradient>')
        dur = max(6.0, len(pts) * 0.42)
        body += (f'<circle r="{CS * 0.78:.1f}" fill="url(#{hb})">'
                 f'<animateMotion dur="{dur:.1f}s" repeatCount="indefinite" '
                 f'path="{dstr}"/></circle>'
                 f'<circle r="4.4" fill="#FFFFFF">'
                 f'<animateMotion dur="{dur:.1f}s" repeatCount="indefinite" '
                 f'path="{dstr}"/>'
                 f'<animate attributeName="r" values="4.4;5.2;4.4" '
                 f'dur="1.1s" repeatCount="indefinite"/></circle>')

    # month labels
    months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG',
              'SEP', 'OCT', 'NOV', 'DEC']
    seen = {}
    for (col, row), d in sorted(cells.items()):
        m = d['date'][5:7]
        if m not in seen:
            seen[m] = col
    for m, col in sorted(seen.items(), key=lambda kv: kv[1]):
        x = GX + col * PITCH + CS / 2
        if x < 80 or x > 950:
            continue
        body += T(x, 268, months[int(m) - 1], fs=10.5, fill=FAINT,
                  anchor='middle', font=MONO, w=600)

    # ---- stat chips ----
    busiest = max((d['contributionCount'] for d in days), default=0)
    stats = [('TOTAL ', total, CYAN), ('ACTIVE DAYS ', len(active), AQUA),
             ('BUSIEST DAY ', busiest, GOLD),
             ('LONGEST STREAK ', longest, PINK)]
    x = 54
    for lab, val, c in stats:
        defs, m, wd = chip(defs, x, 302, lab, val, c)
        body += m
        x += wd + 12
    body += T(958, 316, 'SELF-HOSTED · SPACE AUTOPILOT', fs=12, fill=FAINT,
              anchor='end', font=MONO, w=700, ls=1.2)

    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}" role="img">'
           f'<title>Contribution constellation — live data</title>'
           f'<defs>{defs}</defs>{body}</svg>\n')
    return doc


def main():
    token = os.environ.get('GITHUB_TOKEN', '')
    owner = (os.environ.get('OWNER')
             or os.environ.get('GITHUB_REPOSITORY', '/').split('/')[0])
    out = sys.argv[1] if len(sys.argv) > 1 else 'assets/snake.svg'
    if not owner:
        sys.exit('OWNER could not be resolved')
    if not token:
        sys.exit('GITHUB_TOKEN missing')
    total, days = fetch_calendar(owner, token)
    date_str = datetime.datetime.now(
        datetime.timezone.utc).strftime('%d %b %Y')
    doc = render(total, days, date_str)
    with open(out, 'w') as f:
        f.write(doc)
    print(f'snake.svg written ({os.path.getsize(out)} bytes) — '
          f'total={total}, active={sum(1 for d in days if d["contributionCount"] > 0)}')


if __name__ == '__main__':
    main()
