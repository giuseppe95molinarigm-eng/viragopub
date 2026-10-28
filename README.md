# The 5-Step Book Launch for Experts: interior formatting

Fiverr order for viragopub (Karina G. Sanchez): custom 6 × 9 interior, print-ready PDF and reflowable EPUB.

## Deliverables (`output/`)

| File | Use |
|---|---|
| `The 5-Step Book Launch for Experts - Interior 6x9.pdf` | KDP paperback / hardcover interior. 124 pages, 6.125 × 9.25 in (6 × 9 trim **with bleed**: choose "Bleed" in KDP). All fonts embedded. |
| `The 5-Step Book Launch for Experts.epub` | Kindle and IngramSpark eBook (reflowable, EPUB 3, passes EpubCheck with no errors). |
| `IngramSpark/… Interior 6x9 IngramSpark.pdf` | IngramSpark interior: 126 pages (two blank pages added at the end: IngramSpark prints its manufacturing barcode on a blank last page, and this matches the cover template's page count), same 6.125 × 9.25 in page, PDF/X-1a:2001 (CMYK, no ICC profiles, as IngramSpark requires), black text on the K plate only, max ink 200%, no transparency, no annotations, TrimBox/BleedBox set. |
| `IngramSpark/… Ebook Cover IngramSpark.jpg` | IngramSpark eBook cover: front cover only, 1920 × 2880 px RGB JPG. |
| `IngramSpark/… Paperback Cover IngramSpark.pdf` | IngramSpark paperback cover on their template (Request ID CBP1576063): 6 × 9, Standard Color, White, 126 pages, spine 0.268 in, artwork 12.518 × 9.25 in, ISBN barcode from the template, CMYK PDF/X-1a:2001, max ink 185%. |

## Sources

- `source/Manuscript.docx`: the final manuscript (Manuscript_1 from the author's Drive folder; copyright 2027, includes the dedication).
- `assets/inserts/*.pdf`: the author's insert pages (audiobook, video training, YouTube/Instagram, worksheets opt-in). In print they are placed as vector pages with clickable links.
- `assets/inserts/audiobook.pdf`: the "Download the audiobook" insert (sent 27 Oct, replaces the earlier "Reserve" version); links to www.theroyaltycoach.com/audiobook-download.
- `assets/inserts/discovery-call.pdf`: the "Book your call" insert (high-resolution version sent 26 Oct); placed in the book as `assets/images/insert-discovery-call.jpg` (300+ ppi at its printed size).
- `source/Cover-Paperback-KDP.pdf`: the author's KDP paperback cover (spine 0.279 in), used for the IngramSpark eBook cover image and paperback cover.
- `source/IngramSpark-Cover-Template-9781069528292.pdf`: IngramSpark cover template from the author's account.

## Rebuilding

```
./build.sh
```

Pipeline (Ghostscript is needed for the IngramSpark step): `build/build_html.py` (docx → structured HTML) → `build/render.mjs` (Paged.js in Chromium, `build/book.css`) → `build/finalize_pdf.py` (merges the insert PDFs and trims spine-side bleed) → `build/build_epub.py` (`build/epub.css`) → `build/make_ingram.py` (CMYK PDF/X-1a for IngramSpark).

**Audiobook insert update:** replace `assets/inserts/audiobook.pdf` with the new 6 × 9 PDF, update the link in `build/finalize_pdf.py` (`INSERT_SPECS`) and `build/build_html.py` (`LINKS`) if the URL changes, then run `./build.sh`. For the EPUB image, run `pdftoppm -r 200 -png -singlefile assets/inserts/audiobook.pdf assets/images/epub-audiobook`.
