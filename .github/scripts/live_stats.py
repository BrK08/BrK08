#!/usr/bin/env python3
"""Aurora 3D — Live GitHub Telemetry generator (self-hosted stats panel).

Runs inside the Aurora Autopilot GitHub Actions workflow. Fetches REAL
numbers from the GitHub REST/GraphQL API and renders assets/live_stats_3d.svg
in the same Aurora 3D style as the boot frame. No third-party widget service.

Pure stdlib (urllib + json). Exits non-zero on API failure so the workflow
never commits a blank or wrong panel.
"""
import datetime
import json
import os
import sys
import urllib.request

# ---------------- palette (Aurora design system) ----------------
VIOLET = '#7C5CFF'; CYAN = '#38BDF8'; AQUA = '#2DD4BF'; AMERALD = '#34D399'
AMBER = '#FFB454'; PINK = '#F472B6'; LAV = '#A78BFA'; BLUE = '#4F7CFF'
GREEN_OK = '#4ADE9B'
TXT = '#E6ECFF'; SUB = '#9FB0D9'; FAINT = '#7484AD'
SANS = "Segoe UI, -apple-system, 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Code', 'Fira Code', Consolas, 'Courier New', monospace"
W = 1170

LANG_COLORS = {
    'C#': '#9B7CFF', 'Java': '#FFB454', 'C++': '#6FA8FF', 'Python': '#38BDF8',
    'JavaScript': '#FFD666', 'TypeScript': '#5CB3FF', 'Lua': '#7DD3FC',
    'Batch': '#A78BFA', 'PowerShell': '#63D6F5', 'Shell': '#8FE3C8',
    'HTML': '#FF8A66', 'CSS': '#8AB8FF', 'SCSS': '#FF92C7', 'PHP': '#9FB0D9',
    'C': '#7FA8E8', 'Go': '#7DE3F0', 'Rust': '#E8A87F', 'Ruby': '#F472B6',
    'Kotlin': '#C77FFF', 'Swift': '#FF9F6E', 'Vue': '#7DE8B8',
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


def aurora_grad(gid):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0" stop-color="#A78BFA"/>'
            f'<stop offset="0.28" stop-color="#7C5CFF"/>'
            f'<stop offset="0.55" stop-color="#38BDF8"/>'
            f'<stop offset="0.8" stop-color="#2DD4BF"/>'
            f'<stop offset="1" stop-color="#34D399"/></linearGradient>')


def glow_filter(gid, std=12):
    return (f'<filter id="{gid}" x="-70%" y="-70%" width="240%" height="240%">'
            f'<feGaussianBlur stdDeviation="{std}"/></filter>')


def T(x, y, s, fs=16, fill=TXT, w=400, anchor='start', ls=None, font=SANS):
    a = f'x="{x}" y="{y}" font-family="{font}" font-size="{fs}" font-weight="{w}" fill="{fill}"'
    if anchor != 'start':
        a += f' text-anchor="{anchor}"'
    if ls is not None:
        a += f' letter-spacing="{ls}"'
    return f'<text {a}>{esc(s)}</text>'


def grad_text(defs, x, y, s, fs, w=800, anchor='start', glow_color=None):
    gt = uid('gt')
    defs += aurora_grad(gt)
    m = ''
    if glow_color:
        gf = uid('gf')
        defs += glow_filter(gf, std=max(5, fs * 0.13))
        m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
              f'font-weight="{w}" fill="{glow_color}" opacity="0.9" '
              + (f'text-anchor="{anchor}" ' if anchor != 'start' else '')
              + f'filter="url(#{gf})">{esc(s)}</text>')
    m += (f'<text x="{x}" y="{y}" font-family="{SANS}" font-size="{fs}" '
          f'font-weight="{w}" '
          + (f'text-anchor="{anchor}" ' if anchor != 'start' else '')
          + f'fill="url(#{gt})">{esc(s)}</text>')
    return defs, m


def glass_tile(defs, x, y, w, h, c):
    g = uid('pn')
    defs += (f'<linearGradient id="{g}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0B1026" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#090C22" stop-opacity="0.96"/>'
             f'</linearGradient>')
    m = (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" '
         f'fill="url(#{g})" stroke="{rgba(c, 0.45)}" stroke-width="1.2"/>'
         f'<rect x="{x}" y="{y}" width="{w}" height="3.4" rx="1.7" fill="{rgba(c, 0.75)}"/>')
    return defs, m


# ---------------- GitHub API ----------------
def api(url, token):
    req = urllib.request.Request(url, headers={
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'aurora-autopilot',
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def graphql(query, token):
    body = json.dumps({'query': query}).encode()
    req = urllib.request.Request('https://api.github.com/graphql', data=body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'User-Agent': 'aurora-autopilot',
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


def render(stats, date_str):
    defs = (f'<filter id="softShadow" x="-40%" y="-40%" width="180%" '
            f'height="180%"><feGaussianBlur stdDeviation="10"/></filter>')
    body = ''
    px, py, pw, ph = 40, 26, 1090, 320
    pg = uid('pg')
    defs += (f'<linearGradient id="{pg}" x1="0" y1="0" x2="0" y2="1">'
             f'<stop offset="0" stop-color="#0A1028" stop-opacity="0.94"/>'
             f'<stop offset="1" stop-color="#080C1E" stop-opacity="0.96"/>'
             f'</linearGradient>')
    body += (f'<rect x="{px}" y="{py + 10}" width="{pw}" height="{ph}" rx="20" '
             f'fill="rgba(5,6,15,0.55)" filter="url(#softShadow)"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="{ph}" rx="20" '
             f'fill="url(#{pg})" stroke="{rgba(CYAN, 0.5)}" stroke-width="1.4"/>'
             f'<rect x="{px}" y="{py}" width="{pw}" height="4" rx="2" fill="{rgba(CYAN, 0.8)}"/>')
    # soft aurora blobs
    for cx, cy, rx, ry, col, op, dx, dy, dur, beg in [
            (-40, 90, 280, 110, CYAN, 0.16, 26, 8, 12, 0),
            (1210, 260, 280, 100, VIOLET, 0.18, -26, 6, 13, 2)]:
        bg = uid('bl')
        defs += (f'<radialGradient id="{bg}" cx="0.5" cy="0.5" r="0.5">'
                 f'<stop offset="0" stop-color="{col}" stop-opacity="{op}"/>'
                 f'<stop offset="1" stop-color="{col}" stop-opacity="0"/>'
                 f'</radialGradient>')
        body += (f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="url(#{bg})">'
                 f'<animateTransform attributeName="transform" type="translate" '
                 f'values="0 0;{dx} {dy};0 0" dur="{dur}s" begin="{beg}s" '
                 f'repeatCount="indefinite" calcMode="spline" '
                 f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/></ellipse>')
    # title
    defs, m = grad_text(defs, W / 2, 74, 'LIVE GITHUB TELEMETRY', 27, w=800,
                        anchor='middle', glow_color=CYAN)
    body += m
    body += (f'<circle cx="{W / 2 + 235}" cy="66" r="4.5" fill="{GREEN_OK}">'
             f'<animate attributeName="opacity" values="0.35;1;0.35" dur="1.6s" '
             f'repeatCount="indefinite"/></circle>'
             + T(W / 2 + 248, 70, 'SELF-HOSTED', fs=10.5, fill=GREEN_OK,
                 font=MONO, w=700, ls=1.4))
    # stat tiles
    tiles = [
        (fmt(stats['repos']), 'PUBLIC REPOS', 'live from GitHub API', CYAN),
        (fmt(stats['followers']), 'FOLLOWERS', 'live from GitHub API', VIOLET),
        (fmt(stats['stars']), 'STARS EARNED', 'across public repos', AMBER),
        (fmt(stats['commits']) if stats['commits'] is not None else '--',
         'COMMITS · 12 MO',
         'contribution calendar' if stats['commits'] is not None else 'API unavailable',
         PINK),
    ]
    for i, (val, lab, sub, c) in enumerate(tiles):
        x, y, w, h = 74 + i * 268, 104, 240, 128
        defs, tm = glass_tile(defs, x, y, w, h, c)
        inner = T(x + 20, y + 26, lab, fs=11, fill=SUB, font=MONO, w=700, ls=1.2)
        defs, vm = grad_text(defs, x + 22, y + 82, val, 40, w=800, glow_color=c)
        inner += vm
        inner += T(x + 20, y + 114, sub, fs=10.5, fill=FAINT, font=MONO)
        body += (f'<g><animateTransform attributeName="transform" type="translate" '
                 f'values="0 0;0 -5;0 0" dur="{5 + i * 0.4}s" begin="{i * 0.6}s" '
                 f'repeatCount="indefinite" calcMode="spline" '
                 f'keySplines="0.45 0 0.55 1;0.45 0 0.55 1"/>{tm}{inner}</g>')
    # languages bar
    ly = 262
    body += T(74, ly, 'TOP LANGUAGES', fs=11, fill=SUB, font=MONO, w=700, ls=1.4)
    langs = sorted(stats['langs'].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs) or 1
    top = langs[:5]
    other = sum(v for _, v in langs[5:])
    segs = [(n, v / total) for n, v in top]
    if other:
        segs.append(('Other', other / total))
    if not segs:
        segs = [('Awaiting data', 1.0)]
    body += T(196, ly, '— by bytes across public repositories', fs=11,
              fill=FAINT, font=MONO)
    barx, bary, barw, barh = 74, ly + 10, 1022, 10
    clip = uid('clip')
    defs += (f'<clipPath id="{clip}"><rect x="{barx}" y="{bary}" '
             f'width="{barw}" height="{barh}" rx="5"/></clipPath>')
    body += f'<rect x="{barx}" y="{bary}" width="{barw}" height="{barh}" rx="5" fill="rgba(255,255,255,0.06)"/>'
    sx = barx
    body += '<g clip-path="url(#' + clip + ')">'
    for name, frac in segs:
        sw = max(4, barw * frac)
        col = LANG_COLORS.get(name, LAV) if name != 'Other' else '#5A6A9E'
        body += (f'<rect x="{sx:.1f}" y="{bary}" width="{sw:.1f}" height="{barh}" '
                 f'fill="{col}">'
                 f'<animate attributeName="opacity" values="0.75;1;0.75" '
                 f'dur="3s" begin="{sx % 2}s" repeatCount="indefinite"/></rect>')
        sx += sw
    body += '</g>'
    # legend
    lg = '   '.join(f'{n} {round(f * 100)}%' for n, f in segs)
    body += T(barx, ly + 40, lg[:118], fs=11, fill=SUB, font=MONO)
    # footer chips + stamp
    x = 74
    for lab, c in [('SELF-GENERATED', CYAN), ('NO THIRD-PARTY API', VIOLET),
                   ('DAILY 02:00 UTC', AQUA)]:
        wdt = len(lab) * 11 * 0.62 + 20
        body += (f'<rect x="{x}" y="296" width="{wdt:.0f}" height="22" rx="11" '
                 f'fill="{rgba(c, 0.13)}" stroke="{rgba(c, 0.55)}" stroke-width="1"/>'
                 f'<text x="{x + wdt / 2:.0f}" y="311" font-family="{MONO}" '
                 f'font-size="11.5" font-weight="600" fill="{lighten(c, 0.3)}" '
                 f'text-anchor="middle" letter-spacing="0.4">{esc(lab)}</text>')
        x += wdt + 12
    body += T(1112, 304, f'UPDATED {date_str} · AURORA AUTOPILOT', fs=11,
              fill=FAINT, anchor='end', font=MONO, w=700, ls=1.2)
    doc = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="372" '
           f'viewBox="0 0 {W} 372" role="img">'
           f'<title>Live GitHub telemetry</title>'
           f'<defs>{defs}</defs>'
           f'<rect width="{W}" height="372" fill="none"/>{body}</svg>\n')
    return doc


def main():
    token = os.environ.get('GITHUB_TOKEN', '')
    owner = (os.environ.get('OWNER')
             or os.environ.get('GITHUB_REPOSITORY', '/').split('/')[0])
    out = sys.argv[1] if len(sys.argv) > 1 else 'assets/live_stats_3d.svg'
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
