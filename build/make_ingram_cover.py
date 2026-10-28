#!/usr/bin/env python3
"""Build the IngramSpark paperback cover from the KDP cover and the IngramSpark
cover template (Request ID CBP1576063: 6 x 9, Standard Color, White, 126 pages,
spine 0.268 in, artwork 12.518 x 9.250 in on a 15 x 12 in template page).

The KDP cover is a single 320 ppi raster (spine 0.279 in). Its back panel and
front panel are placed unchanged on the template; the spine is cropped to the
template's 0.268 in around its centre (the spine text is 0.125 in wide and
centred, so it keeps ~0.07 in on each side, above the 1 mm spine safety).
The template's ISBN barcode is copied on top of the artwork, then the file is
converted to CMYK PDF/X-1a:2001 like the interior.

Usage: python3 build/make_ingram_cover.py <kdp-cover.pdf> <template.pdf> <out.pdf>
"""
import glob
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_ingram import to_pdfx  # noqa: E402

PT = 72.0
BLEED = 0.125 * PT
TRIM_W, TRIM_H = 6.0 * PT, 9.0 * PT
SPINE = 0.268 * PT                 # from the template
ART_W = 12.518 * PT                # bleed artwork dimensions from the template
ART_H = 9.25 * PT
BARCODE_BOX = (470.75, 230.0, 597.25, 302.0)  # white barcode box on the template (pt)


def main():
    kdp_pdf, template, out = sys.argv[1], sys.argv[2], sys.argv[3]
    tpl = PdfReader(template).pages[0]
    page_w, page_h = float(tpl.mediabox.width), float(tpl.mediabox.height)
    # artwork sits in the top-right corner of the template page
    ax0, ay0 = page_w - ART_W, page_h - ART_H
    back_x0 = ax0                                  # back cover incl. left bleed
    spine_x0 = ax0 + BLEED + TRIM_W                # = back trim right edge
    front_x0 = spine_x0 + SPINE                    # front cover incl. right bleed

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        subprocess.run(["pdfimages", "-j", kdp_pdf, str(tmp / "kdp")], check=True)
        art = Image.open(sorted(glob.glob(str(tmp / "kdp-000.*")))[0]).convert("RGB")
        kdp_w_in = float(PdfReader(kdp_pdf).pages[0].mediabox.width) / PT
        ppi = art.size[0] / kdp_w_in
        px = lambda inches: round(inches * ppi)  # noqa: E731

        panel_in = (BLEED + TRIM_W) / PT                       # 6.125 in
        kdp_spine_in = kdp_w_in - 2 * panel_in                 # 0.279 in
        back = art.crop((0, 0, px(panel_in), art.size[1]))
        front = art.crop((px(kdp_w_in - panel_in), 0, art.size[0], art.size[1]))
        mid = panel_in + kdp_spine_in / 2
        half = SPINE / PT / 2
        spine = art.crop((px(mid - half), 0, px(mid + half), art.size[1]))

        # barcode from the template at 1200 dpi, 1-bit (pure black on white)
        bx0, by0, bx1, by1 = BARCODE_BOX
        subprocess.run([
            "pdftoppm", "-r", "1200", "-mono", "-singlefile",
            "-x", str(round(bx0 / PT * 1200)), "-y", str(round((page_h - by1) / PT * 1200)),
            "-W", str(round((bx1 - bx0) / PT * 1200)), "-H", str(round((by1 - by0) / PT * 1200)),
            template, str(tmp / "barcode"),
        ], check=True)
        barcode = Image.open(tmp / "barcode.pbm").convert("1")

        overlay = tmp / "overlay.pdf"
        c = canvas.Canvas(str(overlay), pagesize=(page_w, page_h))
        c.drawImage(ImageReader(back), back_x0, ay0, panel_in * PT, ART_H)
        c.drawImage(ImageReader(spine), spine_x0, ay0, SPINE, ART_H)
        c.drawImage(ImageReader(front), front_x0, ay0, panel_in * PT, ART_H)
        c.drawImage(ImageReader(barcode), bx0, by0, bx1 - bx0, by1 - by0)
        c.showPage()
        c.save()

        writer = PdfWriter(clone_from=template)
        writer.pages[0].merge_page(PdfReader(overlay).pages[0])
        prepared = tmp / "prepared.pdf"
        with open(prepared, "wb") as fh:
            writer.write(fh)
        to_pdfx(str(prepared), out, title="The 5-Step Book Launch for Experts - Cover")
    print("wrote", out)


if __name__ == "__main__":
    main()
