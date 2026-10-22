#!/usr/bin/env python3
"""Reconstruye capítulos .Rmd de bookdown (gitbook) a partir del HTML publicado.

uso: html2rmd.py capitulo.html salida.Rmd figdir_rel
"""
import re, sys, subprocess, html, json
from bs4 import BeautifulSoup, NavigableString, Tag

src, out, recfig = sys.argv[1], sys.argv[2], sys.argv[3]
soup = BeautifulSoup(open(src, encoding="utf8").read(), "html.parser")
sec = soup.select_one("section.normal")

PH = {}          # placeholder -> texto final (bloque)
INL = {}         # placeholder -> texto final (en línea)
missing_figs = []  # imágenes de figure-html sin código visible
hidden_chunks = []
n = [0]

def tok(prefix):
    n[0] += 1
    return f"ZZ{prefix}{n[0]:05d}ZZ"

def block_ph(text, node):
    t = tok("BLK")
    PH[t] = text
    p = soup.new_tag("p"); p.string = t
    node.replace_with(p)
    return p

def inline_ph(text, node):
    t = tok("INL")
    INL[t] = text
    node.replace_with(NavigableString(t))

def rstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

# ---------- limpieza general ----------
hdr = sec.select_one("#header")
meta = {}
if hdr:
    for k, sel in [("title", ".title"), ("author", ".author"), ("date", ".date")]:
        e = hdr.select_one(sel)
        if e: meta[k] = e.get_text(strip=True)
    hdr.decompose()
for e in sec.select("a.anchor-section, span.header-section-number, script, style, .html-widget, .html-widget-static-bound"):
    e.decompose()

# ---------- bibliografía por capítulo generada por bookdown (no es contenido fuente) ----------
for refs in sec.select("div#refs"):
    h = refs.find_previous_sibling(re.compile(r"^h[1-6]$"))
    if h is not None and h.get_text(strip=True) in ("Referencias", "References"):
        h.decompose()
    refs.decompose()

# ---------- secciones -> encabezados con id/unnumbered ----------
for d in sec.select("div.section"):
    h = d.find(re.compile(r"^h[1-6]$"), recursive=False)
    cls = d.get("class", [])
    if h is not None:
        if "level1" in cls and d.get("id"):
            h["id"] = d["id"]
        if "unnumbered" in cls:
            h["class"] = ["unnumbered"]
    d.unwrap()

# ---------- matemáticas (fuera de <summary>, que queda como HTML crudo) ----------
for m in sec.select("span.math"):
    if m.find_parent("summary"): continue
    t = m.get_text()
    if "display" in m.get("class", []):
        body = re.sub(r"^\s*\\\[|\\\]\s*$", "", t.strip()).strip("\n")
        inline_ph("$$\n" + body.strip() + "\n$$", m)
    else:
        body = re.sub(r"^\\\(|\\\)$", "", t.strip())
        inline_ph("$" + body.strip() + "$", m)

# ---------- citas ----------
for c in sec.select("span.citation"):
    keys = [a["href"].split("#ref-")[1] for a in c.select('a[href*="#ref-"]')]
    txt = c.get_text()
    paren = txt.strip().startswith("(")
    if keys:
        inline_ph(("[" + "; ".join("@" + k for k in keys) + "]") if paren
                  else "; ".join("@" + k for k in keys), c)

# ---------- referencias cruzadas y enlaces internos ----------
for a in sec.find_all("a", href=True):
    href = a["href"]
    if href.startswith(("http", "mailto")):
        continue
    m = re.match(r"^(?:[^#]*\.html)?#(.+)$", href)
    if m:
        anchor = m.group(1)
        if re.match(r"^(fig|tab|eq|thm|lem|def|exm|exr|cor|prp|cnj|rem):", anchor) or \
           re.fullmatch(r"\d+(\.\d+)*", a.get_text(strip=True)):
            inline_ph(f"\\@ref({anchor})", a)
        else:
            a["href"] = "#" + anchor

# ---------- captions de tablas: "Tabla x.y: " -> (\#tab:id) ----------
for cap in sec.find_all("caption"):
    sp = cap.find("span", id=re.compile(r"^tab:"))
    if sp:
        t = tok("INL"); INL[t] = f"(\\#{sp['id']}) "
        sp.replace_with(NavigableString(t))

# ---------- chunks ejecutables (dentro de <details class=chunk-details>) ----------
chunks = []   # dicts con label/opts/code/node
for det in sec.select("details.chunk-details"):
    pre = det.select_one("pre.sourceCode")
    lang = [c for c in pre.get("class", []) if c != "sourceCode"]
    lang = lang[0] if lang else "r"
    code = pre.get_text().rstrip("\n")
    ch = {"lang": lang, "code": code, "label": None,
          "opts": ["eval=FALSE"] if lang in ("bash", "sh", "zsh", "cmd", "powershell") or re.search(r"install\.packages|remotes::install|devtools::install|render_book|serve_book|rmarkdown::render|publish_book", code) else []}
    t = tok("CHK"); ch["tok"] = t
    p = soup.new_tag("p"); p.string = t
    det.replace_with(p)
    chunks.append(ch)
    PH[t] = ch

# chunk anterior en orden de documento
def prev_chunk(node):
    for prev in node.find_all_previous(string=re.compile(r"ZZ(CHK|BLK)\d+ZZ")):
        k = re.search(r"ZZ(?:CHK|BLK)\d+ZZ", prev).group(0)
        return PH.get(k) if k.startswith("ZZCHK") else None
    return None

def text_between(a_tok, node):
    """¿Hay texto narrativo entre el chunk y la imagen?"""
    txt = ""
    for el in node.find_all_previous(string=True):
        if a_tok in el: break
        txt += el
    return txt.strip()

def fig_label(srcpath):
    return re.sub(r"-\d+\.(png|jpg|jpeg|svg|pdf)$", "", srcpath.split("/")[-1])

# ---------- salidas de R: <pre><code>## ... ----------
# Si una salida no tiene un chunk visible justo antes, había un chunk oculto (echo=FALSE).
for pre in sec.find_all("pre"):
    if pre.get("class"): continue
    lines = [l for l in pre.get_text().split("\n") if l.strip()]
    if not (lines and all(l.startswith("##") for l in lines)): continue
    ch = prev_chunk(pre)
    if ch and text_between(ch["tok"], pre) == "":
        pre.decompose(); continue
    salida = "\n".join("# " + l for l in lines)
    c2 = {"lang": "r", "label": None, "opts": ["echo=FALSE", "eval=FALSE"],
          "code": "# TODO: chunk oculto (echo=FALSE); su código no aparece en el HTML.\n# Salida publicada:\n" + salida}
    hidden_chunks.append(lines[0][:60])
    t = tok("CHK"); c2["tok"] = t; PH[t] = c2
    p = soup.new_tag("p"); p.string = t
    pre.replace_with(p)

# ---------- tablas que son salida de un chunk visible (kable) ----------
for tb in sec.find_all("table"):
    ch = prev_chunk(tb)
    if ch and text_between(ch["tok"], tb) == "":
        tb.decompose()

# ---------- figuras con caption (div.figure) ----------
for fig in sec.select("div.figure"):
    img = fig.find("img")
    capel = fig.select_one("p.caption")
    cap = re.sub(r"^\s*Figura\s+[\d.]+:\s*", "", capel.decode_contents()).strip() if capel else None
    cap_txt = html.unescape(re.sub(r"<[^>]+>", "", cap)) if cap else None
    sp = fig.find("span", id=re.compile(r"^fig:"))
    fid = sp["id"][4:] if sp else None
    s = img["src"]
    width = img.get("width")
    align = "center" if "center" in (fig.get("style") or "") else None
    if "figure-html/" in s:
        ch = prev_chunk(fig)
        lab = fid or fig_label(s)
        if ch and (ch["label"] in (None, lab)) and text_between(ch["tok"], fig) == "":
            ch["label"] = lab
            if cap_txt: ch["opts"].append(f"fig.cap={rstr(cap_txt)}")
            if align: ch["opts"].append('fig.align="center"')
            fig.decompose(); continue
        missing_figs.append(s)
        code = f'# TODO: el código de esta figura no era visible (echo=FALSE).\nknitr::include_graphics("{recfig}/{s.split("/")[-1]}")'
    else:
        lab = fid
        srcs = [i["src"] for i in fig.find_all("img")]
        code = (f'knitr::include_graphics("{s}")' if len(srcs) == 1 else
                "knitr::include_graphics(c(\n  " + ",\n  ".join(f'"{x}"' for x in srcs) + "\n))")
    opts = ["echo=FALSE"]
    if cap_txt: opts.append(f"fig.cap={rstr(cap_txt)}")
    if align: opts.append('fig.align="center"')
    if width and width.endswith("%"): opts.append(f'out.width="{width}"')
    ch = {"lang": "r", "code": code, "label": lab, "opts": opts}
    t = tok("CHK"); ch["tok"] = t; PH[t] = ch
    p = soup.new_tag("p"); p.string = t
    fig.replace_with(p)

# ---------- gráficos sin caption (img sueltos de figure-html) ----------
for img in sec.find_all("img"):
    s = img.get("src", "")
    if "figure-html/" not in s: continue
    ch = prev_chunk(img)
    lab = fig_label(s)
    if ch and ch["label"] in (None, lab) and ch["lang"] == "r" and text_between(ch["tok"], img) == "":
        ch["label"] = lab
        img.decompose(); continue
    missing_figs.append(s)
    c2 = {"lang": "r", "label": lab, "opts": ["echo=FALSE"],
          "code": f'# TODO: el código de esta figura no era visible (echo=FALSE).\nknitr::include_graphics("{recfig}/{s.split("/")[-1]}")'}
    t = tok("CHK"); c2["tok"] = t; PH[t] = c2
    img.replace_with(NavigableString("\n\n" + t + "\n\n"))

# ---------- tablas kableExtra ----------
def cell_html(td):
    return td.decode_contents().strip()

for tb in sec.select("table.table"):
    prev = tb.find_previous(["p", "pre", "table", "ul", "ol", "h1", "h2", "h3", "h4", "div"])
    after_chunk = prev is not None and prev.name == "p" and re.fullmatch(r"ZZCHK\d+ZZ", prev.get_text(strip=True) or "")
    if after_chunk:
        tb.decompose(); continue           # era salida de un chunk visible
    # tabla de contenido hecha con kableExtra y echo=FALSE: reconstruir código
    cap = tb.find("caption")
    capid, captxt = None, None
    if cap:
        txt = cap.get_text(" ", strip=True)
        m = re.search(r"ZZINL\d+ZZ", txt)
        if m:
            capid = INL[m.group(0)].strip()[3:-1]   # (\#tab:xxx) -> tab:xxx
            txt = txt.replace(m.group(0), "").strip()
        captxt = txt
    heads = [th.get_text(" ", strip=True) for th in tb.select("thead th")]
    rows = [[cell_html(td) for td in tr.find_all("td")] for tr in tb.select("tbody tr")]
    cols = []
    for j, hname in enumerate(heads):
        vals = ",\n    ".join(rstr(re.sub(r"\s*\n\s*", " ", r[j])) for r in rows)
        cols.append(f"  {rstr(hname)} = c(\n    {vals})")
    widths = []
    for j, td in enumerate(tb.select("tbody tr")[0].find_all("td")):
        m = re.search(r"width:\s*([\d.]+\s*cm)", td.get("style", ""))
        if m: widths.append(f'  column_spec({j+1}, width = "{m.group(1).replace(" ", "")}")')
    code = "library(kableExtra)\ntabla <- data.frame(\n" + ",\n".join(cols) + ",\n  check.names = FALSE)\n\n"
    code += f"kbl(tabla, caption = {rstr(captxt or '')}, escape = FALSE) |>\n"
    code += '  kable_styling(bootstrap_options = c("striped", "hover", "condensed", "responsive"),\n                full_width = FALSE) |>\n'
    code += '  row_spec(0, bold = TRUE, color = "black", background = "#D9E2F1")'
    if widths: code += " |>\n" + " |>\n".join(widths)
    code += "\n# Nota: código reconstruido a partir del HTML; revisar estilos de filas."
    lab = capid[4:] if capid else None
    ch = {"lang": "r", "code": code, "label": lab, "opts": ["echo=FALSE"]}
    t = tok("CHK"); ch["tok"] = t; PH[t] = ch
    p = soup.new_tag("p"); p.string = t
    tb.replace_with(p)

# ---------- bloques <details class="admon-box ..."> (colapsables): HTML crudo ----------
for det in sec.select("details.admon-box"):
    summ = det.find("summary")
    open_t = tok("BLK"); close_t = tok("BLK")
    cls = " ".join(det.get("class", []))
    PH[open_t] = f'<details class="{cls}">\n{str(summ)}\n'
    PH[close_t] = "</details>"
    summ.decompose()
    det.insert(0, BeautifulSoup(f"<p>{open_t}</p>", "html.parser"))
    det.append(BeautifulSoup(f"<p>{close_t}</p>", "html.parser"))
    det.unwrap()

# ---------- código estático (no ejecutado) dentro de div.sourceCode ----------
for d in sec.select("div.sourceCode"):
    pre = d.find("pre")
    lang = [c for c in pre.get("class", []) if c != "sourceCode"]
    code = pre.get_text().rstrip("\n")
    block_ph(f"```{lang[0] if lang else ''}\n{code}\n```", d)

# ---------- pandoc ----------
frag = sec.decode_contents()
fmt = ("markdown-native_spans-native_divs-raw_attribute-smart"
       "-simple_tables-multiline_tables-grid_tables")
md = subprocess.run(["pandoc", "-f", "html", "-t", fmt, "--wrap=none"],
                    input=frag, capture_output=True, text=True, check=True).stdout

def render_chunk(ch):
    head = ch["lang"]
    parts = [p for p in [ch.get("label")] if p] + ch["opts"]
    if parts: head += " " + ", ".join(parts)
    return f"```{{{head}}}\n{ch['code']}\n```"

for t, v in PH.items():
    rep = render_chunk(v) if isinstance(v, dict) else v
    md = md.replace(t, rep.replace("\\", "\\\\") if False else rep)
def _inl(mo):
    v = INL[mo.group(0)]
    return v
out_lines = []
for line in md.split("\n"):
    if "ZZINL" in line:
        ind = re.match(r"\s*", line).group(0)
        # en listas, la sangría de continuación incluye el marcador
        mlist = re.match(r"(\s*)([-*+]|\d+[.)])(\s+)", line)
        if mlist: ind = " " * len(mlist.group(0))
        line = re.sub(r"ZZINL\d+ZZ", lambda mo: INL[mo.group(0)].replace("\n", "\n" + ind), line)
    out_lines.append(line)
md = "\n".join(out_lines)

# limpieza: <span class="icon"></span> -> []{.icon}; líneas en blanco múltiples
md = re.sub(r"\n{3,}", "\n\n", md)
open(out, "w", encoding="utf8").write(md.strip() + "\n")
json.dump({"meta": meta, "missing_figs": missing_figs,
           "chunks": len(chunks), "hidden": hidden_chunks}, open(out + ".json", "w"), ensure_ascii=False)
print(out, "chunks:", len(chunks), "figs sin código:", len(missing_figs), "chunks ocultos:", len(hidden_chunks))
