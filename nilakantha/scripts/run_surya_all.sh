#!/bin/bash
# run surya OCR on all 6 volumes (skipping Śāntiparva pages already done with Gemini)
# estimated: ~1,577 pages, ~4-5 hours on RTX A4000

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PDF_DIR="/storage/mbh/nilakantha/600dpi"
BASE_OUT="/storage/mbh/nilakantha/ocr_clean"

echo "=========================================="
echo "Nīlakaṇṭha OCR — Surya batch run"
echo "started: $(date)"
echo "=========================================="

# vol 8995: Ādi + Sabhā (275 pages)
echo -e "\n>>> VOL 8995: Ādi + Sabhā"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/8995_text.pdf" \
    --parva vol8995_adi_sabha \
    --output "$BASE_OUT/vol8995/" \
    --dpi 300

# vol 8996: Āraṇyaka + Virāṭa (318 pages)
echo -e "\n>>> VOL 8996: Āraṇyaka + Virāṭa"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/8996_text.pdf" \
    --parva vol8996_aranyaka_virata \
    --output "$BASE_OUT/vol8996/" \
    --dpi 300

# vol 8997: Udyoga + Bhīṣma (312 pages)
echo -e "\n>>> VOL 8997: Udyoga + Bhīṣma"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/8997_text.pdf" \
    --parva vol8997_udyoga_bhishma \
    --output "$BASE_OUT/vol8997/" \
    --dpi 300

# vol 8998: Droṇa + Karṇa (344 pages)
echo -e "\n>>> VOL 8998: Droṇa + Karṇa"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/8998_text.pdf" \
    --parva vol8998_drona_karna \
    --output "$BASE_OUT/vol8998/" \
    --dpi 300

# vol 8999: Sauptika + Strī ONLY (pp1-41), Śānti already done via Gemini
echo -e "\n>>> VOL 8999: Sauptika + Strī (pp1-41 only, Śānti done)"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/8999_text.pdf" \
    --parva vol8999_sauptika_stri \
    --output "$BASE_OUT/vol8999/" \
    --start 1 --end 41 \
    --dpi 300

# vol 9000: Anuśāsana + rest (287 pages)
echo -e "\n>>> VOL 9000: Anuśāsana + rest"
python3 "$SCRIPT_DIR/ocr_surya.py" \
    --pdf "$PDF_DIR/9000_text.pdf" \
    --parva vol9000_anushasana \
    --output "$BASE_OUT/vol9000/" \
    --dpi 300

echo -e "\n=========================================="
echo "ALL VOLUMES COMPLETE"
echo "finished: $(date)"
echo "=========================================="
