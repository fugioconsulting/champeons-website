#!/usr/bin/env python3
"""Build the ChampEOns employee-ownership media timeline artifact from entries.json."""

import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).parent
ENTRIES = HERE / "entries.json"
OUT = HERE / "ownership-airwaves.html"

MEDIUM_LABELS = {
    "newspaper": "Newspaper",
    "magazine": "Magazine",
    "tv-news": "TV news",
    "tv-newsmagazine": "TV newsmagazine",
    "talk-show": "Talk show",
    "late-night": "Late night",
    "radio": "Radio",
    "podcast": "Podcast",
    "documentary": "Documentary",
    "film": "Film",
    "tv-drama": "Scripted TV",
    "advertising": "Advertising",
    "super-bowl": "Super Bowl",
    "book": "Book",
    "viral-social": "Viral / social",
    "wire": "Wire story",
    "political-speech": "Politics",
    "sports": "Sports",
    "youtube": "YouTube",
    "music": "Music",
    "theater": "Theater",
    "video-game": "Video game",
    "other": "Other",
}

REACH_ORDER = {"massive": 4, "national": 3, "regional": 2, "trade": 1, "niche": 1, "unknown": 0}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def year_of(entry):
    m = re.search(r"(1[6-9]\d\d|20\d\d)", str(entry.get("date", "")))
    return int(m.group(1)) if m else 0


def decade_of(y):
    return (y // 10) * 10


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")


def pretty_date(entry):
    d = str(entry.get("date", "")).strip()
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    if m:
        return f"{months[int(m.group(2)) - 1]} {int(m.group(3))}, {m.group(1)}"
    m = re.match(r"^(\d{4})-(\d{2})$", d)
    if m:
        return f"{months[int(m.group(2)) - 1]} {m.group(1)}"
    return d


def norm_medium(entry):
    raw = slug(entry.get("medium", "other"))
    if raw in MEDIUM_LABELS:
        return raw
    for key in MEDIUM_LABELS:
        if key in raw:
            return key
    return "other"


def norm_reach(entry):
    r = str(entry.get("reach", "unknown")).lower().strip()
    return r if r in REACH_ORDER else "unknown"


def norm_valence(entry):
    v = str(entry.get("valence", "neutral")).lower().strip()
    return v if v in ("pro", "neutral", "critical", "mixed") else "neutral"


def build():
    data = json.loads(ENTRIES.read_text())
    entries = data["entries"] if isinstance(data, dict) else data
    entries = [e for e in entries if year_of(e) > 0]
    entries.sort(key=lambda e: (year_of(e), str(e.get("date", ""))))

    for e in entries:
        e["_year"] = year_of(e)
        e["_medium"] = norm_medium(e)
        e["_reach"] = norm_reach(e)
        e["_valence"] = norm_valence(e)
        e["_track"] = "culture" if str(e.get("track", "news")).lower().startswith("cult") else "news"

    decades = {}
    for e in entries:
        decades.setdefault(decade_of(e["_year"]), []).append(e)

    span_lo, span_hi = entries[0]["_year"], entries[-1]["_year"]
    massive = sum(1 for e in entries if e["_reach"] == "massive")
    critical = sum(1 for e in entries if e["_valence"] == "critical")
    peak_decade = max(decades.items(), key=lambda kv: len(kv[1]))[0]
    max_count = max(len(v) for v in decades.values())
    media_counts = Counter(e["_medium"] for e in entries)

    # ---- filter controls -------------------------------------------------
    present_media = [m for m, _ in media_counts.most_common()]
    media_chips = "".join(
        f'<button class="chip" data-filter="medium" data-value="{esc(m)}">'
        f'{esc(MEDIUM_LABELS.get(m, m))}<span class="chip-n">{media_counts[m]}</span></button>'
        for m in present_media
    )

    reach_chips = "".join(
        f'<button class="chip chip-reach r-{r}" data-filter="reach" data-value="{r}">{label}'
        f'<span class="chip-n">{sum(1 for e in entries if e["_reach"] == r)}</span></button>'
        for r, label in [("massive", "Mass audience"), ("national", "National"),
                         ("regional", "Regional"), ("trade", "Trade"), ("niche", "Niche")]
        if any(e["_reach"] == r for e in entries)
    )

    track_chips = "".join(
        f'<button class="chip chip-track t-{t}" data-filter="track" data-value="{t}">{label}'
        f'<span class="chip-n">{sum(1 for e in entries if e["_track"] == t)}</span></button>'
        for t, label in [("news", "The news record"), ("culture", "Pop culture")]
        if any(e["_track"] == t for e in entries)
    )

    valence_chips = "".join(
        f'<button class="chip chip-val v-{v}" data-filter="valence" data-value="{v}">{label}'
        f'<span class="chip-n">{sum(1 for e in entries if e["_valence"] == v)}</span></button>'
        for v, label in [("pro", "Favourable"), ("neutral", "Straight"),
                         ("mixed", "Mixed"), ("critical", "Critical")]
        if any(e["_valence"] == v for e in entries)
    )

    # ---- decade rail -----------------------------------------------------
    rail = "".join(
        f'<a class="rail-item" href="#d{d}"><span class="rail-yr">{str(d)[2:]}</span>'
        f'<span class="rail-bar"><i style="height:{max(6, round(100 * len(decades[d]) / max_count))}%"></i></span>'
        f'<span class="rail-n">{len(decades[d])}</span></a>'
        for d in sorted(decades)
    )

    # ---- body ------------------------------------------------------------
    sections = []
    for d in sorted(decades):
        items = decades[d]
        loud = sum(1 for e in items if e["_reach"] in ("massive", "national"))
        rows = []
        for i, e in enumerate(items):
            links = []
            for n, key in ((1, "source_url"), (2, "source_url_2")):
                u = str(e.get(key, "") or "").strip()
                if u.startswith("http"):
                    label = "Source" if n == 1 else "Also"
                    links.append(f'<a class="src" href="{esc(u)}" target="_blank" rel="noopener">'
                                 f'{label}<span aria-hidden="true">&#8599;</span></a>')
            if not links and e.get("source_note"):
                links.append(f'<span class="src src-none">{esc(e["source_note"])[:90]}</span>')

            meta_bits = [f'<span class="m-medium">{esc(MEDIUM_LABELS.get(e["_medium"], e["_medium"]))}</span>']
            if e.get("company"):
                meta_bits.append(f'<span class="m-co">{esc(e["company"])}</span>')
            if e.get("eo_model"):
                meta_bits.append(f'<span class="m-model">{esc(e["eo_model"])}</span>')
            if e.get("audience_metric"):
                meta_bits.append(f'<span class="m-reach">{esc(e["audience_metric"])[:70]}</span>')
            conf = str(e.get("confidence", "")).lower()
            if conf in ("likely", "uncertain"):
                meta_bits.append(f'<span class="m-conf c-{conf}">{conf}</span>')

            quote = str(e.get("quote", "") or "").strip().strip('"“”')
            quote_html = ""
            if quote and len(quote.split()) <= 18:
                quote_html = f'\n          <blockquote class="ev-quote">{esc(quote)}</blockquote>'

            angle = str(e.get("champeons_angle", "") or "").strip()
            angle_html = ""
            if angle:
                angle_html = f'\n          <p class="ev-angle"><span>Use it</span>{esc(angle)}</p>'

            searchable = " ".join(str(e.get(k, "") or "") for k in
                                  ("title", "venue", "company", "what_happened", "why_it_mattered", "eo_model"))

            rows.append(f"""      <article class="ev r-{e['_reach']} v-{e['_valence']} t-{e['_track']}"
        data-medium="{esc(e['_medium'])}" data-reach="{e['_reach']}" data-valence="{e['_valence']}" data-track="{e['_track']}"
        data-text="{esc(searchable.lower())}">
        <div class="ev-rail"><span class="dot" aria-hidden="true"></span></div>
        <div class="ev-when"><time>{esc(pretty_date(e))}</time></div>
        <div class="ev-body">
          <h3>{esc(e.get('title'))}</h3>
          <p class="ev-venue">{esc(e.get('venue'))}</p>{quote_html}
          <p class="ev-what">{esc(e.get('what_happened'))}</p>
          <p class="ev-why"><span>Why it mattered</span>{esc(e.get('why_it_mattered'))}</p>{angle_html}
          <div class="ev-meta">{''.join(meta_bits)}{''.join(links)}</div>
        </div>
      </article>""")

        sections.append(f"""    <section class="decade" id="d{d}">
      <header class="dec-head">
        <h2><span class="dec-num">{d}</span><span class="dec-s">s</span></h2>
        <div class="dec-stat">
          <span class="dec-count">{len(items)}</span>
          <span class="dec-label">moment{'s' if len(items) != 1 else ''} &middot; {loud} reached a national audience or bigger</span>
        </div>
      </header>
{chr(10).join(rows)}
    </section>""")

    css = CSS
    js = JS

    doc = f"""<title>The Ownership Airwaves</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Graduate&family=Archivo:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap">
<style>{css}</style>

<header class="strip">
  <span class="strip-mark">Champ<span class="eo">EO</span>ns</span>
  <span class="strip-rule" aria-hidden="true"></span>
  <span class="strip-note">A Fugio Consulting research file &middot; Champions of Employee Ownership</span>
</header>

<main>
  <section class="hero">
    <p class="eyebrow">The public record, {span_lo}&ndash;{span_hi}</p>
    <h1>The Ownership<br><em>Airwaves</em></h1>
    <p class="lede">Every time employee ownership escaped the trade press and landed in front of ordinary people &mdash; front pages, network news, ad campaigns, documentaries, viral posts and Senate floor speeches. {len(entries)} moments, each one checked against a source.</p>
    <dl class="stats">
      <div><dt>Moments logged</dt><dd>{len(entries)}</dd></div>
      <div><dt>Reached a mass audience</dt><dd>{massive}</dd></div>
      <div><dt>Loudest decade</dt><dd>{peak_decade}s</dd></div>
      <div><dt>Critical coverage</dt><dd>{critical}</dd></div>
    </dl>
  </section>

  <section class="controls" aria-label="Filter the timeline">
    <div class="ctl-row">
      <label class="search">
        <span class="sr">Search the timeline</span>
        <input type="search" id="q" placeholder="Search a company, outlet, or story&hellip;" autocomplete="off">
      </label>
      <button class="reset" id="reset" hidden>Clear filters</button>
    </div>
    <div class="ctl-group"><span class="ctl-label">Track</span><div class="chips">{track_chips}</div></div>
    <div class="ctl-group"><span class="ctl-label">Reach</span><div class="chips">{reach_chips}</div></div>
    <div class="ctl-group"><span class="ctl-label">Tone</span><div class="chips">{valence_chips}</div></div>
    <div class="ctl-group"><span class="ctl-label">Medium</span><div class="chips">{media_chips}</div></div>
    <p class="count" id="count" aria-live="polite"></p>
  </section>

  <nav class="rail" aria-label="Jump to decade">
    <span class="rail-cap">Signal density by decade</span>
    <div class="rail-track">{rail}</div>
  </nav>

  <div class="timeline">
{chr(10).join(sections)}
  </div>

  <footer class="foot">
    <p><strong>How this was built.</strong> Sixteen research agents swept the record by era and by channel &mdash; newspapers, network television, talk shows, advertising, film, politics, audio and social. A second pass fact-checked every candidate against a live source and threw out what could not be substantiated. A third pass named what was still missing and went back for it. Entries marked <span class="m-conf c-likely">likely</span> or <span class="m-conf c-uncertain">uncertain</span> are ones we believe happened but could not pin to a public source; treat them as leads, not citations.</p>
    <p class="foot-sig">The robots are coming. And we better own them.</p>
  </footer>
</main>
<script>{js}</script>
"""
    OUT.write_text(doc)
    print(f"wrote {OUT} — {len(entries)} entries, {len(decades)} decades, {span_lo}-{span_hi}")


CSS = r"""
*,*::before,*::after{box-sizing:border-box}
:root{
  --brand:#112347; --deep:#0B1A38;
  --ground:#EEF1F7; --surface:#FFFFFF; --surface-2:#F6F8FC;
  --ink:#0B1A38; --ink-2:#41506E; --ink-3:#77849E;
  --line:#D3DAE8; --line-soft:#E2E7F1;
  --signal:#C98A14; --signal-fill:#E5A62B;
  --critical:#A23D2D; --mixed:#5D6B88;
  --shadow:0 1px 2px rgba(11,26,56,.06),0 8px 24px -16px rgba(11,26,56,.22);
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#060D1B; --surface:#0C1930; --surface-2:#111F3A;
    --ink:#E9EDF5; --ink-2:#AEB9CE; --ink-3:#7C89A4;
    --line:#1E2E4E; --line-soft:#182541;
    --signal:#F0B750; --signal-fill:#F0B750;
    --critical:#DE7A66; --mixed:#8B99B4;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 28px -18px rgba(0,0,0,.8);
  }
}
:root[data-theme="dark"]{
  --ground:#060D1B; --surface:#0C1930; --surface-2:#111F3A;
  --ink:#E9EDF5; --ink-2:#AEB9CE; --ink-3:#7C89A4;
  --line:#1E2E4E; --line-soft:#182541;
  --signal:#F0B750; --signal-fill:#F0B750;
  --critical:#DE7A66; --mixed:#8B99B4;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 28px -18px rgba(0,0,0,.8);
}
body{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:Archivo,"Helvetica Neue",Helvetica,Arial,sans-serif;
  font-size:16px; line-height:1.55; -webkit-font-smoothing:antialiased;
}
.sr{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
a{color:inherit}
:focus-visible{outline:2px solid var(--signal-fill);outline-offset:2px;border-radius:2px}

/* ---- letterhead strip ---- */
.strip{
  display:flex;align-items:center;gap:14px;
  padding:10px max(20px,calc((100% - 1120px)/2));
  background:var(--brand);color:#fff;
  font-size:11px;letter-spacing:.09em;text-transform:uppercase;
}
.strip-mark{font-family:Graduate,Archivo,serif;font-size:13px;letter-spacing:.04em}
.strip-mark .eo{color:var(--signal-fill)}
.strip-rule{flex:0 0 28px;height:1px;background:rgba(255,255,255,.35)}
.strip-note{color:rgba(255,255,255,.72);font-size:10.5px}

main{max-width:1120px;margin:0 auto;padding:0 max(20px,4vw) 80px}

/* ---- hero ---- */
.hero{padding:56px 0 40px;border-bottom:1px solid var(--line)}
.eyebrow{
  margin:0 0 18px;font-size:11px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--signal);font-weight:600;
}
h1{
  font-family:Graduate,Archivo,serif;font-weight:400;
  font-size:clamp(2.6rem,7.5vw,5.4rem);line-height:.98;letter-spacing:-.005em;
  margin:0 0 22px;text-wrap:balance;
}
h1 em{font-style:normal;color:var(--signal)}
.lede{max-width:64ch;font-size:clamp(1rem,1.6vw,1.2rem);color:var(--ink-2);margin:0 0 34px}
.stats{
  display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));
  gap:1px;margin:0;background:var(--line-soft);border:1px solid var(--line-soft);
}
.stats>div{background:var(--surface);padding:16px 18px}
.stats dt{font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink-3);margin-bottom:6px}
.stats dd{
  margin:0;font-family:Graduate,Archivo,serif;font-size:1.8rem;line-height:1;
  font-variant-numeric:tabular-nums;color:var(--brand);
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .stats dd{color:var(--signal)}}
:root[data-theme="dark"] .stats dd{color:var(--signal)}

/* ---- controls ---- */
.controls{padding:26px 0 22px;border-bottom:1px solid var(--line);display:flex;flex-direction:column;gap:14px}
.ctl-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.search{flex:1 1 260px;display:block}
.search input{
  width:100%;padding:11px 14px;font:inherit;font-size:15px;
  background:var(--surface);color:var(--ink);
  border:1px solid var(--line);border-radius:2px;
}
.search input::placeholder{color:var(--ink-3)}
.reset{
  padding:10px 14px;font:inherit;font-size:12px;letter-spacing:.06em;text-transform:uppercase;
  background:transparent;color:var(--ink-2);border:1px solid var(--line);border-radius:2px;cursor:pointer;
}
.reset:hover{color:var(--ink);border-color:var(--ink-3)}
.ctl-group{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}
.ctl-label{
  flex:0 0 64px;font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);padding-top:4px;
}
.chips{display:flex;flex-wrap:wrap;gap:6px;flex:1}
.chip{
  display:inline-flex;align-items:center;gap:6px;
  padding:5px 10px;font:inherit;font-size:12.5px;line-height:1.2;
  background:var(--surface);color:var(--ink-2);
  border:1px solid var(--line);border-radius:999px;cursor:pointer;
  transition:background .12s,color .12s,border-color .12s;
}
.chip:hover{border-color:var(--ink-3);color:var(--ink)}
.chip[aria-pressed="true"]{background:var(--brand);border-color:var(--brand);color:#fff}
.chip[aria-pressed="true"] .chip-n{color:rgba(255,255,255,.7)}
.chip-n{font-size:10.5px;color:var(--ink-3);font-variant-numeric:tabular-nums}
.chip.r-massive[aria-pressed="true"],.chip.v-pro[aria-pressed="true"]{background:var(--signal);border-color:var(--signal);color:#1a1200}
.chip.r-massive[aria-pressed="true"] .chip-n,.chip.v-pro[aria-pressed="true"] .chip-n{color:rgba(26,18,0,.6)}
.chip.v-critical[aria-pressed="true"]{background:var(--critical);border-color:var(--critical);color:#fff}
.chip.chip-track{font-weight:600;letter-spacing:.02em}
.chip.t-culture[aria-pressed="true"]{background:var(--signal);border-color:var(--signal);color:#1a1200}
.chip.t-culture[aria-pressed="true"] .chip-n{color:rgba(26,18,0,.6)}
.count{margin:2px 0 0;font-size:12px;color:var(--ink-3);font-variant-numeric:tabular-nums}

/* ---- decade rail ---- */
.rail{padding:22px 0 8px}
.rail-cap{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3)}
.rail-track{display:flex;gap:3px;align-items:flex-end;margin-top:10px;overflow-x:auto;padding-bottom:6px}
.rail-item{
  flex:1 1 0;min-width:34px;display:flex;flex-direction:column;align-items:center;gap:5px;
  text-decoration:none;color:var(--ink-3);padding:4px 0;border-radius:2px;
}
.rail-item:hover{color:var(--ink)}
.rail-bar{display:block;width:100%;height:52px;background:var(--line-soft);display:flex;align-items:flex-end}
.rail-bar i{display:block;width:100%;background:var(--brand);transition:background .15s}
.rail-item:hover .rail-bar i{background:var(--signal-fill)}
.rail-yr{font-family:Graduate,Archivo,serif;font-size:11px;font-variant-numeric:tabular-nums}
.rail-n{font-size:10px;font-variant-numeric:tabular-nums}

/* ---- timeline ---- */
.decade{margin-top:56px}
.dec-head{
  display:flex;align-items:baseline;gap:18px;flex-wrap:wrap;
  padding-bottom:12px;border-bottom:2px solid var(--brand);margin-bottom:8px;
  position:sticky;top:0;background:var(--ground);z-index:2;padding-top:10px;
}
.dec-head h2{
  margin:0;font-family:Graduate,Archivo,serif;font-weight:400;
  font-size:clamp(1.9rem,4.4vw,2.9rem);line-height:1;letter-spacing:-.01em;
  font-variant-numeric:tabular-nums;
}
.dec-s{color:var(--signal)}
.dec-stat{display:flex;align-items:baseline;gap:8px;color:var(--ink-3);font-size:12px}
.dec-count{font-variant-numeric:tabular-nums;color:var(--ink-2);font-weight:600}
.dec-label{letter-spacing:.02em}

.ev{
  display:grid;grid-template-columns:22px 128px 1fr;gap:0 18px;
  padding:20px 0;border-bottom:1px solid var(--line-soft);
}
.ev.hidden{display:none}
.ev-rail{position:relative;display:flex;justify-content:center}
.ev-rail::before{content:"";position:absolute;top:0;bottom:-21px;width:1px;background:var(--line)}
.dot{
  position:relative;z-index:1;width:9px;height:9px;margin-top:7px;border-radius:50%;
  background:var(--ground);border:1.5px solid var(--ink-3);
}
.r-national .dot{background:var(--brand);border-color:var(--brand);width:11px;height:11px}
.r-massive .dot{
  background:var(--signal-fill);border-color:var(--signal-fill);width:13px;height:13px;
  box-shadow:0 0 0 4px color-mix(in srgb,var(--signal-fill) 22%,transparent);
}
.v-critical .dot{border-color:var(--critical)}
.r-national.v-critical .dot,.r-massive.v-critical .dot{background:var(--critical);border-color:var(--critical);box-shadow:none}

.ev-when time{
  display:block;padding-top:4px;font-size:12.5px;color:var(--ink-3);
  font-variant-numeric:tabular-nums;letter-spacing:.02em;
}
.ev-body h3{
  margin:0 0 3px;font-size:1.08rem;line-height:1.3;font-weight:600;
  letter-spacing:-.005em;text-wrap:balance;
}
.r-massive .ev-body h3{font-size:1.22rem}
.ev-venue{
  margin:0 0 9px;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;
  color:var(--signal);font-weight:600;
}
.v-critical .ev-venue{color:var(--critical)}
.ev-quote{
  margin:0 0 10px;max-width:52ch;
  font-family:Graduate,Archivo,serif;font-size:1.02rem;line-height:1.35;
  color:var(--ink);letter-spacing:-.005em;
}
.ev-quote::before{content:"\201C"}
.ev-quote::after{content:"\201D"}
.ev-what{margin:0 0 9px;max-width:68ch;color:var(--ink-2);font-size:14.5px}
.ev-why{
  margin:0 0 11px;max-width:66ch;font-size:13.5px;color:var(--ink-2);
  padding-left:12px;border-left:2px solid var(--line);
}
.ev-why span{
  display:block;font-size:10px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:2px;
}
.ev-angle{
  margin:0 0 11px;max-width:66ch;font-size:13px;color:var(--ink-2);
  padding:9px 12px;background:var(--surface-2);border-left:2px solid var(--signal);
}
.ev-angle span{
  display:block;font-size:10px;letter-spacing:.13em;text-transform:uppercase;
  color:var(--signal);font-weight:600;margin-bottom:2px;
}
.ev-meta{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:11px}
.ev-meta>*{
  padding:2px 7px;border:1px solid var(--line);border-radius:2px;
  color:var(--ink-3);letter-spacing:.04em;
}
.m-medium{background:var(--surface-2);color:var(--ink-2)!important;text-transform:uppercase;font-size:10px;letter-spacing:.09em}
.m-co{color:var(--ink-2)!important;font-weight:500}
.m-model{border-style:dashed}
.m-reach{font-variant-numeric:tabular-nums;color:var(--ink-2)!important;background:var(--surface-2)}
.m-conf{border-color:var(--signal);color:var(--signal)!important;text-transform:uppercase;font-size:10px;letter-spacing:.09em}
.m-conf.c-uncertain{border-color:var(--critical);color:var(--critical)!important}
a.src{text-decoration:none;border-color:var(--ink-3);color:var(--ink-2)!important}
a.src:hover{border-color:var(--brand);color:var(--ink)!important;background:var(--surface)}
a.src span{margin-left:3px;font-size:9px;vertical-align:1px}
.src-none{font-style:italic;border-style:dotted}

.empty{padding:60px 0;text-align:center;color:var(--ink-3);font-size:15px}

/* ---- footer ---- */
.foot{margin-top:70px;padding-top:26px;border-top:2px solid var(--brand);color:var(--ink-2);font-size:13.5px}
.foot p{max-width:78ch}
.foot strong{color:var(--ink)}
.foot .m-conf{display:inline-block;padding:1px 5px;border:1px solid var(--signal);border-radius:2px;font-size:10px}
.foot-sig{
  margin-top:22px;font-family:Graduate,Archivo,serif;font-size:1.05rem;
  color:var(--signal);letter-spacing:.01em;
}

@media (max-width:720px){
  .ev{grid-template-columns:18px 1fr;gap:0 12px}
  .ev-when{grid-column:2;order:-1}
  .ev-when time{padding-top:0;margin-bottom:4px}
  .ev-body{grid-column:2}
  .ctl-label{flex-basis:100%}
  .dec-head{position:static}
}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto!important}}
"""

JS = r"""
(function(){
  var active={medium:new Set(),reach:new Set(),valence:new Set(),track:new Set()};
  var q=document.getElementById('q');
  var reset=document.getElementById('reset');
  var count=document.getElementById('count');
  var evs=Array.prototype.slice.call(document.querySelectorAll('.ev'));
  var secs=Array.prototype.slice.call(document.querySelectorAll('.decade'));
  var chips=Array.prototype.slice.call(document.querySelectorAll('.chip'));
  var total=evs.length;

  chips.forEach(function(c){
    c.setAttribute('aria-pressed','false');
    c.addEventListener('click',function(){
      var f=c.dataset.filter,v=c.dataset.value;
      if(active[f].has(v)){active[f].delete(v);c.setAttribute('aria-pressed','false');}
      else{active[f].add(v);c.setAttribute('aria-pressed','true');}
      apply();
    });
  });
  q.addEventListener('input',apply);
  reset.addEventListener('click',function(){
    active={medium:new Set(),reach:new Set(),valence:new Set(),track:new Set()};
    chips.forEach(function(c){c.setAttribute('aria-pressed','false');});
    q.value='';apply();
  });

  function apply(){
    var term=q.value.trim().toLowerCase();
    var shown=0;
    evs.forEach(function(e){
      var ok=true;
      if(active.medium.size&&!active.medium.has(e.dataset.medium))ok=false;
      if(ok&&active.reach.size&&!active.reach.has(e.dataset.reach))ok=false;
      if(ok&&active.valence.size&&!active.valence.has(e.dataset.valence))ok=false;
      if(ok&&active.track.size&&!active.track.has(e.dataset.track))ok=false;
      if(ok&&term&&e.dataset.text.indexOf(term)===-1)ok=false;
      e.classList.toggle('hidden',!ok);
      if(ok)shown++;
    });
    secs.forEach(function(s){
      s.style.display=s.querySelectorAll('.ev:not(.hidden)').length?'':'none';
    });
    var filtering=term||active.medium.size||active.reach.size||active.valence.size||active.track.size;
    reset.hidden=!filtering;
    count.textContent=filtering?('Showing '+shown+' of '+total+' moments'):'';
  }
  apply();
})();
"""

if __name__ == "__main__":
    if not ENTRIES.exists():
        sys.exit(f"missing {ENTRIES}")
    build()
