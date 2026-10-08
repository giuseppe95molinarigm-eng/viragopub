#!/usr/bin/env python3
"""Finish build/out/raw.pdf into the KDP print file.

1. Replaces the insert placeholder pages with the author's vector insert PDFs
   (assets/inserts), at 100% inside the 6 x 9 trim, bleed filled with the
   insert's background colour, and keeps/adds the clickable links.
2. Trims the spine-side bleed so every page is 6.125 x 9.25 in
   (KDP 6 x 9 with bleed: 0.125 in on top, bottom and outside edge).

Usage: python3 build/finalize_pdf.py [output.pdf]
"""
import json
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter, Transformation
from pypdf.generic import (ArrayObject, DictionaryObject, FloatObject, NameObject,
                           NumberObject, RectangleObject, TextStringObject, DecodedStreamObject)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "out"
BLEED = 9.0           # 0.125 in
TRIM_W, TRIM_H = 432.0, 648.0

# Background colour of each insert (for the bleed area) and extra link areas
# (x0, y0, x1, y1 in the insert's own 432 x 648 pt space).
INSERT_SPECS = {
    "audiobook.pdf": {"bg": (0.957, 0.933, 0.890), "links": [
        ("https://www.theroyaltycoach.com/free-audiobook", (24, 37, 408, 164))]},
    "video-training.pdf": {"bg": (1, 1, 1), "links": [
        ("https://www.theroyaltycoach.com/prove-method-video", (45, 45, 387, 155)),
        ("https://www.theroyaltycoach.com/prove-method-video", (50, 177, 382, 369))]},
    "youtube-instagram.pdf": {"bg": (1, 1, 1), "links": [
        ("https://youtube.com/@theroyaltycoach", (30, 345, 402, 600)),
        ("https://instagram.com/karina.g.sanchez", (30, 40, 402, 300))]},
}


def link_annot(uri, rect):
    return DictionaryObject({
        NameObject("/Type"): NameObject("/Annot"),
        NameObject("/Subtype"): NameObject("/Link"),
        NameObject("/Rect"): ArrayObject([FloatObject(v) for v in rect]),
        NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
        NameObject("/A"): DictionaryObject({
            NameObject("/S"): NameObject("/URI"),
            NameObject("/URI"): TextStringObject(uri),
        }),
    })


def shift_annots(page, dx, dy, writer):
    annots = page.get("/Annots")
    if not annots:
        return
    for ref in annots:
        a = ref.get_object()
        r = [float(v) for v in a["/Rect"]]
        a[NameObject("/Rect")] = ArrayObject(
            [FloatObject(r[0] + dx), FloatObject(r[1] + dy), FloatObject(r[2] + dx), FloatObject(r[3] + dy)])


def build_insert_page(writer, raw_page, insert_file):
    spec = INSERT_SPECS[insert_file]
    w, h = float(raw_page.mediabox.width), float(raw_page.mediabox.height)
    page = writer.add_blank_page(width=w, height=h)
    # background (fills the bleed)
    r, g, b = spec["bg"]
    bg = DecodedStreamObject()
    bg.set_data(f"q {r} {g} {b} rg 0 0 {w} {h} re f Q\n".encode())
    page[NameObject("/Contents")] = writer._add_object(bg)
    src = PdfReader(ROOT / "assets" / "inserts" / insert_file).pages[0]
    sw, sh = float(src.mediabox.width), float(src.mediabox.height)
    scale = min(TRIM_W / sw, TRIM_H / sh)
    ox = BLEED + (TRIM_W - sw * scale) / 2
    oy = BLEED + (TRIM_H - sh * scale) / 2
    page.merge_transformed_page(src, Transformation().scale(scale).translate(ox, oy))
    annots = ArrayObject()
    for ref in src.get("/Annots") or []:
        a = ref.get_object()
        uri = a.get("/A", {}).get("/URI")
        if uri:
            x0, y0, x1, y1 = [float(v) for v in a["/Rect"]]
            annots.append(writer._add_object(link_annot(
                uri, (x0 * scale + ox, y0 * scale + oy, x1 * scale + ox, y1 * scale + oy))))
    for uri, (x0, y0, x1, y1) in spec["links"]:
        annots.append(writer._add_object(link_annot(
            uri, (x0 * scale + ox, y0 * scale + oy, x1 * scale + ox, y1 * scale + oy))))
    page[NameObject("/Annots")] = annots
    return page


def main():
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT / "interior.pdf"
    reader = PdfReader(OUT / "raw.pdf")
    inserts = {d["index"]: d["file"] for d in json.loads((OUT / "inserts.json").read_text())}
    writer = PdfWriter()
    for idx, raw_page in enumerate(reader.pages):
        if idx in inserts:
            build_insert_page(writer, raw_page, inserts[idx])
        else:
            writer.add_page(raw_page)
    # keep the TOC's internal links working (Chromium uses named destinations)
    for name, dest in reader.named_destinations.items():
        writer.add_named_destination(name, reader.get_destination_page_number(dest))

    # trim spine-side bleed
    for i, page in enumerate(writer.pages):
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        recto = i % 2 == 0  # page 1 is a right-hand page
        if recto:
            page.add_transformation(Transformation().translate(-BLEED, 0))
            shift_annots(page, -BLEED, 0, writer)
        for box in ("/MediaBox", "/CropBox", "/TrimBox", "/BleedBox", "/ArtBox"):
            if box in page:
                del page[box]
        page[NameObject("/MediaBox")] = RectangleObject([0, 0, w - BLEED, h])

    # Lossless size reduction: compress page content and drop duplicate objects.
    for page in writer.pages:
        page.compress_content_streams(level=9)
    writer.compress_identical_objects(remove_identicals=True, remove_orphans=True)

    writer.add_metadata({"/Title": "The 5-Step Book Launch for Experts",
                         "/Author": "Karina G. Sanchez"})
    with open(out_path, "wb") as fh:
        writer.write(fh)
    print("wrote", out_path, len(writer.pages), "pages")


if __name__ == "__main__":
    main()
