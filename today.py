#!/usr/bin/env python3
"""Gera dark_mode.svg e light_mode.svg (terminal estilo neofetch) para o README do perfil.

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
PROFILE = [
    ("Role", "Software Engineer"),
    ("Uptime", None),  # calculado
    ("Host", "Universidade Veiga de Almeida"),
    ("IDE", "VSCode, IntelliJ IDEA"),
    None,
    ("Languages.Code", "Java, Python, C"),
    None,
    ("Focus", "Full-Stack"),
    None,
    ("Hobbies", "Games, Music, Anime, Movies"),
    None,
    ("- Contact", None),
    ("Email", "davioviegas@gmail.com"),
]
TAGLINE = '"Take Your Heart"'

THEMES = {
    "dark_mode": dict(bg="#0d0d0d", border="#2a2a2a", key="#e60012", val="#f2f2f2",
                      dots="#555555", head="#e60012", tag="#e60012", black="#4a4a4a"),
    "light_mode": dict(bg="#fafafa", border="#d9d9d9", key="#c4000f", val="#111111",
                       dots="#aaaaaa", head="#c4000f", tag="#c4000f", black="#000000"),
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
    """Lê o HTML gerado por conversores ASCII (spans coloridos + <br>) -> lista de linhas de (char, hex)."""
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


def art_svg_lines(rows, theme, x, y0, step_y, step_x=1):
    out = []
    for i, row in enumerate(rows):
        spans = []
        for ch, col in row[::step_x]:
            lum = luminance(col)
            if lum > 0.93 or ch == " ":      # fundo branco do conversor -> vazio
                spans.append(" ")
                continue
            if lum < 0.08:                    # pretos somem no tema escuro
                col = theme["black"]
            spans.append(f'<tspan fill="{col}">{html.escape(ch)}</tspan>')
        text = "".join(spans).rstrip()
        out.append(f'<text x="{x}" y="{y0 + i * step_y}" xml:space="preserve" class="art">{text}</text>')
    return out

# ----------------------------------------------------------------- svg
def build_svg(theme_name, rows, stats):
    t = THEMES[theme_name]
    cols = max(len(r) for r in rows)
    ART_FS, ART_STEP = 7, 8
    art_w = int(cols * ART_FS * 0.6) + 20
    info_x = art_w + 40
    W_CHARS = 58                 # largura da coluna de info (caracteres)
    FS = 13
    width = info_x + int(W_CHARS * FS * 0.6) + 30
    height = max(len(rows) * ART_STEP + 70, 380)

    lines = []
    lines.append(f'<tspan class="head">{USER}@github</tspan> <tspan fill="{t["dots"]}">{"-" * (W_CHARS - len(USER) - 8)}</tspan>')

    def entry(key, val):
        label = f"{key}:"
        dots = max(2, W_CHARS - len(label) - len(val) - 2)
        return (f'<tspan class="key">{html.escape(label)}</tspan>'
                f'<tspan class="dots"> {"." * dots} </tspan>'
                f'<tspan class="val">{html.escape(val)}</tspan>')

    for item in PROFILE:
        if item is None:
            lines.append("")
            continue
        key, val = item
        if key.startswith("- "):
            lines.append(f'<tspan fill="{t["dots"]}">- </tspan><tspan class="key">{html.escape(key[2:])}</tspan> '
                         f'<tspan fill="{t["dots"]}">{"-" * (W_CHARS - len(key) - 1)}</tspan>')
            continue
        if key == "Uptime":
            val = uptime()
        lines.append(entry(key, val))
    lines.append("")
    lines.append(f'<tspan fill="{t["dots"]}">- </tspan><tspan class="key">GitHub Stats</tspan> '
                 f'<tspan fill="{t["dots"]}">{"-" * (W_CHARS - 14)}</tspan>')
    for k in ("Repos", "Commits", "Stars", "Followers"):
        lines.append(entry(k, stats.get(k, "--")))
    lines.append("")
    lines.append(f'<tspan class="tag">{html.escape(TAGLINE)}</tspan>')

    info = []
    for i, ln in enumerate(lines):
        if ln:
            info.append(f'<text x="{info_x}" y="{40 + i * 20}" xml:space="preserve" class="info">{ln}</text>')

    art = art_svg_lines(rows, t, 20, 40, ART_STEP)

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace">
<style>
.art{{font-size:{ART_FS}px;white-space:pre}}
.info{{font-size:{FS}px;white-space:pre;fill:{t["val"]}}}
.key{{fill:{t["key"]};font-weight:bold}}
.val{{fill:{t["val"]}}}
.dots{{fill:{t["dots"]}}}
.head{{fill:{t["head"]};font-weight:bold}}
.tag{{fill:{t["tag"]};font-style:italic;font-weight:bold}}
</style>
<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12" fill="{t["bg"]}" stroke="{t["border"]}"/>
{chr(10).join(art)}
{chr(10).join(info)}
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
