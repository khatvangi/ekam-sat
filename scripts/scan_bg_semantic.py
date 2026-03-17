#!/usr/bin/env python3
"""
BG Verse Semantic Echo Scanner — Option 2
==========================================
Uses sentence-transformer embeddings to find MBH verses semantically similar
to each of the 700 BG verses. Unlike term matching, this catches meaning-level
parallels even when vocabulary differs.

Requires: embeddings already built via semantic_search.py --mode build

Usage:
    python scan_bg_semantic.py --bg-dir ../data/bg_chapters/ \
                               --embeddings ../output/embeddings/ \
                               --output ../output/bg_semantic/
"""

import re
import json
import csv
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime


PARVAS = {
    "00": "Conventions", "01": "Adi", "02": "Sabha",
    "03": "Aranyaka", "04": "Virata", "05": "Udyoga",
    "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri",
    "12": "Shanti", "13": "Anushasana", "14": "Ashvamedha",
    "15": "Ashramavasika", "16": "Mausala",
    "17": "Mahaprasthanika", "18": "Svargarohana",
}

BG_CHAPTERS = set(range(23, 41))


def load_bg_verses(bg_dir):
    """Load BG verses grouped by base verse ID."""
    bg_path = Path(bg_dir)
    verses = []
    seen = set()

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

                base_id = verse_id[:8]
                chapter = int(verse_id[2:5])
                verse_num = int(verse_id[5:8])
                bg_ch = chapter - 22

                if base_id not in seen:
                    seen.add(base_id)
                    verses.append({
                        "verse_id": base_id,
                        "bg_ref": f"{bg_ch}.{verse_num}",
                        "bg_chapter": bg_ch,
                        "parts": [],
                        "full_text": "",
                    })

                verses[-1]["parts"].append(text)
                verses[-1]["full_text"] = " ".join(verses[-1]["parts"])

    return verses


def main():
    parser = argparse.ArgumentParser(description="BG Semantic Echo Scanner (Option 2)")
    parser.add_argument("--bg-dir", default="../data/bg_chapters/")
    parser.add_argument("--embeddings", default="../output/embeddings/", help="Dir with embeddings.npy and verse_ids.json")
    parser.add_argument("--output", default="../output/bg_semantic/")
    parser.add_argument("--top-k", type=int, default=30, help="Top matches per BG verse")
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    args = parser.parse_args()

    # load model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: pip install sentence-transformers")
        return

    # load MBH embeddings
    emb_dir = Path(args.embeddings)
    print("Loading MBH embeddings...")
    embeddings = np.load(emb_dir / "embeddings.npy")
    with open(emb_dir / "verse_ids.json") as f:
        verse_ids = json.load(f)

    if len(verse_ids) != len(embeddings):
        print(f"ERROR: embeddings ({len(embeddings)}) != verse_ids ({len(verse_ids)})")
        return

    # pre-normalize MBH embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    # build BG exclusion mask (parva 06, chapters 23-40)
    bg_mask = np.ones(len(verse_ids), dtype=bool)
    for i, vid in enumerate(verse_ids):
        if vid[:2] == "06":
            ch = int(vid[2:5])
            if ch in BG_CHAPTERS:
                bg_mask[i] = False

    non_bg_indices = np.where(bg_mask)[0]
    non_bg_embeddings = normalized[non_bg_indices]
    non_bg_ids = [verse_ids[i] for i in non_bg_indices]

    print(f"MBH embeddings: {len(verse_ids)} total, {len(non_bg_ids)} non-BG")

    # load BG verses
    bg_verses = load_bg_verses(args.bg_dir)
    print(f"BG verses: {len(bg_verses)}")

    # encode all BG verses at once
    print(f"Loading model: {args.model}")
    model = SentenceTransformer(args.model)

    bg_texts = [v["full_text"] for v in bg_verses]
    print("Encoding BG verses...")
    bg_embeddings = model.encode(bg_texts, show_progress_bar=True, batch_size=64)

    # normalize BG embeddings
    bg_norms = np.linalg.norm(bg_embeddings, axis=1, keepdims=True)
    bg_norms[bg_norms == 0] = 1
    bg_normalized = bg_embeddings / bg_norms

    # compute similarity matrix: (700 BG) x (non-BG MBH)
    print("Computing similarity matrix...")
    sim_matrix = bg_normalized @ non_bg_embeddings.T

    # extract top-k for each BG verse
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = []
    verse_summary = []

    print(f"Extracting top-{args.top_k} matches per verse...")

    for i, bg in enumerate(bg_verses):
        sims = sim_matrix[i]
        top_idx = np.argsort(sims)[::-1][:args.top_k]

        matches = []
        for idx in top_idx:
            vid = non_bg_ids[idx]
            score = float(sims[idx])
            if score < 0.1:
                break
            matches.append({
                "bg_ref": bg["bg_ref"],
                "bg_verse_id": bg["verse_id"],
                "bg_chapter": bg["bg_chapter"],
                "bg_text": bg["full_text"][:150],
                "mbh_verse_id": vid,
                "parva_num": vid[:2],
                "parva_name": PARVAS.get(vid[:2], "?"),
                "chapter": int(vid[2:5]),
                "similarity": round(score, 4),
            })

        all_results.extend(matches)

        # summary
        parva_dist = defaultdict(int)
        for m in matches:
            parva_dist[m["parva_num"]] += 1

        verse_summary.append({
            "bg_ref": bg["bg_ref"],
            "verse_id": bg["verse_id"],
            "bg_chapter": bg["bg_chapter"],
            "match_count": len(matches),
            "top_sim": matches[0]["similarity"] if matches else 0,
            "top_match_id": matches[0]["mbh_verse_id"] if matches else "",
            "top_parva": max(parva_dist, key=parva_dist.get) if parva_dist else "",
        })

        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(bg_verses)} done")

    # ─── save outputs ─────────────────────────────────────────────────────

    # 1. echo CSV
    fields = ["bg_ref", "bg_verse_id", "bg_chapter", "mbh_verse_id",
              "parva_num", "parva_name", "chapter", "similarity", "bg_text"]

    with open(output_dir / "bg_semantic_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)

    # 2. summary CSV
    with open(output_dir / "bg_semantic_summary.csv", "w", newline="", encoding="utf-8") as f:
        fields2 = ["bg_ref", "verse_id", "bg_chapter", "match_count", "top_sim", "top_match_id", "top_parva"]
        writer = csv.DictWriter(f, fieldnames=fields2)
        writer.writeheader()
        writer.writerows(verse_summary)

    # 3. summary JSON
    with open(output_dir / "bg_semantic_summary.json", "w", encoding="utf-8") as f:
        json.dump(verse_summary, f, ensure_ascii=False, indent=2)

    # 4. report
    parva_totals = defaultdict(int)
    for r in all_results:
        parva_totals[r["parva_num"]] += 1

    high_sim = [r for r in all_results if r["similarity"] >= 0.7]

    lines = [
        "=" * 70,
        "EKAM SAT — BG SEMANTIC ECHO SCAN (Option 2)",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Model: {args.model.split('/')[-1]}",
        "=" * 70,
        "",
        f"BG verses encoded: {len(bg_verses)}",
        f"MBH verses searched: {len(non_bg_ids)}",
        f"Total matches (sim > 0.1): {len(all_results)}",
        f"High similarity (>= 0.7): {len(high_sim)}",
        f"Top-k per verse: {args.top_k}",
        "",
        "-" * 70,
        "SEMANTIC ECHO DENSITY BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "?")
        bar = "#" * min(count // 10, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>6}  {bar}")

    # top BG verses by highest similarity
    top_sim_verses = sorted(verse_summary, key=lambda x: x["top_sim"], reverse=True)[:20]
    lines += [
        "",
        "-" * 70,
        "TOP 20 BG VERSES BY HIGHEST SEMANTIC SIMILARITY",
        "-" * 70,
    ]
    for s in top_sim_verses:
        lines.append(f"  BG {s['bg_ref']:>6} | sim={s['top_sim']:.4f} | match: {s['top_match_id']} (P{s['top_parva']})")

    # high-similarity pairs
    high_sim_sorted = sorted(high_sim, key=lambda x: x["similarity"], reverse=True)[:30]
    lines += [
        "",
        "-" * 70,
        f"TOP 30 HIGH-SIMILARITY PAIRS (>= 0.7) — {len(high_sim)} total",
        "-" * 70,
    ]
    for r in high_sim_sorted:
        lines.append(f"  BG {r['bg_ref']:>6} ↔ {r['mbh_verse_id']} (P{r['parva_num']} {r['parva_name']}) sim={r['similarity']:.4f}")

    # lowest similarity top matches (BG verses least like anything in MBH)
    bottom = sorted(verse_summary, key=lambda x: x["top_sim"])[:15]
    lines += [
        "",
        "-" * 70,
        "15 BG VERSES MOST SEMANTICALLY UNIQUE (lowest top-match similarity)",
        "-" * 70,
    ]
    for s in bottom:
        lines.append(f"  BG {s['bg_ref']:>6} | best sim={s['top_sim']:.4f}")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "bg_semantic_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:35]))
    print(f"\nFull report: {output_dir / 'bg_semantic_report.txt'}")
    print(f"Done. {len(all_results)} semantic echoes.")


if __name__ == "__main__":
    main()
