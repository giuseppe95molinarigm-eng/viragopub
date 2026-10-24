#!/usr/bin/env python3
"""Make the IngramSpark print interior from the KDP print PDF.

IngramSpark preflight wants CMYK (no RGB), an output intent (PDF/X), no
annotations, and TrimBox/BleedBox on every page. The page size is the same as
KDP's (6.125 x 9.25 in: 6 x 9 trim, 0.125 in bleed on top, bottom and outside).

Colour conversion uses Ghostscript's non-ICC ("fast") RGB->CMYK conversion with
full black generation / undercolour removal on purpose: black and greys come out
on the K plate only, so body text prints in black ink instead of four-colour
rich black, and total ink stays low (no bleed-through).

Usage: python3 build/make_ingram.py <kdp.pdf> <ingram.pdf>
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, RectangleObject

BLEED = 9.0
ICC = "/usr/share/ghostscript/10.02.1/iccprofiles/default_cmyk.icc"


def prepare(src, dst):
    reader = PdfReader(src)
    writer = PdfWriter(clone_from=reader)
    for i, page in enumerate(writer.pages):
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        recto = i % 2 == 0  # bleed on the right for rectos, on the left for versos
        x0 = 0.0 if recto else BLEED
        page[NameObject("/TrimBox")] = RectangleObject([x0, BLEED, x0 + w - BLEED, h - BLEED])
        page[NameObject("/BleedBox")] = RectangleObject([0, 0, w, h])
        if "/Annots" in page:
            del page["/Annots"]  # links are not allowed in PDF/X print files
    root = writer._root_object
    for key in ("/Names", "/Dests", "/OpenAction"):
        if key in root:
            del root[key]
    with open(dst, "wb") as fh:
        writer.write(fh)


def pdfx_def(path, title):
    Path(path).write_text(f"""%!
[ /GTS_PDFXVersion (PDF/X-3:2002)
  /Title ({title})
  /Trapped /False
/DOCINFO pdfmark
/ICCProfile ({ICC}) def
[/_objdef {{icc_PDFX}} /type /stream /OBJ pdfmark
[{{icc_PDFX}} << /N 4 >> /PUT pdfmark
[{{icc_PDFX}} ICCProfile (r) file /PUT pdfmark
[/_objdef {{OutputIntent_PDFX}} /type /dict /OBJ pdfmark
[{{OutputIntent_PDFX}} <<
  /Type /OutputIntent
  /S /GTS_PDFX
  /OutputCondition (Commercial and specialty printing)
  /Info (none)
  /OutputConditionIdentifier (CGATS TR 001)
  /RegistryName (http://www.color.org)
  /DestOutputProfile {{icc_PDFX}}
>> /PUT pdfmark
[{{Catalog}} <</OutputIntents [ {{OutputIntent_PDFX}} ]>> /PUT pdfmark
""")


def main():
    src, out = sys.argv[1], sys.argv[2]
    with tempfile.TemporaryDirectory() as tmp:
        prepared = str(Path(tmp) / "prepared.pdf")
        defs = str(Path(tmp) / "pdfx_def.ps")
        prepare(src, prepared)
        pdfx_def(defs, "The 5-Step Book Launch for Experts")
        subprocess.run([
            "gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER", f"--permit-file-read={ICC}",
            "-sDEVICE=pdfwrite", "-dPDFX=true", "-dCompatibilityLevel=1.4",
            "-sColorConversionStrategy=CMYK", "-sProcessColorModel=DeviceCMYK",
            "-dUseFastColor=true", "-dOverrideICC=true",
            "-dEmbedAllFonts=true", "-dSubsetFonts=true",
            "-dAutoRotatePages=/None", "-dPreserveAnnots=false",
            "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
            "-dAutoFilterColorImages=false", "-sColorImageFilter=FlateEncode",
            f"-sOutputFile={out}",
            # full grey-component replacement: neutrals and black text go to K only
            "-c", "{} setblackgeneration {} setundercolorremoval",
            "-f", defs, prepared,
        ], check=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
