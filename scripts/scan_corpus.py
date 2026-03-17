#!/usr/bin/env python3
"""
MBH Corpus Scanner — Ekam Sat Project
======================================
Scans the BORI Critical Edition (Harvard-Kyoto format) for echoes of BG nodes.
Output: indexed database of every significant echo with BORI citation.

Usage:
    python scan_corpus.py --corpus /storage/mbh/bori/hk --output ../output/
    python scan_corpus.py --corpus /storage/mbh/bori/hk --node N03 --output ../output/
    python scan_corpus.py --corpus /storage/mbh/bori/hk --freq-map --output ../output/
"""

import os
import re
import json
import argparse
import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ─── BORI Parva metadata ──────────────────────────────────────────────────────
PARVAS = {
    "00": "Conventions",
    "01": "Adi",
    "02": "Sabha",
    "03": "Aranyaka (Vanaparva)",
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

# BG is Parva 06, chapters 23-40 in BORI (BG ch1=06.023, ch18=06.040)
# chapters 41-42 are post-BG narrative — should be searched for echoes
BG_CHAPTERS_IN_BHISHMA = set(range(23, 41))


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
    return {"parva": parva, "chapter": int(chapter), "verse": int(verse), "half": half, "raw": verse_id}


def is_bg_verse(parsed):
    """Exclude the BG itself (Bhishmaparva ch 23-40) from echo search."""
    if parsed and parsed["parva"] == "06":
        if parsed["chapter"] in BG_CHAPTERS_IN_BHISHMA:
            return True
    return False


def load_corpus(corpus_dir):
    """
    Load all HK files from corpus directory.
    Returns dict: {verse_id: verse_text}
    Expected file format per line: <verse_id><whitespace><text>
    or files named by parva containing lines with verse IDs.
    """
    print(f"Loading corpus from: {corpus_dir}")
    corpus = {}
    corpus_path = Path(corpus_dir)
    
    # Try multiple file patterns
    patterns = ["*.hk", "*.txt", "*.roman", "*"]
    found_files = []
    
    for pattern in patterns:
        files = list(corpus_path.glob(pattern))
        if files:
            found_files = [f for f in files if f.is_file()]
            break
    
    if not found_files:
        print(f"ERROR: No files found in {corpus_dir}")
        print("Expected Harvard-Kyoto .hk or .txt files")
        return corpus
    
    print(f"Found {len(found_files)} files")
    
    for filepath in sorted(found_files):
        print(f"  Reading: {filepath.name}")
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
            
            current_id = None
            current_text_parts = []
            
            for line in lines:
                line = line.rstrip()
                if not line:
                    continue
                
                # Try to detect verse ID at start of line: PPcccvvvx format
                # Pattern: starts with 2 digits, then 3 digits, then 3 digits, then optional letter
                m = re.match(r'^(\d{2}\d{3}\d{3}[a-e]?)\s*(.*)', line)
                if m:
                    # Save previous verse
                    if current_id and current_text_parts:
                        corpus[current_id] = " ".join(current_text_parts).strip()
                    current_id = m.group(1)
                    current_text_parts = [m.group(2)] if m.group(2) else []
                else:
                    # Continuation line
                    if current_id:
                        current_text_parts.append(line.strip())
            
            # Don't forget last verse
            if current_id and current_text_parts:
                corpus[current_id] = " ".join(current_text_parts).strip()
                
        except Exception as e:
            print(f"  ERROR reading {filepath}: {e}")
    
    print(f"Loaded {len(corpus)} verses total")
    return corpus


def search_node(corpus, node, exclude_bg=True):
    """
    Search corpus for a given BG node using its HK terms.
    Returns list of matches with context.
    """
    results = []
    
    # Build regex patterns from node terms
    all_terms = node.get("hk_terms", []) + node.get("core_hk", [])
    # Deduplicate
    all_terms = list(set(all_terms))
    
    # Build regex: word-boundary aware search for each term
    patterns = []
    for term in all_terms:
        # Escape special chars, allow for sandhi variations
        escaped = re.escape(term)
        patterns.append(escaped)
    
    combined_pattern = "|".join(patterns)
    if not combined_pattern:
        return results
    
    try:
        regex = re.compile(combined_pattern)
    except re.error as e:
        print(f"  Regex error for node {node['id']}: {e}")
        return results
    
    for verse_id, text in corpus.items():
        parsed = parse_verse_id(verse_id)
        if not parsed:
            continue
        if exclude_bg and is_bg_verse(parsed):
            continue
        
        matches = regex.findall(text)
        if matches:
            # Score by number of distinct core terms matched
            core_terms = node.get("core_hk", [])
            core_matches = [t for t in core_terms if re.search(re.escape(t), text)]
            
            results.append({
                "verse_id": verse_id,
                "parva_num": parsed["parva"],
                "parva_name": PARVAS.get(parsed["parva"], "Unknown"),
                "chapter": parsed["chapter"],
                "verse": parsed["verse"],
                "half": parsed["half"],
                "text": text,
                "matched_terms": list(set(matches)),
                "core_matches": core_matches,
                "match_strength": len(core_matches),
                "node_id": node["id"],
                "node_name": node["name"],
            })
    
    # Sort by match strength descending
    results.sort(key=lambda x: x["match_strength"], reverse=True)
    return results


def build_frequency_map(corpus, nodes, exclude_bg=True):
    """
    For each node, count hits per parva. Produces a heat map matrix.
    Returns: {node_id: {parva_num: count}}
    """
    freq_map = defaultdict(lambda: defaultdict(int))
    
    for node in nodes:
        print(f"  Scanning: [{node['id']}] {node['name']}")
        results = search_node(corpus, node, exclude_bg)
        for r in results:
            freq_map[node["id"]][r["parva_num"]] += 1
    
    return freq_map


def save_results_csv(all_results, output_path):
    """Save all echo results to CSV."""
    if not all_results:
        print("No results to save.")
        return
    
    fieldnames = ["node_id", "node_name", "verse_id", "parva_num", "parva_name",
                  "chapter", "verse", "half", "match_strength", "matched_terms", "text"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_results:
            row = {k: r.get(k, "") for k in fieldnames}
            row["matched_terms"] = "|".join(r.get("matched_terms", []))
            writer.writerow(row)
    
    print(f"Saved {len(all_results)} results to {output_path}")


def save_frequency_map(freq_map, nodes, output_path):
    """Save frequency heat map as CSV."""
    parva_nums = [f"{i:02d}" for i in range(0, 19)]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ["node_id", "node_name"] + [f"P{p}_{PARVAS.get(p,'?')[:8]}" for p in parva_nums]
        writer.writerow(header)
        
        for node in nodes:
            row = [node["id"], node["name"]]
            for p in parva_nums:
                row.append(freq_map[node["id"]].get(p, 0))
            writer.writerow(row)
    
    print(f"Saved frequency map to {output_path}")


def generate_report(all_results, freq_map, nodes, output_path):
    """Generate a human-readable summary report."""
    total = len(all_results)
    
    # Top parvas by echo count
    parva_totals = defaultdict(int)
    for r in all_results:
        parva_totals[r["parva_num"]] += 1
    
    # Top nodes
    node_totals = defaultdict(int)
    for r in all_results:
        node_totals[r["node_id"]] += 1
    
    # Strong echoes (core_matches >= 2)
    strong = [r for r in all_results if r["match_strength"] >= 2]
    
    lines = [
        "=" * 70,
        "EKAM SAT PROJECT — MBH CORPUS SCAN REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"Total verse-level echoes found: {total}",
        f"Strong echoes (2+ core terms): {len(strong)}",
        f"Nodes scanned: {len(nodes)}",
        "",
        "─" * 70,
        "ECHO DENSITY BY PARVA (all nodes combined)",
        "─" * 70,
    ]
    
    for parva_num, count in sorted(parva_totals.items(), key=lambda x: x[1], reverse=True):
        parva_name = PARVAS.get(parva_num, "Unknown")
        bar = "█" * min(count // 10, 50)
        lines.append(f"  P{parva_num} {parva_name:<20} {count:>5}  {bar}")
    
    lines += [
        "",
        "─" * 70,
        "TOP NODES BY ECHO COUNT",
        "─" * 70,
    ]
    
    node_map = {n["id"]: n["name"] for n in nodes}
    for node_id, count in sorted(node_totals.items(), key=lambda x: x[1], reverse=True)[:15]:
        lines.append(f"  [{node_id}] {node_map.get(node_id, '?'):<45} {count:>4} echoes")
    
    lines += [
        "",
        "─" * 70,
        "STRONG ECHOES SAMPLE (first 20, strength >= 2)",
        "─" * 70,
    ]
    
    for r in strong[:20]:
        lines.append(f"\n  [{r['node_id']}] {r['node_name']}")
        lines.append(f"  BORI: {r['verse_id']} | {r['parva_name']} {r['chapter']}.{r['verse']}")
        lines.append(f"  Terms: {', '.join(r['matched_terms'])}")
        # Truncate long text
        text_preview = r['text'][:120] + "..." if len(r['text']) > 120 else r['text']
        lines.append(f"  Text: {text_preview}")
    
    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Report saved to {output_path}")
    # Also print to console
    print("\n".join(lines[:40]))


def main():
    parser = argparse.ArgumentParser(description="MBH Corpus Scanner — Ekam Sat Project")
    parser.add_argument("--corpus", required=True, help="Path to BORI HK corpus directory")
    parser.add_argument("--nodes", default="../data/bg_nodes.json", help="Path to BG nodes JSON")
    parser.add_argument("--output", default="../output/", help="Output directory")
    parser.add_argument("--node", default=None, help="Scan only one node ID (e.g. N03)")
    parser.add_argument("--freq-map", action="store_true", help="Build frequency heat map")
    parser.add_argument("--include-bg", action="store_true", help="Include BG verses in search")
    parser.add_argument("--min-strength", type=int, default=1, help="Min core term matches to report")
    
    args = parser.parse_args()
    
    # Load nodes
    with open(args.nodes, "r", encoding="utf-8") as f:
        node_data = json.load(f)
    nodes = node_data["nodes"]
    
    if args.node:
        nodes = [n for n in nodes if n["id"] == args.node]
        if not nodes:
            print(f"Node {args.node} not found.")
            return
    
    # Load corpus
    corpus = load_corpus(args.corpus)
    if not corpus:
        print("Corpus empty or not found. Check --corpus path.")
        return
    
    exclude_bg = not args.include_bg
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.freq_map:
        print("\nBuilding frequency heat map...")
        freq_map = build_frequency_map(corpus, nodes, exclude_bg)
        save_frequency_map(freq_map, nodes, output_dir / "frequency_map.csv")
    
    # Full scan
    print(f"\nScanning {len(nodes)} nodes across {len(corpus)} verses...")
    all_results = []
    
    for node in nodes:
        print(f"  [{node['id']}] {node['name']}...")
        results = search_node(corpus, node, exclude_bg)
        strong = [r for r in results if r["match_strength"] >= args.min_strength]
        all_results.extend(strong)
        print(f"         → {len(results)} hits, {len(strong)} strong")
    
    save_results_csv(all_results, output_dir / "echo_results.csv")
    
    freq_map = defaultdict(lambda: defaultdict(int))
    for r in all_results:
        freq_map[r["node_id"]][r["parva_num"]] += 1
    
    generate_report(all_results, freq_map, nodes, output_dir / "scan_report.txt")
    
    print(f"\nDone. {len(all_results)} echoes written to {output_dir}")


if __name__ == "__main__":
    main()
