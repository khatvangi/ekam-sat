"""
pipeline_runner.py — run the 4-chapter term dictionary pipeline.

reads term dictionary entries + collocational markers,
scans the corpus for occurrences, detects register via
marker co-occurrence, and produces frequency-weighted indices.

three outputs:
  1. per-term frequency table (how often each term appears)
  2. per-term register profile (which markers co-occur)
  3. frequency-weighted indices (SI, H, MHI) per chapter

usage:
  cd src/
  python pipeline_runner.py
"""

import yaml
import re
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from dataclasses import dataclass, asdict

# ─── paths ───────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "term_dictionary" / "entries"
OUTPUT_DIR = ROOT / "output" / "reports"
EVIDENCE_DIR = ROOT / "output" / "evidence"

CHAPTER_FILES = {
    "ch1": "ch1_anatta_drift.yaml",
    "ch2": "ch2_vedic_baseline.yaml",
    "ch3": "ch3_method_drift.yaml",
    "ch4": "ch4_nibbana_drift.yaml",
    "ch5": "ch5_wrong_question.yaml",
}

# ─── reuse existing infrastructure ───────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from corpus_config import get_primary_sources, CorpusSource
from parsers import get_parser


# ─── data structures ─────────────────────────────────────────────

@dataclass
class TermHit:
    """a single corpus hit for a term"""
    term_id: str
    chapter: str
    matched_form: str
    source_file: str
    sutta_id: str
    tradition: str
    stratum: int
    context: str              # ±100 chars around match
    practice_markers: list    # co-occurring practice markers
    system_markers: list      # co-occurring system markers
    ontic_markers: list       # co-occurring ontic markers


# ─── loaders ─────────────────────────────────────────────────────

def load_chapter(chapter):
    filepath = ENTRIES_DIR / CHAPTER_FILES[chapter]
    with open(filepath, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_markers():
    filepath = ENTRIES_DIR / "collocational_markers.yaml"
    with open(filepath, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    markers = {}
    for key, val in raw.items():
        markers[val["id"]] = {
            "register": val["register"],
            "forms": val.get("forms", {}),
        }
    return markers


def build_search_patterns(entries, chapter):
    """
    build regex patterns from each entry's forms.
    returns dict of {entry_id: [compiled_regex_patterns]}
    """
    patterns = {}
    for entry_id, entry in entries.items():
        forms_data = entry.get("forms", {})
        regexes = []
        for lang, form_list in forms_data.items():
            if isinstance(form_list, list):
                for item in form_list:
                    term = None
                    if isinstance(item, dict) and "term" in item and item["term"]:
                        term = str(item["term"])
                    elif isinstance(item, str):
                        term = item
                    if term and len(term) > 1:
                        # escape regex special chars, add word boundary where possible
                        escaped = re.escape(term)
                        regexes.append(escaped)
            elif isinstance(form_list, str) and len(form_list) > 1:
                regexes.append(re.escape(form_list))

        if regexes:
            # combine into single alternation pattern for efficiency
            combined = "|".join(regexes)
            try:
                compiled = re.compile(combined, re.IGNORECASE)
                patterns[entry_id] = compiled
            except re.error:
                print(f"  warning: bad regex for {entry_id}, skipping")
        else:
            print(f"  warning: no searchable forms for {entry_id}")

    return patterns


def build_marker_patterns(markers):
    """
    build regex patterns for collocational markers, grouped by register.
    returns {register: [(marker_id, compiled_regex)]}
    """
    register_patterns = defaultdict(list)
    for mid, info in markers.items():
        forms = info.get("forms", {})
        regexes = []
        for lang, form_list in forms.items():
            if isinstance(form_list, list):
                for form in form_list:
                    if isinstance(form, str) and len(form) > 1:
                        regexes.append(re.escape(form))
            elif isinstance(form_list, str) and len(form_list) > 1:
                regexes.append(re.escape(form_list))

        if regexes:
            combined = "|".join(regexes)
            try:
                compiled = re.compile(combined, re.IGNORECASE)
                register_patterns[info["register"]].append((mid, compiled))
            except re.error:
                pass

    return dict(register_patterns)


# ─── scanning ─────────────────────────────────────────────────────

def scan_corpus(chapter_patterns, marker_patterns):
    """
    scan all primary corpus sources for term occurrences.
    for each hit, check collocational marker co-occurrence.

    chapter_patterns: {chapter: {entry_id: compiled_regex}}
    marker_patterns: {register: [(marker_id, compiled_regex)]}

    returns list of TermHit
    """
    hits = []
    source_count = 0

    for source in get_primary_sources():
        if not source.base_path.exists():
            print(f"  skip (not found): {source.name}")
            continue

        source_count += 1
        parser = get_parser(source.parser)
        tradition = source.tradition.value
        stratum = source.stratum.value
        hit_count = 0

        for segment in parser.parse_directory(source.base_path, source.glob_pattern):
            text = segment.text
            if not text:
                continue

            # search for each chapter's terms
            for chapter, patterns in chapter_patterns.items():
                for entry_id, regex in patterns.items():
                    for match in regex.finditer(text):
                        # extract context window (±100 chars)
                        ctx_start = max(0, match.start() - 100)
                        ctx_end = min(len(text), match.end() + 100)
                        context = text[ctx_start:ctx_end]

                        # detect collocational markers in context
                        practice_m = []
                        system_m = []
                        ontic_m = []

                        for mid, mreg in marker_patterns.get("practice", []):
                            if mreg.search(context):
                                practice_m.append(mid)
                        for mid, mreg in marker_patterns.get("system", []):
                            if mreg.search(context):
                                system_m.append(mid)
                        for mid, mreg in marker_patterns.get("ontic", []):
                            if mreg.search(context):
                                ontic_m.append(mid)

                        hits.append(TermHit(
                            term_id=entry_id,
                            chapter=chapter,
                            matched_form=match.group(),
                            source_file=str(segment.source_file),
                            sutta_id=segment.sutta_id,
                            tradition=tradition,
                            stratum=stratum,
                            context=context,
                            practice_markers=practice_m,
                            system_markers=system_m,
                            ontic_markers=ontic_m,
                        ))
                        hit_count += 1

        print(f"  {source.name}: {hit_count} hits")

    print(f"\ntotal: {len(hits)} hits from {source_count} sources")
    return hits


# ─── aggregation ──────────────────────────────────────────────────

def aggregate_hits(hits, chapters):
    """
    aggregate hits per chapter, per term.
    returns {chapter: {term_id: {count, practice, system, ontic, traditions, strata}}}
    """
    agg = defaultdict(lambda: defaultdict(lambda: {
        "count": 0,
        "practice_markers": 0,
        "system_markers": 0,
        "ontic_markers": 0,
        "traditions": Counter(),
        "strata": Counter(),
    }))

    for hit in hits:
        rec = agg[hit.chapter][hit.term_id]
        rec["count"] += 1
        rec["practice_markers"] += len(hit.practice_markers)
        rec["system_markers"] += len(hit.system_markers)
        rec["ontic_markers"] += len(hit.ontic_markers)
        rec["traditions"][hit.tradition] += 1
        rec["strata"][hit.stratum] += 1

    return dict(agg)


def compute_weighted_mhi(agg_ch3, entries_ch3):
    """
    corpus-weighted MHI: for each term, compute practice vs system
    marker density, weighted by occurrence count.

    MHI = Σ(system_density × count) / Σ((practice_density + system_density) × count)
    """
    total_practice_weighted = 0
    total_system_weighted = 0
    term_profiles = []

    for term_id, rec in agg_ch3.items():
        count = rec["count"]
        if count == 0:
            continue
        p_density = rec["practice_markers"] / count
        s_density = rec["system_markers"] / count

        total_practice_weighted += p_density * count
        total_system_weighted += s_density * count

        # qualitative register from term dictionary
        ic = entries_ch3.get(term_id, {}).get("index_contribution", {})
        mhi_reg = ic.get("MHI_register", "unknown") if isinstance(ic, dict) else "unknown"

        term_profiles.append({
            "term_id": term_id,
            "count": count,
            "practice_density": round(p_density, 3),
            "system_density": round(s_density, 3),
            "assigned_register": mhi_reg,
        })

    denom = total_practice_weighted + total_system_weighted
    mhi = total_system_weighted / denom if denom > 0 else 0.0

    return round(mhi, 3), term_profiles


def compute_weighted_si(agg_chapter, entries, chapter):
    """
    frequency-weighted SI: weight each term's occurrence count
    by its index_contribution role (engagement/opposition).
    """
    engagement_weighted = 0
    opposition_weighted = 0
    details = []

    for term_id, rec in agg_chapter.items():
        count = rec["count"]
        if count == 0:
            continue

        ic = entries.get(term_id, {}).get("index_contribution")
        if not ic or not isinstance(ic, list):
            continue

        for item in ic:
            if item.get("index") != "SI":
                continue
            role = item.get("role", "").strip().lower()
            if role == "engagement":
                engagement_weighted += count
            elif role == "opposition":
                opposition_weighted += count
            elif role == "both":
                engagement_weighted += count * 0.5
                opposition_weighted += count * 0.5

        details.append((term_id, count))

    total = engagement_weighted + opposition_weighted
    si = engagement_weighted / total if total > 0 else 0.0
    return round(si, 3), engagement_weighted, opposition_weighted, details


def compute_weighted_h(agg_chapter, entries, chapter):
    """
    frequency-weighted H: weight each term's occurrence count
    by its H role (numerator/denominator).
    """
    numerator_weighted = 0
    denominator_weighted = 0
    details = []

    for term_id, rec in agg_chapter.items():
        count = rec["count"]
        if count == 0:
            continue

        ic = entries.get(term_id, {}).get("index_contribution")
        if not ic or not isinstance(ic, list):
            continue

        for item in ic:
            if item.get("index") != "H":
                continue
            role = item.get("role", "").strip().lower()
            if "numerator" in role:
                numerator_weighted += count
            elif role == "denominator":
                denominator_weighted += count
            # primary and tracks_hardening are qualitative, not weighted

        details.append((term_id, count))

    total = numerator_weighted + denominator_weighted
    h = numerator_weighted / total if total > 0 else 0.0
    return round(h, 3), numerator_weighted, denominator_weighted, details


# ─── report ───────────────────────────────────────────────────────

def write_report(agg, hits, all_entries, markers):
    """write the final pipeline report"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    outfile = OUTPUT_DIR / "pipeline_results.md"

    lines = []
    w = lambda s="": lines.append(s)

    w("# 5-chapter pipeline results")
    w()
    w(f"**generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    w(f"**total corpus hits:** {len(hits)}")
    w(f"**method:** term dictionary search → collocational marker co-occurrence → weighted indices")
    w()
    w("---")
    w()

    # ─── per-chapter frequency tables ─────────────────────────
    for ch in ["ch1", "ch2", "ch3", "ch4", "ch5"]:
        ch_agg = agg.get(ch, {})
        ch_entries = all_entries[ch]

        w(f"## {ch} — frequency table")
        w()
        w("| # | term | hits | pāli | chinese | practice markers | system markers | ontic markers |")
        w("|---|------|------|------|---------|-----------------|---------------|--------------|")

        sorted_terms = sorted(ch_agg.items(), key=lambda x: x[1]["count"], reverse=True)
        for i, (tid, rec) in enumerate(sorted_terms, 1):
            pali = rec["traditions"].get("pali", 0)
            chinese = rec["traditions"].get("chinese", 0)
            w(f"| {i} | `{tid}` | {rec['count']} | {pali} | {chinese} | "
              f"{rec['practice_markers']} | {rec['system_markers']} | {rec['ontic_markers']} |")

        ch_total = sum(r["count"] for r in ch_agg.values())
        w(f"| | **total** | **{ch_total}** | | | | | |")
        w()
        w("---")
        w()

    # ─── weighted indices ─────────────────────────────────────
    w("## corpus-weighted indices")
    w()
    w("these indices are FREQUENCY-WEIGHTED — unlike the structural")
    w("indices in index_summary.md (which count roles), these weight")
    w("each term's contribution by how often it actually appears in")
    w("the corpus.")
    w()

    results = {}

    # ch2 SI
    ch2_agg = agg.get("ch2", {})
    if ch2_agg:
        si, ew, ow, det = compute_weighted_si(ch2_agg, all_entries["ch2"], "ch2")
        results["ch2_si"] = si
        w(f"### ch2 SI (frequency-weighted) = **{si}**")
        w(f"- engagement-weighted: {ew:.0f}")
        w(f"- opposition-weighted: {ow:.0f}")
        w()

    # ch5 SI
    ch5_agg = agg.get("ch5", {})
    if ch5_agg:
        si, ew, ow, det = compute_weighted_si(ch5_agg, all_entries["ch5"], "ch5")
        results["ch5_si"] = si
        w(f"### ch5 SI (frequency-weighted) = **{si}**")
        w(f"- engagement-weighted: {ew:.0f}")
        w(f"- opposition-weighted: {ow:.0f}")
        w()

    # ch1 H
    ch1_agg = agg.get("ch1", {})
    if ch1_agg:
        h, nw, dw, det = compute_weighted_h(ch1_agg, all_entries["ch1"], "ch1")
        results["ch1_h"] = h
        w(f"### ch1 H (frequency-weighted) = **{h}**")
        w(f"- numerator-weighted: {nw:.0f}")
        w(f"- denominator-weighted: {dw:.0f}")
        w()

    # ch5 H
    if ch5_agg:
        h, nw, dw, det = compute_weighted_h(ch5_agg, all_entries["ch5"], "ch5")
        results["ch5_h"] = h
        w(f"### ch5 H (frequency-weighted) = **{h}**")
        w(f"- numerator-weighted: {nw:.0f}")
        w(f"- denominator-weighted: {dw:.0f}")
        w()

    # ch4 H
    ch4_agg = agg.get("ch4", {})
    if ch4_agg:
        h, nw, dw, det = compute_weighted_h(ch4_agg, all_entries["ch4"], "ch4")
        results["ch4_h"] = h
        w(f"### ch4 H (frequency-weighted) = **{h}**")
        w(f"- numerator-weighted: {nw:.0f}")
        w(f"- denominator-weighted: {dw:.0f}")
        w()

    # ch3 MHI
    ch3_agg = agg.get("ch3", {})
    if ch3_agg:
        mhi, profiles = compute_weighted_mhi(ch3_agg, all_entries["ch3"])
        results["ch3_mhi"] = mhi
        w(f"### ch3 MHI (corpus-weighted) = **{mhi}**")
        w()
        w("| term | hits | practice density | system density | assigned register |")
        w("|------|------|-----------------|---------------|-------------------|")
        for p in sorted(profiles, key=lambda x: x["count"], reverse=True):
            w(f"| `{p['term_id']}` | {p['count']} | {p['practice_density']} | "
              f"{p['system_density']} | {p['assigned_register']} |")
        w()

    # ─── structural vs corpus comparison ──────────────────────
    w("---")
    w()
    w("## structural vs corpus-weighted comparison")
    w()
    w("| chapter | index | structural | corpus-weighted | delta |")
    w("|---------|-------|-----------|-----------------|-------|")

    # load structural indices from index_summary (hardcoded from compute_indices.py results)
    structural = {
        "ch2_si": 0.52,
        "ch1_h": 0.167,
        "ch3_mhi": 0.583,
        "ch4_h": 0.375,
        "ch5_si": 0.389,
        "ch5_h": 0.4,
    }

    for key in ["ch2_si", "ch1_h", "ch3_mhi", "ch4_h", "ch5_si", "ch5_h"]:
        s_val = structural.get(key, "—")
        c_val = results.get(key, "—")
        if isinstance(s_val, (int, float)) and isinstance(c_val, (int, float)):
            delta = round(c_val - s_val, 3)
            sign = "+" if delta > 0 else ""
            w(f"| {key[:3]} | {key[4:].upper()} | {s_val} | {c_val} | {sign}{delta} |")
        else:
            w(f"| {key[:3]} | {key[4:].upper()} | {s_val} | {c_val} | — |")

    w()
    w("---")
    w()

    report = "\n".join(lines)
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\nreport written to: {outfile}")

    # also save raw hit data as json (for further analysis)
    hits_file = EVIDENCE_DIR / "term_dictionary_hits.json"
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    with open(hits_file, "w", encoding="utf-8") as f:
        json.dump(
            [asdict(h) for h in hits[:10000]],  # cap at 10k for file size
            f, ensure_ascii=False, indent=2
        )
    print(f"hit sample saved to: {hits_file} ({min(len(hits), 10000)} entries)")


# ─── main ─────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("5-CHAPTER PIPELINE RUNNER")
    print(f"started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # load term dictionary
    print("\n[1/4] loading term dictionary...")
    all_entries = {}
    chapter_patterns = {}
    for ch in ["ch1", "ch2", "ch3", "ch4", "ch5"]:
        entries = load_chapter(ch)
        all_entries[ch] = entries
        patterns = build_search_patterns(entries, ch)
        chapter_patterns[ch] = patterns
        print(f"  {ch}: {len(patterns)} searchable terms")

    # load collocational markers
    print("\n[2/4] loading collocational markers...")
    markers = load_markers()
    marker_patterns = build_marker_patterns(markers)
    for reg, pats in marker_patterns.items():
        print(f"  {reg}: {len(pats)} marker patterns")

    # scan corpus
    print("\n[3/4] scanning corpus...")
    hits = scan_corpus(chapter_patterns, marker_patterns)

    # aggregate and report
    print("\n[4/4] aggregating and writing report...")
    agg = aggregate_hits(hits, all_entries)
    write_report(agg, hits, all_entries, markers)

    print(f"\ncompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
