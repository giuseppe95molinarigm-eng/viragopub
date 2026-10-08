# The 5-Step Book Launch for Experts: interior formatting

Fiverr order for viragopub (Karina G. Sanchez): custom 6 × 9 interior, print-ready PDF and reflowable EPUB.

## Deliverables (`output/`)

| File | Use |
|---|---|
| `The 5-Step Book Launch for Experts - Interior 6x9.pdf` | KDP paperback / hardcover interior. 124 pages, 6.125 × 9.25 in (6 × 9 trim **with bleed**: choose "Bleed" in KDP). All fonts embedded. |
| `The 5-Step Book Launch for Experts.epub` | Kindle eBook (reflowable, EPUB 3, passes EpubCheck with no errors). |

## Sources

- `source/Manuscript.docx`: the final manuscript (Manuscript_1 from the author's Drive folder; copyright 2027, includes the dedication).
- `assets/inserts/*.pdf`: the author's insert pages (audiobook, video training, YouTube/Instagram, worksheets opt-in). In print they are placed as vector pages with clickable links.
- `assets/images/insert-discovery-call.png`: the "Book your call" insert, taken from the manuscript because no separate file was supplied.

## Rebuilding

```
./build.sh
```

Pipeline: `build/build_html.py` (docx → structured HTML) → `build/render.mjs` (Paged.js in Chromium, `build/book.css`) → `build/finalize_pdf.py` (merges the insert PDFs and trims spine-side bleed) → `build/build_epub.py` (`build/epub.css`).

**Audiobook insert update:** replace `assets/inserts/audiobook.pdf` with the new 6 × 9 PDF, update the link in `build/finalize_pdf.py` (`INSERT_SPECS`) and `build/build_html.py` (`LINKS`) if the URL changes, then run `./build.sh`. For the EPUB image, run `pdftoppm -r 200 -png -singlefile assets/inserts/audiobook.pdf assets/images/epub-audiobook`.
