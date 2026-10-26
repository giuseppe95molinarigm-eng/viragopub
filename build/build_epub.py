#!/usr/bin/env python3
"""Build the reflowable EPUB (output/…epub) from the same structured HTML as the print
edition. Usage: python3 build/build_epub.py [output.epub]"""
import re
import sys
import uuid
from pathlib import Path

from bs4 import BeautifulSoup
from ebooklib import epub

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_html  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

FONTS = ["Anton-Regular.ttf", "Oswald-Medium.ttf", "Oswald-SemiBold.ttf"]


def fix_paths(sec):
    for img in sec.find_all("img"):
        img["src"] = "images/" + Path(img["src"]).name
    return sec


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build" / "out" / "interior.epub"
    doc = build_html.build(epub=True)

    book = epub.EpubBook()
    book.set_identifier("urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "5-step-book-launch-for-experts")))
    book.set_title("The 5-Step Book Launch for Experts")
    book.set_language("en")
    book.add_author("Karina G. Sanchez")
    book.add_metadata("DC", "description",
                      "The Insider’s Guide to Self-Publish Your Book, Nail Your Launch, "
                      "and Turn Readers Into High-Paying Clients")
    book.add_metadata("DC", "rights", f"Copyright © {build_html.COPYRIGHT_YEAR} Karina G. Sanchez")
    book.set_cover("images/cover.jpg", (ASSETS / "images" / "cover.jpg").read_bytes())

    css = epub.EpubItem(uid="style", file_name="style/epub.css", media_type="text/css",
                        content=(ROOT / "build" / "epub.css").read_bytes())
    book.add_item(css)
    for f in FONTS:
        book.add_item(epub.EpubItem(uid=f, file_name="fonts/" + f, media_type="font/ttf",
                                    content=(ASSETS / "fonts" / f).read_bytes()))

    used_images = set()
    spine, toc_links, chapters = ["nav"], [], []
    file_of = {}

    sections = doc.body.find_all("section", recursive=False)
    # first pass: assign file names
    for n, sec in enumerate(sections):
        cls = sec.get("class", [])
        if "toc" in cls:
            name = "contents.xhtml"
        elif "chapter" in cls:
            name = f"{sec['id']}.xhtml"
        else:
            name = f"front-{n:02d}.xhtml"
        file_of[sec.get("id") or name] = name
        sec["data-file"] = name

    for sec in sections:
        name = sec["data-file"]
        cls = sec.get("class", [])
        if "toc" in cls:
            for a in sec.find_all("a"):
                a["href"] = file_of[a["href"][1:]] + a["href"]
            for pg in sec.select(".toc-pg"):
                pg.decompose()
        for h in sec.select(".rh-src, .ghost-num"):
            h.decompose()
        fix_paths(sec)
        for img in sec.find_all("img"):
            used_images.add(img["src"])
        del sec["data-file"]
        title = "The 5-Step Book Launch for Experts"
        h1 = sec.find("h1")
        if h1:
            title = re.sub(r"\s+", " ", h1.get_text(" ")).strip()
        item = epub.EpubHtml(title=title, file_name=name, lang="en")
        item.content = ("<html xmlns=\"http://www.w3.org/1999/xhtml\"><head><title>"
                        f"{title}</title></head><body>{sec}</body></html>")
        item.add_item(css)
        book.add_item(item)
        spine.append(item)
        if "chapter" in cls:
            label = sec.select_one(".opener-label").get_text()
            t = sec.get("data-h1", title)
            toc_links.append(epub.Link(name, re.sub(r"\.\.\.$", "…", t), sec["id"]))
        elif "toc" in cls:
            toc_links.insert(0, epub.Link(name, "Contents", "contents"))

    for src in sorted(used_images):
        p = ASSETS / "images" / Path(src).name
        if p.name == "cover.jpg":
            continue
        mt = "image/jpeg" if p.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        book.add_item(epub.EpubItem(uid=p.stem, file_name=src, media_type=mt, content=p.read_bytes()))

    book.toc = toc_links
    book.spine = spine
    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    nav.add_item(css)
    book.add_item(nav)
    book.guide = [{"type": "toc", "href": "contents.xhtml", "title": "Contents"}]
    epub.write_epub(str(out), book)
    print("wrote", out)


if __name__ == "__main__":
    main()
