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

    # ensemble baseline: simulate FULL node architecture (not single pseudo-nodes)
    # each trial creates a complete set of pseudo-nodes matching the real architecture
    for trial in range(n_trials):
        total_trial_echoes = 0

        # create a full ensemble of pseudo-nodes matching real node count + term distribution
        n_pseudo_nodes = len(nodes)
        for _ in range(n_pseudo_nodes):
            n_terms = random.choice(term_counts)
            n_core = max(2, n_terms // 3)
            if len(candidate_words) < n_terms:
                continue
            terms = random.sample(candidate_words, n_terms)
            core = terms[:n_core]

            for vid, text in corpus.items():
                # use word-boundary matching: split text into tokens
                text_tokens = set(text.split())
                matches = sum(1 for t in core if t in text_tokens)
                if matches >= 2:
                    total_trial_echoes += 1

        random_echo_counts.append(total_trial_echoes)

        # high-frequency ensemble control
        hf_total = 0
        for _ in range(n_pseudo_nodes):
            n_core = max(2, random.choice(term_counts) // 3)
            hf_terms = random.sample(high_freq_words, min(n_core, len(high_freq_words)))
            for vid, text in corpus.items():
                text_tokens = set(text.split())
                matches = sum(1 for t in hf_terms if t in text_tokens)
                if matches >= 2:
                    hf_total += 1
        highfreq_echo_counts.append(hf_total)

        if (trial + 1) % 5 == 0:
            print(f"    trial {trial+1}/{n_trials} (ensemble of {n_pseudo_nodes} pseudo-nodes each)")

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

    # compute per-node frequencies for normalization
    node_freq = np.zeros(n)
    for vid, node_set in verse_nodes.items():
        for nid in node_set:
            if nid in node_idx:
                node_freq[node_idx[nid]] += 1

    total_verses = len(verse_nodes)

    # compute PMI (pointwise mutual information) for each pair
    # PMI(a,b) = log2(P(a,b) / (P(a) * P(b)))
    # also compute Jaccard: |A∩B| / |A∪B|
    pairs_raw = []
    pairs_pmi = []
    pairs_jaccard = []

    for i in range(n):
        for j in range(i + 1, n):
            if cooc[i][j] > 0:
                raw = int(cooc[i][j])
                p_ab = raw / max(total_verses, 1)
                p_a = node_freq[i] / max(total_verses, 1)
                p_b = node_freq[j] / max(total_verses, 1)
                pmi = np.log2(p_ab / max(p_a * p_b, 1e-10)) if p_ab > 0 else 0
                jaccard = raw / max(node_freq[i] + node_freq[j] - raw, 1)

                pairs_raw.append((node_ids[i], node_ids[j], raw))
                pairs_pmi.append((node_ids[i], node_ids[j], round(pmi, 3)))
                pairs_jaccard.append((node_ids[i], node_ids[j], round(jaccard, 4)))

    pairs_raw.sort(key=lambda x: x[2], reverse=True)
    pairs_pmi.sort(key=lambda x: x[2], reverse=True)
    pairs_jaccard.sort(key=lambda x: x[2], reverse=True)

    # cluster stability test: run connected components at multiple thresholds
    # using PMI-based edges (frequency-normalized)
    from collections import deque

    def find_clusters_at_threshold(pair_list, pct):
        """find connected components using top pct% of pairs."""
        if not pair_list:
            return []
        cutoff = np.percentile([p[2] for p in pair_list if p[2] > 0], 100 - pct)
        strong = [(a, b) for a, b, c in pair_list if c >= cutoff]
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

    # test stability across thresholds
    stability = {}
    for pct in [5, 10, 15, 20, 30]:
        cl = find_clusters_at_threshold(pairs_pmi, pct)
        stability[f"top_{pct}pct"] = {"n_clusters": len(cl), "sizes": [len(c) for c in cl]}

    # use top 10% PMI as primary clustering
    clusters = find_clusters_at_threshold(pairs_pmi, 10)

    node_names = {n["id"]: n["name"] for n in nodes}

    print(f"  Verses with 2+ nodes: {sum(1 for ns in verse_nodes.values() if len(ns) >= 2)}")
    print(f"  Node pairs with co-occurrence: {len([p for p in pairs_raw if p[2] > 0])}")
    print(f"  Clusters (PMI top 10%): {len(clusters)}")

    print(f"\n  Cluster stability across PMI thresholds:")
    for thresh, info in sorted(stability.items()):
        print(f"    {thresh}: {info['n_clusters']} clusters, sizes={info['sizes']}")

    print(f"\n  Top 10 by raw co-occurrence:")
    for a, b, c in pairs_raw[:10]:
        print(f"    {a} × {b}: {c} raw")

    print(f"\n  Top 10 by PMI (frequency-normalized — true doctrinal affinity):")
    for a, b, c in pairs_pmi[:10]:
        print(f"    {a} × {b}: PMI={c}")
        print(f"      {node_names.get(a, '?')[:40]}")
        print(f"      {node_names.get(b, '?')[:40]}")

    print(f"\n  Top 10 by Jaccard (proportional overlap):")
    for a, b, c in pairs_jaccard[:10]:
        print(f"    {a} × {b}: J={c}")

    print(f"\n  Doctrinal clusters (strong co-occurrence):")
    for i, cluster in enumerate(clusters):
        print(f"\n    Cluster {i+1} ({len(cluster)} nodes):")
        for nid in cluster:
            print(f"      {nid}: {node_names.get(nid, '?')[:55]}")

    return {
        "cooccurrence_matrix": cooc.tolist(),
        "node_ids": node_ids,
        "top_pairs_raw": [(a, b, c) for a, b, c in pairs_raw[:50]],
        "top_pairs_pmi": [(a, b, c) for a, b, c in pairs_pmi[:50]],
        "top_pairs_jaccard": [(a, b, c) for a, b, c in pairs_jaccard[:50]],
        "clusters_pmi": clusters,
        "cluster_stability": stability,
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

        # breadth density: unique nodes per 100 verses
        breadth = len(sp["unique_nodes"]) / max(sp["total_verses"], 1) * 100
        # intensity: total node-mentions per 100 verses (rewards sustained teaching)
        total_mentions = sum(sp["node_counts"].values())
        intensity = total_mentions / max(sp["total_verses"], 1) * 100
        # concentration: how focused on top nodes (Herfindahl index)
        # high = specialized teacher, low = broad teacher
        if total_mentions > 0:
            shares = [c / total_mentions for c in sp["node_counts"].values()]
            herfindahl = sum(s * s for s in shares)
        else:
            herfindahl = 0

        sig = {
            "speaker": speaker,
            "total_verses": sp["total_verses"],
            "total_discourses": sp["total_discourses"],
            "unique_nodes": len(sp["unique_nodes"]),
            "breadth_density": round(breadth, 2),
            "teaching_intensity": round(intensity, 2),
            "concentration_hhi": round(herfindahl, 4),
            "top_nodes": [(nid, count) for nid, count in top],
            "absent_count": len(absent),
        }
        signatures.append(sig)

    print(f"  Speakers with 100+ verses: {len(signatures)}")
    print(f"\n  {'Speaker':<18} {'Verses':>6} {'Nodes':>5} {'Breadth':>8} {'Intensity':>10} {'HHI':>6}")
    print(f"  {'':─<18} {'':─>6} {'':─>5} {'':─>8} {'':─>10} {'':─>6}")
    for sig in signatures[:20]:
        print(f"  {sig['speaker']:<18} {sig['total_verses']:>6} {sig['unique_nodes']:>5} "
              f"{sig['breadth_density']:>7.1f} {sig['teaching_intensity']:>9.1f} "
              f"{sig['concentration_hhi']:>6.3f}")

    print(f"\n  Top 5 by teaching intensity (sustained depth, not just breadth):")
    by_intensity = sorted(signatures, key=lambda x: x["teaching_intensity"], reverse=True)
    for sig in by_intensity[:5]:
        print(f"    {sig['speaker']:<20} intensity={sig['teaching_intensity']:.1f}/100v "
              f"breadth={sig['breadth_density']:.1f}/100v")
        for nid, count in sig["top_nodes"][:3]:
            print(f"      → {nid} ({node_names.get(nid, '?')[:40]}): {count}")

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

    # compute eigenvector centrality on BOTH raw and PMI-normalized graphs
    def power_iteration_centrality(adj_matrix):
        """eigenvector centrality via power iteration."""
        a = adj_matrix.astype(float).copy()
        np.fill_diagonal(a, 0)
        rs = a.sum(axis=1, keepdims=True)
        rs[rs == 0] = 1
        a_norm = a / rs
        v = np.ones(len(a)) / len(a)
        for _ in range(200):
            v_new = a_norm.T @ v
            nm = np.linalg.norm(v_new)
            if nm > 0:
                v_new /= nm
            if np.allclose(v, v_new, atol=1e-10):
                break
            v = v_new
        return v

    # raw co-occurrence centrality
    eig_raw = power_iteration_centrality(matrix)
    eigen_raw = {node_ids[i]: float(eig_raw[i]) for i in range(n)}

    # PMI-weighted centrality (frequency-normalized)
    pmi_matrix = np.zeros((n, n))
    node_freq_arr = np.zeros(n)
    verse_nodes_flat = defaultdict(set)
    for e in cooc_data.get("_echoes_ref", []):
        pass  # not available here, use node_freq from diagonal

    # reconstruct node frequencies from co-occurrence diagonal + row sums
    for i in range(n):
        node_freq_arr[i] = sum(1 for j in range(n) if matrix[i][j] > 0)

    total_v = max(sum(matrix[i][j] for i in range(n) for j in range(i+1, n)), 1)
    for i in range(n):
        for j in range(i+1, n):
            if matrix[i][j] > 0:
                p_ab = matrix[i][j] / total_v
                p_a = sum(matrix[i]) / total_v
                p_b = sum(matrix[j]) / total_v
                pmi_val = np.log2(p_ab / max(p_a * p_b, 1e-15))
                pmi_matrix[i][j] = max(pmi_val, 0)  # positive PMI only
                pmi_matrix[j][i] = pmi_matrix[i][j]

    eig_pmi = power_iteration_centrality(pmi_matrix)
    eigen_pmi = {node_ids[i]: float(eig_pmi[i]) for i in range(n)}

    # rank stability: compare raw vs PMI rankings
    raw_rank = {nid: rank for rank, nid in enumerate(sorted(eigen_raw, key=eigen_raw.get, reverse=True))}
    pmi_rank = {nid: rank for rank, nid in enumerate(sorted(eigen_pmi, key=eigen_pmi.get, reverse=True))}

    # use average of both for final classification
    eigen_centrality = {nid: (eigen_raw.get(nid, 0) + eigen_pmi.get(nid, 0)) / 2 for nid in node_ids}

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

    print(f"\n  Top 15 by combined centrality (raw + PMI averaged):")
    print(f"  {'Node':<6} {'Name':<42} {'Combined':>8} {'RawRank':>7} {'PMIRank':>7} {'Stable?':>7}")
    for c in classifications[:15]:
        nid = c["node_id"]
        rr = raw_rank.get(nid, 999)
        pr = pmi_rank.get(nid, 999)
        stable = "yes" if abs(rr - pr) <= 10 else "NO"
        print(f"    {nid:<6} {c['name'][:40]:<42} "
              f"{c['eigen_centrality']:.4f} {rr:>5} {pr:>7} {stable:>7}")

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

        # breadth compression: unique nodes per 100 verses
        breadth_comp = n_nodes / max(n_verses, 1) * 100

        # intensity compression: total node-hits per 100 verses
        total_hits = sum(len(verse_nodes.get(v, set())) for v in verses)
        intensity_comp = total_hits / max(n_verses, 1) * 100

        # sliding window peak: max unique nodes in any 20-verse window
        window_size = min(20, len(verses))
        peak_window = 0
        for w_start in range(0, len(verses) - window_size + 1):
            window_nodes = set()
            for v in verses[w_start:w_start + window_size]:
                window_nodes.update(verse_nodes.get(v, set()))
            peak_window = max(peak_window, len(window_nodes))

        # cluster richness: how many distinct node-pairs co-occur (not just individual nodes)
        node_pairs_in_discourse = set()
        for v in verses:
            v_nodes = verse_nodes.get(v, set())
            for a, b in combinations(sorted(v_nodes), 2):
                node_pairs_in_discourse.add((a, b))

        discourse_compression.append({
            "speaker": d.get("speaker", "?"),
            "parva": d.get("parva", "?"),
            "start": d.get("start_verse", ""),
            "verses": n_verses,
            "unique_nodes": n_nodes,
            "breadth_compression": round(breadth_comp, 2),
            "intensity_compression": round(intensity_comp, 2),
            "peak_window_20v": peak_window,
            "cluster_richness": len(node_pairs_in_discourse),
        })

    discourse_compression.sort(key=lambda x: x["intensity_compression"], reverse=True)

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
    print(f"\n  Top 15 by teaching intensity (node-hits per 100 verses):")
    print(f"  {'Speaker':<18} {'Parva':<12} {'Verses':>5} {'Nodes':>5} {'Breadth':>7} "
          f"{'Intens':>6} {'Peak20':>6} {'Pairs':>5}")
    for d in discourse_compression[:15]:
        pname = PARVAS.get(d["parva"], "?")
        print(f"    {d['speaker']:<18} {pname:<12} {d['verses']:>5} {d['unique_nodes']:>5} "
              f"{d['breadth_compression']:>6.1f} {d['intensity_compression']:>6.1f} "
              f"{d['peak_window_20v']:>5} {d['cluster_richness']:>5}")

    print(f"\n  Least compressed (>100 verses, by intensity):")
    bottom = [d for d in discourse_compression if d["verses"] >= 100]
    bottom.sort(key=lambda x: x["intensity_compression"])
    for d in bottom[:10]:
        pname = PARVAS.get(d["parva"], "?")
        print(f"    {d['speaker']:<18} {pname:<12} {d['verses']:>5} "
              f"intensity={d['intensity_compression']:.1f}")

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

    # context-sensitive false-friend detection
    # a term is a false friend if it is common AND appears indiscriminately
    # across doctrinal and non-doctrinal contexts.
    # measure: what % of a term's corpus occurrences are in echo-tagged verses?
    # high selectivity = the term mostly appears where doctrinal content is → signal
    # low selectivity = the term appears everywhere regardless → noise

    # build set of echo-tagged verses
    echo_verse_ids = set(e["verse_id"] for e in echoes)

    # for each term, count occurrences in echo vs non-echo verses
    term_in_echo = Counter()
    term_in_non_echo = Counter()
    corpus_path_ff = Path(corpus_dir)
    for filepath in sorted(corpus_path_ff.iterdir()):
        if not filepath.is_file():
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m_ff = re.match(r'^(\d{8})[a-e]?\s+(.*)', line.strip())
                if m_ff:
                    vid = m_ff.group(1)
                    text = m_ff.group(2)
                    is_echo = vid in echo_verse_ids
                    for word in text.split():
                        if word in term_echo_count:
                            if is_echo:
                                term_in_echo[word] += 1
                            else:
                                term_in_non_echo[word] += 1

    classified = []
    for term, echo_contribs in term_echo_count.most_common():
        freq = corpus_freq.get(term, 0)
        corpus_ratio = freq / max(total_verses, 1)
        in_echo = term_in_echo.get(term, 0)
        in_non = term_in_non_echo.get(term, 0)
        total_occ = in_echo + in_non

        # selectivity: fraction of occurrences in echo-tagged verses
        selectivity = in_echo / max(total_occ, 1)

        # classify using both frequency and selectivity
        if corpus_ratio > 0.05 and selectivity < 0.3:
            cls = "high_noise"
        elif corpus_ratio > 0.01 and selectivity < 0.4:
            cls = "contextual_noise"
        elif corpus_ratio > 0.01 and selectivity >= 0.4:
            cls = "high_freq_but_selective"
        else:
            cls = "signal"

        classified.append({
            "term": term,
            "echo_contributions": echo_contribs,
            "corpus_frequency": freq,
            "corpus_ratio": round(corpus_ratio, 4),
            "selectivity": round(selectivity, 3),
            "class": cls,
        })

    noise_terms = [t for t in classified if "noise" in t["class"]]
    signal_terms = [t for t in classified if t["class"] == "signal"]
    selective_highfreq = [t for t in classified if t["class"] == "high_freq_but_selective"]

    print(f"  Total unique matched terms: {len(term_echo_count)}")
    print(f"  Signal (rare + selective): {len(signal_terms)}")
    print(f"  High-freq but selective: {len(selective_highfreq)}")
    print(f"  Noise (common + indiscriminate): {len(noise_terms)}")

    print(f"\n  Context-sensitive noise (common AND non-selective):")
    noise_terms.sort(key=lambda x: x["corpus_ratio"], reverse=True)
    for t in noise_terms[:10]:
        print(f"    {t['term']:<20} corpus={t['corpus_ratio']*100:.1f}% "
              f"selectivity={t['selectivity']:.2f} echoes={t['echo_contributions']:>5} [{t['class']}]")

    print(f"\n  High-frequency BUT selective (common yet doctrinally discriminative):")
    selective_highfreq.sort(key=lambda x: x["selectivity"], reverse=True)
    for t in selective_highfreq[:10]:
        print(f"    {t['term']:<20} corpus={t['corpus_ratio']*100:.1f}% "
              f"selectivity={t['selectivity']:.2f} echoes={t['echo_contributions']:>5}")

    print(f"\n  Top 10 strongest signal terms:")
    signal_terms.sort(key=lambda x: x["echo_contributions"], reverse=True)
    for t in signal_terms[:10]:
        print(f"    {t['term']:<20} corpus={t['corpus_ratio']*100:.2f}% "
              f"selectivity={t['selectivity']:.2f} echoes={t['echo_contributions']:>5}")

    return {"noise": noise_terms, "selective_highfreq": selective_highfreq[:30],
            "signal": signal_terms[:50]}


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
