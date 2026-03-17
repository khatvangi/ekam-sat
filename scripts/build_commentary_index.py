#!/usr/bin/env python3
"""
Verse-Commentary Alignment Index
==================================
Builds an index mapping BORI verse IDs to Nīlakaṇṭha commentary pages.

Strategy:
  1. Detect chapter colophons in OCR text to segment by chapter
  2. Map vulgate chapter numbers to BORI chapters
  3. Detect verse numbers within each chapter segment
  4. Output: {BORI_verse_id → [commentary_volume, page, chapter]}

Usage:
    python build_commentary_index.py \
        --ocr-dir ../nilakantha/ocr_clean/ \
        --output ../output/commentary_index/
"""

import re
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict, OrderedDict
from datetime import datetime


# ─── volume-to-parva mapping ─────────────────────────────────────────────────
VOLUME_PARVA_MAP = {
    "vol8995": {"parvas": ["01", "02"], "name": "Ādi + Sabhā"},
    "vol8996": {"parvas": ["03", "04"], "name": "Āraṇyaka + Virāṭa"},
    "vol8997": {"parvas": ["05", "06"], "name": "Udyoga + Bhīṣma"},
    "vol8998": {"parvas": ["07", "08"], "name": "Droṇa + Karṇa"},
    "vol8999": {"parvas": ["09", "10", "11"], "name": "Sauptika + Strī"},
    "shanti":  {"parvas": ["12"], "name": "Śāntiparva"},
    "vol9000": {"parvas": ["13", "14", "15", "16", "17", "18"], "name": "Anuśāsana + rest"},
}

PARVA_NAMES_HK = {
    "01": ["Adi", "Adi"],
    "02": ["samA", "sabhA"],
    "03": ["AraNyaka", "vana", "araNya"],
    "04": ["virATa", "virAta"],
    "05": ["udyoga"],
    "06": ["bhISma", "bhIzma"],
    "07": ["droNa"],
    "08": ["karNa"],
    "09": ["zalya", "zAlya"],
    "10": ["sauptika"],
    "11": ["strI"],
    "12": ["zAnti", "zAMti", "shAnti"],
    "13": ["anuzAsana", "AnuzAsana"],
    "14": ["azvamedhika", "Azvamedhika", "azvamedha"],
    "15": ["AzramavAsika"],
    "16": ["mausala"],
    "17": ["mahAprasthAnika"],
    "18": ["svargArohaNa"],
}

# devanagari digit mapping
DEVA_DIGITS = {'०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
               '५': '5', '६': '6', '७': '7', '८': '8', '९': '9'}


def deva_to_int(s):
    """Convert Devanagari numeral string to integer."""
    result = ""
    for c in s:
        if c in DEVA_DIGITS:
            result += DEVA_DIGITS[c]
        elif c.isdigit():
            result += c
    return int(result) if result else None


def extract_chapter_markers(text, is_devanagari=False):
    """
    Find chapter colophons in OCR text.
    Returns list of {chapter_num, parva_hint, position, type}
    """
    markers = []

    if is_devanagari:
        # devanagari pattern: अध्यायः followed by number
        pattern = r'(?:अध्यायः|अध्याय)\s*(?:॥\s*)?([०-९\d]+)'
        for m in re.finditer(pattern, text):
            num = deva_to_int(m.group(1))
            if num and 1 <= num <= 400:
                markers.append({
                    "chapter_num": num,
                    "position": m.start(),
                    "raw": m.group(0)[:50],
                })

    # HK pattern: adhyAyaH followed by number
    # OCR often merges words: "...mo'dhyAyaH || 92 ||" or "...adhyAyaH|| 92||"
    # be very flexible with spacing and separators
    hk_patterns = [
        r"dhyAyaH\s*(?:\|\|?\s*)*(\d+)",          # adhyAyaH || 92
        r"dhyAya\s*(?:\|\|?\s*)*(\d+)",            # adhyAya || 92
        r"dhyAyaH\s*\|\|\s*(\d+)\s*\|\|",          # adhyAyaH || 92 ||
    ]
    for pat in hk_patterns:
        for m in re.finditer(pat, text):
            num = int(m.group(1))
            if 1 <= num <= 400:
                markers.append({
                    "chapter_num": num,
                    "position": m.start(),
                    "raw": m.group(0)[:60],
                })

    # also look for parva names to identify which parva we're in
    parva_hint = None
    for parva_num, keywords in PARVA_NAMES_HK.items():
        for kw in keywords:
            if kw.lower() in text.lower():
                parva_hint = parva_num
                break

    for m in markers:
        m["parva_hint"] = parva_hint

    return markers


def extract_verse_numbers(text):
    """
    Find verse numbers in commentary text.
    Commentary format: number followed by | or || or at end of gloss.
    Returns list of (verse_num, position).
    """
    verses = []

    # devanagari verse numbers: ३५ ॥ or just ३५
    for m in re.finditer(r'([०-९]+)\s*(?:॥|।)', text):
        num = deva_to_int(m.group(1))
        if num and 1 <= num <= 200:
            verses.append((num, m.start()))

    # HK verse numbers: 35 || or just 35 at word boundary
    for m in re.finditer(r'(?:^|\s|[|])(\d{1,3})\s*(?:\|\|?|$)', text, re.MULTILINE):
        num = int(m.group(1))
        if 1 <= num <= 200:
            verses.append((num, m.start()))

    return verses


def load_pages(ocr_dir, volume):
    """Load all pages from a volume."""
    ocr_path = Path(ocr_dir)

    if volume == "shanti":
        pages_dir = ocr_path / "pages"
    else:
        pages_dir = ocr_path / volume / "pages"

    if not pages_dir.exists():
        return []

    pages = []
    for page_file in sorted(pages_dir.glob("page_*.txt")):
        text = page_file.read_text(encoding="utf-8", errors="replace")

        # separate devanagari and HK sections
        hk_marker = "--- HK TRANSLITERATION ---"
        if hk_marker in text:
            parts = text.split(hk_marker, 1)
            deva_text = parts[0]
            hk_text = parts[1]
        else:
            deva_text = text
            hk_text = ""

        # strip page header
        for section in [deva_text, hk_text]:
            lines = section.split("\n")
            section = "\n".join(l for l in lines if not l.startswith("=== PAGE"))

        page_num = int(page_file.stem.split("_")[1])
        pages.append({
            "page_num": page_num,
            "deva_text": deva_text,
            "hk_text": hk_text,
            "full_text": text,
            "volume": volume,
        })

    return pages


def build_index(ocr_dir, output_dir):
    """Build the verse-commentary alignment index."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_chapter_markers = []
    page_chapter_map = OrderedDict()  # (volume, page) -> {chapter info}
    volume_summaries = {}

    for volume, info in VOLUME_PARVA_MAP.items():
        print(f"\n{'='*60}")
        print(f"Processing {volume} ({info['name']})")
        print(f"Expected parvas: {', '.join(info['parvas'])}")
        print(f"{'='*60}")

        pages = load_pages(ocr_dir, volume)
        if not pages:
            print(f"  No pages found for {volume}")
            continue

        print(f"  Loaded {len(pages)} pages")

        # scan for chapter markers
        chapter_pages = []  # (page_num, chapter_num, parva_hint)
        current_chapter = None
        chapters_found = set()

        for page in pages:
            # check both devanagari and HK text
            markers = []
            markers.extend(extract_chapter_markers(page["deva_text"], is_devanagari=True))
            if page["hk_text"]:
                markers.extend(extract_chapter_markers(page["hk_text"], is_devanagari=False))

            # also extract verse numbers for finer granularity
            verse_nums = extract_verse_numbers(page["deva_text"])
            if page["hk_text"]:
                verse_nums.extend(extract_verse_numbers(page["hk_text"]))

            # deduplicate markers by chapter number
            seen_chapters = set()
            unique_markers = []
            for m in markers:
                if m["chapter_num"] not in seen_chapters:
                    seen_chapters.add(m["chapter_num"])
                    unique_markers.append(m)

            if unique_markers:
                for m in unique_markers:
                    chapter_pages.append((page["page_num"], m["chapter_num"], m.get("parva_hint")))
                    chapters_found.add(m["chapter_num"])
                    current_chapter = m["chapter_num"]

            # deduplicate verse numbers
            unique_verses = sorted(set(v[0] for v in verse_nums))

            # store page mapping
            page_chapter_map[(volume, page["page_num"])] = {
                "volume": volume,
                "page": page["page_num"],
                "chapter_markers": [m["chapter_num"] for m in unique_markers],
                "verse_numbers": unique_verses[:20],  # cap to avoid noise
                "current_chapter": current_chapter,
            }

        # report
        chapter_list = sorted(chapters_found)
        print(f"  Chapters detected: {len(chapter_list)}")
        if chapter_list:
            print(f"  Range: {min(chapter_list)} - {max(chapter_list)}")
            print(f"  First 10: {chapter_list[:10]}")

        volume_summaries[volume] = {
            "volume": volume,
            "name": info["name"],
            "pages": len(pages),
            "chapters_detected": len(chapters_found),
            "chapter_range": f"{min(chapter_list)}-{max(chapter_list)}" if chapter_list else "none",
            "expected_parvas": info["parvas"],
        }

    # ─── build the alignment index ───────────────────────────────────────

    # for each page, assign a chapter range based on surrounding markers
    # pages between chapter N end and chapter N+1 end belong to chapter N+1
    index_entries = []

    for (vol, page_num), info in page_chapter_map.items():
        entry = {
            "volume": vol,
            "page": page_num,
            "detected_chapters": info["chapter_markers"],
            "verse_numbers_on_page": info["verse_numbers"],
            "assigned_chapter": info["current_chapter"],
        }
        index_entries.append(entry)

    # ─── save outputs ────────────────────────────────────────────────────

    # 1. page-level index CSV
    with open(output_dir / "page_chapter_index.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["volume", "page", "assigned_chapter", "detected_chapters", "verse_numbers_on_page"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for e in index_entries:
            row = {
                "volume": e["volume"],
                "page": e["page"],
                "assigned_chapter": e["assigned_chapter"] or "",
                "detected_chapters": "|".join(str(c) for c in e["detected_chapters"]),
                "verse_numbers_on_page": "|".join(str(v) for v in e["verse_numbers_on_page"]),
            }
            writer.writerow(row)

    # 2. volume summary JSON
    with open(output_dir / "volume_summary.json", "w", encoding="utf-8") as f:
        json.dump(volume_summaries, f, ensure_ascii=False, indent=2)

    # 3. chapter-to-page lookup JSON
    chapter_pages_lookup = defaultdict(list)
    for e in index_entries:
        if e["assigned_chapter"]:
            key = f"{e['volume']}_ch{e['assigned_chapter']}"
            chapter_pages_lookup[key].append(e["page"])

    with open(output_dir / "chapter_page_lookup.json", "w", encoding="utf-8") as f:
        json.dump(dict(chapter_pages_lookup), f, indent=2)

    # 4. report
    total_pages = sum(v["pages"] for v in volume_summaries.values())
    total_chapters = sum(v["chapters_detected"] for v in volume_summaries.values())
    pages_with_chapter = sum(1 for e in index_entries if e["assigned_chapter"])
    pages_with_verses = sum(1 for e in index_entries if e["verse_numbers_on_page"])

    lines = [
        "=" * 70,
        "VERSE-COMMENTARY ALIGNMENT INDEX",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"Total OCR pages processed: {total_pages}",
        f"Chapter boundaries detected: {total_chapters}",
        f"Pages with chapter assignment: {pages_with_chapter} ({100*pages_with_chapter/total_pages:.1f}%)",
        f"Pages with verse numbers: {pages_with_verses} ({100*pages_with_verses/total_pages:.1f}%)",
        "",
        "-" * 70,
        "PER-VOLUME SUMMARY",
        "-" * 70,
    ]

    for vol, summary in volume_summaries.items():
        lines.append(
            f"  {vol:<12} ({summary['name']:<25}) "
            f"pages={summary['pages']:>4}  "
            f"chapters={summary['chapters_detected']:>3}  "
            f"range={summary['chapter_range']}"
        )

    # chapter density: pages per chapter
    lines += [
        "",
        "-" * 70,
        "CHAPTER-TO-PAGE MAPPING (first 30 chapters)",
        "-" * 70,
    ]
    for key in sorted(chapter_pages_lookup.keys())[:30]:
        pages = chapter_pages_lookup[key]
        lines.append(f"  {key:<30} pages {min(pages):>4}-{max(pages):>4} ({len(pages)} pages)")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "alignment_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines))
    print(f"\nOutputs in {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Build Verse-Commentary Alignment Index")
    parser.add_argument("--ocr-dir", default="../nilakantha/ocr_clean/")
    parser.add_argument("--output", default="../output/commentary_index/")
    args = parser.parse_args()

    build_index(args.ocr_dir, args.output)


if __name__ == "__main__":
    main()
