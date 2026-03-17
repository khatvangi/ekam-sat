#!/usr/bin/env python3
"""
Sanskrit Paraphrase Family Builder — Ekam Sat Project
=======================================================
Builds stem-based paraphrase families for each doctrinal node.
Instead of matching exact surface terms, groups all corpus words
that share stems with node terms — catching inflections, compounds,
and derivational forms.

Three-pass approach:
  1. Extract stems from existing node terms (stem = first N chars, heuristic)
  2. Search corpus for all words sharing those stems
  3. Group into families and compute expanded echo counts

Output: enriched node families for manual curation, then re-scanning.

Usage:
    python build_paraphrase_families.py \
        --nodes ../data/bg_nodes_v2.json \
        --corpus ../bori/hk \
        --output ../output/paraphrase/
"""

import re
import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


BG_CHAPTERS = set(range(23, 41))

PARVAS = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}

# ─── known synonym groups ────────────────────────────────────────────────────
# these are NOT node-specific. they are cross-cutting concept families
# where different words refer to the same philosophical entity.
# this is the layer that requires Sanskrit knowledge.
SYNONYM_GROUPS = {
    "atman_self": {
        "concept": "the self / individual soul",
        "stems": ["Atm", "Atman", "jIv", "dehin", "zarIr", "kSetrajJ",
                   "puruS", "pratyagAtm", "antarAtm", "paramAtm"],
    },
    "brahman_absolute": {
        "concept": "the absolute / ultimate reality",
        "stems": ["brahm", "akSar", "avyakta", "parampad", "tatpad",
                   "parabrahm", "tattvam"],
    },
    "karma_action": {
        "concept": "action / deed / ritual work",
        "stems": ["karm", "kriyA", "ceST", "pravRtt", "nivRtt",
                   "naiSkarm", "akarm", "vikarm"],
    },
    "jnana_knowledge": {
        "concept": "knowledge / wisdom / understanding",
        "stems": ["jJAn", "vidyA", "prajJA", "buddh", "vivek",
                   "bodh", "cetanA", "vijJAn", "medhA"],
    },
    "bhakti_devotion": {
        "concept": "devotion / worship / self-offering",
        "stems": ["bhakt", "bhaj", "upAs", "prapatti", "zaraN",
                   "namask", "pUj", "sevA", "ananya"],
    },
    "yoga_discipline": {
        "concept": "discipline / union / practice",
        "stems": ["yog", "yukt", "samAdh", "dhyAn", "tapas",
                   "abhyAs", "niyam", "yam", "dhAraN"],
    },
    "dharma_order": {
        "concept": "cosmic order / duty / righteousness",
        "stems": ["dharm", "Rta", "satya", "nyAya", "svadh"],
    },
    "moksha_liberation": {
        "concept": "liberation / freedom / release",
        "stems": ["mokS", "mukti", "mukta", "kaivalya", "nirvAN",
                   "vimukta", "apavarg", "niHzreyas"],
    },
    "maya_illusion": {
        "concept": "illusion / concealment / creative power",
        "stems": ["mAyA", "moha", "ajJAn", "avidyA", "bhrama",
                   "saMmoha", "vimoh"],
    },
    "guna_quality": {
        "concept": "material quality / strand of nature",
        "stems": ["guN", "sattv", "rajas", "tamas", "prakRt",
                   "triguN", "nirguN", "guNAtIt"],
    },
    "kama_desire": {
        "concept": "desire / craving / attachment",
        "stems": ["kAm", "lobh", "tRSNA", "rAga", "icchA",
                   "spRhA", "moha", "saGg", "Asakti"],
    },
    "tyaga_renunciation": {
        "concept": "renunciation / letting go / sacrifice",
        "stems": ["tyAg", "saMnyAs", "vairAgy", "utsRj",
                   "parityAg", "niHsaGg", "nirAz"],
    },
}


def extract_stems(term, min_len=3):
    """
    Extract candidate stems from an HK term.
    Sanskrit stems are typically the invariant prefix before case/tense suffixes.
    Returns stems of decreasing length for fuzzy matching.
    """
    # strip common HK suffixes (case endings, verb forms)
    # these are approximate — not a real morphological analyzer
    suffixes = [
        # nominal case endings (HK)
        "asya", "Aya", "ena", "At", "AnAm", "ebhyaH", "eSu",
        "am", "aH", "au", "AH", "AnAm", "aiH", "Ani",
        "iH", "eH", "yAH", "yA", "Im",
        # verb endings
        "ati", "anti", "eti", "oti", "ate", "ante",
        "tavya", "anIya", "ya",
        # participial
        "vAn", "mAna", "Ana", "ta", "tvA",
    ]

    stems = set()
    # the term itself (if long enough)
    if len(term) >= min_len:
        stems.add(term)

    # try stripping suffixes
    for suf in sorted(suffixes, key=len, reverse=True):
        if term.endswith(suf) and len(term) - len(suf) >= min_len:
            stems.add(term[:len(term) - len(suf)])

    # also try prefix-based stems (first 4-6 chars)
    for length in range(min(len(term), 7), min_len - 1, -1):
        stems.add(term[:length])

    return stems


def build_corpus_word_index(corpus_dir):
    """
    Build a word → {verse_ids} index from the corpus.
    Also returns verse texts for context extraction.
    """
    print("  Building corpus word index...")
    word_index = defaultdict(set)  # word → set of verse_ids
    verse_texts = {}
    corpus_path = Path(corpus_dir)

    for filepath in sorted(corpus_path.iterdir()):
        if not filepath.is_file():
            continue
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r'^(\d{8})[a-e]?\s+(.*)', line.strip())
                if not m:
                    continue
                vid = m.group(1)
                text = m.group(2)

                # skip BG
                if vid[:2] == "06" and int(vid[2:5]) in BG_CHAPTERS:
                    continue

                if vid not in verse_texts:
                    verse_texts[vid] = ""
                verse_texts[vid] += " " + text

                for word in text.split():
                    if len(word) >= 3:
                        word_index[word].add(vid)

    print(f"  Indexed {len(word_index)} unique words across {len(verse_texts)} verses")
    return word_index, verse_texts


def build_families(nodes, word_index, verse_texts):
    """
    For each node, build a paraphrase family by finding all corpus words
    that share stems with the node's terms.
    """
    print("\n  Building paraphrase families...")

    families = []

    for node in nodes:
        nid = node["id"]
        name = node["name"]
        terms = list(set(node.get("hk_terms", []) + node.get("core_hk", [])))

        # extract stems from all node terms
        all_stems = set()
        term_to_stems = {}
        for t in terms:
            stems = extract_stems(t)
            term_to_stems[t] = stems
            all_stems.update(stems)

        # find all corpus words matching any stem (as prefix)
        # require stems to be long enough to avoid false matches:
        # - stems from actual multi-word terms: use full term as stem (exact)
        # - stems from single words: need >= 5 chars to be useful as prefix
        # - stems 3-4 chars: only match exact words (not as prefix)
        matched_words = defaultdict(set)  # corpus_word → matching stems
        for word in word_index:
            for stem in all_stems:
                if len(stem) >= 5 and word.startswith(stem) and word != stem:
                    matched_words[word].add(stem)
                elif len(stem) >= 3 and word == stem:
                    matched_words[word].add(stem)

        # exclude the original terms (we already search those)
        new_words = {w: s for w, s in matched_words.items() if w not in terms}

        # count how many verses each new word appears in
        word_verse_counts = {}
        for w in new_words:
            word_verse_counts[w] = len(word_index.get(w, set()))

        # filter: keep words that are genuine inflections/compounds, not common words
        # criterion 1: frequency cap (>2000 = too common to be discriminative)
        # criterion 2: must share a stem of >= 5 chars (shorter stems are too promiscuous)
        # criterion 3: exclude words that are just common grammatical forms
        common_noise = {"sarve", "sarvaM", "sarvam", "sarvAn", "sarvazaH", "sarva",
                        "sarvataH", "sarvair", "sarveSAM", "sarvabhUtAnAM", "sarveSu",
                        "mahArAja", "mahAn", "mahAtmanaH", "mahAtmanA", "mahAbAho",
                        "mahAbalaH", "mahArathAH", "mahArathaH", "mahat", "mahad",
                        "paraM", "paramaM", "param", "parasparam", "paraMtapa",
                        "vai", "ahaM", "mAm", "tat", "yan", "prabho",
                        "dharmaM", "dharmo", "dharmam", "dharmaH", "dharmeNa",
                        "rAjan", "rAjann", "samare", "samantataH", "punaH", "punar",
                        "prati", "tAm", "manasA", "manaH", "buddhir", "buddhyA",
                        }
        filtered = {w: s for w, s in new_words.items()
                    if 3 <= word_verse_counts.get(w, 0) <= 2000
                    and w not in common_noise
                    and any(len(stem) >= 5 for stem in s)}

        # sort by frequency (most useful expansion terms first)
        sorted_words = sorted(filtered.keys(),
                              key=lambda w: word_verse_counts.get(w, 0),
                              reverse=True)

        # compute expanded echo coverage
        original_verses = set()
        for t in terms:
            original_verses.update(word_index.get(t, set()))

        expanded_verses = set(original_verses)
        for w in sorted_words:
            expanded_verses.update(word_index.get(w, set()))

        gain = len(expanded_verses) - len(original_verses)

        family = {
            "node_id": nid,
            "node_name": name,
            "original_terms": terms,
            "original_coverage": len(original_verses),
            "stem_count": len(all_stems),
            "expansion_words": sorted_words[:50],  # top 50
            "expansion_word_count": len(sorted_words),
            "expanded_coverage": len(expanded_verses),
            "coverage_gain": gain,
            "coverage_gain_pct": round(100 * gain / max(len(original_verses), 1), 1),
            "sample_expansions": [
                {"word": w, "freq": word_verse_counts.get(w, 0),
                 "stems": sorted(filtered[w])}
                for w in sorted_words[:20]
            ],
        }
        families.append(family)

    return families


def build_synonym_expansion(word_index, verse_texts):
    """
    Use the pre-defined synonym groups to find cross-concept connections.
    Returns which synonym stems appear in the corpus and where.
    """
    print("\n  Building synonym group expansions...")

    syn_results = {}

    for group_name, group in SYNONYM_GROUPS.items():
        stems = group["stems"]
        concept = group["concept"]

        # find all corpus words matching any stem in this group
        group_words = defaultdict(set)
        for word in word_index:
            for stem in stems:
                if word.startswith(stem) and len(stem) >= 3:
                    group_words[word].add(stem)

        # count total verse coverage
        all_verses = set()
        stem_coverage = {}
        for stem in stems:
            stem_verses = set()
            for word, matched_stems in group_words.items():
                if stem in matched_stems:
                    stem_verses.update(word_index.get(word, set()))
            stem_coverage[stem] = len(stem_verses)
            all_verses.update(stem_verses)

        syn_results[group_name] = {
            "concept": concept,
            "stems": stems,
            "total_words_found": len(group_words),
            "total_verse_coverage": len(all_verses),
            "stem_coverage": stem_coverage,
            "top_words": sorted(group_words.keys(),
                                key=lambda w: len(word_index.get(w, set())),
                                reverse=True)[:30],
        }

    return syn_results


def main():
    parser = argparse.ArgumentParser(description="Sanskrit Paraphrase Family Builder")
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", default="../output/paraphrase/")

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load nodes
    with open(args.nodes) as f:
        node_data = json.load(f)
    nodes = node_data["nodes"]
    print(f"Loaded {len(nodes)} nodes")

    # build corpus index
    word_index, verse_texts = build_corpus_word_index(args.corpus)

    # build per-node paraphrase families
    families = build_families(nodes, word_index, verse_texts)

    # build synonym group expansions
    syn_results = build_synonym_expansion(word_index, verse_texts)

    # ─── save outputs ────────────────────────────────────────────────────

    # 1. paraphrase families JSON (for manual curation)
    with open(output_dir / "paraphrase_families.json", "w", encoding="utf-8") as f:
        json.dump(families, f, ensure_ascii=False, indent=2)

    # 2. synonym groups JSON
    with open(output_dir / "synonym_groups.json", "w", encoding="utf-8") as f:
        json.dump(syn_results, f, ensure_ascii=False, indent=2)

    # 3. summary CSV
    with open(output_dir / "family_summary.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["node_id", "node_name", "original_terms_count", "original_coverage",
                  "expansion_count", "expanded_coverage", "coverage_gain", "gain_pct"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for fam in families:
            writer.writerow({
                "node_id": fam["node_id"],
                "node_name": fam["node_name"],
                "original_terms_count": len(fam["original_terms"]),
                "original_coverage": fam["original_coverage"],
                "expansion_count": fam["expansion_word_count"],
                "expanded_coverage": fam["expanded_coverage"],
                "coverage_gain": fam["coverage_gain"],
                "gain_pct": fam["coverage_gain_pct"],
            })

    # 4. report
    families.sort(key=lambda x: x["coverage_gain"], reverse=True)

    lines = [
        "=" * 70,
        "SANSKRIT PARAPHRASE FAMILIES",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"Nodes processed: {len(families)}",
        f"Total expansion words found: {sum(f['expansion_word_count'] for f in families)}",
        "",
        "-" * 70,
        "TOP 20 NODES BY COVERAGE GAIN (stem expansion)",
        "-" * 70,
    ]

    for fam in families[:20]:
        lines.append(
            f"\n  [{fam['node_id']}] {fam['node_name'][:50]}"
            f"\n  original: {fam['original_coverage']} verses ({len(fam['original_terms'])} terms)"
            f"\n  expanded: {fam['expanded_coverage']} verses (+{fam['coverage_gain']}, "
            f"+{fam['coverage_gain_pct']}%)"
            f"\n  top expansions: {', '.join(fam['expansion_words'][:8])}"
        )

    # synonym group summary
    lines += [
        "",
        "-" * 70,
        "SYNONYM GROUP COVERAGE",
        "-" * 70,
    ]
    for group_name, sr in sorted(syn_results.items(),
                                  key=lambda x: x[1]["total_verse_coverage"],
                                  reverse=True):
        lines.append(
            f"  {group_name:<25} {sr['concept']:<35} "
            f"words={sr['total_words_found']:>5} verses={sr['total_verse_coverage']:>6}"
        )
        # per-stem coverage
        top_stems = sorted(sr["stem_coverage"].items(), key=lambda x: x[1], reverse=True)[:5]
        for stem, cov in top_stems:
            lines.append(f"    {stem:<15} {cov:>5} verses")

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "paraphrase_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:50]))
    print(f"\nFull report: {output_dir / 'paraphrase_report.txt'}")
    print(f"Families JSON: {output_dir / 'paraphrase_families.json'}")
    print(f"Synonym groups: {output_dir / 'synonym_groups.json'}")


if __name__ == "__main__":
    main()
