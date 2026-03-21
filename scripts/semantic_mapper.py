#!/usr/bin/env python3
"""
Semantic Mapper — Ekam Sat Project
===================================
Scores BORI corpus passages against meaning families from node_semantics.yaml.
Falls back to term-only scoring for nodes not yet in the semantic YAML.

Scoring formula:
  SemanticScore(node, passage) =
    1.0 * direct_match          (any direct_hk expression found as substring)
  + 0.8 * paraphrase_match      (any paraphrase_hk found)
  + 0.6 * inferential_match     (placeholder — always 0)
  + 0.5 * required_feature_fraction (term-density proxy)
  + 0.2 * context_support       (placeholder — 0)
  - 1.0 * exclusion_trigger     (placeholder — 0)

  Normalized to [0, 1].

Usage:
  python semantic_mapper.py \\
    --nodes ../data/node_semantics.yaml \\
    --bg-nodes ../data/bg_nodes_v2.json \\
    --corpus ../bori/hk \\
    --bg-dir ../data/bg_chapters/ \\
    --output ../output/semantic_map/
"""

import os
import re
import json
import argparse
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install with: pip install pyyaml")
    raise


# ── parva metadata ──────────────────────────────────────────────────────────
PARVAS = {
    "00": "Conventions",
    "01": "Adi",
    "02": "Sabha",
    "03": "Aranyaka",
    "04": "Virata",
    "05": "Udyoga",
    "06": "Bhishma",
    "07": "Drona",
    "08": "Karna",
    "09": "Shalya",
    "10": "Sauptika",
    "11": "Stri",
    "12": "Shanti",
    "13": "Anushasana",
    "14": "Ashvamedha",
    "15": "Ashramavasika",
    "16": "Mausala",
    "17": "Mahaprasthanika",
    "18": "Svargarohana",
}

# BG is parva 06, chapters 23-40 in BORI (BG ch1 = 06.023, ch18 = 06.040)
BG_CHAPTERS_IN_BHISHMA = set(range(23, 41))

# maximum possible raw score: 1.0 + 0.8 + 0.6 + 0.5 + 0.2 = 3.1
# (exclusion can subtract, but we cap at 0 before normalizing)
MAX_RAW_SCORE = 3.1


# ── corpus loading ──────────────────────────────────────────────────────────

def parse_verse_id(verse_id):
    """
    Parse BORI verse ID: PPcccvvvx
    e.g. 05067005a -> parva=05, chapter=067, verse=005, half=a
    """
    if len(verse_id) < 8:
        return None
    parva = verse_id[0:2]
    chapter = verse_id[2:5]
    verse = verse_id[5:8]
    half = verse_id[8] if len(verse_id) > 8 else ""
    return {
        "parva": parva,
        "chapter": int(chapter),
        "verse": int(verse),
        "half": half,
        "raw": verse_id,
    }


def is_bg_verse(parsed):
    """Check if a parsed verse falls inside BG (parva 06, chapters 23-40)."""
    if parsed and parsed["parva"] == "06":
        if parsed["chapter"] in BG_CHAPTERS_IN_BHISHMA:
            return True
    return False


def load_corpus(corpus_dir):
    """
    Load all HK files from corpus directory.
    Returns dict: {verse_id: verse_text}
    Lines are expected as: PPcccvvvx <text>
    """
    print(f"loading corpus from: {corpus_dir}")
    corpus = {}
    corpus_path = Path(corpus_dir)

    found_files = sorted([f for f in corpus_path.iterdir() if f.is_file()])
    if not found_files:
        print(f"ERROR: no files found in {corpus_dir}")
        return corpus

    print(f"  found {len(found_files)} files")

    for filepath in found_files:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                # match verse ID at start: 8+ digits optionally followed by [a-e]
                m = re.match(r'^(\d{2}\d{3}\d{3}[a-e]?)\s+(.*)', line)
                if m:
                    vid = m.group(1)
                    text = m.group(2)
                    corpus[vid] = text

    print(f"  loaded {len(corpus)} half-verses")
    return corpus


def load_bg_verses(bg_dir):
    """
    Load BG chapter files from data/bg_chapters/.
    Returns dict: {verse_id: verse_text}
    Same format as corpus files.
    """
    print(f"loading BG verses from: {bg_dir}")
    bg = {}
    bg_path = Path(bg_dir)

    for filepath in sorted(bg_path.glob("bg_ch*.txt")):
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                m = re.match(r'^(\d{2}\d{3}\d{3}[a-e]?)\s+(.*)', line)
                if m:
                    bg[m.group(1)] = m.group(2)

    print(f"  loaded {len(bg)} BG half-verses")
    return bg


# ── node loading ────────────────────────────────────────────────────────────

def load_semantic_nodes(yaml_path):
    """
    Load node_semantics.yaml.
    Returns dict: {node_id: node_dict}
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = {}
    for n in data.get("nodes", []):
        nodes[n["id"]] = n
    print(f"loaded {len(nodes)} semantic nodes from YAML")
    return nodes


def load_bg_nodes(json_path):
    """
    Load bg_nodes_v2.json for fallback term lists.
    Returns dict: {node_id: node_dict}
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = {}
    for n in data.get("nodes", []):
        nodes[n["id"]] = n
    print(f"loaded {len(nodes)} BG nodes from JSON")
    return nodes


def build_unified_node_list(sem_nodes, bg_nodes):
    """
    Build a unified list of scoring profiles.
    Nodes in sem_nodes get full semantic scoring.
    Nodes only in bg_nodes get term-only fallback scoring.
    Returns list of dicts with standardized fields.
    """
    unified = []

    # all node IDs from both sources
    all_ids = sorted(set(list(sem_nodes.keys()) + list(bg_nodes.keys())))

    for nid in all_ids:
        entry = {"id": nid, "has_semantics": False}

        if nid in sem_nodes:
            sn = sem_nodes[nid]
            entry["has_semantics"] = True
            entry["label"] = sn.get("short_label", nid)
            ef = sn.get("expression_families", {})
            entry["direct_hk"] = ef.get("direct_hk", [])
            entry["paraphrase_hk"] = ef.get("paraphrase_hk", [])

            # gather hk_terms and core_hk from bg_nodes if available
            if nid in bg_nodes:
                bn = bg_nodes[nid]
                entry["hk_terms"] = bn.get("hk_terms", [])
                entry["core_hk"] = bn.get("core_hk", [])
            else:
                # no bg_nodes entry — use direct + paraphrase terms as proxy
                entry["hk_terms"] = entry["direct_hk"] + entry["paraphrase_hk"]
                entry["core_hk"] = entry["direct_hk"]

        elif nid in bg_nodes:
            # fallback: term-only scoring
            bn = bg_nodes[nid]
            entry["label"] = bn.get("name", nid)
            entry["hk_terms"] = bn.get("hk_terms", [])
            entry["core_hk"] = bn.get("core_hk", [])
            entry["direct_hk"] = []
            entry["paraphrase_hk"] = []

        unified.append(entry)

    print(f"unified node list: {len(unified)} nodes "
          f"({sum(1 for u in unified if u['has_semantics'])} with semantic profiles)")
    return unified


# ── scoring ─────────────────────────────────────────────────────────────────

def score_verse(node, text):
    """
    Compute semantic score for a single verse against a node.
    Returns (score, matched_direct, matched_paraphrase) or None if score < threshold.

    HK is CASE SENSITIVE — no re.IGNORECASE.
    """
    # -- direct match: 1.0 if any direct_hk expression found as substring
    matched_direct = []
    for expr in node.get("direct_hk", []):
        if expr in text:
            matched_direct.append(expr)
    direct_match = 1.0 if matched_direct else 0.0

    # -- paraphrase match: 0.8 if any paraphrase_hk found as substring
    matched_paraphrase = []
    for expr in node.get("paraphrase_hk", []):
        if expr in text:
            matched_paraphrase.append(expr)
    paraphrase_match = 1.0 if matched_paraphrase else 0.0

    # -- inferential match: placeholder, always 0
    inferential_match = 0.0

    # -- required feature fraction: term-density proxy
    # count how many of the node's hk_terms + core_hk appear in the verse
    all_terms = list(set(node.get("hk_terms", []) + node.get("core_hk", [])))
    if all_terms:
        hits = sum(1 for t in all_terms if t in text)
        feature_fraction = hits / len(all_terms)
    else:
        feature_fraction = 0.0

    # -- context support: placeholder, 0
    context_support = 0.0

    # -- exclusion trigger: placeholder, 0
    exclusion_trigger = 0.0

    # -- weighted sum
    raw = (1.0 * direct_match
           + 0.8 * paraphrase_match
           + 0.6 * inferential_match
           + 0.5 * feature_fraction
           + 0.2 * context_support
           - 1.0 * exclusion_trigger)

    # clamp to [0, MAX_RAW_SCORE] then normalize
    raw = max(0.0, raw)
    score = min(raw / MAX_RAW_SCORE, 1.0)

    return score, matched_direct, matched_paraphrase


def classify_strength(score):
    """Classify score into strength bucket."""
    if score >= 0.85:
        return "strong"
    elif score >= 0.60:
        return "moderate"
    elif score >= 0.35:
        return "weak"
    else:
        return None  # skip


# ── main pipeline ───────────────────────────────────────────────────────────

def run_scan(unified_nodes, corpus, bg_verses, output_dir):
    """
    Score every node against every corpus verse (excluding BG) and BG verses.
    Write results to CSV files and a human-readable report.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_hits = []       # for semantic_hits.csv
    node_stats = {}     # for node_density.csv

    total_nodes = len(unified_nodes)

    for idx, node in enumerate(unified_nodes, 1):
        nid = node["id"]
        label = node["label"]
        print(f"  [{idx}/{total_nodes}] {nid} — {label[:50]}")

        bg_scores = []
        outside_scores = []
        parvas_hit = set()

        # -- score corpus verses (excluding BG)
        for vid, text in corpus.items():
            parsed = parse_verse_id(vid)
            if not parsed:
                continue
            if is_bg_verse(parsed):
                continue

            score, md, mp = score_verse(node, text)
            strength = classify_strength(score)
            if strength is None:
                continue

            outside_scores.append(score)
            parvas_hit.add(parsed["parva"])

            all_hits.append({
                "node_id": nid,
                "node_label": label,
                "verse_id": vid,
                "parva_num": parsed["parva"],
                "parva_name": PARVAS.get(parsed["parva"], "Unknown"),
                "chapter": parsed["chapter"],
                "score": round(score, 4),
                "strength": strength,
                "matched_direct": "|".join(md),
                "matched_paraphrase": "|".join(mp),
                "in_bg": 0,
            })

        # -- score BG verses
        for vid, text in bg_verses.items():
            score, md, mp = score_verse(node, text)
            strength = classify_strength(score)
            if strength is None:
                continue

            bg_scores.append(score)
            parsed = parse_verse_id(vid)

            all_hits.append({
                "node_id": nid,
                "node_label": label,
                "verse_id": vid,
                "parva_num": "06",
                "parva_name": "Bhishma (BG)",
                "chapter": parsed["chapter"] if parsed else 0,
                "score": round(score, 4),
                "strength": strength,
                "matched_direct": "|".join(md),
                "matched_paraphrase": "|".join(mp),
                "in_bg": 1,
            })

        # -- compute density stats for this node
        bg_density = sum(bg_scores) / len(bg_scores) if bg_scores else 0.0
        outside_density = sum(outside_scores) / len(outside_scores) if outside_scores else 0.0

        node_stats[nid] = {
            "node_id": nid,
            "label": label,
            "bg_density": round(bg_density, 4),
            "outside_density": round(outside_density, 4),
            "bg_hit_count": len(bg_scores),
            "outside_hit_count": len(outside_scores),
            "parva_spread": len(parvas_hit),
            "speaker_spread_placeholder": 0,
        }

        outside_strong = sum(1 for s in outside_scores if s >= 0.85 * MAX_RAW_SCORE / MAX_RAW_SCORE)
        # simpler: count by strength
        out_strong = sum(1 for h in all_hits if h["node_id"] == nid and h["in_bg"] == 0 and h["strength"] == "strong")
        print(f"         bg={len(bg_scores)} outside={len(outside_scores)} "
              f"(strong={out_strong}) parvas={len(parvas_hit)}")

    # -- write semantic_hits.csv
    hits_path = output_dir / "semantic_hits.csv"
    fieldnames = ["node_id", "node_label", "verse_id", "parva_num", "parva_name",
                  "chapter", "score", "strength", "matched_direct", "matched_paraphrase", "in_bg"]

    with open(hits_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        # sort by score descending
        for row in sorted(all_hits, key=lambda x: x["score"], reverse=True):
            writer.writerow(row)

    print(f"\nwrote {len(all_hits)} hits to {hits_path}")

    # -- write node_density.csv
    density_path = output_dir / "node_density.csv"
    density_fields = ["node_id", "label", "bg_density", "outside_density",
                      "bg_hit_count", "outside_hit_count", "parva_spread",
                      "speaker_spread_placeholder"]

    with open(density_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=density_fields)
        writer.writeheader()
        for nid in sorted(node_stats.keys()):
            writer.writerow(node_stats[nid])

    print(f"wrote {len(node_stats)} node densities to {density_path}")

    # -- write human-readable report
    report_path = output_dir / "semantic_report.txt"
    write_report(all_hits, node_stats, unified_nodes, report_path)

    return all_hits, node_stats


def write_report(all_hits, node_stats, unified_nodes, report_path):
    """Generate a human-readable summary report."""
    total = len(all_hits)
    outside_hits = [h for h in all_hits if h["in_bg"] == 0]
    bg_hits = [h for h in all_hits if h["in_bg"] == 1]
    strong = [h for h in outside_hits if h["strength"] == "strong"]
    moderate = [h for h in outside_hits if h["strength"] == "moderate"]
    weak = [h for h in outside_hits if h["strength"] == "weak"]

    # parva distribution (outside BG only)
    parva_counts = defaultdict(int)
    for h in outside_hits:
        parva_counts[h["parva_num"]] += 1

    # nodes with semantics vs fallback
    sem_count = sum(1 for n in unified_nodes if n["has_semantics"])
    fallback_count = len(unified_nodes) - sem_count

    lines = [
        "=" * 70,
        "EKAM SAT PROJECT -- SEMANTIC MAPPER REPORT",
        f"generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"total hits (score >= 0.35):     {total}",
        f"  outside BG:                   {len(outside_hits)}",
        f"  inside BG:                    {len(bg_hits)}",
        "",
        f"outside-BG breakdown:",
        f"  strong  (>= 0.85):            {len(strong)}",
        f"  moderate (0.60-0.84):         {len(moderate)}",
        f"  weak    (0.35-0.59):          {len(weak)}",
        "",
        f"nodes scanned:                  {len(unified_nodes)}",
        f"  with semantic profiles:       {sem_count}",
        f"  term-only fallback:           {fallback_count}",
        "",
        "-" * 70,
        "OUTSIDE-BG HITS BY PARVA",
        "-" * 70,
    ]

    for pnum, count in sorted(parva_counts.items(), key=lambda x: x[1], reverse=True):
        pname = PARVAS.get(pnum, "Unknown")
        bar = "#" * min(count // 20, 50)
        lines.append(f"  P{pnum} {pname:<20} {count:>6}  {bar}")

    # top nodes by outside hit count
    lines += [
        "",
        "-" * 70,
        "TOP 20 NODES BY OUTSIDE-BG HIT COUNT",
        "-" * 70,
    ]

    sorted_nodes = sorted(node_stats.values(),
                          key=lambda x: x["outside_hit_count"], reverse=True)
    for ns in sorted_nodes[:20]:
        lines.append(
            f"  [{ns['node_id']}] {ns['label']:<40} "
            f"outside={ns['outside_hit_count']:>5}  bg={ns['bg_hit_count']:>3}  "
            f"parvas={ns['parva_spread']:>2}  "
            f"density(out)={ns['outside_density']:.3f}"
        )

    # nodes with highest bg density (top 10)
    lines += [
        "",
        "-" * 70,
        "TOP 10 NODES BY BG DENSITY (mean score within BG)",
        "-" * 70,
    ]

    by_bg_density = sorted(node_stats.values(),
                           key=lambda x: x["bg_density"], reverse=True)
    for ns in by_bg_density[:10]:
        lines.append(
            f"  [{ns['node_id']}] {ns['label']:<40} "
            f"bg_density={ns['bg_density']:.3f}  outside_density={ns['outside_density']:.3f}"
        )

    # sample strong hits
    lines += [
        "",
        "-" * 70,
        "SAMPLE STRONG HITS (first 20, outside BG)",
        "-" * 70,
    ]

    for h in strong[:20]:
        lines.append(
            f"  [{h['node_id']}] {h['node_label']}"
        )
        lines.append(
            f"  verse={h['verse_id']}  parva={h['parva_name']}  "
            f"ch={h['chapter']}  score={h['score']:.3f}"
        )
        if h["matched_direct"]:
            lines.append(f"    direct: {h['matched_direct']}")
        if h["matched_paraphrase"]:
            lines.append(f"    paraphrase: {h['matched_paraphrase']}")
        lines.append("")

    lines += ["=" * 70, "END OF REPORT", "=" * 70]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"wrote report to {report_path}")
    # also print summary to console
    for line in lines[:30]:
        print(line)


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Semantic Mapper -- score MBH passages against meaning families"
    )
    parser.add_argument("--nodes", required=True,
                        help="path to node_semantics.yaml")
    parser.add_argument("--bg-nodes", required=True,
                        help="path to bg_nodes_v2.json (fallback term lists)")
    parser.add_argument("--corpus", required=True,
                        help="path to BORI HK corpus directory")
    parser.add_argument("--bg-dir", required=True,
                        help="path to BG chapter files directory")
    parser.add_argument("--output", default="../output/semantic_map/",
                        help="output directory")

    args = parser.parse_args()

    # load semantic profiles from YAML
    sem_nodes = load_semantic_nodes(args.nodes)

    # load fallback term lists from JSON
    bg_nodes = load_bg_nodes(args.bg_nodes)

    # build unified scoring list
    unified = build_unified_node_list(sem_nodes, bg_nodes)

    # load BORI corpus (all parvas, BG exclusion happens during scoring)
    corpus = load_corpus(args.corpus)
    if not corpus:
        print("ERROR: corpus empty. check --corpus path.")
        return

    # load BG verses separately for BG density computation
    bg_verses = load_bg_verses(args.bg_dir)
    if not bg_verses:
        print("WARNING: no BG verses loaded. BG density will be 0.")

    # run the scan
    print(f"\nscoring {len(unified)} nodes against "
          f"{len(corpus)} corpus verses + {len(bg_verses)} BG verses...")
    run_scan(unified, corpus, bg_verses, args.output)

    print("\ndone.")


if __name__ == "__main__":
    main()
