#!/usr/bin/env python3
"""Space 3D — Live Deep-Space Telemetry generator (self-hosted stats panel).

Runs inside the Space Autopilot GitHub Actions workflow. Fetches REAL numbers
from the GitHub REST/GraphQL API and renders assets/live_stats_3d.svg in the
same Space 3D style as the boot frame. No third-party widget service.

Pure stdlib (urllib + json). Exits non-zero on API failure so the workflow
never commits a blank or wrong panel.

Usage:
  live_stats.py <out.svg>            # real data (needs GITHUB_TOKEN + OWNER)
  live_stats.py <out.svg> --boot     # boot frame placeholder
"""
import datetime
import json
import os
import random
import sys
import urllib.request

# ---------------- palette (Space design system) ----------------
VIOLET = '#8B5CF6'; LAV = '#A78BFA'; CYAN = '#22D3EE'; ICE = '#7DD3FC'
AQUA = '#2DD4BF'; MAGENTA = '#FF3D9A'; PINK = '#F472B6'; BLUE = '#7B8CFF'
GOLD = '#FBBF24'; ORANGE = '#FB923C'; GREEN_OK = '#4ADE9B'
TXT = '#EEF2FF'; SUB = '#A6B4D8'; FAINT = '#7E8BB3'; INK = '#040212'
SANS = "Segoe UI, -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace"
W = 1012
H = 438

LANG_COLORS = {
    'C#': '#A78BFA', 'Java': '#FBBF24', 'C++': '#7B8CFF', 'Python': '#22D3EE',
    'JavaScript': '#FDE68A', 'TypeScript': '#67E8F9', 'Lua': '#7DD3FC',
    'Batch': '#C4B5FD', 'PowerShell': '#5EEAD4', 'Shell': '#99F6E4',
    'HTML': '#FB923C', 'CSS': '#93C5FD', 'SCSS': '#F9A8D4', 'PHP': '#A6B4D8',
    'C': '#8FA8E8', 'Go': '#22D3EE', 'Rust': '#F472B6', 'Ruby': '#FF3D9A',
    'Kotlin': '#C084FC', 'Swift': '#FB923C', 'Vue': '#2DD4BF',
}

_uid = [0]


def uid(p='ls'):
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


def fade(values, dur, begin=0):
    return (f'<animate attributeName="opacity" values="{values}" dur="{dur}s" '
            f'begin="{begin}s" repeatCount="indefinite"/>')


def bob(values, dur, begin):
    return (f'<animateTransform attributeName="transform" type="translate" '
            f'values="{values}" dur="{dur}s" begin="{begin}s" '
            f'repeatCount="indefinite" calcMode="spline" '
            f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>')


def grad_text(defs, x, y, s, fs, w=800, anchor='start', glow_color=None):
    gt = uid('gt')
    defs += nebula_grad(gt)
    anc = f' text-anchor="{anchor}"' if anchor != 'start' else ''
    m = ''
    if glow_color:
        gf = uid('gf')
        defs += (f'<filter id="{gf}" x="-70%" y="-70%" width="240%" height="240%">'
                 f'<feGaussianBlur stdDeviation="{max(5, fs * 0.13)}"/></filter>')
        m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
              f'font-weight="{w}" fill="{glow_color}" opacity="0.9"{anc} '
              f'filter="url(#{gf})">{esc(s)}</text>')
    m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
          f'font-weight="{w}"{anc} fill="url(#{gt})">{esc(s)}</text>')
    return defs, m


def glass_tile(defs, x, y, w, h, c):
    g = uid('pn')
    defs += (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0D1130" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#090C24" stop-opacity="0.96"/>'
             f'</linearGradient>')
    m = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" '
         f'fill="url(#{g})" stroke="{rgba(c, 0.45)}" stroke-width="1.2"/>'
         f'<rect x="{x}" y="{y}" width="{w}" height="3.6" rx="1.8" fill="{rgba(c, 0.75)}"/>')
    return defs, m


def hud_corners(x, y, w, h, c, L=13):
    st = f'stroke="{rgba(c, 0.8)}" stroke-width="2" fill="none" stroke-linecap="round"'
    return (f'<path d="M{x},{y + L} V{y} H{x + L}" {st}/>'
            f'<path d="M{x + w - L},{y} H{x + w} V{y + L}" {st}/>'
            f'<path d="M{x},{y + h - L} V{y + h} H{x + L}" {st}/>'
            f'<path d="M{x + w - L},{y + h} H{x + w} V{y + h - L}" {st}/>')


def star_field(n, seed):
    rnd = random.Random(seed)
    out = []
    for _ in range(n):
        x = rnd.uniform(14, W - 14)
        y = rnd.uniform(12, H - 14)
        r = rnd.uniform(0.9, 1.9)
        d = rnd.uniform(2.4, 5.4)
        b = rnd.uniform(-d, 0)
        c = rnd.choice(['#FFFFFF', '#BFD3FF', '#FFE9C8', '#C9D6FF'])
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{c}">'
                   f'{fade("0.15;0.85;0.15", d, b)}</circle>')
    return ''.join(out)


def satellite(cx, cy, sc, color):
    return (f'<g transform="translate({cx} {cy}) scale({sc})">'
            f'<line x1="0" y1="-8" x2="0" y2="-15" stroke="{SUB}" stroke-width="1.4"/>'
            f'<circle cx="0" cy="-18" r="4.4" fill="none" stroke="{color}" stroke-width="1.7"/>'
            f'<rect x="-25" y="-4.5" width="14" height="9" rx="1" '
            f'fill="{rgba(color, 0.8)}" stroke="{rgba("#02030C", 0.4)}" stroke-width="0.8"/>'
            f'<rect x="11" y="-4.5" width="14" height="9" rx="1" '
            f'fill="{rgba(color, 0.8)}" stroke="{rgba("#02030C", 0.4)}" stroke-width="0.8"/>'
            f'<rect x="-8" y="-6" width="16" height="12" rx="2.5" fill="#C9D2F0" '
            f'stroke="{rgba("#0B1030", 0.5)}" stroke-width="1"/>'
            f'<circle cx="-5" cy="-2" r="1.4" fill="{GREEN_OK}">'
            f'{fade("0.25;1;0.25", 1.6, 0)}</circle></g>')


# ---------------- GitHub API ----------------
def api(url, token):
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'space-autopilot',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def graphql(query, token):
    body = json.dumps({'query': query}).encode()
    req = urllib.request.Request('https://api.github.com/graphql', data=body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'space-autopilot',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch(owner, token):
    user = api(f'https://api.github.com/users/{owner}', token)
    stats = {
        'repos': user.get('public_repos', 0),
        'followers': user.get('followers', 0),
        'stars': 0,
        'commits': None,
    }
    repos, page = [], 1
    while page <= 3:
        chunk = api(f'https://api.github.com/users/{owner}/repos'
                    f'?per_page=100&page={page}', token)
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1
    for r in repos:
        stats['stars'] += r.get('stargazers_count', 0)
    langs = {}
    for r in repos[:10]:
        try:
            data = api(f'https://api.github.com/repos/{owner}/{r["name"]}/languages', token)
            for lang, byts in data.items():
                langs[lang] = langs.get(lang, 0) + byts
        except Exception:
            continue
    stats['langs'] = langs
    try:
        q = ('query{user(login:"%s"){contributionsCollection{'
             'contributionCalendar{totalContributions}}}}' % owner)
        resp = graphql(q, token)
        stats['commits'] = resp['data']['user']['contributionsCollection'][
            'contributionCalendar']['totalContributions']
    except Exception:
        stats['commits'] = None  # degrade gracefully, keep tile honest
    return stats


# ---------------- render ----------------
def fmt(n):
    return f'{n:,}'.replace(',', ' ')


def _panel(defs, body):
    px, py, pw, ph = 30, 26, 952, 386
    pg = uid('pg')
    defs += (f'<linearGradient id="{pg}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0A0E28" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#080B20" stop-opacity="0.96"/>'
             f'</linearGradient>')
    body += (f'<rect x="{px}" y="{py + 10}" width="{pw}" height="{ph}" rx="20" '
             f'fill="rgba(4,2,18,0.55)" filter="url(#softShadow)"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" '
             f'fill="url(#{pg})" stroke="{rgba(CYAN, 0.5)}" stroke-width="1.4"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="4" rx="2" fill="{rgba(CYAN, 0.8)}"/>'
             + hud_corners(px + 10, py + 10, pw - 20, ph - 20, CYAN, 13))
    # nebulae + stars
    for cx, cy, rx, ry, col, op, dx, dy, dur, beg in [
            (-40, 100, 300, 110, CYAN, 0.13, 26, 8, 12, 0),
            (1050, 320, 280, 100, VIOLET, 0.16, -26, 6, 13, 2)]:
        bg = uid('bl')
        defs += (f'<radialGradient id="{bg}" cx="0.5" cy="0.5" r="0.5">'
                 f'<stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                 f'<stop offset="1" stop-color="{col}" stop-opacity="0"/>'
                 f'</radialGradient>')
        body += (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{bg})">'
                 f'{bob(f"0 0;{dx} {dy};0 0", dur, beg)}</ellipse>')
    body += star_field(30, 31)
    body += satellite(px + pw - 40, py + 36, 0.62, ICE)
    return defs, body, (px, py, pw, ph)


def render_title(defs, body):
    defs, m = grad_text(defs, W / 2, 78, 'DEEP SPACE TELEMETRY', 30, w=800,
                        anchor='middle', glow_color=CYAN)
    body += m
    body += (f'<circle cx="{W / 2 + 262}" cy="70" r="5" fill="{GREEN_OK}">'
             f'{fade("0.35;1;0.35", 1.6, 0)}</circle>'
             + T(W / 2 + 276, 75, 'SELF-HOSTED', fs=12.5, fill=GREEN_OK,
                 font=MONO, w=700, ls=1.6))
    return defs, body


def _tiles_defs():
    return [
        ('repos', 'PUBLIC REPOS', 'live from GitHub API', CYAN),
        ('followers', 'FOLLOWERS', 'live from GitHub API', VIOLET),
        ('stars', 'STARS EARNED', 'across public repos', GOLD),
        ('commits', 'COMMITS · 12 MO', 'contribution calendar', PINK),
    ]


def tile_layout(i):
    x, y, w, h = 54 + i * 230, 112, 210, 150
    return x, y, w, h


def render_tiles(defs, body, values, boot=False):
    for i, (key, lab, sub, c) in enumerate(_tiles_defs()):
        x, y, w, h = tile_layout(i)
        defs, tm = glass_tile(defs, x, y, w, h, c)
        inner = T(x + 22, y + 32, lab, fs=13, fill=SUB, font=MONO, w=700, ls=1.2)
        val = values[key]
        pending = boot and key != 'repos'
        if pending:
            shg = uid('sh')
            defs += (f'<linearGradient id="{shg}" x1="0" y1="0" x2="1" y2="0">'
                     f'<stop offset="0" stop-color="{c}" stop-opacity="0.1"/>'
                     f'<stop offset="0.5" stop-color="{c}" stop-opacity="0.55"/>'
                     f'<stop offset="1" stop-color="{c}" stop-opacity="0.1"/>'
                     f'</linearGradient>')
            inner += (f'<text x="{x + 22}" y="{y + 96}" font-family="{SANS}" '
                      f'font-size="44" font-weight="800" fill="{rgba(c, 0.75)}" '
                      f'letter-spacing="7">...'
                      f'{fade("0.25;1;0.25", 1.8, i * 0.4)}</text>')
            inner += (f'<rect x="{x + 22}" y="{y + 108}" width="150" height="7" rx="3.5" '
                      f'fill="{rgba("#FFFFFF", 0.06)}"/>'
                      f'<rect x="{x + 22}" y="{y + 108}" width="40" height="7" rx="3.5" '
                      f'fill="url(#{shg})">'
                      f'<animate attributeName="x" values="{x + 22};{x + 132}" '
                      f'dur="1.9s" begin="{i * 0.35}s" repeatCount="indefinite" '
                      f'calcMode="spline" keySplines="0.45 0 0.55 1"/></rect>')
            sub = 'fills on first run'
        else:
            defs, vm = grad_text(defs, x + 24, y + 100, val, 44, w=800,
                                 glow_color=c)
            inner += vm
        inner += T(x + 22, y + 132, sub, fs=12.5, fill=FAINT, font=MONO)
        body += (f'<g>{bob("0 0;0 -5;0 0", 5 + i * 0.4, i * 0.6)}{tm}{inner}</g>')
    return defs, body


def render_langs(defs, body, segs, note):
    ly = 308
    body += T(54, ly, 'TOP LANGUAGES', fs=13, fill=SUB, font=MONO, w=700, ls=1.6)
    body += T(200, ly, note, fs=12.5, fill=FAINT, font=MONO)
    barx, bary, barw, barh = 54, ly + 12, 904, 12
    clip = uid('clip')
    defs += (f'<clipPath id="{clip}"><rect x="{barx}" y="{bary}" '
             f'width="{barw}" height="{barh}" rx="6"/></clipPath>')
    body += (f'<rect x="{barx}" y="{bary}" width="{barw}" height="{barh}" rx="6" '
             f'fill="rgba(255,255,255,0.06)"/>')
    sx = barx
    body += f'<g clip-path="url(#{clip})">'
    if segs is None:
        ag = uid('ag')
        defs += nebula_grad(ag)
        body += (f'<rect x="{barx}" y="{bary}" width="90" height="{barh}" rx="6" '
                 f'fill="url(#{ag})" opacity="0.9">'
                 f'<animate attributeName="width" values="50;140;50" dur="3.2s" '
                 f'repeatCount="indefinite"/></rect>')
    else:
        for name, frac in segs:
            sw = max(5, barw * frac)
            col = LANG_COLORS.get(name, LAV) if name != 'Other' else '#5A6A9E'
            body += (f'<rect x="{sx:.1f}" y="{bary}" width="{sw:.1f}" height="{barh}" '
                     f'fill="{col}">'
                     f'<animate attributeName="opacity" values="0.75;1;0.75" '
                     f'dur="3s" begin="{sx % 2}s" repeatCount="indefinite"/></rect>')
            sx += sw
    body += '</g>'
    return defs, body, ly


def render_footer(defs, body, stamp):
    chips = [('SELF-GENERATED', CYAN), ('NO THIRD-PARTY API', VIOLET),
             ('DAILY 02:00 UTC', AQUA)]
    x = 54
    for lab, c in chips:
        wdt = len(lab) * 13 * 0.62 + 26
        body += (f'<rect x="{x}" y="362" width="{wdt:.0f}" height="27" rx="13.5" '
                 f'fill="{rgba(c, 0.13)}" stroke="{rgba(c, 0.55)}" stroke-width="1"/>'
                 f'<text x="{x + wdt / 2:.0f}" y="380" font-family="{MONO}" '
                 f'font-size="13" font-weight="600" fill="{lighten(c, 0.3)}" '
                 f'text-anchor="middle" letter-spacing="0.4">{esc(lab)}</text>')
        x += wdt + 12
    body += T(958, 380, stamp, fs=12, fill=FAINT, anchor='end',
              font=MONO, w=700, ls=1.2)
    return defs, body


def wrap(defs, body):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" role="img">'
            '<title>Deep Space Telemetry — live GitHub stats</title>'
            f'<defs><filter id="softShadow" x="-40%" y="-40%" width="180%" '
            f'height="180%"><feGaussianBlur stdDeviation="10"/></filter>'
            f'{defs}</defs>{body}</svg>\n')


def render(stats, date_str):
    defs = ''
    body = ''
    defs, body, _ = _panel(defs, body)
    defs, body = render_title(defs, body)
    values = {
        'repos': fmt(stats['repos']),
        'followers': fmt(stats['followers']),
        'stars': fmt(stats['stars']),
        'commits': fmt(stats['commits']) if stats['commits'] is not None else '--',
    }
    if stats['commits'] is None:
        for key, lab, sub, c in _tiles_defs():
            if key == 'commits':
                pass
    defs, body = render_tiles(defs, body, values, boot=False)
    langs = sorted(stats['langs'].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs) or 1
    top = langs[:5]
    other = sum(v for _, v in langs[5:])
    segs = [(n, v / total) for n, v in top]
    if other:
        segs.append(('Other', other / total))
    if not segs:
        segs = [('Awaiting data', 1.0)]
    defs, body, ly = render_langs(defs, body, segs,
                                  '— by bytes across public repositories')
    lg = '   '.join(f'{n} {round(f * 100)}%' for n, f in segs)
    body += T(54, ly + 52, lg[:118], fs=13, fill=SUB, font=MONO)
    defs, body = render_footer(defs, body,
                              f'UPDATED {date_str} · SPACE AUTOPILOT')
    return wrap(defs, body)


def render_boot():
    defs = ''
    body = ''
    defs, body, _ = _panel(defs, body)
    defs, body = render_title(defs, body)
    values = {'repos': '4', 'followers': '...', 'stars': '...',
              'commits': '...'}
    defs, body = render_tiles(defs, body, values, boot=True)
    defs, body, ly = render_langs(defs, body, None,
                                  '— computed from live repo data on first run')
    body += T(54, ly + 52, 'booting telemetry core...', fs=13, fill=FAINT,
              font=MONO)
    defs, body = render_footer(defs, body,
                               'SPACE AUTOPILOT · AWAITING FIRST RUN')
    return wrap(defs, body)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    boot = '--boot' in sys.argv
    out = args[0] if args else 'assets/live_stats_3d.svg'
    if boot:
        doc = render_boot()
        with open(out, 'w') as f:
            f.write(doc)
        print(f'live_stats_3d.svg boot frame written ({os.path.getsize(out)} bytes)')
        return
    token = os.environ.get('GITHUB_TOKEN', '')
    owner = (os.environ.get('OWNER')
             or os.environ.get('GITHUB_REPOSITORY', '/').split('/')[0])
    if not owner:
        sys.exit('OWNER could not be resolved')
    if not token:
        sys.exit('GITHUB_TOKEN missing — this script must run inside Actions '
                 'or with a token in env')
    stats = fetch(owner, token)
    date_str = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y')
    doc = render(stats, date_str)
    with open(out, 'w') as f:
        f.write(doc)
    print(f'live_stats_3d.svg written ({os.path.getsize(out)} bytes)')
    print('stats:', json.dumps(stats, ensure_ascii=False)[:400])


if __name__ == '__main__':
    main()
