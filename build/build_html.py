#!/usr/bin/env python3
"""Convert source/Manuscript.docx into the structured HTML used for the print
PDF (Paged.js) and the reflowable EPUB.

Usage: python3 build/build_html.py
Writes build/out/book.html (print) and build/out/epub.html (EPUB source).
"""
import copy
import re
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "out"
DOCX = ROOT / "source" / "Manuscript.docx"

BOOK_TITLE = "The 5-Step Book Launch for Experts"
COPYRIGHT_YEAR = "2027"  # per author's note (Google Doc version), 8 Oct

# Clickable link targets for the inserts (from the URLs printed on each insert).
LINKS = {
    "audiobook": "https://theroyaltycoach.com/free-audiobook",
    "video": "https://www.theroyaltycoach.com/prove-method-video",
    "youtube": "https://youtube.com/@theroyaltycoach",
    "instagram": "https://instagram.com/karina.g.sanchez",
    "worksheets": "https://www.theroyaltycoach.com/book-worksheets",
    "call": "https://calendly.com/karina-1-on-1/45min",
}

# Embedded images in source/Manuscript.docx (Manuscript_1 from the Drive folder)
IMAGE_MAP = {
    "image2.png": "insert-audiobook.png",
    "image4.png": "insert-video-summary.png",
    "image1.png": "insert-social.png",
    "image6.png": "insert-worksheets.png",
    "image5.png": "insert-discovery-call.jpg",
}

# Chapter opener copy: (label, title, tag line)
OPENERS = {
    "intro": ("Introduction", "How It All Started…", None),
    1: ("Chapter 1", "Self-Publishing vs. Traditional Publishing", "Which Path Is for You?"),
    2: ("Chapter 2", "Who’s Your Ideal Client?", "That’s Your Avatar."),
    3: ("Chapter 3", "Where Will Your Book Live on Amazon?", None),
    4: ("Chapter 4", "The P.R.O.V.E. Method", "Start With the Problem"),
    5: ("Chapter 5", "Package the Promise So the Right People Notice", None),
    6: ("Chapter 6", "Get Your Method Out of Your Head", None),
    7: ("Chapter 7", "Turn Your Method Into a Book People Finish", None),
    8: ("Chapter 8", "Show Them Why Your Method Deserves Trust", None),
    9: ("Chapter 9", "Let Readers Experience Your Expertise", None),
    10: ("Chapter 10", "What Can Readers Hire You to Do?", None),
    11: ("Chapter 11", "Make It Easy to Take the Next Step", None),
    12: ("Chapter 12", "Get Your Book Ready for Launch", None),
    13: ("Chapter 13", "Launch Your Book and Start the Conversations", None),
    14: ("Chapter 14", "Keep Your Book Working After Launch Week", None),
    "conclusion": ("Conclusion", "Let’s Show Them What You’ve Got", None),
    "message": ("From Karina", "A Message From the Author", None),
    "references": ("Sources", "References", None),
}

# Short running-head text for recto pages.
RUNNING = {
    1: "Self-Publishing vs. Traditional",
    5: "Package the Promise",
    13: "Launch Your Book",
    14: "Keep Your Book Working",
}

# Pull quotes: (sentence to locate in a paragraph, quote HTML)
PULL_QUOTES = {
    "intro": [("My book became my business card.",
               "My book became<br>my <em>business card.</em><br>It became a door opener.")],
    1: [("Your book shouldn’t interest everybody.",
         "Your book shouldn’t interest everybody. It needs to <em>matter</em> to the people you can help.")],
    2: [("Clients describe what happened on Tuesday.",
         "Experts often describe problems using the language of their profession. <em>Clients describe what happened on Tuesday.</em>")],
    3: [("You want your book surrounded by a conversation it actually belongs in.",
         "You want your book surrounded by a conversation it <em>actually belongs in.</em>")],
    4: [("Choose one main problem and let supporting topics earn their place.",
         "Choose <em>one main problem</em> and let supporting topics earn their place.")],
    5: [("Listen, you can love a title and still need to change it.",
         "Listen, you can love a title and <em>still need to change it.</em>")],
    6: [("A method gives them a path through your teaching.",
         "A method gives them <em>a path</em> through your teaching.")],
    7: [("Nobody needs you to become a different person because you’re writing a book.",
         "Nobody needs you to become <em>a different person</em> because you’re writing a book.")],
    8: [("Your reader came for help, and your experience should help them find it.",
         "Your reader came for help, and your experience should <em>help them find it.</em>")],
    9: [("You don’t need fifty opinions arriving the night before publication.",
         "You don’t need <em>fifty opinions</em> arriving the night before publication.")],
    10: [("Be honest about what you can sustain.",
          "Be honest about what you can <em>sustain.</em>")],
    11: [("A practical checklist may be more useful than another fifty pages of explanations.",
          "A practical checklist may be more useful than <em>another fifty pages</em> of explanations.")],
    12: [("Don’t rush through the final screens because you’re excited to hit the button.",
          "Don’t rush through the final screens because you’re <em>excited to hit the button.</em>")],
    13: [("I wanted people to leave with something they could read, remember, and share.",
          "I wanted people to leave with something they could <em>read, remember, and share.</em>")],
    14: [("Your book can continue introducing your expertise while your knowledge develops.",
          "Your book can continue introducing your expertise <em>while your knowledge develops.</em>")],
    "conclusion": [("I was the same person before and after publishing.",
                    "I was the same person before and after publishing. The book gave people <em>a way to see it.</em>")],
}

PROVE = [
    ("P", "Pinpoint the Problem"),
    ("R", "Reveal Your Method"),
    ("O", "Offer the Evidence"),
    ("V", "Value Your Expertise"),
    ("E", "Engage Your Future Clients"),
]


def run_pandoc():
    html = subprocess.run(
        ["pandoc", str(DOCX), "-t", "html5", "--wrap=none"],
        check=True, capture_output=True, text=True).stdout
    return BeautifulSoup(html, "html.parser")


def text_of(el):
    return re.sub(r"\s+", " ", el.get_text()).strip()


def new(soup, name, cls=None, html=None, **attrs):
    t = soup.new_tag(name, **attrs)
    if cls:
        t["class"] = cls.split()
    if html is not None:
        t.append(BeautifulSoup(html, "html.parser"))
    return t


def strip_emoji(s):
    return re.sub(r"^[\U0001F300-\U0001FAFF☀-➿️\s]+", "", s)


def clean_inline(soup):
    # Author's request (10 Oct): no dashes in the book's text; use a comma instead.
    # Decorative dashes in the design (sign-off, folios) stay, per her follow-up.
    for node in list(soup.find_all(string=re.compile("[\u2014\u2013]"))):
        node.replace_with(re.sub(r"\s*[\u2014\u2013]\s*", ", ", str(node)))
    # Pandoc renders Word underlines on links as <span class="underline">.
    for sp in soup.select("span.underline"):
        sp.unwrap()
    for u in soup.find_all("u"):
        u.unwrap()
    # Headings in the docx are bolded runs; drop the redundant <strong>.
    for h in soup.find_all(["h1", "h2", "h3"]):
        for s in h.find_all("strong"):
            s.unwrap()
    # Word list indents come through as blockquotes; flatten them.
    for bq in soup.find_all("blockquote"):
        bq.unwrap()
    for li in soup.find_all("li"):
        ps = li.find_all("p", recursive=False)
        if len(ps) == 1:
            ps[0].unwrap()
    # Runs of underscores -> printable write-in blanks.
    for node in list(soup.find_all(string=re.compile(r"_{4,}"))):
        parts = re.split(r"(_{4,})", str(node))
        frag = []
        for p in parts:
            if re.fullmatch(r"_{4,}", p):
                frag.append(new(soup, "span", "blank"))
                frag[-1].string = " "
            elif p:
                frag.append(NavigableString(p))
        for f in frag:
            node.insert_before(f)
        node.extract()


def split_sections(body):
    """Return list of (h1_text, [elements]) with front matter under None."""
    sections = [(None, [])]
    for el in list(body.children):
        if isinstance(el, NavigableString):
            if el.strip():
                sections[-1][1].append(el)
            continue
        if el.name == "h1":
            sections.append((text_of(el), []))
        else:
            sections[-1][1].append(el)
    return sections


def key_for(h1):
    m = re.match(r"Chapter (\d+)", h1)
    if m:
        return int(m.group(1))
    low = h1.lower()
    for k in ("introduction", "conclusion", "references"):
        if low.startswith(k):
            return {"introduction": "intro"}.get(k, k)
    if low.startswith("a message"):
        return "message"
    if low.startswith("dedication"):
        return "dedication"
    if low.startswith("table of contents"):
        return "toc"
    return low


def img_src(img):
    name = Path(img["src"]).name
    return "../../assets/images/" + IMAGE_MAP[name]


# ---------------------------------------------------------------- components

def linked_insert(soup, file, link, alt, cls="insert-figure"):
    fig = new(soup, "figure", cls)
    a = new(soup, "a", href=link)
    a.append(new(soup, "img", src="../../assets/images/" + file, alt=alt))
    fig.append(a)
    return fig


def prove_roadmap(soup, ol, epub=False):
    items = ol.find_all("li", recursive=False)
    box = new(soup, "div", "prove-roadmap")
    box.append(new(soup, "p", "kicker", "Your roadmap · 5 steps"))
    box.append(new(soup, "h4", "roadmap-title", "The <span>P.R.O.V.E.</span> Method"))
    box.append(new(soup, "p", "roadmap-sub",
                   "Expertise in, clients out. Come back to this page whenever you need to see where you are."))
    for i, li in enumerate(items):
        letter, name = PROVE[i]
        li = copy.copy(li)
        strong = li.find("strong")
        if strong:
            strong.extract()
        body_html = "".join(str(c) for c in li.contents).strip()
        step = new(soup, "div", "prove-step" + (" alt" if i % 2 else ""))
        step.append(new(soup, "div", "prove-letter", letter))
        txt = new(soup, "div", "prove-text")
        txt.append(new(soup, "p", "step-no", f"Step 0{i + 1}"))
        txt.append(new(soup, "p", "step-name", name))
        txt.append(new(soup, "p", "step-body", body_html))
        step.append(txt)
        box.append(step)
    return box


def prove_strip(soup):
    strip = new(soup, "div", "prove-strip")
    for i, (letter, name) in enumerate(PROVE):
        cell = new(soup, "div", "prove-cell" + (" alt" if i % 2 else ""))
        cell.append(new(soup, "span", "pl", letter))
        cell.append(new(soup, "span", "pn", name))
        strip.append(cell)
    return strip


def royalty_chart(soup):
    rows = [
        ("Book’s cover price", "$20", "$20", ""),
        ("Amount used to calculate your royalty", "$20 cover price", "$10 received by the publisher", "small"),
        ("Your royalty rate", "10%", "10%", ""),
        ("Your royalty per eligible sale", "$2", "$1", "key"),
        ("Royalties earned on 1,000 eligible sales", "$2,000", "$1,000", ""),
        ("Advance paid against future royalties", "$10,000", "$10,000", ""),
        ("Eligible sales needed to earn out your advance", "5,000 copies", "10,000 copies", "key big"),
    ]
    html = ['<div class="chart" id="chart-1-1">',
            '<p class="kicker">Chart 1.1</p>',
            '<h4 class="chart-title">How Royalties and<br>Advances Add Up</h4>',
            '<table class="royalty">',
            '<thead><tr><th>What you’re comparing</th><th>Royalty based on<br>cover price</th>'
            '<th class="hl">Royalty based on<br>publisher’s receipts</th></tr></thead><tbody>']
    for label, a, b, cls in rows:
        html.append(f'<tr class="{cls}"><td>{label}</td><td>{a}</td><td class="hl">{b}</td></tr>')
    html.append('<tr class="small"><td>When additional royalty payments become due</td>'
                '<td colspan="2" class="merged">After royalties exceed the $10,000 advance, '
                'according to the payment schedule</td></tr>')
    html.append('</tbody></table>')
    html.append('<div class="bars"><p class="bars-title">Copies to sell before you see another royalty payment</p>'
                '<div class="bar-row"><span class="bar-label">Cover price</span>'
                '<span class="bar-track"><span class="bar dark" style="width:50%">5,000</span></span></div>'
                '<div class="bar-row"><span class="bar-label">Publisher’s receipts</span>'
                '<span class="bar-track"><span class="bar" style="width:100%">10,000</span></span></div></div>')
    html.append('<div class="callout-eq"><span class="eq">=10%</span><span class="eq-text">'
                'Same percentage. Half the money per sale. Twice as many sales to earn out the same advance.'
                '</span></div>')
    html.append('</div>')
    return BeautifulSoup("".join(html), "html.parser")


def worksheet_table(soup, table):
    rows = []
    for tr in table.find_all("tr"):
        cells = [text_of(td) for td in tr.find_all(["td", "th"])]
        rows.append(cells)
    head, body = rows[0], rows[1:]
    html = ['<div class="chart worksheet-chart" id="chart-3-1">',
            '<p class="kicker">Chart 3.1 · Worksheet</p>',
            '<h4 class="chart-title">Competitor Research</h4>',
            '<table class="research"><thead><tr>',
            f'<th>{head[0]}</th>', *[f'<th class="book-col">Book {i}</th>' for i in range(1, 6)],
            '</tr></thead><tbody>']
    for r in body:
        html.append(f'<tr><td>{r[0]}</td>' + '<td></td>' * 5 + '</tr>')
    html.append('</tbody></table></div>')
    return BeautifulSoup("".join(html), "html.parser")


def checklist(soup, p):
    ul = new(soup, "ul", "checklist")
    chunks = re.split(r"<br\s*/?>", "".join(str(c) for c in p.contents))
    for c in chunks:
        c = c.replace("☐", "").strip()
        if c:
            ul.append(new(soup, "li", None, c))
    return ul


# ---------------------------------------------------------------- chapters

def build_chapter(soup, key, h1, elements, epub=False):
    label, title, tag = OPENERS[key]
    sec = new(soup, "section", "chapter")
    sec["id"] = f"ch-{key}"
    sec["data-key"] = str(key)
    sec["data-h1"] = h1
    simple = key in ("message", "references")
    if simple:
        sec["class"].append("chapter-simple")
    num = key if isinstance(key, int) else None

    opener = new(soup, "header", "opener" + (" opener-simple" if simple else ""))
    if num:
        opener.append(new(soup, "span", "ghost-num", str(num)))
    opener.append(new(soup, "p", "opener-label", label))
    h = new(soup, "h1", "opener-title" + (" long" if len(title) > 38 else ""), title)
    h["data-toc-label"] = label
    opener.append(h)
    if tag:
        opener.append(new(soup, "p", "opener-tag", f"<span>{tag}</span>"))
    sec.append(opener)
    run = RUNNING.get(key, title.rstrip("…?."))
    sec.append(new(soup, "p", "rh-src", f"{label} · {run}" if not simple else title))

    body = new(soup, "div", "chapter-body")
    sec.append(body)

    els = [e for e in elements if isinstance(e, Tag)]
    first_para_done = False
    i = 0
    pq = list(PULL_QUOTES.get(key, []))
    while i < len(els):
        el = els[i]
        t = text_of(el)

        # --- special blocks introduced by h3
        if el.name == "h3":
            raw = strip_emoji(t)
            group = []
            j = i + 1
            while j < len(els) and els[j].name not in ("h3", "h1"):
                group.append(els[j])
                j += 1
            if raw.startswith("Activity:"):
                box = new(soup, "div", "activity")
                box.append(new(soup, "p", "box-label", "<span>Activity</span>"))
                box.append(new(soup, "h3", "box-title", raw.split(":", 1)[1].strip()))
                for g in group:
                    box.append(transform_block(soup, g, key, epub))
                body.append(box)
                i = j
                continue
            if raw.startswith("Refer to Worksheet:"):
                box = new(soup, "div", "worksheet")
                box.append(new(soup, "p", "box-label", "<span>Worksheet</span>"))
                box.append(new(soup, "h3", "box-title", raw.split(":", 1)[1].strip()))
                for g in group:
                    box.append(transform_block(soup, g, key, epub))
                body.append(box)
                i = j
                continue
            if raw.startswith("Free Giveaway:"):
                box = new(soup, "div", "giveaway")
                box.append(new(soup, "p", "box-label", "<span>Free giveaway</span>"))
                box.append(new(soup, "h3", "box-title", raw.split(":", 1)[1].strip()))
                tail = []
                for g in group:
                    gt = text_of(g)
                    if g.find("img"):
                        box.append(linked_insert(soup, "insert-worksheets.png", LINKS["worksheets"],
                                                 "Download all 15 worksheets. Scan the QR code or visit "
                                                 "theroyaltycoach.com/book-worksheets"))
                    elif gt.startswith("Let’s show them") or gt.startswith("See you inside"):
                        tail.append(gt)
                    else:
                        box.append(transform_block(soup, g, key, epub))
                body.append(box)
                if tail:
                    so = new(soup, "div", "signoff")
                    so.append(new(soup, "p", "signoff-lead", "Let’s show them what you’ve got."))
                    so.append(new(soup, "p", "signoff-big", "<span>See you inside!</span>"))
                    so.append(new(soup, "p", "signoff-name", "— Karina"))
                    body.append(so)
                i = j
                continue
            body.append(new(soup, "h2", "section-head", raw))
            i += 1
            continue

        # --- PROVE method lists
        if el.name == "ol" and key == "intro" and "Pinpoint the Problem" in t:
            body.append(prove_roadmap(soup, el, epub))
            i += 1
            continue
        if el.name == "ol" and key == 4 and t.startswith("Pinpoint the Problem"):
            keep = new(soup, "div", "keep-together")
            prev = [c for c in body.contents if isinstance(c, Tag)][-2:]
            for c in prev:
                keep.append(c.extract())
            keep.append(prove_strip(soup))
            body.append(keep)
            i += 1
            continue

        # --- Chart 1.1 (royalties): heading paragraph + table + bold summary line
        if key == 1 and el.name == "p" and t == "How Royalties and Advances Add Up":
            body.append(royalty_chart(soup))
            # skip the table and the bold summary sentence (both rendered in the chart)
            i += 1
            while i < len(els) and (els[i].name == "table" or text_of(els[i]).startswith("Same percentage.")):
                i += 1
            continue
        if key == 1 and el.name == "p" and t.startswith("Before you sign, ask:"):
            box = new(soup, "div", "ask-box")
            strong = el.find("strong")
            strong.extract()
            box.append(new(soup, "p", "ask-label", "Before you sign, ask"))
            box.append(new(soup, "p", None, "".join(str(c) for c in el.contents).strip()))
            body.append(box)
            i += 1
            continue
        if key == 1 and el.name == "p" and (t.startswith("Most small publishing") or t.startswith("Illustrative examples")):
            p = transform_block(soup, el, key, epub)
            p["class"] = ["chart-note"]
            body.append(p)
            i += 1
            continue

        # --- Chapter 3 discovery-call call to action + insert
        if el.name == "p" and el.find("img"):
            src = Path(el.find("img")["src"]).name
            if IMAGE_MAP.get(src) == "insert-discovery-call.jpg":
                body.append(linked_insert(soup, "insert-discovery-call.jpg", LINKS["call"],
                                          "Book your 45-minute discovery call at calendly.com/karina-1-on-1/45min",
                                          "insert-figure call-insert"))
            i += 1
            continue

        if key == "references" and el.name == "p":
            strong = el.find("strong")
            if strong is not None and text_of(strong) == t:
                body.append(new(soup, "h4", "ref-head", t))
            else:
                p = copy.copy(el)
                p["class"] = ["ref"]
                body.append(p)
            i += 1
            continue

        blk = transform_block(soup, el, key, epub)
        if el.name == "p" and not first_para_done and not blk.get("class"):
            blk["class"] = ["first", "dropcap"]
            first_para_done = True
        body.append(blk)

        # pull quotes go after the paragraph containing the sentence
        for needle, qhtml in list(pq):
            if needle in t:
                q = new(soup, "aside", "pullquote")
                q.append(new(soup, "p", None, qhtml))
                body.append(q)
                pq.remove((needle, qhtml))
        i += 1
    return sec


def transform_block(soup, el, key, epub):
    el = copy.copy(el)
    t = text_of(el)
    if el.name == "p" and "☐" in t:
        return checklist(soup, el)
    if el.name == "table":
        return worksheet_table(soup, el)
    if el.name == "p":
        strong = el.find("strong")
        only_strong = strong is not None and text_of(strong) == t
        if only_strong and re.match(r"^(Part \d+:|Column [AB])", t):
            el.name = "h4"
            el["class"] = ["mini-head" + (" column-head" if t.startswith("Column") else "")]
            strong.unwrap()
            return el
        if only_strong and "calendly.com" in t:
            el["class"] = ["cta"]
            return el
    return el


# ---------------------------------------------------------------- front matter

def front_matter(soup, elements):
    out = []
    # Title page
    tp = new(soup, "section", "front title-page")
    tp.append(new(soup, "p", "tp-five", "5"))
    tp.append(new(soup, "h1", "tp-title", "The 5-Step<br>Book Launch"))
    tp.append(new(soup, "p", "tp-for", "<span>For Experts</span>"))
    tp.append(new(soup, "p", "tp-sub",
                  "The Insider’s Guide to Self-Publish Your Book, Nail Your Launch, "
                  "and Turn Readers Into <span class=\"hl\">High-Paying Clients</span>"))
    tp.append(new(soup, "p", "tp-author", "Karina G. Sanchez"))
    out.append(tp)

    # Copyright page: everything after the subtitle up to the TOC heading
    cp = new(soup, "section", "front copyright")
    inner = new(soup, "div", "copyright-inner")
    started = False
    for el in elements:
        if not isinstance(el, Tag):
            continue
        t = text_of(el)
        if t.startswith("Copyright"):
            started = True
            inner.append(new(soup, "p", "c-strong", f"Copyright © {COPYRIGHT_YEAR} Karina G. Sanchez"))
            continue
        if started:
            el = copy.copy(el)
            if t.startswith("First edition"):
                el.string = f"First edition, {COPYRIGHT_YEAR}"
            inner.append(el)
    cp.append(inner)
    out.append(cp)
    return out


def dedication(soup, elements):
    sec = new(soup, "section", "front dedication")
    inner = new(soup, "div", "dedication-inner")
    for el in elements:
        if isinstance(el, Tag) and el.name == "p" and not el.find("img"):
            inner.append(copy.copy(el))
    sec.append(inner)
    return sec


def toc_section(soup, chapters):
    sec = new(soup, "section", "front toc")
    sec.append(new(soup, "h1", "toc-title", "Contents"))
    ol = new(soup, "ol", "toc-list")
    for ch in chapters:
        key = ch["data-key"]
        li = new(soup, "li", "toc-ch" if key.isdigit() else "toc-matter")
        a = new(soup, "a", href=f"#{ch['id']}")
        if key.isdigit():
            a.append(new(soup, "span", "toc-num", f"{int(key):02d}"))
        name = re.sub(r"^Chapter \d+:\s*", "", ch["data-h1"]).replace("...", "…")
        a.append(new(soup, "span", "toc-text", name))
        a.append(new(soup, "span", "toc-pg"))
        li.append(a)
        ol.append(li)
    sec.append(ol)
    return sec


# Full-page inserts from the author's Drive folder (6 x 9 PDFs). In print they are
# blank placeholder pages that merge_inserts.py replaces with the vector PDF page;
# in the EPUB they are images wrapped in links.
INSERTS = [
    ("audiobook", "audiobook.pdf", "epub-audiobook.png", ["audiobook"],
     "Reserve the audiobook version of this book for free. Scan the QR code or visit theroyaltycoach.com/free-audiobook"),
    ("video", "video-training.pdf", "epub-video-training.png", ["video"],
     "Want a video summary of this book? Scan to watch or visit www.theroyaltycoach.com/prove-method-video"),
    ("social", "youtube-instagram.pdf", "epub-youtube-instagram.png", ["youtube", "instagram"],
     "Watch and learn on YouTube: youtube.com/@theroyaltycoach. Connect daily on Instagram: instagram.com/karina.g.sanchez"),
]


def inserts(soup, epub=False):
    out = []
    for name, pdf, png, links, alt in INSERTS:
        sec = new(soup, "section", f"insert-page insert-{name}")
        sec["data-insert"] = pdf
        if epub:
            a = new(soup, "a", href=LINKS[links[0]])
            a.append(new(soup, "img", src="images/" + png, alt=alt))
            sec.append(a)
            if len(links) > 1:
                p = new(soup, "p", "insert-links")
                for l in links:
                    p.append(new(soup, "a", None, LINKS[l].replace("https://", ""), href=LINKS[l]))
                    p.append(" ")
                sec.append(p)
        out.append(sec)
    return out


# ---------------------------------------------------------------- main

def build(epub=False):
    soup = run_pandoc()
    clean_inline(soup)
    sections = split_sections(soup)

    doc = BeautifulSoup('<html lang="en"><head></head><body></body></html>', "html.parser")
    body = doc.body

    pre_toc, ded_els = sections[0][1], []
    chapters_src = []
    for h1, els in sections[1:]:
        k = key_for(h1)
        if k.__class__ is str and k.startswith("the 5-step book launch"):
            pre_toc += els
        elif k == "dedication":
            ded_els = els
        elif k == "toc":
            pass  # TOC is generated; the insert images there are placed as full pages
        else:
            chapters_src.append((k, h1, els))

    chapters = [build_chapter(doc, k, h1, els, epub) for k, h1, els in chapters_src]

    for s in front_matter(doc, pre_toc):
        body.append(s)
    body.append(dedication(doc, ded_els))
    body.append(toc_section(doc, chapters))
    for s in inserts(doc, epub):
        body.append(s)
    for ch in chapters:
        body.append(ch)
    return doc


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    doc = build()
    head = doc.head
    head.append(BeautifulSoup(
        '<meta charset="utf-8"><title>The 5-Step Book Launch for Experts</title>'
        '<link rel="stylesheet" href="../book.css">', "html.parser"))
    (OUT / "book.html").write_text(str(doc), encoding="utf-8")
    print("wrote", OUT / "book.html")


if __name__ == "__main__":
    main()
