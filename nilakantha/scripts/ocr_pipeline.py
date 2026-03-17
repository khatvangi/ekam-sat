#!/usr/bin/env python3
"""
Nilakantha Bharatabhavadipa -- Gemini Vision OCR Pipeline
=========================================================
Converts 600 DPI scanned PDFs to clean Devanagari Unicode text.
Uses Google Gemini 2.5 Flash vision (free tier, same approach as vedanta project).

Usage:
    export GOOGLE_API_KEY="your-key"

    # test mode: first 5 pages
    python ocr_pipeline.py --pdf /storage/mbh/nilakantha/600dpi/8999_text.pdf \
                           --parva shanti --start 42 --test

    # full Shantiparva OCR (pages 42-422 of vol 8999)
    python ocr_pipeline.py --pdf /storage/mbh/nilakantha/600dpi/8999_text.pdf \
                           --parva shanti --start 42 --end 422

    # Aranyakaparva (vol 8996)
    python ocr_pipeline.py --pdf /storage/mbh/nilakantha/600dpi/8996_text.pdf \
                           --parva aranyaka
"""

import os
import io
import json
import re
import time
import argparse
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
from pdf2image import convert_from_path


# --- OCR prompt tuned for Nilakantha commentary layout ---
OCR_PROMPT = """OCR this page from Nīlakaṇṭha's Bhāratabhāvadīpa commentary on the Mahābhārata (Chitrashala Press edition, Devanagari script).

Instructions:
1. Transcribe ALL Devanagari text exactly as printed
2. Preserve line breaks and verse structure
3. The page has two layers:
   - MBH verse text (larger Devanagari)
   - Nīlakaṇṭha's commentary (smaller Devanagari, word-by-word gloss)
4. Include verse numbers (॥ १ ॥ etc.) and chapter markers
5. Include dandas (।) and double dandas (॥) as printed
6. Use proper Unicode Devanagari — no romanization
7. If a word is unclear, give your best reading

Output ONLY the transcribed text, nothing else."""


def ocr_page_gemini(img_bytes, client, model_name, page_num, max_retries=3):
    """
    send a single page image to Gemini for OCR.
    returns: extracted text string
    """
    from google.genai import types

    for attempt in range(max_retries):
        try:
            r = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_text(text=OCR_PROMPT),
                    types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
                ]
            )
            return r.text.strip()
        except Exception as e:
            err = str(e)
            # rate limit: wait and retry
            if "429" in err or "quota" in err.lower() or "rate" in err.lower():
                wait = 20 * (attempt + 1)
                print(f"\n  rate limited on page {page_num}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"\n  error on page {page_num} (attempt {attempt+1}): {err}")
                if attempt == max_retries - 1:
                    return f"[OCR ERROR: {err}]"
                time.sleep(5)
    return "[OCR FAILED after retries]"


def preprocess_image(img, enhance_contrast=True):
    """optional image preprocessing for degraded scans."""
    if enhance_contrast:
        img = ImageEnhance.Contrast(img).enhance(1.3)
        img = img.filter(ImageFilter.SHARPEN)
    return img


def image_to_bytes(img, fmt="JPEG", quality=90):
    """convert PIL Image to bytes for API call."""
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()


def segment_commentary(page_text):
    """
    attempt to separate MBH verse text from Nilakantha commentary.
    heuristic segmentation -- perfect separation requires layout analysis.
    """
    verse_commentary_pairs = []
    segments = re.split(r'[।॥]{1,2}\s*\n', page_text)

    current_verse = None
    current_commentary = []

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        if len(seg) < 200 and current_verse is None:
            current_verse = seg
        elif current_verse:
            current_commentary.append(seg)
            if re.search(r'इति|॥\s*\d', seg):
                verse_commentary_pairs.append({
                    "verse_text": current_verse,
                    "commentary": " ".join(current_commentary)
                })
                current_verse = None
                current_commentary = []

    if current_verse and current_commentary:
        verse_commentary_pairs.append({
            "verse_text": current_verse,
            "commentary": " ".join(current_commentary)
        })

    return verse_commentary_pairs


def transliterate_to_hk(devanagari_text):
    """convert devanagari to Harvard-Kyoto for alignment with BORI corpus."""
    try:
        from indic_transliteration import sanscript
        from indic_transliteration.sanscript import transliterate
        return transliterate(devanagari_text, sanscript.DEVANAGARI, sanscript.HK)
    except ImportError:
        print("warning: indic-transliteration not installed. pip install indic-transliteration")
        return None
    except Exception as e:
        print(f"transliteration error: {e}")
        return None


def process_pdf(pdf_path, output_dir, parva_name,
                start_page=None, end_page=None,
                save_images=False, dpi=300, enhance=False,
                model_name="gemini-2.5-flash-lite"):
    """
    main pipeline: PDF -> images -> Gemini OCR -> structured output.
    """
    from google import genai

    # check API key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set.")
        print("Run: export GOOGLE_API_KEY='your-key'")
        return []

    client = genai.Client(api_key=api_key)

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"PDF: {pdf_path.name}")
    print(f"parva: {parva_name}")
    print(f"model: {model_name}")
    print(f"DPI: {dpi} | pages: {start_page or 1}-{end_page or 'end'}")
    print(f"output: {output_dir}")

    # process pages in batches to avoid loading entire PDF into memory
    BATCH_SIZE = 10
    first = start_page or 1
    last = end_page or 9999  # will be clamped by pdf2image

    results = []
    errors = []
    total_chars = 0
    skipped = 0

    page_num = first
    while page_num <= last:
        batch_end = min(page_num + BATCH_SIZE - 1, last)

        # check how many in this batch are already done
        batch_skip_count = 0
        for p in range(page_num, batch_end + 1):
            page_out = output_dir / "pages" / f"page_{p:04d}.txt"
            if page_out.exists() and page_out.stat().st_size > 100:
                batch_skip_count += 1
        if batch_skip_count == (batch_end - page_num + 1):
            skipped += batch_skip_count
            print(f"  batch {page_num}-{batch_end}: skipped (already done)")
            page_num = batch_end + 1
            continue

        # convert this batch of pages
        try:
            pages = convert_from_path(
                str(pdf_path), dpi=dpi, fmt="jpeg",
                jpegopt={"quality": 90},
                first_page=page_num, last_page=batch_end
            )
        except Exception as e:
            if "page" in str(e).lower() or "beyond" in str(e).lower():
                break  # past end of PDF
            raise

        print(f"\n  batch {page_num}-{batch_end}: converted {len(pages)} pages")

        for i, page_img in enumerate(pages):
            cur_page = page_num + i

            # skip pages already OCR'd
            page_out = output_dir / "pages" / f"page_{cur_page:04d}.txt"
            if page_out.exists() and page_out.stat().st_size > 100:
                skipped += 1
                continue

            if enhance:
                page_img = preprocess_image(page_img)

            img_bytes = image_to_bytes(page_img)

            if save_images:
                img_dir = output_dir / "page_images"
                img_dir.mkdir(exist_ok=True)
                img_path = img_dir / f"{parva_name}_{cur_page:04d}.jpg"
                with open(img_path, "wb") as f:
                    f.write(img_bytes)

            # OCR via Gemini
            text = ocr_page_gemini(img_bytes, client, model_name, cur_page)

            if text.startswith("[OCR"):
                errors.append({"page": cur_page, "error": text})
                print(f"  p{cur_page}: ERROR")
                continue

            # segment verse / commentary
            segments = segment_commentary(text)

            # transliterate to HK
            hk_text = transliterate_to_hk(text)

            char_count = len(text)
            total_chars += char_count

            result = {
                "page": cur_page,
                "parva": parva_name,
                "raw_devanagari": text,
                "hk_transliteration": hk_text,
                "segments": segments,
                "char_count": char_count
            }
            results.append(result)

            # save per-page text immediately (crash-safe)
            page_out = output_dir / "pages" / f"page_{cur_page:04d}.txt"
            page_out.parent.mkdir(exist_ok=True)
            with open(page_out, "w", encoding="utf-8") as f:
                f.write(f"=== PAGE {cur_page} | {parva_name} ===\n\n")
                f.write(text)
                if hk_text:
                    f.write(f"\n\n--- HK TRANSLITERATION ---\n{hk_text}")

            # progress
            print(f"  p{cur_page}: {char_count} chars | {len(segments)} segments")

            # respect rate limits: ~4 seconds between requests
            time.sleep(4)

        # free batch memory
        del pages
        page_num = batch_end + 1

    # save complete results JSON
    results_file = output_dir / f"{parva_name}_ocr_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # save concatenated clean devanagari
    clean_text_file = output_dir / f"{parva_name}_clean_devanagari.txt"
    with open(clean_text_file, "w", encoding="utf-8") as f:
        for r in results:
            f.write(f"\n\n{'='*60}\n")
            f.write(f"PAGE {r['page']}\n")
            f.write(f"{'='*60}\n\n")
            f.write(r["raw_devanagari"])

    # save concatenated HK
    hk_text_file = output_dir / f"{parva_name}_clean_hk.txt"
    with open(hk_text_file, "w", encoding="utf-8") as f:
        for r in results:
            if r.get("hk_transliteration"):
                f.write(f"\n\n=== PAGE {r['page']} ===\n\n")
                f.write(r["hk_transliteration"])

    # save error log
    if errors:
        with open(output_dir / f"{parva_name}_errors.json", "w") as f:
            json.dump(errors, f, indent=2)

    # summary
    avg_chars = total_chars // len(results) if results else 0

    print(f"\n{'='*60}")
    print(f"OCR COMPLETE -- {parva_name}")
    print(f"pages processed: {len(results)}")
    print(f"pages skipped (already done): {skipped}")
    print(f"errors: {len(errors)}")
    print(f"total characters: {total_chars:,}")
    print(f"avg chars/page: {avg_chars:,}")
    print(f"output: {output_dir}")
    print(f"{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Nilakantha OCR Pipeline (Gemini Vision)")
    parser.add_argument("--pdf", required=True, help="path to PDF file")
    parser.add_argument("--parva", required=True, help="parva name (e.g. shanti, aranyaka)")
    parser.add_argument("--output", default="/storage/mbh/nilakantha/ocr_clean/")
    parser.add_argument("--start", type=int, default=None, help="start page number")
    parser.add_argument("--end", type=int, default=None, help="end page number")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for image conversion")
    parser.add_argument("--save-images", action="store_true", help="keep page images")
    parser.add_argument("--enhance", action="store_true", help="contrast/sharpen preprocessing")
    parser.add_argument("--test", action="store_true", help="test mode: first 5 pages only")
    parser.add_argument("--model", default="gemini-2.5-flash-lite",
                        help="Gemini model (default: gemini-2.5-flash)")

    args = parser.parse_args()

    if args.test:
        args.start = args.start or 1
        args.end = (args.start or 1) + 4
        print(f"TEST MODE: pages {args.start}-{args.end}")

    process_pdf(
        pdf_path=args.pdf,
        output_dir=args.output,
        parva_name=args.parva,
        start_page=args.start,
        end_page=args.end,
        save_images=args.save_images,
        dpi=args.dpi,
        enhance=args.enhance,
        model_name=args.model
    )


if __name__ == "__main__":
    main()
