#!/usr/bin/env python3
"""
Meaning Sweep — Ekam Sat Project
==================================
Tests whether each of 123 BG teachings resonates across the MBH by meaning,
not vocabulary. Uses each node's English proposition as a semantic query
against the full MBH corpus via multilingual embeddings.

This answers the core question: does Krishna's teaching echo in the words
of other sages — not the same words, but the same meaning?

Usage:
    python meaning_sweep.py \
        --nodes ../data/bg_nodes_v2.json \
        --embeddings ../output/embeddings/ \
        --output ../output/meaning_sweep/
"""

import json
import csv
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict
from datetime import datetime


PARVAS = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}

BG_CHAPTERS = set(range(23, 41))


def main():
    parser = argparse.ArgumentParser(description="Meaning Sweep — all 123 nodes")
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--embeddings", required=True)
    parser.add_argument("--output", default="../output/meaning_sweep/")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--min-sim", type=float, default=0.25,
                        help="minimum similarity to report")
    parser.add_argument("--model",
                        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load nodes
    with open(args.nodes) as f:
        nodes = json.load(f)["nodes"]
    print(f"Loaded {len(nodes)} nodes")

    # load embeddings
    emb_dir = Path(args.embeddings)
    print("Loading MBH embeddings...")
    embeddings = np.load(emb_dir / "embeddings.npy")
    with open(emb_dir / "verse_ids.json") as f:
        verse_ids = json.load(f)

    if len(verse_ids) != len(embeddings):
        print(f"ERROR: mismatch {len(embeddings)} embeddings vs {len(verse_ids)} verse IDs")
        return

    # pre-normalize MBH embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    # build BG exclusion mask
    bg_mask = np.ones(len(verse_ids), dtype=bool)
    for i, vid in enumerate(verse_ids):
        if vid[:2] == "06":
            ch = int(vid[2:5])
            if ch in BG_CHAPTERS:
                bg_mask[i] = False

    non_bg_idx = np.where(bg_mask)[0]
    non_bg_emb = normalized[non_bg_idx]
    non_bg_ids = [verse_ids[i] for i in non_bg_idx]
    print(f"MBH: {len(verse_ids)} total, {len(non_bg_ids)} non-BG")

    # load model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: pip install sentence-transformers")
        return

    print(f"Loading model: {args.model}")
    model = SentenceTransformer(args.model)

    # build English meaning queries from propositions
    queries = []
    for node in nodes:
        proposition = node.get("proposition", "")
        if not proposition:
            continue

        # use the proposition directly — it's already an English meaning statement
        # also add the echo_hypothesis if present, for richer context
        echo_hyp = node.get("echo_hypothesis", "")
        query_text = proposition
        if echo_hyp:
            query_text += " " + echo_hyp

        queries.append({
            "node_id": node["id"],
            "node_name": node["name"],
            "query": query_text[:500],  # cap length for model
        })

    print(f"Queries: {len(queries)}")

    # encode all queries at once
    print("Encoding queries...")
    query_texts = [q["query"] for q in queries]
    query_embs = model.encode(query_texts, batch_size=32, show_progress_bar=True)
    q_norms = np.linalg.norm(query_embs, axis=1, keepdims=True)
    q_norms[q_norms == 0] = 1
    query_normalized = query_embs / q_norms

    # compute similarity matrix: (123 queries) x (non-BG MBH)
    print("Computing similarity matrix...")
    sim_matrix = query_normalized @ non_bg_emb.T

    # extract results
    all_hits = []
    node_summaries = []

    print(f"Extracting top-{args.top_k} per node (min similarity {args.min_sim})...")

    for i, q in enumerate(queries):
        sims = sim_matrix[i]
        top_idx = np.argsort(sims)[::-1][:args.top_k]

        hits = []
        parva_set = set()
        for idx in top_idx:
            score = float(sims[idx])
            if score < args.min_sim:
                break
            vid = non_bg_ids[idx]
            parva = vid[:2]
            parva_set.add(parva)
            hit = {
                "node_id": q["node_id"],
                "node_name": q["node_name"],
                "mbh_verse_id": vid,
                "parva_num": parva,
                "parva_name": PARVAS.get(parva, "?"),
                "similarity": round(score, 4),
            }
            hits.append(hit)
            all_hits.append(hit)

        # summary for this node
        if hits:
            top_sim = hits[0]["similarity"]
            mean_sim = np.mean([h["similarity"] for h in hits])
        else:
            top_sim = 0
            mean_sim = 0

        node_summaries.append({
            "node_id": q["node_id"],
            "node_name": q["node_name"],
            "hit_count": len(hits),
            "top_similarity": round(top_sim, 4),
            "mean_similarity": round(mean_sim, 4),
            "parva_spread": len(parva_set),
            "top_parva": hits[0]["parva_name"] if hits else "",
            "top_verse": hits[0]["mbh_verse_id"] if hits else "",
        })

        if (i + 1) % 20 == 0:
            print(f"  {i+1}/{len(queries)} nodes done")

    # ─── parva distribution across all meaning echoes ─────────────────
    parva_totals = defaultdict(int)
    for h in all_hits:
        parva_totals[h["parva_num"]] += 1

    # ─── save outputs ─────────────────────────────────────────────────

    # 1. all hits CSV
    hit_fields = ["node_id", "node_name", "mbh_verse_id", "parva_num",
                  "parva_name", "similarity"]
    with open(output_dir / "meaning_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=hit_fields)
        writer.writeheader()
        writer.writerows(all_hits)

    # 2. node summary CSV
    summary_fields = ["node_id", "node_name", "hit_count", "top_similarity",
                      "mean_similarity", "parva_spread", "top_parva", "top_verse"]
    with open(output_dir / "node_meaning_summary.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=summary_fields)
        writer.writeheader()
        writer.writerows(node_summaries)

    # 3. report
    nodes_with_hits = sum(1 for s in node_summaries if s["hit_count"] > 0)
    high_sim_hits = [h for h in all_hits if h["similarity"] >= 0.5]

    lines = [
        "=" * 70,
        "EKAM SAT — MEANING SWEEP: DO KRISHNA'S TEACHINGS",
        "RESONATE ACROSS THE MAHABHARATA?",
        f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"model: {args.model.split('/')[-1]}",
        "=" * 70,
        "",
        f"nodes queried (by English meaning): {len(queries)}",
        f"nodes with meaning echoes:          {nodes_with_hits} "
        f"({100*nodes_with_hits/len(queries):.1f}%)",
        f"total meaning echoes:               {len(all_hits)}",
        f"high-similarity (>= 0.5):           {len(high_sim_hits)}",
        f"minimum similarity threshold:       {args.min_sim}",
        "",
        "-" * 70,
        "MEANING ECHO DENSITY BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "?")
        bar = "#" * min(count // 5, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>5}  {bar}")

    # top nodes by meaning resonance
    by_top_sim = sorted(node_summaries, key=lambda x: x["top_similarity"], reverse=True)
    lines += [
        "",
        "-" * 70,
        "TOP 30 TEACHINGS BY STRONGEST MEANING ECHO",
        "-" * 70,
    ]
    for s in by_top_sim[:30]:
        lines.append(
            f"  [{s['node_id']}] {s['node_name'][:45]:<45} "
            f"sim={s['top_similarity']:.3f} hits={s['hit_count']:>3} "
            f"parvas={s['parva_spread']:>2}"
        )

    # nodes with weakest meaning resonance
    by_lowest = sorted(node_summaries, key=lambda x: x["top_similarity"])
    lines += [
        "",
        "-" * 70,
        "BOTTOM 15 — TEACHINGS WITH WEAKEST MEANING RESONANCE",
        "(these may be unique to the Gita's formulation)",
        "-" * 70,
    ]
    for s in by_lowest[:15]:
        lines.append(
            f"  [{s['node_id']}] {s['node_name'][:50]:<50} "
            f"sim={s['top_similarity']:.3f}"
        )

    # sample high-similarity pairs
    high_sorted = sorted(all_hits, key=lambda x: x["similarity"], reverse=True)
    lines += [
        "",
        "-" * 70,
        "TOP 20 STRONGEST MEANING ECHOES (node ↔ MBH verse)",
        "-" * 70,
    ]
    for h in high_sorted[:20]:
        lines.append(
            f"  [{h['node_id']}] {h['node_name'][:40]:<40} "
            f"↔ {h['mbh_verse_id']} (P{h['parva_num']} {h['parva_name']}) "
            f"sim={h['similarity']:.4f}"
        )

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "meaning_sweep_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:50]))
    print(f"\nFull report: {output_dir / 'meaning_sweep_report.txt'}")
    print(f"Done. {len(all_hits)} meaning echoes across {nodes_with_hits}/{len(queries)} nodes.")


if __name__ == "__main__":
    main()
