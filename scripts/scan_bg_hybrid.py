#!/usr/bin/env python3
"""
BG Hybrid Echo Scanner — Option 3
===================================
Combines term overlap (Option 1) with semantic similarity (Option 2) to produce
a unified ranking. Candidate MBH verses are pulled from term matches, then
scored by semantic similarity for meaning-level confirmation.

Also introduces: English query mode. Since MiniLM is multilingual, we can
search using English paraphrases of BG teachings to find meaning-level echoes
that transcend vocabulary.

Usage:
    # hybrid merge of options 1 and 2
    python scan_bg_hybrid.py --term-echoes ../output/bg_verses/bg_verse_echoes.csv \
                             --sem-echoes ../output/bg_semantic/bg_semantic_echoes.csv \
                             --output ../output/bg_hybrid/

    # english meaning queries (requires embeddings)
    python scan_bg_hybrid.py --mode english \
                             --embeddings ../output/embeddings/ \
                             --output ../output/bg_english/
"""

import csv
import json
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

# english meaning summaries of BG teachings — grouped by doctrine
# these are what the model understands best (multilingual training was on English-aligned data)
BG_ENGLISH_QUERIES = {
    # chapter 2 core teachings
    "2.20_atman_eternal": "The soul is never born and never dies. It is eternal, ancient, and indestructible. When the body is destroyed, the soul is not destroyed.",
    "2.47_nishkama_karma": "You have the right to perform your duty but not to claim the fruits of your action. Do not be motivated by the results of action, nor be attached to inaction.",
    "2.55_sthitaprajna": "When a person abandons all desires of the mind and is content in the self alone, that person is called one of steady wisdom.",
    "2.62_desire_chain": "Contemplating sense objects creates attachment. From attachment comes desire. From desire comes anger. From anger comes delusion.",

    # chapter 3 karma yoga
    "3.19_detached_action": "Perform your duty without attachment, for by working without attachment one attains the Supreme.",
    "3.27_prakriti_acts": "All actions are performed by the qualities of material nature. The self deluded by ego thinks 'I am the doer.'",
    "3.35_svadharma": "It is better to perform one's own duty imperfectly than to perform another's duty perfectly. Death in one's own duty is better.",

    # chapter 4 jnana yoga
    "4.7_avatar_doctrine": "Whenever righteousness declines and unrighteousness rises, I manifest myself on earth to protect the good and destroy evil.",
    "4.18_action_inaction": "One who sees inaction in action and action in inaction is wise among humans.",
    "4.33_jnana_yajna": "The sacrifice of knowledge is superior to all material sacrifices, for all actions culminate in knowledge.",

    # chapter 5-6 renunciation and meditation
    "5.18_equal_vision": "The wise see the same reality in a learned brahmin, a cow, an elephant, a dog, and an outcaste.",
    "6.29_sarva_bhuta": "The person united in yoga sees the self in all beings and all beings in the self, seeing equally everywhere.",
    "6.47_bhakti_supreme": "Among all yogis, the one who worships me with faith and devotion, with the inner self absorbed in me, is the most united.",

    # chapter 7-9 divine knowledge
    "7.7_string_of_pearls": "There is nothing higher than me. Everything is strung on me like pearls on a thread.",
    "9.22_yoga_kshema": "To those who worship me with devotion, meditating on my transcendental form, I carry what they lack and preserve what they have.",
    "9.29_equal_to_all": "I am equally disposed to all living beings. There is no one hateful or dear to me. But those who worship me with devotion are in me, and I am in them.",

    # chapter 10-11 divine manifestation
    "10.20_self_in_heart": "I am the Self seated in the hearts of all beings. I am the beginning, the middle, and the end of all beings.",
    "11.32_kala_death": "I am Time, the great destroyer of worlds, and I have come here to destroy all people.",

    # chapter 12-13 devotion and field/knower
    "12.13_devotee_qualities": "One who has no hatred toward any being, who is friendly and compassionate, free from possessiveness and ego, equal in pleasure and pain, forgiving.",
    "13.27_seeing_god_everywhere": "One who sees the supreme lord dwelling equally in all beings, the imperishable in the perishable — that person truly sees.",

    # chapter 14-15 gunas and supreme person
    "14.5_three_gunas": "Sattva, rajas, and tamas — these three qualities born of material nature bind the embodied self in the body.",
    "15.15_in_all_hearts": "I am seated in the hearts of all beings. From me come memory, knowledge, and their loss.",

    # chapter 16-17 divine and demonic natures
    "16.1_divine_qualities": "Fearlessness, purity of heart, steadfastness in knowledge and yoga, charity, self-control, sacrifice, study, austerity, uprightness.",
    "17.3_faith_determines": "The faith of each person corresponds to their nature. A person is made of their faith. Whatever their faith is, that is what they become.",

    # chapter 18 liberation
    "18.20_sattvic_knowledge": "Knowledge by which one sees the one imperishable reality in all beings, undivided in the divided — that is sattvic knowledge.",
    "18.61_lord_in_heart": "The lord dwells in the hearts of all beings, causing them to revolve as if mounted on a machine, by the power of illusion.",
    "18.66_final_teaching": "Abandon all varieties of dharma and simply surrender unto me. I shall deliver you from all sins. Do not grieve.",
    "18.78_wherever_krishna": "Wherever there is Krishna, the lord of yoga, and wherever there is Arjuna, the archer, there will be prosperity, victory, happiness, and firm morality.",
}


def merge_hybrid(term_csv, sem_csv, output_dir):
    """Merge term-match and semantic results into unified ranking."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load term echoes
    print("Loading term echoes...")
    term_echoes = defaultdict(dict)  # {(bg_ref, mbh_id): {data}}
    with open(term_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = (row["bg_ref"], row["mbh_verse_id"])
            term_echoes[key] = {
                "bg_ref": row["bg_ref"],
                "mbh_verse_id": row["mbh_verse_id"],
                "parva_num": row["parva_num"],
                "parva_name": row.get("parva_name", ""),
                "term_match_count": int(row.get("match_count", 0)),
                "term_coverage": float(row.get("coverage", 0)),
                "matched_terms": row.get("matched_terms", ""),
                "bg_text": row.get("bg_text", ""),
                "mbh_text": row.get("mbh_text", ""),
            }

    # load semantic echoes — normalize to base verse ID (strip half-verse marker)
    print("Loading semantic echoes...")
    sem_echoes = defaultdict(dict)
    with open(sem_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            mbh_id = row["mbh_verse_id"][:8]  # strip half-verse a/b/c/d/e
            key = (row["bg_ref"], mbh_id)
            # keep highest similarity per base verse
            existing_sim = sem_echoes.get(key, {}).get("similarity", 0)
            new_sim = float(row.get("similarity", 0))
            if new_sim > existing_sim:
                sem_echoes[key] = {
                    "similarity": new_sim,
                }

    # merge: all pairs that appear in either set
    all_keys = set(term_echoes.keys()) | set(sem_echoes.keys())
    print(f"Term-only pairs: {len(term_echoes)}")
    print(f"Semantic-only pairs: {len(sem_echoes)}")
    print(f"Union: {len(all_keys)}")

    merged = []
    both_count = 0

    for key in all_keys:
        bg_ref, mbh_id = key
        t = term_echoes.get(key, {})
        s = sem_echoes.get(key, {})

        term_coverage = t.get("term_coverage", 0)
        similarity = s.get("similarity", 0)

        # hybrid score: weighted combination
        # term coverage and semantic similarity complement each other
        # both on 0-1 scale
        hybrid_score = 0.4 * term_coverage + 0.6 * similarity

        has_both = bool(t) and bool(s)
        if has_both:
            both_count += 1

        merged.append({
            "bg_ref": bg_ref,
            "mbh_verse_id": mbh_id,
            "parva_num": t.get("parva_num", mbh_id[:2]),
            "parva_name": t.get("parva_name", PARVAS.get(mbh_id[:2], "?")),
            "term_coverage": round(term_coverage, 3),
            "similarity": round(similarity, 4),
            "hybrid_score": round(hybrid_score, 4),
            "evidence": "both" if has_both else ("term" if t else "semantic"),
            "term_match_count": t.get("term_match_count", 0),
            "matched_terms": t.get("matched_terms", ""),
            "bg_text": t.get("bg_text", ""),
            "mbh_text": t.get("mbh_text", ""),
        })

    # sort by hybrid score
    merged.sort(key=lambda x: x["hybrid_score"], reverse=True)

    print(f"Pairs with BOTH term + semantic evidence: {both_count}")

    # ─── save ──────────────────────────────────────────────────────────────

    fields = ["bg_ref", "mbh_verse_id", "parva_num", "parva_name",
              "hybrid_score", "term_coverage", "similarity", "evidence",
              "term_match_count", "matched_terms", "bg_text", "mbh_text"]

    with open(output_dir / "bg_hybrid_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(merged)

    # per-verse summary
    verse_stats = defaultdict(lambda: {"total": 0, "both": 0, "term_only": 0,
                                        "sem_only": 0, "top_hybrid": 0})
    for r in merged:
        bg = r["bg_ref"]
        verse_stats[bg]["total"] += 1
        verse_stats[bg]["top_hybrid"] = max(verse_stats[bg]["top_hybrid"], r["hybrid_score"])
        if r["evidence"] == "both":
            verse_stats[bg]["both"] += 1
        elif r["evidence"] == "term":
            verse_stats[bg]["term_only"] += 1
        else:
            verse_stats[bg]["sem_only"] += 1

    # report
    parva_totals = defaultdict(int)
    for r in merged:
        parva_totals[r["parva_num"]] += 1

    high_hybrid = [r for r in merged if r["hybrid_score"] >= 0.5]
    both_evidence = [r for r in merged if r["evidence"] == "both"]

    lines = [
        "=" * 70,
        "EKAM SAT — HYBRID ECHO ANALYSIS (Option 3)",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"Total echo pairs: {len(merged)}",
        f"  Term-only: {sum(1 for r in merged if r['evidence'] == 'term')}",
        f"  Semantic-only: {sum(1 for r in merged if r['evidence'] == 'semantic')}",
        f"  Both (strongest): {both_count}",
        f"High hybrid score (>= 0.5): {len(high_hybrid)}",
        "",
        "-" * 70,
        "HYBRID ECHO DENSITY BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "?")
        bar = "#" * min(count // 20, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>6}  {bar}")

    # top 30 strongest hybrid echoes
    lines += [
        "",
        "-" * 70,
        "TOP 30 STRONGEST HYBRID ECHOES (term + semantic convergence)",
        "-" * 70,
    ]
    for r in merged[:30]:
        lines.append(
            f"  BG {r['bg_ref']:>6} ↔ {r['mbh_verse_id']} "
            f"(P{r['parva_num']}) H={r['hybrid_score']:.3f} "
            f"[T={r['term_coverage']:.2f} S={r['similarity']:.3f} {r['evidence']}]"
        )

    # "both" evidence pairs sorted by hybrid
    both_sorted = sorted(both_evidence, key=lambda x: x["hybrid_score"], reverse=True)
    lines += [
        "",
        "-" * 70,
        f"TOP 20 'BOTH EVIDENCE' PAIRS (term match + semantic confirmation) — {len(both_evidence)} total",
        "-" * 70,
    ]
    for r in both_sorted[:20]:
        lines.append(
            f"  BG {r['bg_ref']:>6} ↔ {r['mbh_verse_id']} "
            f"(P{r['parva_num']} {r['parva_name']}) "
            f"H={r['hybrid_score']:.3f} terms={r['matched_terms'][:60]}"
        )

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "bg_hybrid_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:40]))
    print(f"\nReport: {output_dir / 'bg_hybrid_report.txt'}")
    print(f"Done. {len(merged)} hybrid echoes.")


def english_queries(embeddings_dir, output_dir, top_k=30, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    """Search MBH corpus using English meaning queries."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: pip install sentence-transformers")
        return

    emb_dir = Path(embeddings_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load embeddings
    print("Loading MBH embeddings...")
    embeddings = np.load(emb_dir / "embeddings.npy")
    with open(emb_dir / "verse_ids.json") as f:
        verse_ids = json.load(f)

    # normalize
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms

    # BG exclusion mask
    bg_mask = np.ones(len(verse_ids), dtype=bool)
    for i, vid in enumerate(verse_ids):
        if vid[:2] == "06" and int(vid[2:5]) in BG_CHAPTERS:
            bg_mask[i] = False
    non_bg_idx = np.where(bg_mask)[0]
    non_bg_emb = normalized[non_bg_idx]
    non_bg_ids = [verse_ids[i] for i in non_bg_idx]

    # load model and encode queries
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)

    queries = list(BG_ENGLISH_QUERIES.items())
    query_texts = [q[1] for q in queries]
    query_keys = [q[0] for q in queries]

    print(f"Encoding {len(queries)} English queries...")
    query_embs = model.encode(query_texts, batch_size=32)
    q_norms = np.linalg.norm(query_embs, axis=1, keepdims=True)
    q_norms[q_norms == 0] = 1
    query_normalized = query_embs / q_norms

    # similarity
    print("Computing similarities...")
    sim_matrix = query_normalized @ non_bg_emb.T

    all_results = []

    for i, (key, text) in enumerate(queries):
        sims = sim_matrix[i]
        top_idx = np.argsort(sims)[::-1][:top_k]

        for idx in top_idx:
            vid = non_bg_ids[idx]
            score = float(sims[idx])
            if score < 0.15:
                break
            all_results.append({
                "query_key": key,
                "query_text": text[:120],
                "mbh_verse_id": vid,
                "parva_num": vid[:2],
                "parva_name": PARVAS.get(vid[:2], "?"),
                "similarity": round(score, 4),
            })

    # save
    fields = ["query_key", "mbh_verse_id", "parva_num", "parva_name",
              "similarity", "query_text"]

    with open(output_dir / "bg_english_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(all_results)

    # report
    parva_totals = defaultdict(int)
    for r in all_results:
        parva_totals[r["parva_num"]] += 1

    lines = [
        "=" * 70,
        "EKAM SAT — ENGLISH MEANING QUERY RESULTS",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Model: {model_name.split('/')[-1]}",
        "=" * 70,
        "",
        f"Queries: {len(queries)}",
        f"Total matches (sim > 0.15): {len(all_results)}",
        "",
        "-" * 70,
        "MATCHES BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "?")
        bar = "#" * min(count // 5, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>5}  {bar}")

    # top matches per query
    lines += [
        "",
        "-" * 70,
        "TOP 3 MATCHES PER ENGLISH QUERY",
        "-" * 70,
    ]

    for key, text in queries:
        matches = [r for r in all_results if r["query_key"] == key]
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        lines.append(f"\n  [{key}] {text[:80]}...")
        for m in matches[:3]:
            lines.append(f"    → {m['mbh_verse_id']} (P{m['parva_num']} {m['parva_name']}) sim={m['similarity']:.4f}")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "bg_english_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:35]))
    print(f"\nReport: {output_dir / 'bg_english_report.txt'}")
    print(f"Done. {len(all_results)} English-query echoes.")


def main():
    parser = argparse.ArgumentParser(description="BG Hybrid Echo Scanner (Option 3)")
    parser.add_argument("--mode", choices=["hybrid", "english", "both"], default="both")
    parser.add_argument("--term-echoes", default="../output/bg_verses/bg_verse_echoes.csv")
    parser.add_argument("--sem-echoes", default="../output/bg_semantic/bg_semantic_echoes.csv")
    parser.add_argument("--embeddings", default="../output/embeddings/")
    parser.add_argument("--output", default="../output/bg_hybrid/")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

    args = parser.parse_args()

    if args.mode in ("hybrid", "both"):
        merge_hybrid(args.term_echoes, args.sem_echoes, args.output)

    if args.mode in ("english", "both"):
        english_queries(args.embeddings, Path(args.output) / "english", args.top_k, args.model)


if __name__ == "__main__":
    main()
