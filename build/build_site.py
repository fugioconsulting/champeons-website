#!/usr/bin/env python3
"""Build the ChampEOns Ownership Airwaves site (index.html) from data/entries.json + data/photos.json."""

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENTRIES = ROOT / "data" / "entries.json"
PHOTOS = ROOT / "data" / "photos.json"
OUT = ROOT / "index.html"

MEDIUM_LABELS = {
    "newspaper": "Newspaper", "magazine": "Magazine", "tv-news": "TV news",
    "tv-newsmagazine": "TV newsmagazine", "talk-show": "Talk show", "late-night": "Late night",
    "radio": "Radio", "podcast": "Podcast", "documentary": "Documentary", "film": "Film",
    "tv-drama": "Scripted TV", "advertising": "Advertising", "super-bowl": "Super Bowl",
    "book": "Book", "viral-social": "Viral / social", "wire": "Wire story",
    "political-speech": "Politics", "sports": "Sports", "youtube": "YouTube",
    "music": "Music", "theater": "Theater", "video-game": "Video game", "other": "Other",
}

CHAPTERS = [
    dict(id="prologue", lo=0, hi=1949, num="1844", label="1844–1949",
         name="The Long Prologue",
         intro="Before anyone said the word ESOP, the idea kept knocking. Rochdale weavers open a store they own together and the story crosses the Atlantic. The Knights of Labor build hundreds of worker co-ops under a banner that says workers should own the machine, not just feed it. Procter &amp; Gamble invents profit-sharing because fourteen strikes in two years is a lousy business model. And Pullman builds the company town that proves the opposite point forever. A century of rough drafts."),
    dict(id="fifties-sixties", lo=1950, hi=1969, num="1958", label="1950s–60s",
         name="The Manifesto",
         intro="1958: a San Francisco lawyer named Louis Kelso and a celebrity philosopher named Mortimer Adler publish The Capitalist Manifesto and put a wild claim in front of mainstream America — capitalism is great, there just aren't enough capitalists. Meanwhile Tennessee Ernie Ford's 'Sixteen Tons' sits at number one, sixteen million Americans humming about owing their soul to the company store. The problem statement and the solution hit the airwaves in the same decade."),
    dict(id="seventies", lo=1970, hi=1979, num="1974", label="1970s",
         name="Kelso Gets His Law",
         intro="The decade employee ownership stopped being a book and became a statute. Russell Long — son of Huey, king of the Senate Finance Committee — hears Kelso out and writes the ESOP — the Employee Stock Ownership Plan — into ERISA in 1974. Mike Wallace puts Kelso on 60 Minutes and America meets the two-factor theory in prime time. Ursula K. Le Guin publishes The Dispossessed and science fiction spends the rest of the century arguing about who owns the means of production."),
    dict(id="eighties", lo=1980, hi=1989, num="1983", label="1980s",
         name="Primetime",
         intro="Employee ownership goes to the movies. Weirton's steelworkers buy their mill and make every front page in America. Dolly Parton takes '9 to 5' to number one and an Oscar nomination. Oliver Stone puts a union stock deal at the center of Wall Street — the good guys' plan, opposite Gordon Gekko. Reagan, of all people, keeps quoting Kelso. The idea has never had this much screen time since."),
    dict(id="nineties", lo=1990, hi=1999, num="1994", label="1990s",
         name="We're Owners",
         intro="United Airlines becomes the largest employee-owned company on Earth and paints it on the fuselage: 55,000 owners, a Super Bowl-scale ad campaign, the whole country watching the experiment. Jack Stack teaches open-book management from a rebuilt engine plant in Springfield. Avis runs years of 'We're trying harder — we're owners' spots. The high-water mark for employee ownership as a mass-market brand."),
    dict(id="aughts", lo=2000, hi=2009, num="2001", label="2000s",
         name="The Backlash",
         intro="The bill comes due for every half-version of the idea. Enron's collapse torches retirement accounts stuffed with company stock and the press files it — wrongly but durably — under 'employee ownership fails.' United's ESOP unwinds in bankruptcy. Sam Zell buys Tribune with the employees' plan and rides it into the ground. And in a Chicago window factory in 2008, laid-off workers sit down, refuse to leave, and remind everyone what the fight was actually about."),
    dict(id="tens", lo=2010, hi=2019, num="2010", label="2010s",
         name="Going Viral",
         intro="Bob Moore turns 81, hands Bob's Red Mill to his employees, and the internet decides this is the best story it has ever heard — then re-decides every eighteen months. Chobani's founder gives workers 10% and makes global news. New Belgium's brewers become millionaires. Bernie and Warren put ownership in their platforms. The story stops needing a press release; it travels on its own."),
    dict(id="twenties", lo=2020, hi=2100, num="2022", label="2020s",
         name="The Movement",
         intro="Patagonia's founder gives the whole company to a trust and the Earth, and it leads the New York Times. Pete Stavros walks 60 Minutes through warehouse workers getting six-figure checks. The UK converts companies to employee ownership trusts by the hundred. State ownership offices multiply. And the automation question sharpens into the only question: the robots are coming — who owns them?"),
]

PRIME_TIME = [
    ("60 minutes mike wallace interviews louis kelso", "Kelso on 60 Minutes"),
    ("wall street the bluestar", "Wall Street (1987)"),
    ("weirton", "Weirton Steel buyout"),
    ("united airlines esop launch", "United: 55,000 owners"),
    ("enron collapse employees 401", "Enron backlash"),
    ("bob moores 81stbirthday esop", "Bob's Red Mill gift"),
    ("hamdi ulukaya hands 10 of chobani", "Chobani's 10%"),
    ("chouinards earth is now our only shareholder", "Patagonia's trust"),
    ("most americans dont like their job", "Stavros on 60 Minutes"),
    ("green bay packers inc fancommunity ownership", "The Packers model"),
]

# Podcast links. Add Substack/Spotify/Apple here and they appear in the closing CTA.
SHOW_LINKS = [
    ("Watch on YouTube", "https://www.youtube.com/@champeonsofeo", True),
]

REACH_LABEL = {"massive": "Mass audience", "national": "National", "regional": "Regional",
               "trade": "Trade", "niche": "Niche", "unknown": "—"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", str(s or "").lower())).strip()


def year_of(e):
    m = re.search(r"(1[6-9]\d\d|20\d\d)", str(e.get("date", "")))
    return int(m.group(1)) if m else 0


def pretty_date(e):
    d = str(e.get("date", "")).strip()
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", d)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{months[int(m.group(2)) - 1]} {int(m.group(3))}, {m.group(1)}"
    m = re.match(r"^(\d{4})-(\d{2})$", d)
    if m and 1 <= int(m.group(2)) <= 12:
        return f"{months[int(m.group(2)) - 1]} {m.group(1)}"
    m = re.match(r"^(\d{4}s?)-(\d{4}s?)$", d)
    if m:
        return f"{m.group(1)}–{m.group(2)}"
    return d


def norm_medium(e):
    raw = re.sub(r"[^a-z-]", "", str(e.get("medium", "other")).lower())
    if raw in MEDIUM_LABELS:
        return raw
    for k in MEDIUM_LABELS:
        if k in raw:
            return k
    return "other"


def load_photos():
    if not PHOTOS.exists():
        return [], {}
    plist = json.loads(PHOTOS.read_text())
    by_frag, by_decade = [], {}
    for p in plist:
        if p.get("match_title_fragment"):
            by_frag.append((norm(p["match_title_fragment"]), p))
        elif p.get("era_decade"):
            by_decade.setdefault(str(p["era_decade"])[:3], []).append(p)
    return by_frag, by_decade


def photo_for(e, by_frag, used):
    n = norm(e.get("title"))
    for frag, p in by_frag:
        if frag and frag in n and id(p) not in used:
            used.add(id(p))
            return p
    return None


def photo_fig(p, cls="card-photo"):
    src = esc(p["local"])
    dims = ""
    if p.get("w") and p.get("h"):
        dims = f' width="{esc(p["w"])}" height="{esc(p["h"])}"'
    return (f'<figure class="{cls}"><img src="{src}" alt="{esc(p.get("caption") or p.get("subject"))}" loading="lazy" '
            f'tabindex="0" role="button" aria-label="View photo full size"{dims} '
            f'data-caption="{esc(p.get("caption") or p.get("subject"))}" data-credit="{esc(p.get("author"))}" '
            f'data-license="{esc(p.get("license"))}" data-page="{esc(p.get("file_page_url"))}">'
            f'<figcaption>{esc(p.get("caption") or p.get("subject"))} <span class="ph-credit">{esc(p.get("license"))}</span></figcaption></figure>')


def trunc60(s):
    s = str(s or "")
    return s if len(s) <= 60 else s[:60] + "…"


def meta_row(e):
    bits = [f'<span class="m-medium">{esc(MEDIUM_LABELS.get(e["_medium"], e["_medium"]))}</span>']
    if e.get("company"):
        bits.append(f'<span class="m-co" title="{esc(e["company"])}">{esc(trunc60(e["company"]))}</span>')
    if e.get("eo_model"):
        bits.append(f'<span class="m-model" title="{esc(e["eo_model"])}">{esc(trunc60(e["eo_model"]))}</span>')
    if e.get("audience_metric"):
        met = str(e["audience_metric"])
        short = met if len(met) <= 90 else met[:89] + "\u2026"
        bits.append(f'<span class="m-num" title="{esc(met)}">{esc(short)}</span>')
    conf = str(e.get("confidence", "")).lower()
    if conf in ("likely", "uncertain"):
        bits.append(f'<span class="m-conf c-{conf}">{conf}</span>')
    for n, key in ((1, "source_url"), (2, "source_url_2")):
        u = str(e.get(key, "") or "").strip()
        if u.startswith("http"):
            bits.append(f'<a class="src" href="{esc(u)}" target="_blank" rel="noopener">{"Source" if n == 1 else "Also"}&nbsp;&#8599;</a>')
    return "".join(bits)


_ID_SEEN = {}
def entry_id(e):
    base = "e-" + re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", norm(e["title"])))[:64].strip("-")
    key = id(e)
    if key in _ID_SEEN:
        return _ID_SEEN[key]
    n = sum(1 for v in _ID_SEEN.values() if v == base or v.startswith(base + "-x"))
    out = base if n == 0 else f"{base}-x{n}"
    _ID_SEEN[key] = out
    return out


YT_RE = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{6,20})")

def youtube_id(e):
    for k in ("source_url", "source_url_2"):
        m = YT_RE.search(str(e.get(k, "") or ""))
        if m:
            return m.group(1)
    return None


def render_entry(e, photo):
    quote = str(e.get("quote", "") or "").strip().strip('"“”')
    qh = f'<blockquote class="ev-quote">{esc(quote)}</blockquote>' if quote and len(quote.split()) <= 18 else ""
    angle = str(e.get("champeons_angle", "") or "").strip()
    ah = f'<p class="ev-angle"><span>Use it on the show</span>{esc(angle)}</p>' if angle else ""
    yid = youtube_id(e)
    if yid:
        t0 = int(e.get("yt_start") or 0)
        mmss = f"{t0 // 60}:{t0 % 60:02d}"
        tag = f"Watch from {mmss} &mdash; where the ownership story starts" if t0 else "Watch the video"
        ph = (f'<div class="yt" data-yid="{yid}" data-start="{t0}" role="button" tabindex="0" aria-label="Play video">'
              f'<img src="https://i.ytimg.com/vi/{yid}/hqdefault.jpg" alt="Video: {esc(e.get("title"))}" loading="lazy">'
              f'<span class="yt-play" aria-hidden="true"></span><span class="yt-tag">{tag}</span></div>')
    else:
        ph = photo_fig(photo) if photo else ""
    feature = " feature" if (yid or photo or e["_reach"] == "massive") else ""
    searchable = " ".join(str(e.get(k, "") or "") for k in ("title", "venue", "company", "what_happened", "why_it_mattered", "eo_model"))
    return f"""<article class="ev r-{e['_reach']} v-{e['_valence']}{feature}" id="{entry_id(e)}"
  data-medium="{esc(e['_medium'])}" data-reach="{e['_reach']}" data-valence="{e['_valence']}" data-track="{e['_track']}"
  data-text="{esc(searchable.lower())}">
  <div class="ev-rail"><span class="dot"></span></div>
  <div class="ev-when"><time>{esc(pretty_date(e))}</time><span class="ev-reach">{REACH_LABEL.get(e['_reach'], '')}</span></div>
  <div class="ev-body">
    {ph}<h3>{esc(e.get('title'))}</h3>
    <p class="ev-venue">{esc(e.get('venue'))}</p>
    {qh}<p class="ev-what">{esc(e.get('what_happened'))}</p>
    <p class="ev-why"><span>Why it mattered</span>{esc(e.get('why_it_mattered'))}</p>
    {ah}<div class="ev-meta">{meta_row(e)}</div>
  </div>
</article>"""


def build():
    entries = json.loads(ENTRIES.read_text())["entries"]
    entries = [e for e in entries if year_of(e) > 0]
    entries.sort(key=lambda e: (year_of(e), str(e.get("date", ""))))
    for e in entries:
        e["_year"] = year_of(e)
        e["_medium"] = norm_medium(e)
        r = str(e.get("reach", "unknown")).lower()
        e["_reach"] = r if r in REACH_LABEL else "unknown"
        v = str(e.get("valence", "neutral")).lower()
        e["_valence"] = v if v in ("pro", "neutral", "critical", "mixed") else "neutral"
        e["_track"] = "culture" if str(e.get("track", "news")).startswith("cult") else "news"

    by_frag, by_decade = load_photos()
    used = set()

    total = len(entries)
    massive = sum(1 for e in entries if e["_reach"] == "massive")
    n_sources = sum(1 for e in entries if str(e.get("source_url", "")).startswith("http"))
    n_culture = sum(1 for e in entries if e["_track"] == "culture")

    media_counts = Counter(e["_medium"] for e in entries)
    chips = {
        "track": [("news", "The news record"), ("culture", "Pop culture")],
        "reach": [(k, v) for k, v in REACH_LABEL.items() if k != "unknown"],
        "valence": [("pro", "Favourable"), ("neutral", "Straight news"), ("mixed", "Mixed"), ("critical", "Critical")],
        "medium": [(m, MEDIUM_LABELS[m]) for m, _ in media_counts.most_common()],
    }

    def chip_html(f, vals):
        out = []
        for val, label in vals:
            n = sum(1 for e in entries if {"track": e["_track"], "reach": e["_reach"], "valence": e["_valence"], "medium": e["_medium"]}[f] == val)
            if n:
                out.append(f'<button class="chip" data-filter="{f}" data-value="{val}" aria-pressed="false">{label}<b>{n}</b></button>')
        return "".join(out)

    # prime-time chips
    def find_entry(frag):
        for e in entries:
            if frag in norm(e["title"]):
                return e
        return None

    pt_found = []
    for frag, label in PRIME_TIME:
        e = find_entry(frag)
        if e:
            pt_found.append((e["_year"], entry_id(e), label))
    pt_found.sort()
    pt_chips = [f'<button class="pt-chip" data-target="{eid}"><span class="pt-yr">{yr}</span>{esc(label)}</button>'
                for yr, eid, label in pt_found]

    # chapters
    max_n = max(sum(1 for e in entries if c["lo"] <= e["_year"] <= c["hi"]) for c in CHAPTERS)
    dial_items, sections = [], []
    for c in CHAPTERS:
        items = [e for e in entries if c["lo"] <= e["_year"] <= c["hi"]]
        if not items:
            continue
        h = max(8, round(100 * len(items) / max_n))
        dial_items.append(f'<a class="dial" href="#{c["id"]}" data-section="{c["id"]}"><span class="dial-bar"><i style="height:{h}%"></i></span><span class="dial-label">{c["label"]}</span></a>')
        mood = ""
        plist = json.loads(PHOTOS.read_text()) if PHOTOS.exists() else []
        explicit = [p for p in plist if p.get("chapter") == c["id"] and p.get("local")]
        pool = explicit or by_decade.get(str(c["lo"])[:3], [])
        for p in pool:
            if id(p) not in used and p.get("local"):
                used.add(id(p))
                mood = photo_fig(p, "chapter-photo")
                break
        rows = "\n".join(render_entry(e, photo_for(e, by_frag, used)) for e in items)
        loud = sum(1 for e in items if e["_reach"] in ("massive", "national"))
        sections.append(f"""<section class="chapter" id="{c['id']}" data-label="{c['label']}">
  <header class="ch-head">
    <div class="ch-numwrap"><span class="ch-num">{c['num']}</span><span class="ch-range">{c['label']}</span></div>
    <div class="ch-text">
      <h2>{c['name']}</h2>
      <p class="ch-intro">{c['intro']}</p>
      <p class="ch-count"><b>{len(items)}</b> moments &middot; <b>{loud}</b> reached a national audience or bigger</p>
    </div>
    {mood}
  </header>
  <div class="ch-body">
{rows}
  </div>
</section>""")

    cta_buttons = "".join(
        f'<a class="cta-btn{" primary" if primary else ""}" href="{esc(url)}" target="_blank" rel="noopener">{esc(label)}</a>'
        for label, url, primary in SHOW_LINKS
    )

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Employee Ownership Media History &middot; ChampEOns</title>
<meta name="description" content="Every time employee ownership reached the public — {total} verified moments across {2026 - 1844} years of front pages, films, broadcasts and viral stories. A ChampEOns research file.">
<meta property="og:title" content="Employee Ownership Media History">
<meta property="og:description" content="{total} verified moments when employee ownership reached the public — front pages, films, broadcasts and viral stories, 1844 to today. From the ChampEOns podcast.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://fugioconsulting.github.io/champeons-website/">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Graduate&amp;family=Archivo:wght@400;500;600;700&amp;display=swap">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><rect width=%22100%22 height=%22100%22 rx=%2214%22 fill=%22%23112347%22/><text x=%2250%22 y=%2268%22 font-size=%2246%22 text-anchor=%22middle%22 fill=%22%23F0B750%22 font-family=%22Georgia%22 font-weight=%22bold%22>EO</text></svg>">
<style>{CSS}</style>
</head>
<body>

<header class="masthead">
  <a class="wordmark" href="#top">Champ<span>EO</span>ns</a>
  <span class="mast-note">From the ChampEOns podcast &mdash; Champions of Employee Ownership</span>
</header>

<nav class="channelbar" id="channelbar" aria-label="Jump to era">
  <div class="dialwrap">{''.join(dial_items)}</div>
  <button class="filter-toggle" id="filterToggle" aria-expanded="false">Filter &amp; search <b id="filterCount"></b></button>
</nav>

<div class="drawer" id="drawer" hidden>
  <label class="search"><span class="sr">Search</span><input type="search" id="q" placeholder="Search a company, outlet, film, host&hellip;" autocomplete="off"></label>
  <div class="ctl"><span>Track</span><div class="chips">{chip_html('track', chips['track'])}</div></div>
  <div class="ctl"><span>Reach</span><div class="chips">{chip_html('reach', chips['reach'])}</div></div>
  <div class="ctl"><span>Tone</span><div class="chips">{chip_html('valence', chips['valence'])}</div></div>
  <div class="ctl"><span>Medium</span><div class="chips">{chip_html('medium', chips['medium'])}</div></div>
  <div class="ctl-foot"><span class="count" id="count"></span><button class="reset" id="reset">Clear all</button></div>
</div>

<main id="top">
  <section class="hero">
    <p class="eyebrow">The public record &middot; 1844&ndash;2026</p>
    <h1>Employee Ownership<br><em>Media History</em></h1>
    <p class="lede"><strong>This is the complete public history of employee ownership</strong> &mdash; every time the idea that workers should own their companies escaped the boardroom and reached actual people. Front pages, prime time, movie screens, podcasts, stadium PA systems and viral feeds: {total} moments, every one fact-checked against a source you can click.</p>
    <p class="hero-how">Scroll the eras, or start with the ten biggest moments below. Photos open full-size; gold dots mean a mass audience saw it; red means the coverage was hostile.</p>
    <dl class="stats">
      <div><dd data-count="{total}">0</dd><dt>verified moments</dt></div>
      <div><dd data-count="{massive}">0</dd><dt>reached a mass audience</dt></div>
      <div><dd data-count="{n_culture}">0</dd><dt>pop-culture sightings</dt></div>
      <div><dd data-count="{n_sources}">0</dd><dt>sources linked</dt></div>
    </dl>
  </section>

  <section class="primetime" aria-label="The ten biggest moments">
    <h2 class="pt-title">The Prime-Time Ten</h2>
    <p class="pt-sub">Start with the moments that reached the most people.</p>
    <div class="pt-row">{''.join(pt_chips)}</div>
  </section>

{''.join(sections)}

  <section class="cta">
    <p class="cta-eyebrow">The record ends here. The story doesn&rsquo;t.</p>
    <h2>What&rsquo;s next in<br><em>employee ownership?</em></h2>
    <p class="cta-lede">Every moment on this page was somebody deciding the people who do the work should own the place. That argument is still going &mdash; and it just got the highest stakes it has ever had. <strong>ChampEOns</strong> is Chris Graham and Tim Rettig on the companies, the deals, the villains, and the fight to make ownership normal.</p>
    <div class="cta-actions">{cta_buttons}</div>
    <p class="cta-refrain">The robots are coming.<br>And we better own them.</p>
  </section>

  <footer class="foot">
    <h2 class="foot-title">How this was built</h2>
    <p>More than a hundred research agents swept the record era by era and channel by channel &mdash; newspapers, network television, film, advertising, politics, audio and the viral internet. Every candidate moment was then re-checked by an independent fact-checker against a live source; what couldn't be substantiated was cut. Entries marked <span class="m-conf c-likely">likely</span> or <span class="m-conf c-uncertain">uncertain</span> are believed real but not pinned to a public source &mdash; treat them as leads. Photographs are public domain or Creative Commons, credited in each caption; click any photo for its license and origin.</p>
    <p>Spotted something we missed &mdash; or something wrong? The record should grow. <a href="https://github.com/fugioconsulting/champeons-website/issues" target="_blank" rel="noopener">Send it to the show</a>.</p>
    <p class="foot-brand">&copy; Champions of Employee Ownership LLC &middot; Produced by Fugio Consulting</p>
  </footer>
</main>

<div class="lightbox" id="lightbox" hidden role="dialog" aria-modal="true">
  <button class="lb-close" id="lbClose" aria-label="Close">&times;</button>
  <img id="lbImg" alt="">
  <div class="lb-cap" id="lbCap"></div>
</div>

<script>{JS}</script>
</body>
</html>"""
    OUT.write_text(doc)
    print(f"wrote {OUT} — {total} entries, {len(sections)} chapters, {len(by_frag)} entry photos mapped, {len(pt_chips)} prime-time chips")


CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --ground:#0B1A38; --ground-2:#081228; --surface:#112347; --surface-2:#162B54; --ink:#F2F5FB; --ink-2:#AAB8D4; --ink-3:#6F7FA3;
  --line:#22355F; --line-soft:#1A2A4E;
  --gold:#F0B750; --gold-deep:#C98A14; --crit:#E4705B; --white:#FFFFFF;
}
html{scroll-behavior:smooth}
body{
  margin:0;background:var(--ground);color:var(--ink);
  font-family:Archivo,"Helvetica Neue",Helvetica,Arial,sans-serif;
  font-size:16px;line-height:1.55;-webkit-font-smoothing:antialiased;
}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
a{color:inherit}
:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:2px}
img{max-width:100%;display:block}

/* masthead */
.masthead{
  display:flex;align-items:center;gap:16px;
  padding:12px max(20px,calc((100% - 1180px)/2));
  border-bottom:1px solid var(--line-soft);
}
.wordmark{font-family:Graduate,serif;font-size:19px;letter-spacing:.04em;text-decoration:none;color:var(--white)}
.wordmark span{color:var(--gold)}
.mast-note{flex:1;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}

/* channel bar */
.channelbar{
  position:sticky;top:0;z-index:40;display:flex;align-items:stretch;gap:10px;
  padding:8px max(20px,calc((100% - 1180px)/2));
  background:var(--ground-2);border-bottom:1px solid var(--line-soft);
}
.dialwrap{display:flex;gap:2px;flex:1;overflow-x:auto;scrollbar-width:thin;
  mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 26px),transparent);
  -webkit-mask-image:linear-gradient(90deg,#000 0,#000 calc(100% - 26px),transparent)}
.dial{
  flex:1 0 66px;display:flex;flex-direction:column;align-items:center;gap:4px;
  padding:5px 4px 4px;text-decoration:none;color:var(--ink-3);border-radius:4px;
  border-bottom:2px solid transparent;
}
.dial:hover{color:var(--ink)}
.dial.active{color:var(--gold);border-bottom-color:var(--gold)}
.dial-bar{width:100%;height:26px;display:flex;align-items:flex-end;background:var(--line-soft)}
.dial-bar i{display:block;width:100%;background:var(--ink-3)}
.dial.active .dial-bar i,.dial:hover .dial-bar i{background:var(--gold)}
.dial-label{font-family:Graduate,serif;font-size:10px;white-space:nowrap;font-variant-numeric:tabular-nums}
.filter-toggle{
  font:inherit;font-size:12px;font-weight:600;letter-spacing:.04em;cursor:pointer;
  padding:0 16px;border-radius:6px;background:transparent;color:var(--ink-2);
  border:1px solid var(--line);
}
.filter-toggle:hover,.filter-toggle[aria-expanded="true"]{color:var(--ink);border-color:var(--gold);}
.filter-toggle b{color:var(--gold)}

/* drawer */
.drawer[hidden]{display:none}
.drawer{
  max-height:calc(100vh - 72px);overflow-y:auto;
  position:sticky;top:57px;z-index:39;
  padding:16px max(20px,calc((100% - 1180px)/2)) 18px;
  background:var(--ground-2);border-bottom:1px solid var(--line);
  display:flex;flex-direction:column;gap:12px;
  box-shadow:0 18px 30px -18px rgba(0,0,0,.6);
}
.search input{
  width:100%;padding:11px 14px;font:inherit;font-size:15px;border-radius:6px;
  background:var(--surface);color:var(--ink);border:1px solid var(--line);
}
.search input::placeholder{color:var(--ink-3)}
.ctl{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
.ctl>span{flex:0 0 58px;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}
.chips{display:flex;flex-wrap:wrap;gap:6px;flex:1}
.chip{
  display:inline-flex;align-items:center;gap:6px;padding:9px 13px;min-height:40px;border-radius:999px;
  font:inherit;font-size:12.5px;cursor:pointer;
  background:var(--surface);color:var(--ink-2);border:1px solid var(--line);
  transition:all .12s;
}
.chip b{font-weight:500;font-size:10.5px;color:var(--ink-3)}
.chip:hover{border-color:var(--gold-deep);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--gold);border-color:var(--gold);color:#1a1200}
.chip[aria-pressed="true"] b{color:rgba(26,18,0,.55)}
.ctl-foot{display:flex;align-items:center;gap:14px}
.count{font-size:12.5px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.reset{font:inherit;font-size:12px;letter-spacing:.05em;cursor:pointer;background:none;border:1px solid var(--line);color:var(--ink-2);padding:10px 14px;min-height:40px;border-radius:6px}
.reset:hover{color:var(--ink);border-color:var(--ink-3)}

main{max-width:1180px;margin:0 auto;padding:0 max(20px,4vw) 90px}

/* hero */
.hero{padding:72px 0 46px;border-bottom:1px solid var(--line-soft)}
.eyebrow{margin:0 0 20px;font-size:11.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--gold);font-weight:700}
h1{
  font-family:Graduate,serif;font-weight:400;margin:0 0 24px;
  font-size:clamp(2.8rem,8.6vw,6.4rem);line-height:.96;color:var(--white);text-wrap:balance;
}
h1 em{font-style:normal;color:var(--gold)}
.lede{max-width:62ch;font-size:clamp(1.02rem,1.7vw,1.24rem);color:var(--ink-2);margin:0 0 14px}
.lede strong{color:var(--ink)}
.hero-how{max-width:62ch;font-size:13.5px;color:var(--ink-3);margin:0 0 40px}
.hero-how b{color:var(--gold)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;margin:0;background:var(--line-soft);border:1px solid var(--line-soft)}
.stats>div{background:var(--surface);padding:20px 20px 16px}
.stats dd{margin:0;font-family:Graduate,serif;font-size:2.4rem;line-height:1;color:var(--gold);font-variant-numeric:tabular-nums}
.stats dt{font-size:11px;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-3);margin-top:8px}

/* prime time */
.primetime{padding:44px 0 8px}
.pt-title{font-family:Graduate,serif;font-weight:400;font-size:1.5rem;margin:0 0 4px;color:var(--white)}
.pt-sub{margin:0 0 16px;color:var(--ink-3);font-size:13.5px}
.pt-row{display:flex;gap:8px;overflow-x:auto;padding-bottom:10px;scrollbar-width:thin}
.pt-chip{
  flex:0 0 auto;display:flex;flex-direction:column;align-items:flex-start;gap:2px;
  font:inherit;font-size:13px;font-weight:600;color:var(--ink);cursor:pointer;
  padding:10px 16px;border-radius:8px;background:var(--surface);border:1px solid var(--line);
  transition:all .14s;
}
.pt-chip:hover{border-color:var(--gold);transform:translateY(-2px)}
.pt-yr{font-family:Graduate,serif;font-size:11px;color:var(--gold)}

/* chapters */
.chapter{padding-top:64px}
.ch-head{
  display:grid;grid-template-columns:minmax(110px,150px) 1fr minmax(0,300px);gap:26px;align-items:start;
  padding-bottom:22px;border-bottom:2px solid var(--gold);margin-bottom:6px;
}
.ch-numwrap{display:flex;flex-direction:column}
.ch-num{font-family:Graduate,serif;font-size:clamp(2.4rem,5vw,3.8rem);line-height:1;color:var(--gold);font-variant-numeric:tabular-nums}
.ch-range{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);margin-top:6px}
.ch-text h2{font-family:Graduate,serif;font-weight:400;font-size:clamp(1.5rem,3.4vw,2.2rem);margin:0 0 10px;color:var(--white)}
.ch-intro{margin:0 0 10px;max-width:66ch;color:var(--ink-2);font-size:15px}
.ch-count{margin:0;font-size:12px;color:var(--ink-3)}
.ch-count b{color:var(--gold);font-variant-numeric:tabular-nums}
.chapter-photo{margin:0;border:1px solid var(--line)}
.chapter-photo img{width:100%;max-height:340px;object-fit:contain;background:var(--ground-2);cursor:zoom-in;filter:saturate(.9)}
.chapter-photo figcaption,.card-photo figcaption{font-size:10.5px;color:var(--ink-3);padding:6px 8px;background:var(--ground-2)}
.ph-credit{opacity:.7}
.card-photo,.chapter-photo{position:relative}
.card-photo::after,.chapter-photo::after{
  content:"\2922";position:absolute;top:8px;right:8px;width:26px;height:26px;
  display:flex;align-items:center;justify-content:center;
  font-size:14px;color:#fff;background:rgba(8,18,40,.72);border-radius:4px;pointer-events:none;
}

/* entries */
.ev{
  display:grid;grid-template-columns:22px 130px 1fr;gap:0 20px;
  padding:22px 0;border-bottom:1px solid var(--line-soft);
}
.ev.hidden{display:none}
.ev-rail{position:relative;display:flex;justify-content:center}
.ev-rail::before{content:"";position:absolute;top:0;bottom:-23px;width:1px;background:var(--line)}
.dot{position:relative;z-index:1;width:9px;height:9px;margin-top:7px;border-radius:50%;background:var(--ground);border:1.5px solid var(--ink-3)}
.r-national .dot{background:var(--ink-2);border-color:var(--ink-2);width:11px;height:11px}
.r-massive .dot{background:var(--gold);border-color:var(--gold);width:13px;height:13px;box-shadow:0 0 0 5px rgba(240,183,80,.18)}
.v-critical .dot{border-color:var(--crit)}
.r-massive.v-critical .dot,.r-national.v-critical .dot{background:var(--crit);border-color:var(--crit);box-shadow:none}
.ev-when time{display:block;padding-top:4px;font-size:12.5px;color:var(--ink-2);font-variant-numeric:tabular-nums}
.ev-reach{display:block;margin-top:4px;font-size:9.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}
.r-massive .ev-reach{color:var(--gold)}
.ev-body h3{margin:0 0 3px;font-size:1.1rem;line-height:1.3;font-weight:700;color:var(--white);text-wrap:balance}
.ev.feature .ev-body h3{font-size:1.32rem}
.ev-venue{margin:0 0 10px;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--gold);font-weight:700}
.v-critical .ev-venue{color:var(--crit)}
.ev-quote{margin:0 0 12px;max-width:50ch;font-family:Graduate,serif;font-size:1.12rem;line-height:1.4;color:var(--white)}
.ev-quote::before{content:"\201C";color:var(--gold)}
.ev-quote::after{content:"\201D";color:var(--gold)}
.ev-what{margin:0 0 10px;max-width:68ch;color:var(--ink-2);font-size:14.5px}
.ev-why{margin:0 0 12px;max-width:64ch;font-size:13.5px;color:var(--ink-2);padding-left:12px;border-left:2px solid var(--line)}
.ev-why span,.ev-angle span{display:block;font-size:10px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink-3);margin-bottom:3px}
.ev-angle{margin:0 0 12px;max-width:64ch;font-size:13.5px;color:var(--ink-2);padding:10px 13px;background:var(--surface);border-left:2px solid var(--gold)}
.ev-angle span{color:var(--gold)}
.card-photo{margin:0 0 14px;max-width:460px;border:1px solid var(--line)}
.card-photo img{width:100%;max-height:380px;object-fit:contain;background:var(--ground-2);cursor:zoom-in}
.ev-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:11px}
.ev-meta>*{padding:3px 8px;border:1px solid var(--line);border-radius:3px;color:var(--ink-3);letter-spacing:.04em;text-decoration:none}
.m-medium{background:var(--surface);color:var(--ink-2)!important;text-transform:uppercase;font-size:10px;letter-spacing:.09em}
.m-co{color:var(--ink-2)!important;font-weight:600}
.m-model{border-style:dashed;color:var(--ink-2)!important}
.m-num{font-variant-numeric:tabular-nums;color:var(--ink-2)!important;background:var(--surface)}
.m-conf{border-color:var(--gold-deep);color:var(--gold)!important;text-transform:uppercase;font-size:10px}
.m-conf.c-uncertain{border-color:var(--crit);color:var(--crit)!important}
a.src:hover{border-color:var(--gold);color:var(--ink)!important;background:var(--surface)}

/* youtube facade */
.yt{position:relative;max-width:460px;margin:0 0 14px;cursor:pointer;border:1px solid var(--line);background:#000;aspect-ratio:16/9;overflow:hidden}
.yt img{width:100%;height:100%;object-fit:cover;opacity:.82}
.yt:hover img{opacity:1}
.yt-play{position:absolute;top:50%;left:50%;width:62px;height:44px;transform:translate(-50%,-50%);background:var(--gold);border-radius:10px}
.yt-play::after{content:"";position:absolute;top:50%;left:50%;transform:translate(-40%,-50%);border-style:solid;border-width:11px 0 11px 18px;border-color:transparent transparent transparent #10131a}
.yt:hover .yt-play{background:#fff}
.yt-tag{position:absolute;left:10px;bottom:8px;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#fff;background:rgba(0,0,0,.55);padding:3px 8px;border-radius:3px}
.yt iframe{position:absolute;inset:0;width:100%;height:100%;border:0}

/* zap flash for surprise/prime-time jumps */
@keyframes zap{0%{background:rgba(240,183,80,.22)}100%{background:transparent}}
.ev.zap{animation:zap 1.6s ease-out 1}

/* closing CTA */
.cta{
  margin-top:86px;padding:52px clamp(22px,5vw,60px);
  background:var(--surface);border-top:3px solid var(--gold);
  position:relative;overflow:hidden;
}
.cta::after{
  content:"";position:absolute;right:-70px;top:-70px;width:280px;height:280px;
  border-radius:50%;background:radial-gradient(circle,rgba(240,183,80,.13),transparent 68%);
  pointer-events:none;
}
.cta-eyebrow{margin:0 0 14px;font-size:11px;letter-spacing:.17em;text-transform:uppercase;color:var(--gold);font-weight:700}
.cta h2{
  font-family:Graduate,serif;font-weight:400;margin:0 0 18px;
  font-size:clamp(1.9rem,5.2vw,3.4rem);line-height:1.03;color:var(--white);text-wrap:balance;
}
.cta h2 em{font-style:normal;color:var(--gold)}
.cta-lede{max-width:60ch;margin:0 0 28px;font-size:clamp(.98rem,1.5vw,1.12rem);color:var(--ink-2)}
.cta-lede strong{color:var(--white)}
.cta-actions{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:32px}
.cta-btn{
  display:inline-flex;align-items:center;min-height:48px;padding:0 24px;
  font-size:14.5px;font-weight:700;letter-spacing:.02em;text-decoration:none;border-radius:999px;
  background:transparent;color:var(--ink);border:1px solid var(--line);
  transition:transform .13s ease,border-color .13s ease,background .13s ease;
}
.cta-btn:hover{transform:translateY(-2px);border-color:var(--gold);color:var(--white)}
.cta-btn.primary{background:var(--gold);border-color:var(--gold);color:#17120a}
.cta-btn.primary:hover{background:#ffc95f;color:#17120a}
.cta-refrain{
  margin:0;font-family:Graduate,serif;font-size:clamp(1.15rem,2.6vw,1.75rem);
  line-height:1.25;color:var(--gold);
}

/* footer */
.foot{margin-top:80px;padding-top:30px;border-top:2px solid var(--gold);color:var(--ink-2);font-size:14px}
.foot-title{font-family:Graduate,serif;font-weight:400;font-size:1.3rem;color:var(--white);margin:0 0 12px}
.foot p{max-width:76ch}
.foot .m-conf{display:inline-block;padding:1px 6px;border:1px solid var(--gold-deep);border-radius:3px;font-size:10px}
.refrain{margin-top:28px;font-family:Graduate,serif;font-size:1.25rem;color:var(--gold)}
.foot-brand{font-size:11.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}

/* lightbox */
.lightbox[hidden]{display:none}
.lightbox{
  position:fixed;inset:0;z-index:90;display:flex;flex-direction:column;
  align-items:center;justify-content:center;gap:14px;padding:30px;
  background:rgba(4,9,20,.93);
}
.lightbox img{max-width:min(1100px,calc(94vw - 40px));max-height:74vh;object-fit:contain;border:1px solid var(--line)}
.lb-cap{max-width:80ch;text-align:center;font-size:13px;color:var(--ink-2)}
.lb-cap a{color:var(--gold)}
.lb-close{position:absolute;top:8px;right:12px;min-width:44px;min-height:44px;display:flex;align-items:center;justify-content:center;font-size:34px;line-height:1;background:none;border:0;color:var(--ink-2);cursor:pointer}
.lb-close:hover{color:var(--white)}

@media (max-width:860px){
  .ch-head{grid-template-columns:1fr;gap:14px}
  .chapter-photo{max-width:420px}
}
@media (max-width:720px){
  .ev{grid-template-columns:16px 1fr;gap:0 12px}
  .ev-rail{grid-row:1 / 3}
  .ev-when{grid-column:2;order:-1;display:flex;gap:10px;align-items:baseline;margin-bottom:4px}
  .ev-when time{padding-top:0}
  .ev-body{grid-column:2}
  .mast-note{font-size:9px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
  .ctl>span{flex-basis:100%}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
  html{scroll-behavior:auto}
}
"""

JS = r"""
(function(){
  var $=function(s){return document.querySelector(s)};
  var $$=function(s){return Array.prototype.slice.call(document.querySelectorAll(s))};
  var evs=$$('.ev'), total=evs.length;
  var active={track:new Set(),reach:new Set(),valence:new Set(),medium:new Set()};

  /* count-up stats */
  if(matchMedia('(prefers-reduced-motion: reduce)').matches){
    $$('.stats dd').forEach(function(dd){dd.textContent=dd.dataset.count});
  } else {
    var counted=false;
    function countUp(){
      if(counted)return; counted=true;
      $$('.stats dd').forEach(function(dd){
        var end=+dd.dataset.count, t0=null;
        function step(t){
          if(!t0)t0=t;
          var p=Math.min(1,(t-t0)/1100);
          dd.textContent=Math.round(end*(1-Math.pow(1-p,3)));
          if(p<1)requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }
    if('IntersectionObserver' in window){
      var io=new IntersectionObserver(function(en){ if(en[0].isIntersecting) countUp(); },{threshold:.3});
      io.observe($('.stats'));
    } else countUp();
  }

  /* scrollspy on chapter dial */
  var dials={}; $$('.dial').forEach(function(d){dials[d.dataset.section]=d});
  if('IntersectionObserver' in window){
    var spy=new IntersectionObserver(function(ents){
      ents.forEach(function(en){
        if(en.isIntersecting){
          $$('.dial.active').forEach(function(x){x.classList.remove('active')});
          var d=dials[en.target.id]; if(d)d.classList.add('active');
        }
      });
    },{rootMargin:'-20% 0px -70% 0px'});
    $$('.chapter').forEach(function(s){spy.observe(s)});
  }

  /* filter drawer */
  var drawer=$('#drawer'), toggle=$('#filterToggle');
  toggle.addEventListener('click',function(){
    var open=drawer.hidden;
    drawer.hidden=!open;
    toggle.setAttribute('aria-expanded',String(open));
    if(open)$('#q').focus();
  });

  var q=$('#q'), count=$('#count'), fcount=$('#filterCount');
  $$('.chip').forEach(function(c){
    c.addEventListener('click',function(){
      var f=c.dataset.filter,v=c.dataset.value;
      if(active[f].has(v)){active[f].delete(v);c.setAttribute('aria-pressed','false')}
      else{active[f].add(v);c.setAttribute('aria-pressed','true')}
      apply();
    });
  });
  q.addEventListener('input',apply);
  $('#reset').addEventListener('click',function(){
    Object.keys(active).forEach(function(k){active[k].clear()});
    $$('.chip').forEach(function(c){c.setAttribute('aria-pressed','false')});
    q.value=''; apply();
  });

  function apply(){
    var term=q.value.trim().toLowerCase(), shown=0, nf=0;
    Object.keys(active).forEach(function(k){nf+=active[k].size});
    evs.forEach(function(e){
      var ok=true;
      for(var f in active){ if(active[f].size&&!active[f].has(e.dataset[f])){ok=false;break} }
      if(ok&&term&&e.dataset.text.indexOf(term)===-1)ok=false;
      e.classList.toggle('hidden',!ok); if(ok)shown++;
    });
    $$('.chapter').forEach(function(s){
      s.style.display=s.querySelectorAll('.ev:not(.hidden)').length?'':'none';
    });
    var filtering=term||nf;
    count.textContent=filtering?('Showing '+shown+' of '+total):'All '+total+' moments';
    fcount.textContent=nf?('('+nf+')'):'';
  }
  apply();

  /* jump + flash */
  function jumpTo(el){
    el.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'center'});
    el.classList.remove('zap'); void el.offsetWidth; el.classList.add('zap');
  }
  $$('.pt-chip').forEach(function(c){
    c.addEventListener('click',function(){
      var el=document.getElementById(c.dataset.target);
      if(!el)return;
      if(el.classList.contains('hidden'))$('#reset').click();
      jumpTo(el);
    });
  });

  /* youtube click-to-play */
  function playYt(box){
    if(box.querySelector('iframe'))return;
    var f=document.createElement('iframe');
    var t=parseInt(box.dataset.start||'0',10)||0;
    f.src='https://www.youtube-nocookie.com/embed/'+box.dataset.yid+'?autoplay=1'+(t?('&start='+t):'');
    f.allow='accelerometer; autoplay; encrypted-media; picture-in-picture';
    f.allowFullscreen=true;
    box.innerHTML='';box.appendChild(f);
  }
  $$('.yt').forEach(function(b){
    b.addEventListener('click',function(){playYt(b)});
    b.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();playYt(b)}});
  });

  /* lightbox */
  var lb=$('#lightbox'), lbImg=$('#lbImg'), lbCap=$('#lbCap'), lbClose=$('#lbClose');
  var lbReturnFocus=null;
  function openLightbox(img){
    lbImg.src=img.src; lbImg.alt=img.dataset.caption||'';
    lbCap.innerHTML='';
    var strong=document.createElement('strong');
    strong.textContent=img.dataset.caption||'';
    lbCap.appendChild(strong);
    lbCap.appendChild(document.createElement('br'));
    lbCap.appendChild(document.createTextNode((img.dataset.credit||'')+' · '+(img.dataset.license||'')));
    if(img.dataset.page){
      lbCap.appendChild(document.createTextNode(' · '));
      var a=document.createElement('a');
      a.href=img.dataset.page; a.target='_blank'; a.rel='noopener'; a.textContent='origin';
      lbCap.appendChild(a);
    }
    lbReturnFocus=document.activeElement;
    lb.hidden=false; document.body.style.overflow='hidden';
    lbClose.focus();
  }
  document.addEventListener('click',function(ev){
    var img=ev.target.closest('.card-photo img,.chapter-photo img');
    if(!img)return;
    openLightbox(img);
  });
  document.addEventListener('keydown',function(ev){
    if(ev.key!=='Enter'&&ev.key!==' ')return;
    var img=ev.target.closest&&ev.target.closest('.card-photo img,.chapter-photo img');
    if(!img)return;
    ev.preventDefault();
    openLightbox(img);
  });
  function closeLb(){
    lb.hidden=true;document.body.style.overflow='';
    if(lbReturnFocus&&lbReturnFocus.focus)lbReturnFocus.focus();
    lbReturnFocus=null;
  }
  lbClose.addEventListener('click',closeLb);
  lb.addEventListener('click',function(e){if(e.target===lb)closeLb()});
  document.addEventListener('keydown',function(e){
    if(!lb.hidden){
      if(e.key==='Escape')closeLb();
      if(e.key==='Tab'){e.preventDefault();lbClose.focus()}
      return;
    }
    if(e.key==='Escape'&&!drawer.hidden){
      drawer.hidden=true;toggle.setAttribute('aria-expanded','false');toggle.focus();
    }
  });
})();
"""

if __name__ == "__main__":
    if not ENTRIES.exists():
        sys.exit("missing data/entries.json")
    build()
