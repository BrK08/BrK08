#!/usr/bin/env python3
"""Aurora 3D — Self-hosted contribution snake generator.

Runs inside the Aurora Autopilot GitHub Actions workflow (or locally with a
token). Fetches the REAL contribution calendar from the GitHub GraphQL API
and renders assets/snake.svg in the Aurora 3D style: extruded contribution
cells, a gradient snake weaving through the active days with SMIL motion.

Pure stdlib (urllib + json). Exits non-zero on API failure so the workflow
never commits a blank or wrong panel.
"""
import datetime
import json
import os
import sys
import urllib.request

# ---------------- palette ----------------
VIOLET = '#7C5CFF'; CYAN = '#38BDF8'; AQUA = '#2DD4BF'; EMERALD = '#34D399'
GREEN_OK = '#4ADE9B'; PINK = '#F472B6'; AMBER = '#FFB454'
TXT = '#E6ECFF'; SUB = '#9FB0D9'; FAINT = '#7484AD'
SANS = "Segoe UI, -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace"
W = 1170

LADDER = ['#2A3A6E', '#3D5AA8', '#4F7CFF', '#7C5CFF']  # intensity levels

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


def aurora_grad(gid):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="#A78BFA"/>'
            f'<stop offset="0.28" stop-color="#7C5CFF"/>'
            f'<stop offset="0.55" stop-color="#38BDF8"/>'
            f'<stop offset="0.8" stop-color="#2DD4BF"/>'
            f'<stop offset="1" stop-color="#34D399"/></linearGradient>')


def T(x, y, s, fs=16, fill=TXT, w=400, anchor='start', ls=None, font=SANS):
    a = f'x="{x}" y="{y}" font-family="{font}" font-size="{fs}" font-weight="{w}" fill="{fill}"'
    if anchor != 'start':
        a += f' text-anchor="{anchor}"'
    if ls is not None:
        a += f' letter-spacing="{ls}"'
    return f'<text {a}>{esc(s)}</text>'


def grad_text(defs, x, y, s, fs, w=800, anchor='middle', glow_color=None):
    gt = uid('gt')
    defs += aurora_grad(gt)
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


def chip(defs, x, y, label, value, color, fs=12):
    wdt = len(label) * fs * 0.62 + len(str(value)) * fs * 0.68 + 40
    m = (f'<rect x="{x}" y="{y}" width="{wdt:.0f}" height="26" rx="13" '
         f'fill="{rgba(color, 0.13)}" stroke="{rgba(color, 0.55)}" stroke-width="1"/>'
         f'<circle cx="{x + 14}" cy="{y + 13}" r="3" fill="{color}">'
         f'<animate attributeName="opacity" values="0.35;1;0.35" dur="2.2s" '
         f'repeatCount="indefinite"/></circle>'
         + T(x + 24, y + 17.5, label, fs=fs, fill=SUB, font=MONO, w=600)
         + T(x + 24 + len(label) * fs * 0.62 + 9, y + 17.5, str(value),
             fs=fs, fill=lighten(color, 0.35), font=MONO, w=700))
    return defs, m, wdt


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
                                     'User-Agent': 'aurora-autopilot',
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
    # grid geometry: 53 weeks x 7 days, cell pitch 19
    GX, GY = 82, 118
    PITCH, CS = 19, 16.5
    ncol = max(len(days) // 7, 1)
    defs = (f'<filter id="softShadow" x="-40%" y="-40%" width="180%" '
            f'height="180%"><feGaussianBlur stdDeviation="10"/></filter>')
    body = ''

    # glass panel
    px, py, pw, ph = 40, 26, 1090, 320
    pg = uid('pg')
    defs += (f'<linearGradient id="{pg}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0A1028" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#080C1E" stop-opacity="0.96"/>'
             f'</linearGradient>')
    body += (f'<rect x="{px}" y="{py + 10}" width="{pw}" height="{ph}" rx="20" '
             f'fill="rgba(5,6,15,0.55)" filter="url(#softShadow)"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" '
             f'fill="url(#{pg})" stroke="{rgba(AQUA, 0.5)}" stroke-width="1.4"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="4" rx="2" '
             f'fill="{rgba(AQUA, 0.8)}"/>')

    # aurora blobs
    for cx, cy, rx, ry, col, op, dx, dy, dur, beg in [
            (-40, 90, 300, 120, AQUA, 0.16, 26, 8, 12, 0),
            (1210, 250, 280, 110, VIOLET, 0.18, -26, 6, 13, 2)]:
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
    defs, m = grad_text(defs, W / 2, 74, '3D CONTRIBUTION SNAKE', 27, w=800,
                        anchor='middle', glow_color=AQUA)
    body += m
    active = [d for d in days if d['contributionCount'] > 0]
    body += (f'<circle cx="{W / 2 + 238}" cy="66" r="4.5" fill="{GREEN_OK}">'
             f'<animate attributeName="opacity" values="0.35;1;0.35" dur="1.6s" '
             f'repeatCount="indefinite"/></circle>'
             + T(W / 2 + 250, 70, 'LIVE DATA', fs=10.5, fill=GREEN_OK,
                 font=MONO, w=700, ls=1.4))
    body += T(W / 2, 99, f'last 365 days — regenerated daily by Aurora Autopilot '
             f'({date_str})', fs=11.5, fill=FAINT, anchor='middle', font=MONO)

    # ---- contribution cells ----
    # active dates set for streaks
    adates = sorted(d['date'] for d in active)
    longest = cur = 1 if adates else 0
    for i in range(1, len(adates)):
        prev = (datetime.date.fromisoformat(adates[i - 1])
                + datetime.timedelta(days=1)).isoformat()
        cur = cur + 1 if adates[i] == prev else 1
        longest = max(longest, cur)

    cells = {}          # (col,row) -> dict
    for i, d in enumerate(days):
        col, row = i // 7, i % 7
        cells[(col, row)] = d
    ncol = max(i // 7 for i in range(len(days))) + 1

    # base faint cells
    body += '<g>'
    for (col, row), d in sorted(cells.items()):
        x, y = GX + col * PITCH, GY + row * PITCH
        body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{CS}" height="{CS}" '
                 f'rx="3.2" fill="rgba(255,255,255,0.045)"/>')
    body += '</g>'

    # active cells with 3D extrusion + glow
    for (col, row), d in sorted(cells.items()):
        c = d['contributionCount']
        if c <= 0:
            continue
        x, y = GX + col * PITCH, GY + row * PITCH
        lv = level(c)
        colr = LADDER[lv - 1]
        # drop shadow (extrusion)
        body += (f'<rect x="{x + 2:.1f}" y="{y + 2:.1f}" width="{CS}" '
                 f'height="{CS}" rx="3.2" fill="rgba(3,4,13,0.55)"/>')
        # glow for strong cells
        if lv >= 3:
            gl = uid('gl')
            defs += (f'<radialGradient id="{gl}" cx="0.5" cy="0.5" r="0.5">'
                     f'<stop offset="0" stop-color="{colr}" '
                     f'stop-opacity="{0.55 if lv == 4 else 0.3}"/>'
                     f'<stop offset="1" stop-color="{colr}" '
                     f'stop-opacity="0"/></radialGradient>')
            body += (f'<ellipse cx="{x + CS / 2:.1f}" cy="{y + CS / 2:.1f}" '
                     f'rx="{CS * 0.95}" ry="{CS * 0.95}" fill="url(#{gl})">'
                     f'<animate attributeName="opacity" values="0.6;1;0.6" '
                     f'dur="{2.4 + (col % 5) * 0.3}s" '
                     f'begin="{(col * 0.11):.2f}s" repeatCount="indefinite"/>'
                     f'</ellipse>')
        # cell
        body += (f'<rect x="{x:.1f}" y="{y:.1f}" width="{CS}" height="{CS}" '
                 f'rx="3.2" fill="{colr}" '
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
        # body: soft halo
        body += (f'<path d="{dstr}" fill="none" stroke="{rgba(CYAN, 0.20)}" '
                 f'stroke-width="11" stroke-linecap="round" '
                 f'stroke-linejoin="round"/>')
        # body: aurora gradient flowing dashes
        sg = uid('sg')
        defs += aurora_grad(sg)
        body += (f'<path d="{dstr}" fill="none" stroke="url(#{sg})" '
                 f'stroke-width="7" stroke-linecap="round" '
                 f'stroke-linejoin="round" stroke-dasharray="30 22">'
                 f'<animate attributeName="stroke-dashoffset" '
                 f'values="0;-104" dur="2.6s" repeatCount="indefinite"/>'
                 f'</path>')
        # tail fade dot
        body += (f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="4" '
                 f'fill="{AQUA}" opacity="0.85"/>')
        # head follows the path
        hb = uid('hb')
        defs += (f'<radialGradient id="{hb}" cx="0.5" cy="0.5" r="0.5">'
                 f'<stop offset="0" stop-color="#FFFFFF" '
                 f'stop-opacity="0.95"/>'
                 f'<stop offset="0.4" stop-color="{EMERALD}" '
                 f'stop-opacity="0.55"/>'
                 f'<stop offset="1" stop-color="{EMERALD}" '
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
        if x < 95 or x > 1075:
            continue
        body += T(x, 272, months[int(m) - 1], fs=9.5, fill=FAINT,
                  anchor='middle', font=MONO, w=600)

    # ---- stat chips ----
    busiest = max((d['contributionCount'] for d in days), default=0)
    stats = [('TOTAL ', total, CYAN), ('ACTIVE DAYS ', len(active), AQUA),
             ('BUSIEST DAY ', busiest, AMBER),
             ('LONGEST STREAK ', longest, PINK)]
    x = 74
    for lab, val, c in stats:
        defs, m, wd = chip(defs, x, 296, lab, val, c)
        body += m
        x += wd + 12
    body += T(1112, 304, 'SELF-HOSTED · AURORA AUTOPILOT', fs=11, fill=FAINT,
              anchor='end', font=MONO, w=700, ls=1.2)

    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="372" '
           f'viewBox="0 0 {W} 372" role="img">'
           f'<title>3D contribution snake — live data</title>'
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
