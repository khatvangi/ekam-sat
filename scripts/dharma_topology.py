#!/usr/bin/env python3
"""
Dharma Topology — Ekam Sat Project
====================================
Structural analysis of the MBH's doctrinal network. Moves from "echo detection"
to dharma-topology: co-occurrence architecture, speaker signatures, density
gradients, graph centrality, compression metrics, and null baselines.

Usage:
    python dharma_topology.py \
        --echoes ../output/v3/echo_results.csv \
        --nodes ../data/bg_nodes_v2.json \
        --discourses ../output/v3/discourses.json \
        --corpus ../bori/hk \
        --output ../output/topology/
"""

import re
import csv
import json
import random
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from itertools import combinations


# ─── parva metadata ──────────────────────────────────────────────────────────
PARVAS = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}

BG_CHAPTERS = set(range(23, 41))


# ═════════════════════════════════════════════════════════════════════════════
# 1. NULL BASELINES
# ═════════════════════════════════════════════════════════════════════════════

def build_null_baselines(corpus_dir, nodes, echo_count, n_trials=50):
    """
    Generate random-term baselines to test whether echo counts are significant.

    Creates N random "pseudo-nodes" with the same term-count distribution as
    real nodes, scans corpus, and reports expected echo counts under null.
    """
    print("\n" + "=" * 60)
    print("1. NULL BASELINES")
    print("=" * 60)

    # build vocabulary from corpus
    print("  Building corpus vocabulary...")
    vocab = Counter()
    corpus_path = Path(corpus_dir)
    for filepath in sorted(corpus_path.iterdir()):
        if not filepath.is_file():
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'^\d{8}[a-e]?\s+(.*)', line.strip())
                if m:
                    # skip BG verses
                    vid = line.strip()[:8]
                    if vid[:2] == "06" and int(vid[2:5]) in BG_CHAPTERS:
                        continue
                    for word in m.group(1).split():
                        if len(word) >= 3:
                            vocab[word] += 1

    # get term-count distribution from real nodes
    term_counts = [len(n.get("hk_terms", []) + n.get("core_hk", [])) for n in nodes]
    avg_terms = np.mean(term_counts)
    print(f"  Corpus vocabulary: {len(vocab)} unique words (3+ chars)")
    print(f"  Real nodes: avg {avg_terms:.1f} terms per node")

    # separate vocab by frequency bands to match real term distribution
    # real node terms tend to be mid-frequency (not particles, not hapax)
    real_term_freqs = []
    for n in nodes:
        for t in n.get("hk_terms", []) + n.get("core_hk", []):
            if t in vocab:
                real_term_freqs.append(vocab[t])
    real_median_freq = np.median(real_term_freqs) if real_term_freqs else 100

    # candidate pool: words in similar frequency range as real terms
    freq_lo = real_median_freq * 0.1
    freq_hi = real_median_freq * 10
    candidate_words = [w for w, c in vocab.items() if freq_lo <= c <= freq_hi]
    print(f"  Candidate pool (frequency-matched): {len(candidate_words)} words")

    # also build a high-frequency control (common words that aren't doctrinal)
    high_freq_words = [w for w, c in vocab.most_common(200)]

    # run random trials
    random.seed(42)
    random_echo_counts = []
    highfreq_echo_counts = []

    # load corpus as dict for scanning
    corpus = {}
    for filepath in sorted(corpus_path.iterdir()):
        if not filepath.is_file():
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            current_id = None
            current_parts = []
            for line in f:
                line = line.rstrip()
                m_line = re.match(r'^(\d{8}[a-e]?)\s+(.*)', line)
                if m_line:
                    if current_id and current_parts:
                        corpus[current_id] = " ".join(current_parts)
                    current_id = m_line.group(1)[:8]
                    vid = m_line.group(1)
                    if vid[:2] == "06" and int(vid[2:5]) in BG_CHAPTERS:
                        current_id = None
                        continue
                    current_parts = [m_line.group(2)]
                elif current_id:
                    current_parts.append(line.strip())
            if current_id and current_parts:
                corpus[current_id] = " ".join(current_parts)

    print(f"  Corpus loaded: {len(corpus)} non-BG verses")
    print(f"  Running {n_trials} random trials...")

    for trial in range(n_trials):
        # random pseudo-node: pick random terms matching real distribution
        n_terms = random.choice(term_counts)
        n_core = max(2, n_terms // 3)
        terms = random.sample(candidate_words, min(n_terms, len(candidate_words)))
        core = terms[:n_core]

        # count "echoes" (verses where 2+ core terms co-occur)
        echo_count_trial = 0
        for vid, text in corpus.items():
            matches = sum(1 for t in core if t in text)
            if matches >= 2:
                echo_count_trial += 1
        random_echo_counts.append(echo_count_trial)

        # high-frequency control
        hf_terms = random.sample(high_freq_words, min(n_core, len(high_freq_words)))
        hf_count = 0
        for vid, text in corpus.items():
            matches = sum(1 for t in hf_terms if t in text)
            if matches >= 2:
                hf_count += 1
        highfreq_echo_counts.append(hf_count)

        if (trial + 1) % 10 == 0:
            print(f"    trial {trial+1}/{n_trials}")

    results = {
        "real_strong_echoes": echo_count,
        "random_baseline": {
            "mean": float(np.mean(random_echo_counts)),
            "std": float(np.std(random_echo_counts)),
            "max": int(np.max(random_echo_counts)),
            "min": int(np.min(random_echo_counts)),
            "trials": n_trials,
        },
        "highfreq_baseline": {
            "mean": float(np.mean(highfreq_echo_counts)),
            "std": float(np.std(highfreq_echo_counts)),
            "max": int(np.max(highfreq_echo_counts)),
            "min": int(np.min(highfreq_echo_counts)),
        },
    }

    # z-score
    z = (echo_count - results["random_baseline"]["mean"]) / max(results["random_baseline"]["std"], 1)
    results["z_score_vs_random"] = round(z, 2)

    print(f"\n  Real strong echoes:    {echo_count}")
    print(f"  Random baseline:       {results['random_baseline']['mean']:.1f} ± {results['random_baseline']['std']:.1f}")
    print(f"  High-freq baseline:    {results['highfreq_baseline']['mean']:.1f} ± {results['highfreq_baseline']['std']:.1f}")
    print(f"  Z-score vs random:     {z:.1f}")

    return results


# ═════════════════════════════════════════════════════════════════════════════
# 2. NODE CO-OCCURRENCE CLUSTERS
# ═════════════════════════════════════════════════════════════════════════════

def build_cooccurrence(echoes, nodes):
    """
    Build node × node co-occurrence matrix.
    Two nodes co-occur when they both match the same verse.
    """
    print("\n" + "=" * 60)
    print("2. NODE CO-OCCURRENCE CLUSTERS")
    print("=" * 60)

    # group nodes per verse
    verse_nodes = defaultdict(set)
    for e in echoes:
        verse_nodes[e["verse_id"]].add(e["node_id"])

    # count co-occurrences
    node_ids = sorted(set(n["id"] for n in nodes))
    node_idx = {nid: i for i, nid in enumerate(node_ids)}
    n = len(node_ids)
    cooc = np.zeros((n, n), dtype=int)

    for vid, node_set in verse_nodes.items():
        for a, b in combinations(node_set, 2):
            if a in node_idx and b in node_idx:
                i, j = node_idx[a], node_idx[b]
                cooc[i][j] += 1
                cooc[j][i] += 1

    # find strongest pairs
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            if cooc[i][j] > 0:
                pairs.append((node_ids[i], node_ids[j], int(cooc[i][j])))

    pairs.sort(key=lambda x: x[2], reverse=True)

    # find clusters via simple connected-component grouping at threshold
    threshold = np.percentile([p[2] for p in pairs if p[2] > 0], 90) if pairs else 1
    strong_pairs = [(a, b) for a, b, c in pairs if c >= threshold]

    # build adjacency for clustering
    from collections import deque
    adj = defaultdict(set)
    for a, b in strong_pairs:
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

    node_names = {n["id"]: n["name"] for n in nodes}

    print(f"  Verses with 2+ nodes: {sum(1 for ns in verse_nodes.values() if len(ns) >= 2)}")
    print(f"  Node pairs with co-occurrence: {len([p for p in pairs if p[2] > 0])}")
    print(f"  Strong pairs (>= {threshold:.0f} co-occurrences): {len(strong_pairs)}")
    print(f"  Doctrinal clusters found: {len(clusters)}")

    print(f"\n  Top 15 node pairs:")
    for a, b, c in pairs[:15]:
        print(f"    {a} × {b}: {c} co-occurrences")
        print(f"      {node_names.get(a, '?')[:40]}")
        print(f"      {node_names.get(b, '?')[:40]}")

    print(f"\n  Doctrinal clusters (strong co-occurrence):")
    for i, cluster in enumerate(clusters):
        print(f"\n    Cluster {i+1} ({len(cluster)} nodes):")
        for nid in cluster:
            print(f"      {nid}: {node_names.get(nid, '?')[:55]}")

    return {
        "cooccurrence_matrix": cooc.tolist(),
        "node_ids": node_ids,
        "top_pairs": [(a, b, c) for a, b, c in pairs[:50]],
        "clusters": clusters,
        "threshold": float(threshold),
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. SPEAKER DOCTRINAL SIGNATURES
# ═════════════════════════════════════════════════════════════════════════════

def build_speaker_signatures(discourses, nodes):
    """
    Profile each speaker by doctrinal content: which nodes dominate,
    which are absent, and how they cluster.
    """
    print("\n" + "=" * 60)
    print("3. SPEAKER DOCTRINAL SIGNATURES")
    print("=" * 60)

    node_names = {n["id"]: n["name"] for n in nodes}
    all_node_ids = set(n["id"] for n in nodes)

    speaker_profiles = {}

    for d in discourses:
        speaker = d.get("speaker", "Unknown")
        if speaker not in speaker_profiles:
            speaker_profiles[speaker] = {
                "total_verses": 0,
                "total_discourses": 0,
                "node_counts": Counter(),
                "unique_nodes": set(),
            }

        sp = speaker_profiles[speaker]
        sp["total_verses"] += d.get("verse_count", 0)
        sp["total_discourses"] += 1
        for nid in d.get("echoed_nodes", []):
            sp["node_counts"][nid] += 1
            sp["unique_nodes"].add(nid)

    # compute signatures
    signatures = []
    for speaker, sp in sorted(speaker_profiles.items(), key=lambda x: x[1]["total_verses"], reverse=True):
        if sp["total_verses"] < 100:
            continue

        # top nodes for this speaker
        top = sp["node_counts"].most_common(10)
        # absent nodes (never echoed by this speaker)
        absent = all_node_ids - sp["unique_nodes"]
        # doctrinal density: unique nodes per 100 verses
        density = len(sp["unique_nodes"]) / max(sp["total_verses"], 1) * 100

        sig = {
            "speaker": speaker,
            "total_verses": sp["total_verses"],
            "total_discourses": sp["total_discourses"],
            "unique_nodes": len(sp["unique_nodes"]),
            "doctrinal_density": round(density, 2),
            "top_nodes": [(nid, count) for nid, count in top],
            "absent_count": len(absent),
        }
        signatures.append(sig)

    print(f"  Speakers with 100+ verses: {len(signatures)}")
    for sig in signatures[:15]:
        print(f"\n  {sig['speaker']:<20} {sig['total_verses']:>6} verses | "
              f"{sig['unique_nodes']:>3} nodes | density={sig['doctrinal_density']:.1f}/100v")
        top3 = sig["top_nodes"][:3]
        for nid, count in top3:
            print(f"    → {nid} ({node_names.get(nid, '?')[:45]}): {count}")

    return signatures


# ═════════════════════════════════════════════════════════════════════════════
# 4. DENSITY GRADIENTS
# ═════════════════════════════════════════════════════════════════════════════

def compute_density_gradients(echoes, nodes):
    """
    Classify echoes by depth: surface mention vs concentrated teaching.
    Uses match_strength and co-occurrence density within passages.
    """
    print("\n" + "=" * 60)
    print("4. DENSITY GRADIENTS")
    print("=" * 60)

    # group echoes by (parva, chapter) to find passage-level concentration
    passage_nodes = defaultdict(lambda: defaultdict(int))  # (parva, ch) -> {node_id: count}

    for e in echoes:
        key = (e["parva_num"], e.get("chapter", ""))
        passage_nodes[key][e["node_id"]] += 1

    # classify passages
    levels = {"surface": 0, "moderate": 0, "concentrated": 0, "synthesis": 0}
    passage_levels = []

    for (parva, ch), node_counts in passage_nodes.items():
        unique_nodes = len(node_counts)
        total_hits = sum(node_counts.values())

        if unique_nodes >= 5 and total_hits >= 10:
            level = "synthesis"
        elif unique_nodes >= 3 and total_hits >= 5:
            level = "concentrated"
        elif unique_nodes >= 2:
            level = "moderate"
        else:
            level = "surface"

        levels[level] += 1
        passage_levels.append({
            "parva": parva,
            "chapter": ch,
            "unique_nodes": unique_nodes,
            "total_hits": total_hits,
            "level": level,
            "top_nodes": [nid for nid, _ in Counter(node_counts).most_common(5)],
        })

    # sort by concentration
    passage_levels.sort(key=lambda x: (x["unique_nodes"], x["total_hits"]), reverse=True)

    print(f"  Passage classification (by parva-chapter):")
    for level, count in levels.items():
        bar = "#" * min(count, 50)
        print(f"    {level:<15} {count:>4}  {bar}")

    print(f"\n  Top 15 synthesis-level passages:")
    for p in passage_levels[:15]:
        pname = PARVAS.get(p["parva"], "?")
        print(f"    P{p['parva']} {pname:<15} ch{p['chapter']:<4} "
              f"nodes={p['unique_nodes']:>2} hits={p['total_hits']:>3} [{p['level']}]")

    return {"levels": levels, "passages": passage_levels[:100]}


# ═════════════════════════════════════════════════════════════════════════════
# 5. GRAPH CENTRALITY
# ═════════════════════════════════════════════════════════════════════════════

def compute_graph_centrality(cooc_data, nodes):
    """
    Build a graph from co-occurrence and compute centrality measures.
    Identifies core nodes, bridge nodes, and peripheral nodes.
    """
    print("\n" + "=" * 60)
    print("5. GRAPH CENTRALITY")
    print("=" * 60)

    node_ids = cooc_data["node_ids"]
    matrix = np.array(cooc_data["cooccurrence_matrix"])
    node_names = {n["id"]: n["name"] for n in nodes}
    n = len(node_ids)

    # degree centrality: how many other nodes does each node co-occur with?
    degrees = {}
    weighted_degrees = {}
    for i, nid in enumerate(node_ids):
        connections = sum(1 for j in range(n) if matrix[i][j] > 0 and i != j)
        weight = sum(int(matrix[i][j]) for j in range(n) if i != j)
        degrees[nid] = connections
        weighted_degrees[nid] = weight

    # betweenness-like: nodes that connect otherwise separate clusters
    # simplified: count how many pairs of other nodes a node bridges
    # (using shortest-path approximation via BFS)

    # eigenvector centrality approximation via power iteration
    adj = matrix.astype(float)
    np.fill_diagonal(adj, 0)
    # normalize
    row_sums = adj.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    adj_norm = adj / row_sums

    # power iteration
    v = np.ones(n) / n
    for _ in range(100):
        v_new = adj_norm.T @ v
        norm = np.linalg.norm(v_new)
        if norm > 0:
            v_new /= norm
        if np.allclose(v, v_new, atol=1e-8):
            break
        v = v_new

    eigen_centrality = {node_ids[i]: float(v[i]) for i in range(n)}

    # classify nodes
    classifications = []
    for nid in node_ids:
        deg = degrees[nid]
        eig = eigen_centrality[nid]
        wdeg = weighted_degrees[nid]

        if eig > np.percentile(list(eigen_centrality.values()), 90):
            role = "core"
        elif deg > np.percentile(list(degrees.values()), 75):
            role = "bridge"
        elif deg > 0:
            role = "connected"
        else:
            role = "peripheral"

        classifications.append({
            "node_id": nid,
            "name": node_names.get(nid, "?"),
            "degree": deg,
            "weighted_degree": wdeg,
            "eigen_centrality": round(eig, 6),
            "role": role,
        })

    classifications.sort(key=lambda x: x["eigen_centrality"], reverse=True)

    role_counts = Counter(c["role"] for c in classifications)
    print(f"  Network roles:")
    for role, count in role_counts.most_common():
        print(f"    {role:<12} {count:>3} nodes")

    print(f"\n  Top 15 by eigenvector centrality (doctrinal gravity):")
    for c in classifications[:15]:
        print(f"    {c['node_id']} {c['name'][:45]:<45} "
              f"eig={c['eigen_centrality']:.4f} deg={c['degree']:>3} [{c['role']}]")

    print(f"\n  Peripheral nodes (isolated doctrines):")
    peripheral = [c for c in classifications if c["role"] == "peripheral"]
    for c in peripheral[:10]:
        print(f"    {c['node_id']} {c['name'][:55]}")

    return classifications


# ═════════════════════════════════════════════════════════════════════════════
# 6. MAHĀVĀKYA COMPRESSION TEST
# ═════════════════════════════════════════════════════════════════════════════

def compression_test(echoes, nodes, discourses):
    """
    Measure doctrinal density per speech unit.
    The Gītā hypothesis: it is uniquely compressed compared to other discourses.
    """
    print("\n" + "=" * 60)
    print("6. MAHAVAKYA COMPRESSION TEST")
    print("=" * 60)

    # build echo lookup
    verse_nodes = defaultdict(set)
    for e in echoes:
        verse_nodes[e["verse_id"]].add(e["node_id"])

    # compute compression per discourse
    discourse_compression = []
    for d in discourses:
        verses = d.get("verses", [])
        if not verses or d.get("verse_count", 0) < 10:
            continue

        # count unique nodes in this discourse
        nodes_in_discourse = set()
        for v in verses:
            nodes_in_discourse.update(verse_nodes.get(v, set()))

        n_verses = d.get("verse_count", len(verses))
        n_nodes = len(nodes_in_discourse)
        compression = n_nodes / max(n_verses, 1) * 100  # nodes per 100 verses

        discourse_compression.append({
            "speaker": d.get("speaker", "?"),
            "parva": d.get("parva", "?"),
            "start": d.get("start_verse", ""),
            "verses": n_verses,
            "unique_nodes": n_nodes,
            "compression": round(compression, 2),
        })

    discourse_compression.sort(key=lambda x: x["compression"], reverse=True)

    # parva-level compression
    parva_compression = defaultdict(lambda: {"verses": 0, "nodes": set()})
    for e in echoes:
        parva_compression[e["parva_num"]]["nodes"].add(e["node_id"])
    # need verse counts per parva from corpus
    # approximate from echo data
    parva_verse_ids = defaultdict(set)
    for e in echoes:
        parva_verse_ids[e["parva_num"]].add(e["verse_id"])

    print(f"  Discourses analyzed: {len(discourse_compression)}")
    print(f"\n  Top 15 most compressed discourses (nodes per 100 verses):")
    for d in discourse_compression[:15]:
        pname = PARVAS.get(d["parva"], "?")
        print(f"    {d['speaker']:<20} P{d['parva']} {pname:<15} "
              f"{d['verses']:>5}v {d['unique_nodes']:>3}n "
              f"compression={d['compression']:.1f}")

    print(f"\n  Least compressed (>100 verses):")
    bottom = [d for d in discourse_compression if d["verses"] >= 100]
    bottom.sort(key=lambda x: x["compression"])
    for d in bottom[:10]:
        pname = PARVAS.get(d["parva"], "?")
        print(f"    {d['speaker']:<20} P{d['parva']} {pname:<15} "
              f"{d['verses']:>5}v {d['unique_nodes']:>3}n "
              f"compression={d['compression']:.1f}")

    return discourse_compression


# ═════════════════════════════════════════════════════════════════════════════
# 7. FALSE-FRIEND FILTERING
# ═════════════════════════════════════════════════════════════════════════════

def false_friend_analysis(echoes, nodes, corpus_dir):
    """
    Identify high-noise terms that inflate echo counts.
    Build a noise profile and estimate the clean signal.
    """
    print("\n" + "=" * 60)
    print("7. FALSE-FRIEND ANALYSIS")
    print("=" * 60)

    # count how many echoes each term contributes to
    term_echo_count = Counter()
    for e in echoes:
        for t in e.get("matched_terms", "").split("|"):
            t = t.strip()
            if t:
                term_echo_count[t] += 1

    # get corpus frequency for each term
    corpus_freq = Counter()
    corpus_path = Path(corpus_dir)
    total_verses = 0
    for filepath in sorted(corpus_path.iterdir()):
        if not filepath.is_file():
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'^\d{8}[a-e]?\s+(.*)', line.strip())
                if m:
                    total_verses += 1
                    for word in m.group(1).split():
                        corpus_freq[word] += 1

    # classify terms
    noise_terms = []
    signal_terms = []

    for term, echo_count in term_echo_count.most_common():
        freq = corpus_freq.get(term, 0)
        # noise ratio: what fraction of corpus contains this term?
        if total_verses > 0:
            corpus_ratio = freq / total_verses
        else:
            corpus_ratio = 0

        entry = {
            "term": term,
            "echo_contributions": echo_count,
            "corpus_frequency": freq,
            "corpus_ratio": round(corpus_ratio, 4),
        }

        # high noise: appears in >5% of corpus
        if corpus_ratio > 0.05:
            entry["class"] = "high_noise"
            noise_terms.append(entry)
        elif corpus_ratio > 0.01:
            entry["class"] = "moderate_noise"
            noise_terms.append(entry)
        else:
            entry["class"] = "signal"
            signal_terms.append(entry)

    print(f"  Total unique matched terms: {len(term_echo_count)}")
    print(f"  Signal terms (<1% corpus): {len(signal_terms)}")
    print(f"  Noise terms (>1% corpus): {len(noise_terms)}")

    print(f"\n  Top 15 noisiest terms (inflate echo counts):")
    noise_terms.sort(key=lambda x: x["corpus_ratio"], reverse=True)
    for t in noise_terms[:15]:
        print(f"    {t['term']:<20} corpus={t['corpus_ratio']*100:.1f}% "
              f"echoes={t['echo_contributions']:>5} [{t['class']}]")

    print(f"\n  Top 15 strongest signal terms (rare but echoed):")
    signal_terms.sort(key=lambda x: x["echo_contributions"], reverse=True)
    for t in signal_terms[:15]:
        print(f"    {t['term']:<20} corpus={t['corpus_ratio']*100:.2f}% "
              f"echoes={t['echo_contributions']:>5} [signal]")

    return {"noise": noise_terms[:50], "signal": signal_terms[:50]}


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Dharma Topology — Structural Analysis")
    parser.add_argument("--echoes", required=True)
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--discourses", default=None)
    parser.add_argument("--corpus", default=None, help="Corpus dir (needed for baselines)")
    parser.add_argument("--output", default="../output/topology/")
    parser.add_argument("--skip-baselines", action="store_true", help="Skip slow baseline computation")

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load data
    print("Loading data...")
    with open(args.nodes) as f:
        node_data = json.load(f)
    nodes = node_data["nodes"]

    echoes = []
    with open(args.echoes, "r", encoding="utf-8") as f:
        echoes = list(csv.DictReader(f))
    print(f"  {len(echoes)} echoes, {len(nodes)} nodes")

    discourses = []
    if args.discourses and Path(args.discourses).exists():
        with open(args.discourses) as f:
            discourses = json.load(f)
        print(f"  {len(discourses)} discourse segments")

    strong_echoes = [e for e in echoes if int(e.get("match_strength", 0)) >= 2]
    print(f"  {len(strong_echoes)} strong echoes (strength >= 2)")

    results = {}

    # 1. null baselines
    if args.corpus and not args.skip_baselines:
        results["baselines"] = build_null_baselines(
            args.corpus, nodes, len(strong_echoes), n_trials=30
        )
    else:
        print("\n  [skipping baselines — need --corpus]")

    # 2. co-occurrence
    results["cooccurrence"] = build_cooccurrence(echoes, nodes)

    # 3. speaker signatures
    if discourses:
        results["speakers"] = build_speaker_signatures(discourses, nodes)

    # 4. density gradients
    results["density"] = compute_density_gradients(echoes, nodes)

    # 5. graph centrality
    results["centrality"] = compute_graph_centrality(results["cooccurrence"], nodes)

    # 6. compression test
    if discourses:
        results["compression"] = compression_test(echoes, nodes, discourses)

    # 7. false friends
    if args.corpus:
        results["false_friends"] = false_friend_analysis(echoes, nodes, args.corpus)

    # save all results
    # (convert sets to lists for JSON serialization)
    def jsonify(obj):
        if isinstance(obj, set):
            return sorted(list(obj))
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return obj

    with open(output_dir / "topology_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=jsonify)

    print(f"\n{'='*60}")
    print(f"ALL TOPOLOGY ANALYSES COMPLETE")
    print(f"Results: {output_dir / 'topology_results.json'}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
