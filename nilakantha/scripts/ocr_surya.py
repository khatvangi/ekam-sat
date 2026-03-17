#!/usr/bin/env python3
"""
Nilakantha OCR — Surya (local GPU, free)
========================================
Uses Surya OCR for Devanagari text extraction. Runs entirely on local GPU.
Quality: ~80% of Gemini 2.5-flash. Ligature/spacing errors tagged.

Usage:
    # full volume
    python ocr_surya.py --pdf /storage/mbh/nilakantha/600dpi/8996_text.pdf \
                        --parva aranyaka --output /storage/mbh/nilakantha/ocr_clean/

    # test 5 pages
    python ocr_surya.py --pdf 8996_text.pdf --parva aranyaka --start 1 --test
"""

import os
import io
import json
import re
import time
import argparse
import subprocess
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path


def ocr_page_surya(img, temp_dir):
    """
    OCR a single PIL image using surya CLI.
    returns: text string
    """
    # save image to temp
    img_path = temp_dir / "current_page.jpg"
    img.save(str(img_path), "JPEG", quality=90)

    # run surya CLI
    out_dir = temp_dir / "surya_out"
    out_dir.mkdir(exist_ok=True)

    result = subprocess.run(
        ["surya_ocr", str(img_path), "--output_dir", str(out_dir)],
        capture_output=True, text=True, timeout=120
    )

    # parse JSON output
    results_file = out_dir / "current_page" / "results.json"
    if not results_file.exists():
        return "[OCR ERROR: no output]"

    data = json.load(open(results_file))
    key = list(data.keys())[0]
    lines = data[key][0]["text_lines"]
    text = "\n".join([l["text"] for l in lines])

    # tag low-confidence lines
    tagged = []
    for l in lines:
        line_text = l["text"]
        conf = l.get("confidence", 1.0)
        if conf < 0.5:
            line_text = f"[LOW_CONF:{conf:.2f}] {line_text}"
        tagged.append(line_text)

    # cleanup
    import shutil
    shutil.rmtree(out_dir / "current_page", ignore_errors=True)

    return "\n".join(tagged)


def transliterate_to_hk(devanagari_text):
    """convert devanagari to Harvard-Kyoto."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.HK)
    except ImportError:
        return None
    except Exception:
        return None


def process_pdf(pdf_path, output_dir, parva_name,
                start_page=None, end_page=None, dpi=300):
    """batch process PDF pages with surya OCR."""

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_dir = output_dir / "_temp"
    temp_dir.mkdir(exist_ok=True)

    print(f"PDF: {pdf_path.name}")
    print(f"parva: {parva_name}")
    print(f"engine: surya (local GPU)")
    print(f"DPI: {dpi} | pages: {start_page or 1}-{end_page or 'end'}")

    BATCH_SIZE = 10
    first = start_page or 1
    last = end_page or 9999

    results = []
    errors = []
    total_chars = 0
    skipped = 0

    page_num = first
    while page_num <= last:
        batch_end = min(page_num + BATCH_SIZE - 1, last)

        # skip completed batches
        batch_skip = 0
        for p in range(page_num, batch_end + 1):
            if (output_dir / "pages" / f"page_{p:04d}.txt").exists():
                batch_skip += 1
        if batch_skip == (batch_end - page_num + 1):
            skipped += batch_skip
            page_num = batch_end + 1
            continue

        # convert batch
        try:
            pages = convert_from_path(
                str(pdf_path), dpi=dpi, fmt="jpeg",
                jpegopt={"quality": 90},
                first_page=page_num, last_page=batch_end
            )
        except Exception:
            break

        print(f"\n  batch {page_num}-{batch_end}: {len(pages)} pages")

        for i, page_img in enumerate(pages):
            cur_page = page_num + i

            page_out = output_dir / "pages" / f"page_{cur_page:04d}.txt"
            if page_out.exists():
                skipped += 1
                continue

            # OCR
            text = ocr_page_surya(page_img, temp_dir)

            if text.startswith("[OCR"):
                errors.append({"page": cur_page, "error": text})
                print(f"  p{cur_page}: ERROR")
                continue

            hk_text = transliterate_to_hk(text)
            char_count = len(text)
            total_chars += char_count

            # count low-confidence lines
            low_conf = text.count("[LOW_CONF:")

            results.append({
                "page": cur_page,
                "parva": parva_name,
                "raw_devanagari": text,
                "hk_transliteration": hk_text,
                "char_count": char_count,
                "low_confidence_lines": low_conf
            })

            # save per-page
            page_out.parent.mkdir(exist_ok=True)
            with open(page_out, "w", encoding="utf-8") as f:
                f.write(f"=== PAGE {cur_page} | {parva_name} | engine=surya ===\n\n")
                f.write(text)
                if hk_text:
                    f.write(f"\n\n--- HK TRANSLITERATION ---\n{hk_text}")

            flag = f" [{low_conf} low-conf]" if low_conf else ""
            print(f"  p{cur_page}: {char_count} chars{flag}")

        del pages
        page_num = batch_end + 1

    # rebuild aggregates from ALL page files (not just current run)
    # this ensures resumed runs produce complete outputs
    pages_dir = output_dir / "pages"
    all_page_files = sorted(pages_dir.glob("page_*.txt")) if pages_dir.exists() else []

    with open(output_dir / f"{parva_name}_clean_devanagari.txt", "w") as f:
        for pf in all_page_files:
            page_num_str = pf.stem.split("_")[1]
            page_text = pf.read_text(encoding="utf-8")
            # strip the header lines added during per-page save
            lines = page_text.split("\n")
            # skip header (=== PAGE ... ===) and blank line
            content_lines = []
            in_hk = False
            for line in lines:
                if line.startswith("--- HK TRANSLITERATION ---"):
                    in_hk = True
                    continue
                if line.startswith("=== PAGE"):
                    continue
                if not in_hk:
                    content_lines.append(line)
            devanagari = "\n".join(content_lines).strip()
            f.write(f"\n\n{'='*60}\nPAGE {page_num_str}\n{'='*60}\n\n")
            f.write(devanagari)

    # save current-run results JSON (append-safe — includes only new pages)
    with open(output_dir / f"{parva_name}_surya_results.json", "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    if errors:
        with open(output_dir / f"{parva_name}_errors.json", "w") as f:
            json.dump(errors, f, indent=2)

    # cleanup temp
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    avg = total_chars // len(results) if results else 0
    print(f"\n{'='*60}")
    print(f"OCR COMPLETE — {parva_name} (surya)")
    print(f"pages: {len(results)} done, {skipped} skipped, {len(errors)} errors")
    print(f"total chars: {total_chars:,} | avg: {avg:,}/page")
    print(f"output: {output_dir}")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Nilakantha OCR (Surya, local GPU)")
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--parva", required=True)
    parser.add_argument("--output", default="/storage/mbh/nilakantha/ocr_clean/")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--test", action="store_true")

    args = parser.parse_args()
    if args.test:
        args.start = args.start or 1
        args.end = (args.start or 1) + 4
        print(f"TEST MODE: pages {args.start}-{args.end}")

    process_pdf(args.pdf, args.output, args.parva,
                args.start, args.end, args.dpi)


if __name__ == "__main__":
    main()
