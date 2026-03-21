#!/usr/bin/env python3
"""
inverse_map.py -- build the BG-vs-MBH teaching matrix and classify nodes A-E

for each doctrinal node (BG nodes + MBH extra nodes), compute:
  - bg_density: how strongly the node is present in the BG
  - outside_density: how strongly the node echoes across the rest of MBH
  - parva_spread: how many distinct parvas contain echoes
  - selection_index: (outside - bg) / (outside + bg + eps)
  - node_type: A/B/C/D/E
  - inverse_relation: omitted / muted / backgrounded / etc.

data sources:
  - echo_results.csv from scan_corpus.py (term-based echoes OUTSIDE BG)
  - bg_nodes_v2.json (node definitions, verse counts = BG presence)
  - mbh_extra_nodes.yaml (MBH-only nodes with annotated BG status)

key design note:
  scan_corpus.py intentionally excludes BG verses (parva 06 ch 23-40),
  so echo_results.csv contains only non-BG hits. bg_density is therefore
  derived from node definitions (verse coverage within BG), not from hit data.

outputs:
  inverse_node_matrix.csv      -- full matrix
  inverse_report.txt           -- human-readable summary by type
  selection_histogram_data.csv -- for plotting
"""

import argparse
import csv
import json
import os
import sys

# optional yaml -- graceful fallback
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


# ── constants ───────────────────────────────────────────────────────────
BG_PARVA = 6
BG_CH_MIN = 23
BG_CH_MAX = 40
BG_TOTAL_VERSES = 700  # total BG verses (BORI critical edition)
# approximate total non-BG half-verses in corpus (~89K verses * 2 halves - BG)
MBH_NONBG_HALFVERSES = 176600


def parse_args():
    p = argparse.ArgumentParser(description="build BG-vs-MBH inverse teaching matrix")
    p.add_argument("--hits",
                   default="../output/semantic_map/semantic_hits.csv",
                   help="semantic hits CSV (falls back to echo_results.csv)")
    p.add_argument("--nodes",
                   default="../data/bg_nodes_v2.json",
                   help="BG node definitions (JSON)")
    p.add_argument("--extra-nodes",
                   default="../data/mbh_extra_nodes.yaml",
                   help="MBH extra nodes (YAML)")
    p.add_argument("--output",
                   default="../output/inverse_map/",
                   help="output directory")
    return p.parse_args()


def load_hits(path):
    """load hit data from CSV.
    supports two formats:
      - semantic_hits.csv: has 'score' column (0-1 float)
      - echo_results.csv: has 'match_strength' column (integer 1-3)
    returns list of dicts with: node_id, parva_num, chapter, strength
    """
    if not os.path.isfile(path):
        # try fallback to echo_results.csv
        fallback = os.path.join(os.path.dirname(path), "..", "v3", "echo_results.csv")
        fallback = os.path.normpath(fallback)
        if not os.path.isfile(fallback):
            fallback = os.path.normpath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "output", "v3", "echo_results.csv"))
        if os.path.isfile(fallback):
            print(f"[info] {path} not found, falling back to {fallback}")
            path = fallback
        else:
            print(f"[error] no hit file found at {path} or fallback")
            sys.exit(1)

    hits = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            node_id = row.get("node_id", "")
            parva_num = int(row.get("parva_num", 0))
            chapter = int(row.get("chapter", 0))

            # use 'score' if available (semantic), else 'match_strength' (term-based)
            if "score" in row and row["score"]:
                strength = float(row["score"])
            elif "match_strength" in row and row["match_strength"]:
                strength = float(row["match_strength"])
            else:
                strength = 1.0

            hits.append({
                "node_id": node_id,
                "parva_num": parva_num,
                "chapter": chapter,
                "strength": strength,
            })

    print(f"[info] loaded {len(hits)} hits from {path}")
    return hits


def load_bg_nodes(path):
    """load BG node definitions.
    returns dict node_id -> {short_label, source, bg_verse_count, repetition_count}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    nodes = {}
    for n in data.get("nodes", []):
        nid = n["id"]
        label = n.get("name", nid)
        if len(label) > 60:
            label = label[:57] + "..."
        nodes[nid] = {
            "short_label": label,
            "source": "bg",
            # number of BG verses this node covers -- proxy for BG importance
            "bg_verse_count": len(n.get("all_verses", [])),
            "repetition_count": n.get("repetition_count", 0),
        }
    return nodes


def load_extra_nodes(path):
    """load MBH extra nodes from YAML.
    returns dict node_id -> info with annotated bg_status and inverse_analysis.
    """
    if not os.path.isfile(path):
        print(f"[info] no extra nodes file at {path}, skipping")
        return {}

    if not HAS_YAML:
        print("[warn] pyyaml not installed, cannot load extra nodes YAML")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    nodes = {}
    for n in data.get("nodes", []):
        nid = n["id"]
        label = n.get("short_label", nid)
        bg_status = n.get("bg_status", {})
        inv = n.get("inverse_analysis", {})
        nodes[nid] = {
            "short_label": label,
            "source": "extra",
            "bg_verse_count": 0,
            "repetition_count": 0,
            "bg_present_yaml": bg_status.get("present", False),
            "bg_centrality_yaml": bg_status.get("centrality", 0.0),
            "provisional_type_yaml": inv.get("provisional_type", ""),
            "inverse_relation_yaml": inv.get("inverse_relation", ""),
        }
    return nodes


def compute_metrics(hits, all_nodes):
    """compute per-node metrics.

    bg_density: fraction of BG verses this node covers (from node defs).
      range 0-1. a node covering 20/700 verses = 0.029.
      scaled by repetition_count to weight nodes the BG emphasizes.

    outside_density: weighted hit rate across non-BG corpus.
      total weighted hits / MBH_NONBG_HALFVERSES, then scaled to 0-1.

    for extra nodes (X-prefixed): bg_density comes from YAML centrality.
    """
    # accumulate outside hits per node
    outside_weighted = {}  # node_id -> sum of strengths
    outside_count = {}     # node_id -> raw hit count
    parva_sets = {}        # node_id -> set of parva_nums

    for nid in all_nodes:
        outside_weighted[nid] = 0.0
        outside_count[nid] = 0
        parva_sets[nid] = set()

    for h in hits:
        nid = h["node_id"]
        if nid not in outside_weighted:
            continue
        outside_weighted[nid] += h["strength"]
        outside_count[nid] += 1
        parva_sets[nid].add(h["parva_num"])

    # find max weighted hits for normalization
    max_weighted = max(outside_weighted.values()) if outside_weighted else 1.0
    if max_weighted == 0:
        max_weighted = 1.0

    metrics = {}
    for nid, info in all_nodes.items():
        # -- bg_density --
        if info["source"] == "extra":
            # use YAML-annotated centrality
            bg_density = info.get("bg_centrality_yaml", 0.0)
        else:
            # BG nodes: verse fraction, boosted by repetition
            verse_frac = info["bg_verse_count"] / BG_TOTAL_VERSES
            rep = info.get("repetition_count", 1)
            # scale so a node with 20 verses and rep=3 gets ~0.26
            # max possible: ~50 verses * rep 5 / 700 ~ 0.36
            bg_density = verse_frac * max(rep, 1)

        # -- outside_density --
        # normalize to 0-1 by dividing by max weighted hits across all nodes
        outside_density = outside_weighted[nid] / max_weighted

        parva_spread = len(parva_sets[nid])

        # -- selection index --
        eps = 1e-6
        selection_index = (outside_density - bg_density) / (outside_density + bg_density + eps)

        bg_present = (info["source"] == "bg") or info.get("bg_present_yaml", False)

        metrics[nid] = {
            "bg_present": bg_present,
            "bg_density": round(bg_density, 4),
            "outside_density": round(outside_density, 4),
            "outside_hits": outside_count[nid],
            "parva_spread": parva_spread,
            "speaker_spread": 0,  # placeholder
            "selection_index": round(selection_index, 4),
        }

    return metrics


def classify_node(m, extra_info=None):
    """assign node type A-E based on density thresholds.

    type A: BG-central AND MBH-wide (bg >= 0.01, outside >= 0.05, spread >= 6)
    type B: BG-central but MBH-local (bg >= 0.01, outside < 0.05 or spread <= 3)
    type C: BG-present but weak elsewhere (bg > 0, outside < 0.01)
    type D: MBH-strong but BG-weak (outside >= 0.05, 0 < bg < 0.01)
    type E: MBH-strong and BG-absent (outside > 0, bg == 0)

    thresholds calibrated for normalized densities (0-1 scale).
    """
    bg_d = m["bg_density"]
    out_d = m["outside_density"]
    spread = m["parva_spread"]

    # type A: BG-central and MBH-wide
    if bg_d >= 0.01 and out_d >= 0.05 and spread >= 6:
        return "A"

    # type B: BG-central but MBH-local (present in BG, limited MBH spread)
    if bg_d >= 0.01 and (out_d < 0.05 or spread <= 3):
        return "B"

    # type D: MBH-strong but BG-weak
    if out_d >= 0.05 and 0 < bg_d < 0.01:
        return "D"

    # type E: MBH-present and BG-absent (includes extra nodes)
    if bg_d == 0 and out_d > 0:
        return "E"

    # type C: BG-present but weak elsewhere
    if bg_d > 0 and out_d < 0.01:
        return "C"

    # for extra nodes with no hits, use YAML annotation
    if extra_info and extra_info.get("provisional_type_yaml"):
        return extra_info["provisional_type_yaml"]

    # fallback
    if bg_d > 0 and out_d > 0:
        return "A" if spread >= 6 else "B"
    if bg_d > 0:
        return "C"

    return "U"  # unclassified (no data at all)


def assign_inverse_relation(m, node_type, extra_info=None):
    """for types D and E, assign an inverse_relation tag.
    for other types, return empty string.
    manual YAML annotations take precedence.
    """
    # prefer manual YAML annotation
    if extra_info and extra_info.get("inverse_relation_yaml"):
        return extra_info["inverse_relation_yaml"]

    if node_type not in ("D", "E"):
        return ""

    bg_d = m["bg_density"]
    out_d = m["outside_density"]

    # omitted: BG-absent, MBH-strong
    if bg_d == 0 and out_d >= 0.05:
        return "omitted"

    # muted: BG present but < 35% of MBH density
    if bg_d > 0 and bg_d < out_d * 0.35:
        return "muted"

    # backgrounded: BG present but < 50% of MBH density
    if bg_d > 0 and bg_d < out_d * 0.5:
        return "backgrounded"

    # omitted (weaker): BG-absent, some MBH presence
    if bg_d == 0 and out_d > 0:
        return "omitted"

    return ""


def write_matrix_csv(rows, outpath):
    """write the main inverse_node_matrix.csv"""
    fields = [
        "node_id", "short_label", "source", "bg_present",
        "bg_density", "outside_density", "parva_spread",
        "selection_index", "node_type", "inverse_relation",
    ]
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"[ok] wrote {outpath} ({len(rows)} rows)")


def write_histogram_csv(rows, outpath):
    """write selection_histogram_data.csv for plotting"""
    fields = ["node_id", "short_label", "selection_index", "node_type"]
    with open(outpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"[ok] wrote {outpath}")


def write_report(rows, outpath):
    """write human-readable inverse_report.txt grouped by type"""
    by_type = {}
    for r in rows:
        t = r["node_type"]
        by_type.setdefault(t, []).append(r)

    type_labels = {
        "A": "TYPE A: BG-central and MBH-wide",
        "B": "TYPE B: BG-central but MBH-local",
        "C": "TYPE C: BG-present but weak elsewhere",
        "D": "TYPE D: MBH-strong but BG-weak",
        "E": "TYPE E: MBH-strong and BG-absent",
        "U": "UNCLASSIFIED",
    }

    with open(outpath, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write("INVERSE NODE MATRIX -- BG vs MBH Teaching Distribution\n")
        f.write("=" * 72 + "\n\n")

        # summary counts
        f.write("SUMMARY\n")
        f.write("-" * 40 + "\n")
        total = len(rows)
        for t in ["A", "B", "C", "D", "E", "U"]:
            count = len(by_type.get(t, []))
            if count > 0:
                pct = 100.0 * count / total
                f.write(f"  {t}: {count:4d} nodes ({pct:5.1f}%)\n")
        f.write(f"  Total: {total}\n\n")

        # detail by type
        for t in ["A", "B", "C", "D", "E", "U"]:
            if t not in by_type:
                continue
            nodes = by_type[t]
            label = type_labels.get(t, t)
            f.write("=" * 72 + "\n")
            f.write(f"{label} ({len(nodes)} nodes)\n")
            f.write("-" * 72 + "\n\n")

            # sort by selection_index descending (MBH-heavy first)
            nodes.sort(key=lambda r: r.get("selection_index", 0), reverse=True)

            for r in nodes:
                f.write(f"  {r['node_id']:6s}  {r['short_label']}\n")
                f.write(f"         bg={r['bg_density']:.4f}  "
                        f"outside={r['outside_density']:.4f}  "
                        f"spread={r['parva_spread']}  "
                        f"SI={r['selection_index']:+.4f}")
                if r.get("inverse_relation"):
                    f.write(f"  [{r['inverse_relation']}]")
                f.write("\n\n")

    print(f"[ok] wrote {outpath}")


def main():
    args = parse_args()

    # load node definitions
    bg_nodes = load_bg_nodes(args.nodes)
    extra_nodes = load_extra_nodes(args.extra_nodes)

    # merge into single dict
    all_nodes = {}
    all_nodes.update(bg_nodes)
    all_nodes.update(extra_nodes)
    print(f"[info] {len(bg_nodes)} BG nodes + {len(extra_nodes)} extra nodes = {len(all_nodes)} total")

    # load hits
    hits = load_hits(args.hits)

    # compute metrics
    metrics = compute_metrics(hits, all_nodes)

    # classify and build output rows
    rows = []
    for nid in sorted(all_nodes.keys()):
        info = all_nodes[nid]
        m = metrics[nid]
        extra = info if info.get("source") == "extra" else None

        node_type = classify_node(m, extra)
        inv_rel = assign_inverse_relation(m, node_type, extra)

        rows.append({
            "node_id": nid,
            "short_label": info["short_label"],
            "source": info.get("source", "bg"),
            "bg_present": m["bg_present"],
            "bg_density": m["bg_density"],
            "outside_density": m["outside_density"],
            "parva_spread": m["parva_spread"],
            "selection_index": m["selection_index"],
            "node_type": node_type,
            "inverse_relation": inv_rel,
        })

    # ensure output dir exists
    os.makedirs(args.output, exist_ok=True)

    # write outputs
    matrix_path = os.path.join(args.output, "inverse_node_matrix.csv")
    report_path = os.path.join(args.output, "inverse_report.txt")
    hist_path = os.path.join(args.output, "selection_histogram_data.csv")

    write_matrix_csv(rows, matrix_path)
    write_histogram_csv(rows, hist_path)
    write_report(rows, report_path)

    # print quick summary
    type_counts = {}
    for r in rows:
        t = r["node_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"\n[summary] {len(rows)} nodes classified:")
    for t in sorted(type_counts.keys()):
        print(f"  type {t}: {type_counts[t]}")


if __name__ == "__main__":
    main()
