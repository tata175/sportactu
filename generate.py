#!/usr/bin/env python3
"""Générateur de site média statique (bibliothèque standard uniquement).

Usage:
    python generate.py           # récupère les flux RSS et construit ./public
    python generate.py --demo    # construit le site avec des articles factices (test hors-ligne)
"""
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "public"
DATA = ROOT / "data" / "articles.json"
UA = "Mozilla/5.0 (compatible; MediaAutoBot/1.0)"
NS = {"atom": "http://www.w3.org/2005/Atom", "media": "http://search.yahoo.com/mrss/",
      "content": "http://purl.org/rss/1.0/modules/content/"}


def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def clean(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def excerpt(text, n):
    text = clean(text)
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def parse_date(s):
    if not s:
        return datetime.now(timezone.utc)
    try:
        d = parsedate_to_datetime(s)
    except Exception:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return datetime.now(timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fetch_feed(feed, n_chars):
    req = urllib.request.Request(feed["url"], headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.iter("item"):  # RSS 2.0
        link = (it.findtext("link") or "").strip()
        items.append({
            "title": clean(it.findtext("title")), "link": link,
            "excerpt": excerpt(it.findtext("description"), n_chars),
            "date": parse_date(it.findtext("pubDate")).isoformat(), "source": feed["name"]})
    for en in root.findall("atom:entry", NS):  # Atom
        l = en.find("atom:link", NS)
        items.append({
            "title": clean(en.findtext("atom:title", namespaces=NS)),
            "link": (l.get("href") if l is not None else "") or "",
            "excerpt": excerpt(en.findtext("atom:summary", namespaces=NS), n_chars),
            "date": parse_date(en.findtext("atom:updated", namespaces=NS)).isoformat(),
            "source": feed["name"]})
    return [i for i in items if i["title"] and i["link"].startswith("http")]


def demo_items():
    now = datetime.now(timezone.utc).isoformat()
    return [{"title": f"Article de démonstration n°{i}", "link": f"https://example.com/{i}",
             "excerpt": "Ceci est un extrait factice pour tester la mise en page du site.",
             "date": now, "source": "Démo"} for i in range(1, 9)]


def collect(cfg, demo):
    old = json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else []
    new = demo_items() if demo else []
    if not demo:
        for f in cfg["feeds"]:
            try:
                got = fetch_feed(f, cfg["excerpt_chars"])
                print(f"[ok] {f['name']}: {len(got)} articles")
                new += got
            except Exception as e:
                print(f"[erreur] {f['name']}: {e}", file=sys.stderr)
    seen, merged = set(), []
    for a in sorted(new + old, key=lambda x: x["date"], reverse=True):
        if a["link"] not in seen:
            seen.add(a["link"])
            merged.append(a)
    merged = merged[: cfg["max_items_history"]]
    if not demo:
        DATA.parent.mkdir(exist_ok=True)
        DATA.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    return merged


def ai_digest(cfg, articles):
    """'Le point du jour' original, via l'API Anthropic. Désactivé par défaut."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not (cfg["ai_digest"]["enabled"] and key and articles):
        return ""
    titles = "\n".join(f"- {a['title']} ({a['source']})" for a in articles[:25])
    body = {"model": cfg["ai_digest"]["model"], "max_tokens": 600, "messages": [{"role": "user", "content":
            "Voici les titres de l'actualité sportive récente. Rédige en français, avec tes propres mots, un 'Le point sport du jour' "
            "de 120 à 180 mots qui dégage les 2-3 tendances. Ne recopie aucun titre, n'invente aucun fait, "
            "ne cite que ce qui ressort de ces titres.\n" + titles}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)["content"][0]["text"].strip()
    except Exception as e:
        print(f"[erreur IA] {e}", file=sys.stderr)
        return ""


CSS = """
:root{--bg:#fafaf8;--fg:#1a1a1a;--mut:#666;--acc:#0b5fff;--card:#fff;--bd:#e5e5e0}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--mut:#999;--acc:#6ea0ff;--card:#1d1d1d;--bd:#2c2c2c}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,sans-serif}
header,main,footer{max-width:780px;margin:0 auto;padding:0 18px}header{padding-top:28px;padding-bottom:10px;border-bottom:2px solid var(--fg)}
h1{margin:0;font-size:1.9rem}h1 a{color:inherit;text-decoration:none}.tag{color:var(--mut);margin:4px 0 0}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;margin:14px 0}
.card h2{font-size:1.1rem;margin:0 0 4px}.card a{color:var(--fg);text-decoration:none}.card a:hover{color:var(--acc)}
.meta{font-size:.8rem;color:var(--mut)}.digest{border-left:4px solid var(--acc)}.ad{min-height:100px;margin:14px 0;text-align:center}
footer{padding:24px 18px;color:var(--mut);font-size:.85rem}footer a{color:var(--mut)}
"""


def page(cfg, title, body, desc=""):
    ads = ""
    if cfg["adsense_publisher_id"]:
        ads = (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client='
               f'{cfg["adsense_publisher_id"]}" crossorigin="anonymous"></script>')
    e = html.escape
    return f"""<!doctype html><html lang="{cfg['language']}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title>
<meta name="description" content="{e(desc or cfg['tagline'])}">
<link rel="alternate" type="application/rss+xml" href="{cfg['base_url']}/feed.xml">
<style>{CSS}</style>{ads}</head><body>
<header><h1><a href="{cfg['base_url']}/">{e(cfg['site_name'])}</a></h1><p class="tag">{e(cfg['tagline'])}</p></header>
<main>{body}</main>
<footer><a href="{cfg['base_url']}/a-propos.html">À propos</a> · <a href="{cfg['base_url']}/mentions-legales.html">Mentions légales</a> ·
<a href="{cfg['base_url']}/confidentialite.html">Confidentialité</a> · <a href="{cfg['base_url']}/feed.xml">RSS</a></footer></body></html>"""


def ad_slot(cfg):
    pid = cfg["adsense_publisher_id"]
    if not pid:
        return ""
    return (f'<div class="ad"><ins class="adsbygoogle" style="display:block" data-ad-client="{pid}" '
            'data-ad-format="auto" data-full-width-responsive="true"></ins>'
            '<script>(adsbygoogle=window.adsbygoogle||[]).push({});</script></div>')


def fmt_date(iso):
    return datetime.fromisoformat(iso).strftime("%d/%m/%Y %H:%M")


def build(cfg, articles, digest):
    OUT.mkdir(exist_ok=True)
    e = html.escape
    parts = []
    if digest:
        paras = "".join(f"<p>{e(p)}</p>" for p in digest.split("\n\n"))
        parts.append(f'<div class="card digest"><h2>Le point sport du jour</h2>{paras}'
                     '<p class="meta">Synthèse rédigée par une IA à partir des titres ci-dessous.</p></div>')
    for i, a in enumerate(articles[: cfg["max_items_home"]]):
        parts.append(f'<article class="card"><h2><a href="{e(a["link"])}" rel="noopener" target="_blank">{e(a["title"])}</a></h2>'
                     f'<p>{e(a["excerpt"])}</p><p class="meta">{e(a["source"])} · {fmt_date(a["date"])} · '
                     f'<a href="{e(a["link"])}" rel="noopener" target="_blank">Lire l\'article chez la source →</a></p></article>')
        if i in (2, 12, 25):
            parts.append(ad_slot(cfg))
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    parts.append(f'<p class="meta">Dernière mise à jour : {updated}</p>')
    (OUT / "index.html").write_text(page(cfg, cfg["site_name"], "\n".join(parts)), encoding="utf-8")

    items = "".join(
        f"<item><title>{e(a['title'])}</title><link>{e(a['link'])}</link><guid>{e(a['link'])}</guid>"
        f"<description>{e(a['excerpt'])}</description><pubDate>{parse_date(a['date']).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate></item>"
        for a in articles[:50])
    (OUT / "feed.xml").write_text(
        f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>{e(cfg["site_name"])}</title>'
        f'<link>{cfg["base_url"]}/</link><description>{e(cfg["tagline"])}</description>{items}</channel></rss>', encoding="utf-8")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    pages = ["", "a-propos.html", "mentions-legales.html", "confidentialite.html"]
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "".join(f"<url><loc>{cfg['base_url']}/{p}</loc><lastmod>{today}</lastmod></url>" for p in pages) + "</urlset>")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {cfg['base_url']}/sitemap.xml\n")
    if cfg["adsense_publisher_id"]:
        pub = cfg["adsense_publisher_id"].replace("ca-", "")
        (OUT / "ads.txt").write_text(f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n")

    sources = ", ".join(f["name"] for f in cfg["feeds"])
    about = (f"<h2>À propos</h2><p>{e(cfg['site_name'])} est un site d'actualité automatisé : il rassemble les titres et courts "
             f"extraits publiés par des médias français ({e(sources)}) et renvoie systématiquement vers l'article d'origine. "
             "La page est actualisée automatiquement plusieurs fois par jour. Certaines synthèses peuvent être rédigées par une IA "
             "et sont alors signalées comme telles.</p>")
    legal = (f"<h2>Mentions légales</h2><p>Éditeur : {e(cfg['publisher_name'])}. Contact : {e(cfg['contact_email'])}.</p>"
             "<p>Hébergeur : GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, États-Unis.</p>"
             "<p>Les titres et extraits appartiennent à leurs éditeurs respectifs et sont repris avec renvoi vers la source.</p>")
    priv = ("<h2>Politique de confidentialité</h2><p>Ce site ne collecte pas de données personnelles directement. "
            "Si de la publicité est affichée, des partenaires (dont Google) peuvent déposer des cookies avec votre consentement, "
            "afin de personnaliser les annonces et mesurer leur audience. Vous pouvez retirer votre consentement à tout moment.</p>"
            f"<p>Contact : {e(cfg['contact_email'])}.</p>")
    for name, body in (("a-propos", about), ("mentions-legales", legal), ("confidentialite", priv)):
        (OUT / f"{name}.html").write_text(page(cfg, name.replace("-", " ").title(), f'<div class="card">{body}</div>'), encoding="utf-8")


if __name__ == "__main__":
    cfg = load_config()
    demo = "--demo" in sys.argv
    arts = collect(cfg, demo)
    if not arts:
        sys.exit("Aucun article récupéré : site non modifié.")
    build(cfg, arts, ai_digest(cfg, arts))
    print(f"Site généré dans {OUT} ({len(arts)} articles).")
