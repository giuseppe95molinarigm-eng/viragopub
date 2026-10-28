#!/usr/bin/env python3
"""Make the IngramSpark print interior from the KDP print PDF.

IngramSpark preflight wants CMYK (no RGB), no ICC profiles (PDF/X-1a:2001), no
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


def last_page_is_blank(page):
    res = page.get("/Resources") or {}
    return not page.extract_text().strip() and not (res.get("/XObject") or {})


def prepare(src, dst):
    reader = PdfReader(src)
    writer = PdfWriter(clone_from=reader)
    # IngramSpark prints its manufacturing barcode on the last page, which must be
    # blank, and needs an even page count; otherwise it adds pages itself and the
    # cover template's page count (and spine) no longer matches the file.
    if not last_page_is_blank(writer.pages[-1]):
        w, h = float(writer.pages[-1].mediabox.width), float(writer.pages[-1].mediabox.height)
        writer.add_blank_page(w, h)
        writer.add_blank_page(w, h)
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
    # PDF/X-1a:2001 with a registered characterisation (CGATS TR 001 = US web
    # coated SWOP) and NO embedded ICC profile: IngramSpark rejects files that
    # contain ICC colour profiles.
    Path(path).write_text(f"""%!
[ /GTS_PDFXVersion (PDF/X-1a:2001)
  /GTS_PDFXConformance (PDF/X-1a:2001)
  /Title ({title})
  /Trapped /False
/DOCINFO pdfmark
[/_objdef {{OutputIntent_PDFX}} /type /dict /OBJ pdfmark
[{{OutputIntent_PDFX}} <<
  /Type /OutputIntent
  /S /GTS_PDFX
  /OutputCondition (Commercial and specialty printing)
  /Info (U.S. Web Coated SWOP)
  /OutputConditionIdentifier (CGATS TR 001)
  /RegistryName (http://www.color.org)
>> /PUT pdfmark
[{{Catalog}} <</OutputIntents [ {{OutputIntent_PDFX}} ]>> /PUT pdfmark
""")


def check_no_icc(path):
    """Fail if anything in the file is an ICC profile or an ICCBased colour space."""
    reader = PdfReader(path)
    for num in range(1, int(reader.trailer["/Size"])):
        try:
            obj = reader.get_object(num)
        except Exception:
            continue
        if obj is None:
            continue
        if isinstance(obj, list) and obj and obj[0] == "/ICCBased":
            raise SystemExit(f"ICCBased colour space left in object {num}")
        if hasattr(obj, "get") and "/DestOutputProfile" in obj:
            raise SystemExit("OutputIntent still carries an ICC profile")


def to_pdfx(prepared, out, title="The 5-Step Book Launch for Experts"):
    """Convert a prepared PDF to CMYK PDF/X-1a:2001 (no ICC) with Ghostscript."""
    with tempfile.TemporaryDirectory() as tmp:
        defs = str(Path(tmp) / "pdfx_def.ps")
        pdfx_def(defs, title)
        subprocess.run([
            "gs", "-q", "-dBATCH", "-dNOPAUSE", "-dSAFER",
            "-sDEVICE=pdfwrite", "-dPDFX=true", "-dCompatibilityLevel=1.4",
            "-sColorConversionStrategy=CMYK", "-sProcessColorModel=DeviceCMYK",
            "-dUseFastColor=true", "-dOverrideICC=true",
            "-dEmbedAllFonts=true", "-dSubsetFonts=true",
            "-dAutoRotatePages=/None", "-dPreserveAnnots=false",
            "-dDownsampleColorImages=false", "-dDownsampleGrayImages=false",
            "-dDownsampleMonoImages=false",
            "-dAutoFilterColorImages=false", "-sColorImageFilter=FlateEncode",
            f"-sOutputFile={out}",
            # full grey-component replacement: neutrals and black text go to K only
            "-c", "{} setblackgeneration {} setundercolorremoval",
            "-f", defs, prepared,
        ], check=True)
    check_no_icc(out)


def main():
    src, out = sys.argv[1], sys.argv[2]
    with tempfile.TemporaryDirectory() as tmp:
        prepared = str(Path(tmp) / "prepared.pdf")
        prepare(src, prepared)
        to_pdfx(prepared, out)
    print("wrote", out, len(PdfReader(out).pages), "pages")


if __name__ == "__main__":
    main()
