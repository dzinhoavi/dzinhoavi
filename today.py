#!/usr/bin/env python3
"""Gera dark_mode.svg e light_mode.svg com layout de janelas retrô (estilo Windows 95/98).

Janelas: terminal (neofetch + sua arte), bloco de notas (bio), estatísticas do GitHub,
pastas de hobbies, caixa de diálogo com a frase final e uma barra de tarefas.

Uso:
    python today.py --art ascii-art.html            # com stats reais (precisa de ACCESS_TOKEN)
    python today.py --art ascii-art.html --offline  # sem rede, stats ficam como "--"

Variáveis de ambiente:
    ACCESS_TOKEN  Personal Access Token do GitHub (escopos: read:user, repo)
    USER_NAME     seu usuário do GitHub (padrão: dzinhoavi)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

USER = os.environ.get("USER_NAME", "dzinhoavi")
BIRTHDAY = dt.date(2005, 9, 17)

# ----------------------------------------------------------------- conteúdo
TERMINAL = [
    ("Role", "Software Engineer"),
    ("Uptime", None),  # calculado
    ("Host", "Universidade Veiga de Almeida"),
    ("IDE", "VSCode, IntelliJ IDEA"),
    None,
    ("Languages.Code", "Java, Python, C"),
    ("Focus", "Full-Stack"),
    None,
    ("- Contact", None),
    ("Email", "davioviegas@gmail.com"),
]
BIO_TITLE = f"Hi, I'm {USER}"
BIO = [
    "Software Engineer focado em desenvolvimento full-stack,",
    "usando Java, Python e C.",
    "Estudante na Universidade Veiga de Almeida.",
    "Fora do código: jogos, músicas, animes e filmes.",
    "Contato: davioviegas@gmail.com",
]
HOBBIES = ["Games", "Music", "Anime", "Movies"]
TAGLINE = '"Take Your Heart"'

THEMES = {
    "dark_mode": dict(bg="#101010", border="#2e2e2e"),
    "light_mode": dict(bg="#f4f4f4", border="#cfcfcf"),
}

# ----------------------------------------------------------------- uptime
def uptime(today=None):
    today = today or dt.date.today()
    y = today.year - BIRTHDAY.year
    m = today.month - BIRTHDAY.month
    d = today.day - BIRTHDAY.day
    if d < 0:
        m -= 1
        prev_end = today.replace(day=1) - dt.timedelta(days=1)
        d += prev_end.day
    if m < 0:
        y -= 1
        m += 12
    return f"{y} years, {m} months, {d} days"

# ----------------------------------------------------------------- stats
def gql(token, query, variables=None):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables or {}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_stats(token):
    base = gql(token, """
      query($login:String!){ user(login:$login){
        createdAt followers{totalCount}
        repositories(ownerAffiliations:OWNER, isFork:false, first:100){
          totalCount nodes{stargazerCount} }
        repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST]){totalCount}
      }}""", {"login": USER})["user"]
    created = dt.datetime.fromisoformat(base["createdAt"].replace("Z", "+00:00"))
    commits = 0
    for year in range(created.year, dt.date.today().year + 1):
        c = gql(token, """
          query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
            contributionsCollection(from:$from,to:$to){
              totalCommitContributions restrictedContributionsCount }}}""",
                {"login": USER, "from": f"{year}-01-01T00:00:00Z",
                 "to": f"{year}-12-31T23:59:59Z"})["user"]["contributionsCollection"]
        commits += c["totalCommitContributions"] + c["restrictedContributionsCount"]
    return {
        "Repos": f'{base["repositories"]["totalCount"]} {{Contributed: {base["repositoriesContributedTo"]["totalCount"]}}}',
        "Commits": f"{commits:,}",
        "Stars": f'{sum(n["stargazerCount"] for n in base["repositories"]["nodes"]):,}',
        "Followers": f'{base["followers"]["totalCount"]:,}',
    }

# ----------------------------------------------------------------- arte
SPAN = re.compile(r'<span style="color:#([0-9a-fA-F]{6})">(.*?)</span>', re.S)
UNESC = {"&lt;": "<", "&gt;": ">", "&amp;": "&", "&nbsp;": " "}


def load_art(path):
    """Lê o HTML gerado por conversores ASCII (spans coloridos + <br>) -> linhas de (char, hex)."""
    raw = open(path, encoding="utf-8").read()
    body = raw.split("<body>", 1)[-1].split("</body>", 1)[0]
    rows = []
    for line in re.split(r"<br\s*/?>", body):
        row = []
        for color, ch in SPAN.findall(line):
            ch = UNESC.get(ch, ch)
            row.append((ch if ch else " ", "#" + color.lower()))
        if row:
            rows.append(row)
    return rows


def luminance(hexcolor):
    r, g, b = (int(hexcolor[i:i + 2], 16) for i in (1, 3, 5))
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def art_svg_lines(rows, x, y0, step_y, black="#5a5a5a"):
    out = []
    for i, row in enumerate(rows):
        spans = []
        for ch, col in row:
            lum = luminance(col)
            if lum > 0.93 or ch == " ":      # fundo branco do conversor -> vazio
                spans.append(" ")
                continue
            if lum < 0.08:                    # pretos ficam cinza para aparecer no terminal preto
                col = black
            spans.append(f'<tspan fill="{col}">{html.escape(ch)}</tspan>')
        text = "".join(spans).rstrip()
        if text:
            out.append(f'<text x="{x}" y="{y0 + i * step_y}" xml:space="preserve" class="art">{text}</text>')
    return out

# ----------------------------------------------------------------- peças retrô
GREY = "#c0c0c0"


def e(s):
    return html.escape(str(s))


def raised(x, y, w, h, fill=GREY):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
            f'<path d="M{x + .5},{y + h - .5}V{y + .5}H{x + w - .5}" stroke="#fff" fill="none"/>'
            f'<path d="M{x + w - .5},{y + .5}V{y + h - .5}H{x + .5}" stroke="#000" fill="none"/>'
            f'<path d="M{x + 1.5},{y + h - 1.5}V{y + 1.5}H{x + w - 1.5}" stroke="#dfdfdf" fill="none"/>'
            f'<path d="M{x + w - 1.5},{y + 1.5}V{y + h - 1.5}H{x + 1.5}" stroke="#808080" fill="none"/>')


def sunken(x, y, w, h, fill="#fff"):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}"/>'
            f'<path d="M{x + .5},{y + h - .5}V{y + .5}H{x + w - .5}" stroke="#808080" fill="none"/>'
            f'<path d="M{x + w - .5},{y + .5}V{y + h - .5}H{x + .5}" stroke="#fff" fill="none"/>'
            f'<path d="M{x + 1.5},{y + h - 1.5}V{y + 1.5}H{x + w - 1.5}" stroke="#404040" fill="none"/>'
            f'<path d="M{x + w - 1.5},{y + 1.5}V{y + h - 1.5}H{x + 1.5}" stroke="#dfdfdf" fill="none"/>')


def button(x, y, w, h, label):
    return (raised(x, y, w, h) +
            f'<text x="{x + w / 2}" y="{y + h / 2 + 4}" text-anchor="middle" class="ui">{e(label)}</text>')


def ctl(x, y, kind):
    s = raised(x, y, 16, 14)
    if kind == "min":
        s += f'<rect x="{x + 4}" y="{y + 9}" width="6" height="2" fill="#000"/>'
    elif kind == "max":
        s += (f'<rect x="{x + 3.5}" y="{y + 2.5}" width="9" height="8" fill="none" stroke="#000"/>'
              f'<rect x="{x + 3}" y="{y + 2}" width="10" height="2" fill="#000"/>')
    else:
        s += f'<path d="M{x + 4},{y + 3}L{x + 11},{y + 10}M{x + 11},{y + 3}L{x + 4},{y + 10}" stroke="#000" stroke-width="1.6" fill="none"/>'
    return s


def window(x, y, w, h, title):
    """Desenha a moldura da janela e devolve (svg, (cx, cy, cw, ch)) com a área de conteúdo."""
    s = raised(x, y, w, h)
    s += f'<rect x="{x + 3}" y="{y + 3}" width="{w - 6}" height="18" fill="url(#tb)"/>'
    s += f'<text x="{x + 8}" y="{y + 16}" class="ttl">{e(title)}</text>'
    s += ctl(x + w - 55, y + 5, "min") + ctl(x + w - 39, y + 5, "max") + ctl(x + w - 21, y + 5, "close")
    return s, (x + 4, y + 25, w - 8, h - 29)


def folder(x, y):
    return (f'<polygon points="{x},{y + 8} {x},{y + 2} {x + 14},{y + 2} {x + 18},{y + 8}" fill="#f4dc55" stroke="#5a4a00"/>'
            f'<rect x="{x}" y="{y + 8}" width="40" height="26" fill="#f8e468" stroke="#5a4a00"/>'
            f'<path d="M{x + 1.5},{y + 9.5}H{x + 38.5}" stroke="#fff6a8"/>')


def heart(x, y):
    return (f'<path transform="translate({x},{y})" d="M16 29C3 19 0 11 6 6C10 3 15 5 16 9C17 5 22 3 26 6C32 11 29 19 16 29Z" '
            f'fill="#e60012" stroke="#000" stroke-width="1.5"/>'
            f'<path transform="translate({x},{y})" d="M8 9C9 8 11 8 12 9" stroke="#ff8a93" stroke-width="2" fill="none"/>')

STYLE = """
.ui{font:11px Tahoma,Verdana,'DejaVu Sans',sans-serif;fill:#000}
.uib{font:bold 11px Tahoma,Verdana,'DejaVu Sans',sans-serif;fill:#000}
.h1{font:bold 14px Tahoma,Verdana,'DejaVu Sans',sans-serif;fill:#000}
.ttl{font:bold 11px Tahoma,Verdana,'DejaVu Sans',sans-serif;fill:#fff}
.mono{font:12px Consolas,'Courier New','DejaVu Sans Mono',monospace;white-space:pre;fill:#f2f2f2}
.mono11{font:11px Consolas,'Courier New','DejaVu Sans Mono',monospace;fill:#000}
.art{font:7px Consolas,'Courier New','DejaVu Sans Mono',monospace;white-space:pre}
.key{fill:#ff2a3a;font-weight:bold}
.val{fill:#f2f2f2}
.dots{fill:#6a6a6a}
"""

# ----------------------------------------------------------------- svg
def terminal_lines(info_chars):
    W = info_chars
    lines = [f'<tspan class="val">{e("C:" + chr(92) + "> neofetch")}</tspan>', ""]
    lines.append(f'<tspan class="key">{e(USER)}@github</tspan> <tspan class="dots">{"-" * (W - len(USER) - 8)}</tspan>')
    for item in TERMINAL:
        if item is None:
            lines.append("")
            continue
        key, val = item
        if key.startswith("- "):
            label = key[2:]
            lines.append(f'<tspan class="dots">- </tspan><tspan class="key">{e(label)}</tspan> '
                         f'<tspan class="dots">{"-" * (W - len(label) - 3)}</tspan>')
            continue
        if key == "Uptime":
            val = uptime()
        label = f"{key}:"
        dots = max(2, W - len(label) - len(val) - 2)
        lines.append(f'<tspan class="key">{e(label)}</tspan><tspan class="dots"> {"." * dots} </tspan>'
                     f'<tspan class="val">{e(val)}</tspan>')
    return lines


def build_svg(theme_name, rows, stats):
    t = THEMES[theme_name]
    M, GAP = 20, 14
    ART_FS, ART_STEP = 7, 8
    FS, LH, INFO_CHARS = 12, 18, 50

    cols = max(len(r) for r in rows)
    art_w = int(cols * ART_FS * 0.6) + 4
    art_h = len(rows) * ART_STEP
    info_w = int(INFO_CHARS * FS * 0.6) + 8
    lines = terminal_lines(INFO_CHARS)
    info_h = len(lines) * LH

    tw = max(art_w + info_w + 44, 700)
    body_h = max(art_h, info_h) + 28
    th = body_h + 29
    lw = int(tw * 0.56)
    rw = tw - lw - GAP
    W = tw + 2 * M

    parts = []

    # --- janela 1: terminal -------------------------------------------------
    s, (cx, cy, cw, ch) = window(M, M, tw, th, "Administrator: Command Prompt")
    parts.append(s)
    parts.append(sunken(cx, cy, cw, ch, "#000"))
    extra = tw - (art_w + info_w + 44)
    ax = cx + 14 + extra // 2
    ix = ax + art_w + 16
    ay = cy + 14 + max(0, (info_h - art_h) // 2)
    parts += art_svg_lines(rows, ax, ay + ART_FS, ART_STEP)
    iy = cy + 14 + max(0, (art_h - info_h) // 2) + LH - 4
    for i, ln in enumerate(lines):
        if ln:
            parts.append(f'<text x="{ix}" y="{iy + i * LH}" xml:space="preserve" class="mono">{ln}</text>')

    # --- linha 2: notas + stats ---------------------------------------------
    y1, h1 = M + th + GAP, 160
    s, (cx, cy, cw, ch) = window(M, y1, lw, h1, "Notes")
    parts.append(s)
    parts.append(f'<text x="{cx + 6}" y="{cy + 13}" class="ui" xml:space="preserve">File   Edit   Search   Help</text>')
    parts.append(sunken(cx, cy + 18, cw, ch - 18))
    parts.append(f'<text x="{cx + 10}" y="{cy + 42}" class="h1">{e(BIO_TITLE)}</text>')
    for i, ln in enumerate(BIO):
        parts.append(f'<text x="{cx + 10}" y="{cy + 62 + i * 15}" class="ui">{e(ln)}</text>')

    s, (cx, cy, cw, ch) = window(M + lw + GAP, y1, rw, h1, "GitHub Stats")
    parts.append(s)
    parts.append(sunken(cx + 6, cy + 6, cw - 12, ch - 12))
    for i, k in enumerate(("Repos", "Commits", "Stars", "Followers")):
        ry = cy + 6 + 12 + i * 26
        if i:
            parts.append(f'<path d="M{cx + 10},{ry - 12.5}H{cx + cw - 10}" stroke="#c0c0c0"/>')
        parts.append(f'<text x="{cx + 14}" y="{ry + 8}" class="uib">{e(k)}</text>')
        parts.append(f'<text x="{cx + cw - 14}" y="{ry + 8}" text-anchor="end" class="ui">{e(stats.get(k, "--"))}</text>')

    # --- linha 3: hobbies + diálogo -----------------------------------------
    y2, h2 = y1 + h1 + GAP, 140
    s, (cx, cy, cw, ch) = window(M, y2, lw, h2, "Hobbies")
    parts.append(s)
    parts.append(sunken(cx + 6, cy + 6, cw - 12, 18))
    parts.append(f'<text x="{cx + 12}" y="{cy + 19}" class="mono11" xml:space="preserve">{e("C:" + chr(92) + "Users" + chr(92) + USER + chr(92) + "Hobbies")}</text>')
    px, py, pw, ph = cx + 6, cy + 30, cw - 12, ch - 36
    parts.append(sunken(px, py, pw, ph))
    slot = pw / len(HOBBIES)
    for i, name in enumerate(HOBBIES):
        mid = px + slot * (i + .5)
        parts.append(folder(round(mid - 20), py + 10))
        parts.append(f'<text x="{mid:.1f}" y="{py + 10 + 34 + 16}" text-anchor="middle" class="ui">{e(name)}</text>')

    s, (cx, cy, cw, ch) = window(M + lw + GAP, y2, rw, h2, "Message")
    parts.append(s)
    parts.append(heart(cx + 18, cy + 18))
    parts.append(f'<text x="{cx + 66}" y="{cy + 40}" class="h1">{e(TAGLINE)}</text>')
    parts.append(button(cx + cw // 2 - 37, cy + ch - 34, 74, 24, "OK"))

    # --- barra de tarefas ---------------------------------------------------
    ty = y2 + h2 + 16
    H = ty + 28
    parts.append(raised(0, ty, W, 28))
    parts.append(raised(4, ty + 3, 62, 22))
    for dx, dy, col in ((0, 0, "#e60012"), (6, 0, "#ffffff"), (0, 6, "#000000"), (6, 6, "#e60012")):
        parts.append(f'<rect x="{10 + dx}" y="{ty + 7 + dy}" width="5" height="5" fill="{col}" stroke="#000" stroke-width=".6"/>')
    parts.append(f'<text x="29" y="{ty + 18}" class="uib">Start</text>')
    parts.append(sunken(72, ty + 3, 150, 22, "#d8d8d8"))
    parts.append(f'<text x="80" y="{ty + 18}" class="uib">{e(USER)}@github</text>')
    parts.append(sunken(W - 132, ty + 3, 128, 22))
    parts.append(f'<text x="{W - 68}" y="{ty + 18}" text-anchor="middle" class="ui">Updated {dt.date.today().strftime("%d/%m/%Y")}</text>')

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" shape-rendering="crispEdges" text-rendering="geometricPrecision">
<defs><linearGradient id="tb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#7a0009"/><stop offset="1" stop-color="#ff2a3a"/></linearGradient></defs>
<style>{STYLE}</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="{t["bg"]}" stroke="{t["border"]}"/>
{chr(10).join(parts)}
</svg>
'''

# ----------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", default="ascii-art.html", help="HTML de arte ASCII colorida (seu arquivo)")
    ap.add_argument("--out", default=".", help="pasta de saída")
    ap.add_argument("--offline", action="store_true", help="não consulta a API")
    args = ap.parse_args()

    rows = load_art(args.art)
    if not rows:
        sys.exit(f"Nenhuma linha de arte encontrada em {args.art}")

    stats = {}
    token = os.environ.get("ACCESS_TOKEN")
    if not args.offline:
        if not token:
            sys.exit("Defina ACCESS_TOKEN ou use --offline.")
        stats = fetch_stats(token)

    os.makedirs(args.out, exist_ok=True)
    for name in THEMES:
        path = os.path.join(args.out, f"{name}.svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(build_svg(name, rows, stats))
        print("escrito", path)


if __name__ == "__main__":
    main()
