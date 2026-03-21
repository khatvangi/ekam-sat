#!/usr/bin/env python3
"""
Cluster Asymmetry — Ekam Sat Project
======================================
Compares doctrinal cluster structure between BG-internal and MBH-external
co-occurrence networks. Shows how the BG compresses, reorganizes, or omits
doctrinal clusters found across the wider epic.

Usage:
    python cluster_asymmetry.py \
        --echoes ../output/v3/echo_results.csv \
        --nodes ../data/bg_nodes_v2.json \
        --bg-dir ../data/bg_chapters/ \
        --output ../output/cluster_asymmetry/
"""

import csv
import json
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict, deque
from itertools import combinations


# ── constants ────────────────────────────────────────────────────────────────

BG_CHAPTERS = set(range(23, 41))  # BG = parva 06, chapters 23-40

PARVAS = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}


# ── helpers ──────────────────────────────────────────────────────────────────

def is_bg_verse(verse_id):
    """check if a verse ID falls within BG (parva 06, chapters 23-40)."""
    if len(verse_id) < 8:
        return False
    parva = verse_id[:2]
    chapter = int(verse_id[2:5])
    return parva == "06" and chapter in BG_CHAPTERS


def load_echoes(path):
    """load echo_results.csv, return list of dicts."""
    echoes = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            echoes.append(row)
    return echoes


def load_nodes(path):
    """load bg_nodes_v2.json, return list of node dicts."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["nodes"]


def load_bg_verses(bg_dir):
    """
    load BG chapter files and return dict of {verse_id: text}.
    aggregates half-verse lines into full verse text.
    """
    bg_path = Path(bg_dir)
    verses = defaultdict(list)
    import re as _re
    for fpath in sorted(bg_path.glob("bg_ch*.txt")):
        with open(fpath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or not line[0].isdigit():
                    continue
                m = _re.match(r'^(\d{8})[a-e]?\s+(.*)', line)
                if m:
                    vid = m.group(1)
                    text = m.group(2)
                    # skip speaker labels like "arjuna uvAca"
                    if "uvAca" in text:
                        continue
                    verses[vid].append(text)
    # join half-verse lines into one string per verse
    return {vid: " ".join(parts) for vid, parts in verses.items()}


def scan_bg_for_nodes(bg_verses, nodes):
    """
    scan BG verse texts for node terms and produce echo-like records.
    echo_results.csv excludes BG by design, so we need to build
    BG-internal co-occurrence directly from the source text.

    uses the same matching logic as scan_corpus.py: check if any
    hk_terms appear in the verse text (case-sensitive, word-boundary).
    a node matches a verse if at least 1 core_hk term is found.

    returns list of dicts with 'verse_id' and 'node_id'.
    """
    import re as _re
    bg_echoes = []
    for node in nodes:
        nid = node["id"]
        # use core_hk for matching (same as "strong" in scan_corpus)
        core_terms = node.get("core_hk", [])
        if not core_terms:
            core_terms = node.get("hk_terms", [])[:3]

        # build regex patterns for each term (word boundary, case-sensitive)
        patterns = []
        for term in core_terms:
            if term:
                patterns.append(_re.compile(r'(?<!\w)' + _re.escape(term) + r'(?!\w)'))

        for vid, text in bg_verses.items():
            matches = sum(1 for p in patterns if p.search(text))
            if matches >= 1:
                bg_echoes.append({"verse_id": vid, "node_id": nid})

    return bg_echoes


# ── co-occurrence matrix builder ─────────────────────────────────────────────

def build_cooccurrence_matrix(echoes, nodes, verse_filter_fn):
    """
    build a node x node co-occurrence matrix from echoes,
    only counting verses that pass verse_filter_fn.

    returns: (matrix, node_ids, node_freq, total_verses)
    """
    # group nodes per verse (filtered)
    verse_nodes = defaultdict(set)
    for e in echoes:
        vid = e["verse_id"][:8]
        if verse_filter_fn(vid):
            verse_nodes[vid].add(e["node_id"])

    node_ids = sorted(set(n["id"] for n in nodes))
    node_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)
    cooc = np.zeros((n, n), dtype=int)

    # count co-occurrences (two nodes in the same verse)
    for vid, node_set in verse_nodes.items():
        for a, b in combinations(node_set, 2):
            if a in node_idx and b in node_idx:
                i, j = node_idx[a], node_idx[b]
                cooc[i][j] += 1
                cooc[j][i] += 1

    # per-node frequencies
    node_freq = np.zeros(n)
    for vid, node_set in verse_nodes.items():
        for nid in node_set:
            if nid in node_idx:
                node_freq[node_idx[nid]] += 1

    total_verses = len(verse_nodes)
    return cooc, node_ids, node_freq, total_verses


# ── PMI computation ──────────────────────────────────────────────────────────

def compute_pmi_pairs(cooc, node_ids, node_freq, total_verses):
    """
    compute pointwise mutual information for all co-occurring node pairs.
    PMI(a,b) = log2(P(a,b) / (P(a) * P(b)))
    returns list of (node_a, node_b, pmi_value, raw_count).
    """
    n = len(node_ids)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            raw = int(cooc[i][j])
            if raw > 0 and total_verses > 0:
                p_ab = raw / total_verses
                p_a = node_freq[i] / total_verses
                p_b = node_freq[j] / total_verses
                denom = p_a * p_b
                pmi = np.log2(p_ab / max(denom, 1e-10)) if denom > 0 else 0
                pairs.append((node_ids[i], node_ids[j], round(pmi, 3), raw))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


# ── cluster detection (connected components on top PMI edges) ────────────────

def find_clusters(pmi_pairs, pct=10):
    """
    find connected components using the top pct% of PMI pairs.
    same approach as dharma_topology.py.
    """
    if not pmi_pairs:
        return []

    positive = [p for p in pmi_pairs if p[2] > 0]
    if not positive:
        return []

    cutoff = np.percentile([p[2] for p in positive], 100 - pct)
    strong = [(a, b) for a, b, pmi, raw in positive if pmi >= cutoff]

    # BFS connected components
    adj = defaultdict(set)
    for a, b in strong:
        adj[a].add(b)
        adj[b].add(a)

    visited = set()
    clusters = []
    for node in adj:
        if node not in visited:
            cluster = set()
            queue = deque([node])
            while queue:
                curr = queue.popleft()
                if curr in visited:
                    continue
                visited.add(curr)
                cluster.add(curr)
                queue.extend(adj[curr] - visited)
            if len(cluster) >= 2:
                clusters.append(sorted(cluster))

    return clusters


# ── comparison logic ─────────────────────────────────────────────────────────

def compare_clusters(bg_clusters, mbh_clusters, bg_pmi_pairs, mbh_pmi_pairs,
                     bg_node_freq, mbh_node_freq, bg_total, mbh_total,
                     node_ids, nodes):
    """
    compare cluster structures between BG and MBH.
    returns list of cluster comparison records.
    """
    node_names = {n["id"]: n["name"] for n in nodes}
    node_idx = {nid: i for i, nid in enumerate(node_ids)}

    # build PMI lookup dicts for fast access
    def pmi_dict(pairs):
        d = {}
        for a, b, pmi, raw in pairs:
            key = tuple(sorted([a, b]))
            d[key] = pmi
        return d

    bg_pmi = pmi_dict(bg_pmi_pairs)
    mbh_pmi = pmi_dict(mbh_pmi_pairs)

    # merge all unique clusters from both sources
    # label each cluster by its dominant source and content
    all_clusters = []

    # tag clusters with source
    for i, cl in enumerate(bg_clusters):
        all_clusters.append(("BG", i, cl))
    for i, cl in enumerate(mbh_clusters):
        all_clusters.append(("MBH", i, cl))

    # deduplicate: merge clusters with >50% node overlap
    merged = []
    used = set()
    for idx_a, (src_a, i_a, cl_a) in enumerate(all_clusters):
        if idx_a in used:
            continue
        best = set(cl_a)
        for idx_b, (src_b, i_b, cl_b) in enumerate(all_clusters):
            if idx_b <= idx_a or idx_b in used:
                continue
            overlap = len(set(cl_a) & set(cl_b))
            union = len(set(cl_a) | set(cl_b))
            if union > 0 and overlap / union > 0.5:
                best = best | set(cl_b)
                used.add(idx_b)
        used.add(idx_a)
        merged.append(sorted(best))

    # also add any clusters not merged
    # (already handled by the loop above)

    comparisons = []
    for ci, cluster_nodes in enumerate(merged):
        n_nodes = len(cluster_nodes)

        # coverage: fraction of cluster nodes with nonzero frequency
        bg_present = sum(1 for nid in cluster_nodes
                         if nid in node_idx and bg_node_freq[node_idx[nid]] > 0)
        mbh_present = sum(1 for nid in cluster_nodes
                          if nid in node_idx and mbh_node_freq[node_idx[nid]] > 0)
        bg_coverage = bg_present / max(n_nodes, 1)
        mbh_coverage = mbh_present / max(n_nodes, 1)

        # density: average node frequency within this cluster
        bg_density = np.mean([bg_node_freq[node_idx[nid]]
                              for nid in cluster_nodes if nid in node_idx])
        mbh_density = np.mean([mbh_node_freq[node_idx[nid]]
                               for nid in cluster_nodes if nid in node_idx])

        # compression ratio: BG density / MBH density (normalized by verse count)
        bg_density_norm = bg_density / max(bg_total, 1)
        mbh_density_norm = mbh_density / max(mbh_total, 1)
        compression = bg_density_norm / max(mbh_density_norm, 1e-10)

        # reorganization score: how different is pairwise PMI structure
        # between BG and MBH for this cluster's node pairs
        pair_diffs = []
        for a, b in combinations(cluster_nodes, 2):
            key = tuple(sorted([a, b]))
            pmi_bg = bg_pmi.get(key, 0)
            pmi_mbh = mbh_pmi.get(key, 0)
            pair_diffs.append(abs(pmi_bg - pmi_mbh))

        reorg_score = float(np.mean(pair_diffs)) if pair_diffs else 0.0

        # classify the cluster
        if bg_coverage < 0.1:
            classification = "absent"
        elif bg_coverage >= 0.8:
            if reorg_score > 2.0:
                classification = "reorganized"
            else:
                classification = "fully_represented"
        elif bg_coverage >= 0.3:
            if reorg_score > 2.0:
                classification = "reorganized"
            else:
                classification = "partially_represented"
        else:
            classification = "absent"

        # representative name: most frequent node in the cluster
        rep_node = max(cluster_nodes,
                       key=lambda nid: (bg_node_freq[node_idx[nid]] +
                                        mbh_node_freq[node_idx[nid]])
                       if nid in node_idx else 0)

        comparisons.append({
            "cluster_id": ci + 1,
            "cluster_label": node_names.get(rep_node, rep_node)[:60],
            "n_nodes": n_nodes,
            "node_ids": cluster_nodes,
            "node_names": [node_names.get(nid, nid)[:50] for nid in cluster_nodes],
            "bg_coverage": round(bg_coverage, 3),
            "mbh_coverage": round(mbh_coverage, 3),
            "bg_density_norm": round(bg_density_norm, 6),
            "mbh_density_norm": round(mbh_density_norm, 6),
            "compression_ratio": round(compression, 3),
            "reorganization_score": round(reorg_score, 3),
            "classification": classification,
        })

    comparisons.sort(key=lambda x: x["cluster_id"])
    return comparisons


# ── output writers ───────────────────────────────────────────────────────────

def write_csv(comparisons, output_dir):
    """write cluster_comparison.csv."""
    path = output_dir / "cluster_comparison.csv"
    fields = [
        "cluster_id", "cluster_label", "n_nodes", "bg_coverage",
        "mbh_coverage", "compression_ratio", "reorganization_score",
        "classification",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for c in comparisons:
            writer.writerow(c)
    print(f"  wrote {path}")


def write_report(comparisons, bg_total, mbh_total, bg_clusters, mbh_clusters,
                 output_dir):
    """write asymmetry_report.txt with human-readable summary."""
    path = output_dir / "asymmetry_report.txt"
    lines = []
    lines.append("=" * 70)
    lines.append("CLUSTER ASYMMETRY REPORT")
    lines.append("Ekam Sat Project -- BG vs MBH doctrinal cluster comparison")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"BG verses with echoes:  {bg_total}")
    lines.append(f"MBH verses with echoes: {mbh_total}")
    lines.append(f"BG clusters found:      {len(bg_clusters)}")
    lines.append(f"MBH clusters found:     {len(mbh_clusters)}")
    lines.append(f"Merged clusters:        {len(comparisons)}")
    lines.append("")

    # classification summary
    class_counts = defaultdict(int)
    for c in comparisons:
        class_counts[c["classification"]] += 1
    lines.append("Classification summary:")
    for cls in ["fully_represented", "partially_represented", "reorganized", "absent"]:
        lines.append(f"  {cls:25s} {class_counts.get(cls, 0)}")
    lines.append("")

    # per-cluster detail
    lines.append("-" * 70)
    lines.append("CLUSTER DETAILS")
    lines.append("-" * 70)
    for c in comparisons:
        lines.append("")
        lines.append(f"Cluster {c['cluster_id']}: {c['cluster_label']}")
        lines.append(f"  nodes ({c['n_nodes']}): {', '.join(c['node_ids'])}")
        lines.append(f"  BG coverage:          {c['bg_coverage']:.3f}")
        lines.append(f"  MBH coverage:         {c['mbh_coverage']:.3f}")
        lines.append(f"  compression ratio:    {c['compression_ratio']:.3f}")
        lines.append(f"  reorganization score: {c['reorganization_score']:.3f}")
        lines.append(f"  classification:       {c['classification']}")
        for name in c["node_names"]:
            lines.append(f"    - {name}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  wrote {path}")


def write_cluster_json(clusters, node_names, path, label):
    """write cluster list as JSON."""
    out = []
    for i, cl in enumerate(clusters):
        out.append({
            "cluster_id": i + 1,
            "nodes": cl,
            "node_names": [node_names.get(nid, nid) for nid in cl],
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"  wrote {path} ({len(clusters)} {label} clusters)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Compare doctrinal clusters between BG and non-BG MBH")
    parser.add_argument("--echoes", required=True,
                        help="path to echo_results.csv")
    parser.add_argument("--nodes", required=True,
                        help="path to bg_nodes_v2.json")
    parser.add_argument("--bg-dir", required=True,
                        help="path to data/bg_chapters/ directory")
    parser.add_argument("--output", required=True,
                        help="output directory")
    parser.add_argument("--pmi-pct", type=float, default=10,
                        help="PMI percentile for clustering (default: 10)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load data
    print("loading data...")
    echoes = load_echoes(args.echoes)
    nodes = load_nodes(args.nodes)
    bg_verses = load_bg_verses(args.bg_dir)
    node_names = {n["id"]: n["name"] for n in nodes}

    print(f"  echoes (MBH, non-BG): {len(echoes)}")
    print(f"  nodes: {len(nodes)}")
    print(f"  BG verses loaded: {len(bg_verses)}")

    # scan BG verses against node terms directly
    # (echo_results.csv excludes BG by design)
    print("\nscanning BG verses for node terms...")
    bg_echoes = scan_bg_for_nodes(bg_verses, nodes)
    print(f"  BG echo records generated: {len(bg_echoes)}")

    # build two co-occurrence matrices
    print("\nbuilding BG-internal co-occurrence matrix...")
    bg_cooc, node_ids, bg_freq, bg_total = build_cooccurrence_matrix(
        bg_echoes, nodes, lambda vid: True)  # all bg_echoes are BG
    print(f"  BG verses with node hits: {bg_total}")

    print("\nbuilding MBH-external co-occurrence matrix...")
    mbh_cooc, _, mbh_freq, mbh_total = build_cooccurrence_matrix(
        echoes, nodes, lambda vid: not is_bg_verse(vid))
    print(f"  MBH (non-BG) verses with node hits: {mbh_total}")

    # compute PMI for both
    print("\ncomputing PMI pairs...")
    bg_pmi_pairs = compute_pmi_pairs(bg_cooc, node_ids, bg_freq, bg_total)
    mbh_pmi_pairs = compute_pmi_pairs(mbh_cooc, node_ids, mbh_freq, mbh_total)
    print(f"  BG pairs with co-occurrence:  {len(bg_pmi_pairs)}")
    print(f"  MBH pairs with co-occurrence: {len(mbh_pmi_pairs)}")

    # detect clusters in each
    pct = args.pmi_pct
    print(f"\ndetecting clusters (top {pct}% PMI)...")
    bg_clusters = find_clusters(bg_pmi_pairs, pct)
    mbh_clusters = find_clusters(mbh_pmi_pairs, pct)
    print(f"  BG clusters:  {len(bg_clusters)}")
    print(f"  MBH clusters: {len(mbh_clusters)}")

    # compare
    print("\ncomparing cluster structures...")
    comparisons = compare_clusters(
        bg_clusters, mbh_clusters, bg_pmi_pairs, mbh_pmi_pairs,
        bg_freq, mbh_freq, bg_total, mbh_total, node_ids, nodes)

    # print summary
    print(f"\n{'='*60}")
    print(f"CLUSTER ASYMMETRY SUMMARY")
    print(f"{'='*60}")
    for c in comparisons:
        print(f"  [{c['classification']:22s}] cluster {c['cluster_id']:2d} "
              f"({c['n_nodes']:2d} nodes) "
              f"BG={c['bg_coverage']:.2f} MBH={c['mbh_coverage']:.2f} "
              f"comp={c['compression_ratio']:.1f} "
              f"reorg={c['reorganization_score']:.2f} "
              f"-- {c['cluster_label'][:40]}")

    # write outputs
    print(f"\nwriting outputs to {output_dir}/")
    write_csv(comparisons, output_dir)
    write_report(comparisons, bg_total, mbh_total, bg_clusters, mbh_clusters,
                 output_dir)
    write_cluster_json(bg_clusters, node_names,
                       output_dir / "bg_clusters.json", "BG")
    write_cluster_json(mbh_clusters, node_names,
                       output_dir / "mbh_clusters.json", "MBH")

    print("\ndone.")


if __name__ == "__main__":
    main()
