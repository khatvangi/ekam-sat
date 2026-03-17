#!/usr/bin/env python3
"""
BG Verse-Level Echo Scanner — Ekam Sat Project
================================================
Scans the entire MBH corpus for echoes of EACH individual BG verse (all 700).
Unlike scan_corpus.py (which uses curated node term clusters), this extracts
content words directly from the BG text and searches for co-occurrence.

This answers: "for every single verse in the Gita, where else in the
Mahabharata do we hear the same language?"

Usage:
    python scan_bg_verses.py --corpus /storage/mbh/bori/hk \
                             --bg-dir ../data/bg_chapters/ \
                             --output ../output/bg_verses/

    # require 3+ content words matching (stricter)
    python scan_bg_verses.py --corpus /storage/mbh/bori/hk \
                             --bg-dir ../data/bg_chapters/ \
                             --output ../output/bg_verses/ \
                             --min-matches 3
"""

import os
import re
import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ─── BORI metadata ───────────────────────────────────────────────────────────
PARVAS = {
    "00": "Conventions", "01": "Adi", "02": "Sabha",
    "03": "Aranyaka", "04": "Virata", "05": "Udyoga",
    "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri",
    "12": "Shanti", "13": "Anushasana", "14": "Ashvamedha",
    "15": "Ashramavasika", "16": "Mausala",
    "17": "Mahaprasthanika", "18": "Svargarohana",
}

# BG = Bhishmaparva chapters 23-40
BG_CHAPTERS = set(range(23, 41))

# sanskrit particles, pronouns, vocatives — no doctrinal content
# these appear frequently but tell us nothing about WHAT is being taught
STOPWORDS = {
    # particles and conjunctions
    "ca", "na", "tu", "hi", "eva", "api", "iti", "vA", "hy", "tv",
    "tathA", "atha", "ataH", "tataH", "tato", "tasmAd", "tasmAt",
    "yathA", "kiM", "kathaM", "kutas", "caiva", "cApi", "athavA",
    "yadA", "tadA", "yatra", "tatra", "sarvatra", "evaM", "etad",
    # pronouns and demonstratives
    "sa", "te", "me", "aham", "ahaM", "tat", "tad", "yat", "yad",
    "yo", "ye", "yaH", "ayaM", "idaM", "asau", "iyaM", "etat",
    "tasya", "tena", "taM", "tvam", "tvaM", "mama", "mayA",
    "asya", "atra", "iha", "etAn", "etAni", "etena",
    # vocatives (speaker addresses, not content)
    "pArtha", "kaunteya", "arjuna", "bhArata", "mahAbAho",
    "anagha", "kurunandana", "bhArata", "dhanaJjaya",
    "guDAkeza", "paramtapa", "kuru", "bharatarSabha",
    "bharatasattama", "tAta", "rAjan", "mune",
    # speaker formulae
    "uvAca", "zrIbhagavAn", "saMjaya",
    # common verbs of saying/seeing (grammatical, not doctrinal)
    "abravIt", "proktaM", "procyate", "viddhi", "manyase",
    "ucyate", "ucyante", "pazyati", "cintaya",
    # very short words (< 3 chars are usually sandhi fragments)
    "'pi", "ity",
}

# minimum word length to consider (after stopword filter)
MIN_WORD_LEN = 3


def load_bg_verses(bg_dir):
    """
    Load all BG verses from chapter files.
    Returns list of {verse_id, bg_chapter, bg_verse, text, half}
    """
    bg_path = Path(bg_dir)
    verses = []
    seen_ids = set()

    for filepath in sorted(bg_path.glob("bg_ch*.txt")):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                m = re.match(r'^(\d{8}[a-e]?)\s+(.*)', line)
                if not m:
                    continue

                verse_id = m.group(1)
                text = m.group(2).strip()
                if not text:
                    continue

                # parse verse ID
                parva = verse_id[0:2]
                chapter = int(verse_id[2:5])
                verse_num = int(verse_id[5:8])
                half = verse_id[8] if len(verse_id) > 8 else ""

                # BG chapter = BORI chapter - 22
                bg_ch = chapter - 22

                # group by base verse ID (without half-verse marker)
                base_id = verse_id[:8]
                if base_id not in seen_ids:
                    seen_ids.add(base_id)
                    verses.append({
                        "verse_id": base_id,
                        "bg_ref": f"{bg_ch}.{verse_num}",
                        "bg_chapter": bg_ch,
                        "bg_verse": verse_num,
                        "half_verses": [],
                        "full_text": "",
                    })

                # append half-verse text
                verses[-1]["half_verses"].append(text)
                verses[-1]["full_text"] = " ".join(verses[-1]["half_verses"])

    print(f"Loaded {len(verses)} BG verses from {bg_dir}")
    return verses


def extract_content_words(text):
    """
    Extract content words from HK text.
    Filters stopwords and short words. Returns list of unique content words.
    """
    words = text.split()
    content = []
    seen = set()

    for w in words:
        # strip trailing punctuation
        w = w.rstrip(".,;:!?|")
        if not w:
            continue
        if len(w) < MIN_WORD_LEN:
            continue
        if w in STOPWORDS:
            continue
        if w.lower() in STOPWORDS:
            continue
        if w not in seen:
            content.append(w)
            seen.add(w)

    return content


def load_corpus(corpus_dir):
    """Load MBH corpus, excluding BG chapters."""
    print(f"Loading corpus from: {corpus_dir}")
    corpus = {}
    corpus_path = Path(corpus_dir)

    files = [f for f in corpus_path.iterdir() if f.is_file()]
    if not files:
        print("ERROR: No files found")
        return corpus

    for filepath in sorted(files):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                m = re.match(r'^(\d{8}[a-e]?)\s+(.*)', line)
                if not m:
                    continue

                verse_id = m.group(1)
                text = m.group(2).strip()
                if not text:
                    continue

                # exclude BG itself
                parva = verse_id[0:2]
                chapter = int(verse_id[2:5])
                if parva == "06" and chapter in BG_CHAPTERS:
                    continue

                # group by base verse ID
                base_id = verse_id[:8]
                if base_id in corpus:
                    corpus[base_id] += " " + text
                else:
                    corpus[base_id] = text

    print(f"Loaded {len(corpus)} MBH verses (BG excluded)")
    return corpus


def search_verse_echoes(bg_verse, corpus, min_matches=2):
    """
    Search corpus for echoes of a single BG verse.
    Returns matches where min_matches or more content words co-occur.
    """
    content_words = extract_content_words(bg_verse["full_text"])

    if len(content_words) < 2:
        return [], content_words

    results = []

    for mbh_id, mbh_text in corpus.items():
        matched = []
        for w in content_words:
            # use word boundary-ish matching: the term appears as substring
            # (Sanskrit compounds mean terms often appear within larger words)
            if w in mbh_text:
                matched.append(w)

        if len(matched) >= min_matches:
            coverage = len(matched) / len(content_words)
            results.append({
                "mbh_verse_id": mbh_id,
                "parva_num": mbh_id[0:2],
                "parva_name": PARVAS.get(mbh_id[0:2], "?"),
                "chapter": int(mbh_id[2:5]),
                "matched_terms": matched,
                "match_count": len(matched),
                "total_content_words": len(content_words),
                "coverage": round(coverage, 3),
                "mbh_text": mbh_text[:200],
            })

    # sort by coverage descending
    results.sort(key=lambda x: x["coverage"], reverse=True)
    return results, content_words


def main():
    parser = argparse.ArgumentParser(description="BG Verse-Level Echo Scanner")
    parser.add_argument("--corpus", required=True, help="Path to BORI HK corpus")
    parser.add_argument("--bg-dir", default="../data/bg_chapters/", help="BG chapter files directory")
    parser.add_argument("--output", default="../output/bg_verses/", help="Output directory")
    parser.add_argument("--min-matches", type=int, default=2, help="Minimum content word matches (default 2)")
    parser.add_argument("--min-coverage", type=float, default=0.0, help="Minimum coverage ratio (0.0-1.0)")

    args = parser.parse_args()

    # load data
    bg_verses = load_bg_verses(args.bg_dir)
    corpus = load_corpus(args.corpus)

    if not bg_verses or not corpus:
        print("ERROR: missing data")
        return

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # scan each BG verse
    print(f"\nScanning {len(bg_verses)} BG verses against {len(corpus)} MBH verses...")
    print(f"Min matches: {args.min_matches} | Min coverage: {args.min_coverage}")

    all_results = []
    verse_summary = []
    no_content_verses = []

    for i, bg in enumerate(bg_verses):
        results, content_words = search_verse_echoes(bg, corpus, args.min_matches)

        # filter by coverage
        if args.min_coverage > 0:
            results = [r for r in results if r["coverage"] >= args.min_coverage]

        if len(content_words) < 2:
            no_content_verses.append(bg["bg_ref"])

        # per-verse summary
        parva_dist = defaultdict(int)
        for r in results:
            parva_dist[r["parva_num"]] += 1

        summary = {
            "bg_ref": bg["bg_ref"],
            "verse_id": bg["verse_id"],
            "bg_chapter": bg["bg_chapter"],
            "content_words": content_words,
            "content_word_count": len(content_words),
            "total_echoes": len(results),
            "top_parva": max(parva_dist, key=parva_dist.get) if parva_dist else "",
            "top_parva_count": max(parva_dist.values()) if parva_dist else 0,
        }
        verse_summary.append(summary)

        # add bg_ref to each result for the flat CSV
        for r in results:
            r["bg_ref"] = bg["bg_ref"]
            r["bg_verse_id"] = bg["verse_id"]
            r["bg_chapter"] = bg["bg_chapter"]
            r["bg_text"] = bg["full_text"][:150]
            r["content_words_searched"] = "|".join(content_words)
        all_results.extend(results)

        # progress
        if (i + 1) % 50 == 0 or i == len(bg_verses) - 1:
            print(f"  {i+1}/{len(bg_verses)} verses scanned | {len(all_results)} echoes so far")

    # ─── save outputs ────────────────────────────────────────────────────────

    # 1. flat echo results CSV
    echo_fields = ["bg_ref", "bg_verse_id", "bg_chapter", "mbh_verse_id",
                   "parva_num", "parva_name", "chapter", "match_count",
                   "total_content_words", "coverage", "matched_terms",
                   "content_words_searched", "bg_text", "mbh_text"]

    with open(output_dir / "bg_verse_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=echo_fields)
        writer.writeheader()
        for r in all_results:
            row = {k: r.get(k, "") for k in echo_fields}
            row["matched_terms"] = "|".join(r.get("matched_terms", []))
            writer.writerow(row)

    # 2. per-verse summary CSV
    summary_fields = ["bg_ref", "verse_id", "bg_chapter", "content_word_count",
                      "total_echoes", "top_parva", "top_parva_count", "content_words"]

    with open(output_dir / "bg_verse_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        for s in verse_summary:
            row = {k: s.get(k, "") for k in summary_fields}
            row["content_words"] = "|".join(s.get("content_words", []))
            writer.writerow(row)

    # 3. per-verse summary JSON (richer, for downstream processing)
    with open(output_dir / "bg_verse_summary.json", "w", encoding="utf-8") as f:
        json.dump(verse_summary, f, ensure_ascii=False, indent=2)

    # 4. report
    total_echoes = len(all_results)
    verses_with_echoes = sum(1 for s in verse_summary if s["total_echoes"] > 0)
    high_coverage = [r for r in all_results if r["coverage"] >= 0.5]

    # parva distribution across all echoes
    parva_totals = defaultdict(int)
    for r in all_results:
        parva_totals[r["parva_num"]] += 1

    lines = [
        "=" * 70,
        "EKAM SAT — BG VERSE-LEVEL ECHO SCAN",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"BG verses scanned: {len(bg_verses)}",
        f"BG verses with echoes: {verses_with_echoes} ({100*verses_with_echoes/len(bg_verses):.1f}%)",
        f"BG verses with <2 content words: {len(no_content_verses)}",
        f"Total echoes found: {total_echoes}",
        f"High-coverage echoes (50%+): {len(high_coverage)}",
        f"Min matches required: {args.min_matches}",
        "",
        "-" * 70,
        "ECHO DENSITY BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "?")
        bar = "#" * min(count // 20, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>6}  {bar}")

    # top echoed BG verses
    top_verses = sorted(verse_summary, key=lambda x: x["total_echoes"], reverse=True)[:20]
    lines += [
        "",
        "-" * 70,
        "TOP 20 MOST-ECHOED BG VERSES",
        "-" * 70,
    ]
    for s in top_verses:
        lines.append(f"  BG {s['bg_ref']:>6} | {s['total_echoes']:>5} echoes | "
                     f"words: {', '.join(s['content_words'][:6])}")

    # least echoed (non-zero)
    bottom = [s for s in verse_summary if s["total_echoes"] > 0]
    bottom.sort(key=lambda x: x["total_echoes"])
    lines += [
        "",
        "-" * 70,
        "BOTTOM 10 LEAST-ECHOED BG VERSES (with at least 1 echo)",
        "-" * 70,
    ]
    for s in bottom[:10]:
        lines.append(f"  BG {s['bg_ref']:>6} | {s['total_echoes']:>5} echoes | "
                     f"words: {', '.join(s['content_words'][:6])}")

    # verses with zero echoes
    zero = [s for s in verse_summary if s["total_echoes"] == 0]
    lines += [
        "",
        "-" * 70,
        f"BG VERSES WITH ZERO ECHOES ({len(zero)})",
        "-" * 70,
    ]
    for s in zero:
        cw = ", ".join(s["content_words"]) if s["content_words"] else "(no content words)"
        lines.append(f"  BG {s['bg_ref']:>6} | words: {cw}")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    report_path = output_dir / "bg_verse_echo_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # print summary to console
    print("\n" + "\n".join(lines[:40]))
    print(f"\nFull report: {report_path}")
    print(f"Echo CSV: {output_dir / 'bg_verse_echoes.csv'}")
    print(f"Summary CSV: {output_dir / 'bg_verse_summary.csv'}")
    print(f"Done. {total_echoes} echoes across {verses_with_echoes}/{len(bg_verses)} BG verses.")


if __name__ == "__main__":
    main()
