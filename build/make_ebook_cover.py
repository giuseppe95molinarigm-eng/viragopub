#!/usr/bin/env python3
"""Cut the front cover out of a full-wrap paperback cover PDF (single raster image)
and save it as the eBook cover JPG. IngramSpark minimum: 1600 x 1873 px.

Usage: python3 build/make_ebook_cover.py <cover.pdf> <out.jpg>
"""
import glob
import subprocess
import sys
import tempfile

from PIL import Image
from pypdf import PdfReader

TRIM_W, TRIM_H, BLEED = 6.0, 9.0, 0.125  # inches

src, out = sys.argv[1], sys.argv[2]
page_w = float(PdfReader(src).pages[0].mediabox.width) / 72
with tempfile.TemporaryDirectory() as tmp:
    subprocess.run(["pdfimages", "-j", src, f"{tmp}/c"], check=True)
    im = Image.open(sorted(glob.glob(f"{tmp}/c-000.*"))[0])
    ppi = im.size[0] / page_w
    left = page_w - BLEED - TRIM_W
    box = tuple(round(v * ppi) for v in (left, BLEED, page_w - BLEED, BLEED + TRIM_H))
    front = im.crop(box).convert("RGB")
    assert front.size[0] >= 1600 and front.size[1] >= 1873, front.size
    front.save(out, quality=92, subsampling=0, optimize=True, dpi=(round(ppi), round(ppi)))
print("wrote", out, front.size)
