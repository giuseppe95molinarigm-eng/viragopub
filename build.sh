#!/usr/bin/env bash
# Rebuild the print PDF and EPUB from source/Manuscript.docx.
# Requires: pandoc, python3 (beautifulsoup4, pypdf, ebooklib), node, Chromium, ghostscript.
set -euo pipefail
cd "$(dirname "$0")"
(cd build && [ -d node_modules ] || npm install --silent)
python3 build/build_html.py
node build/render.mjs
python3 build/finalize_pdf.py "output/The 5-Step Book Launch for Experts - Interior 6x9.pdf"
python3 build/build_epub.py "output/The 5-Step Book Launch for Experts.epub"
mkdir -p output/IngramSpark
python3 build/make_ingram.py "output/The 5-Step Book Launch for Experts - Interior 6x9.pdf" \
  "output/IngramSpark/The 5-Step Book Launch for Experts - Interior 6x9 IngramSpark.pdf"
# IngramSpark eBook cover image: front panel of the KDP paperback cover at native resolution
python3 build/make_ebook_cover.py source/Cover-Paperback-KDP.pdf \
  "output/IngramSpark/The 5-Step Book Launch for Experts - Ebook Cover IngramSpark.jpg"
# IngramSpark paperback cover: KDP cover artwork on IngramSpark's template (spine 0.268 in, 126 pages)
python3 build/make_ingram_cover.py source/Cover-Paperback-KDP.pdf source/IngramSpark-Cover-Template-9781069528292.pdf \
  "output/IngramSpark/The 5-Step Book Launch for Experts - Paperback Cover IngramSpark.pdf"
