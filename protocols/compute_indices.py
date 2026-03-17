"""
compute_indices.py — aggregate term dictionary index_contribution fields
into per-chapter SI, H, and MHI values.

three indices:
  SI  (stance index)    — engagement vs opposition (ch2, ch5)
  H   (hardening index) — therapeutic vs ontic language (ch1, ch5)
  MHI (method hardening) — practice vs system register (ch3)

reads:  term_dictionary/entries/*.yaml
        term_dictionary/entries/collocational_markers.yaml
writes: output/reports/index_summary.md

usage:
  python compute_indices.py
"""

import yaml
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date

# ─── paths ───────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "term_dictionary" / "entries"
OUTPUT_DIR = ROOT / "output" / "reports"

CHAPTER_FILES = {
    "ch1": "ch1_anatta_drift.yaml",
    "ch2": "ch2_vedic_baseline.yaml",
    "ch3": "ch3_method_drift.yaml",
    "ch4": "ch4_nibbana_drift.yaml",
    "ch5": "ch5_wrong_question.yaml",
}

MARKERS_FILE = ENTRIES_DIR / "collocational_markers.yaml"


# ─── loaders ─────────────────────────────────────────────────────

def load_chapter(chapter):
    """load all entries for a chapter, return dict of entry_id → entry"""
    filepath = ENTRIES_DIR / CHAPTER_FILES[chapter]
    with open(filepath, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_markers():
    """load collocational markers, return dict of marker_id → {register, forms}"""
    with open(MARKERS_FILE, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    markers = {}
    for key, val in raw.items():
        markers[val["id"]] = {
            "register": val["register"],
            "forms": val.get("forms", {}),
            "concept": val.get("concept", ""),
        }
    return markers


# ─── SI computation ──────────────────────────────────────────────

def compute_si(chapter, entries):
    """
    stance index: engagement vs opposition.
    SI = engagement / (engagement + opposition).
    range: 0.0 (pure opposition) to 1.0 (pure engagement).
    entries with role="both" count 0.5 to each side.

    returns dict with counts, value, and per-entry details.
    """
    engagement = 0
    opposition = 0
    both = 0
    details = []

    for entry_id, entry in entries.items():
        ic = entry.get("index_contribution")
        if not ic or not isinstance(ic, list):
            continue

        for item in ic:
            if item.get("index") != "SI":
                continue
            role = item.get("role", "").strip().lower()
            note = item.get("note", "")

            if role == "engagement":
                engagement += 1
                details.append((entry_id, "engagement", note))
            elif role == "opposition":
                opposition += 1
                details.append((entry_id, "opposition", note))
            elif role == "both":
                both += 1
                details.append((entry_id, "both", note))
            elif role == "methodological":
                # methodological contributions don't shift the stance ratio
                details.append((entry_id, "methodological", note))

    total = engagement + opposition + both
    if total == 0:
        return None

    # "both" splits evenly
    si_value = (engagement + both * 0.5) / total

    return {
        "engagement": engagement,
        "opposition": opposition,
        "both": both,
        "total": total,
        "si_value": round(si_value, 3),
        "details": details,
    }


# ─── H computation ───────────────────────────────────────────────

def compute_h(chapter, entries):
    """
    hardening index: therapeutic/release language vs ontic/systematic language.
    H = numerator / (numerator + denominator).
    range: 0.0 (pure therapeutic) to 1.0 (pure ontic).

    roles:
      - numerator: evidence of hardening (ontic, systematic, definitional)
      - denominator: baseline (therapeutic, release-oriented, practice)
      - primary: the anchor term whose drift IS the hardening
      - tracks hardening: qualitative — shows the trajectory but doesn't
        directly shift the ratio
    """
    numerator = 0
    denominator = 0
    primary = 0
    tracks = 0
    details = []

    for entry_id, entry in entries.items():
        ic = entry.get("index_contribution")
        if not ic or not isinstance(ic, list):
            continue

        for item in ic:
            if item.get("index") != "H":
                continue
            role = item.get("role", "").strip().lower()
            note = item.get("note", "")

            if "numerator" in role:
                numerator += 1
                details.append((entry_id, "numerator", note))
            elif role == "denominator":
                denominator += 1
                details.append((entry_id, "denominator", note))
            elif role == "primary":
                primary += 1
                details.append((entry_id, "primary", note))
            elif "tracks" in role or "hardening" in role:
                tracks += 1
                details.append((entry_id, "tracks_hardening", note))

    total = numerator + denominator + primary + tracks
    if total == 0:
        return None

    # H ratio only from numerator/denominator pair
    # primary and tracks_hardening are qualitative anchors
    denom_sum = numerator + denominator
    h_value = numerator / denom_sum if denom_sum > 0 else 0.0

    return {
        "numerator": numerator,
        "denominator": denominator,
        "primary": primary,
        "tracks_hardening": tracks,
        "total": total,
        "h_value": round(h_value, 3),
        "details": details,
    }


# ─── MHI computation ─────────────────────────────────────────────

def compute_mhi(entries):
    """
    method hardening index: practice vs system register.
    MHI = (system + 0.5 * transition) / total.
    range: 0.0 (pure practice) to 1.0 (pure system).

    registers:
      - practice: term still in experiential/doing register
      - system: term has moved to enumerative/categorical register
      - practice → system: term shows the transition
    """
    practice = 0
    system = 0
    transition = 0
    details = []

    for entry_id, entry in entries.items():
        ic = entry.get("index_contribution")
        if not ic or not isinstance(ic, dict):
            continue

        reg = ic.get("MHI_register", "")
        markers = ic.get("collocational_markers", [])
        direction = ic.get("drift_direction", "")

        if reg == "practice":
            practice += 1
            details.append((entry_id, "practice", direction, markers))
        elif reg == "system":
            system += 1
            details.append((entry_id, "system", direction, markers))
        elif "→" in reg or "->" in reg:
            transition += 1
            details.append((entry_id, "transition", direction, markers))

    total = practice + system + transition
    if total == 0:
        return None

    mhi_value = (system + 0.5 * transition) / total

    return {
        "practice": practice,
        "system": system,
        "transition": transition,
        "total": total,
        "mhi_value": round(mhi_value, 3),
        "details": details,
    }


# ─── marker register summary ─────────────────────────────────────

def summarize_markers(markers):
    """tally markers per register"""
    register_counts = Counter()
    for mid, info in markers.items():
        register_counts[info["register"]] += 1
    return dict(register_counts)


# ─── term list extraction ─────────────────────────────────────────

def extract_search_terms(chapter, entries):
    """
    extract pali/sanskrit forms from each entry for corpus searching.
    forms are structured as: {pali: [{term, grammar, ...}], sanskrit: [...]}
    returns list of (entry_id, [term_strings])
    """
    results = []
    for entry_id, entry in entries.items():
        forms_data = entry.get("forms", {})
        all_forms = []
        for lang, form_list in forms_data.items():
            if isinstance(form_list, list):
                for item in form_list:
                    if isinstance(item, dict) and "term" in item and item["term"]:
                        all_forms.append(str(item["term"]))
                    elif isinstance(item, str):
                        all_forms.append(item)
            elif isinstance(form_list, str):
                all_forms.append(form_list)
        results.append((entry_id, all_forms))
    return results


# ─── report generation ────────────────────────────────────────────

def generate_report():
    """main report generation — writes index_summary.md"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    lines = []
    w = lambda s="": lines.append(s)

    w("# index computation summary")
    w()
    w(f"**generated:** {date.today().isoformat()}")
    w("**source:** `term_dictionary/entries/`")
    w("**method:** qualitative aggregation of `index_contribution` fields")
    w()
    w("> these are STRUCTURAL indices derived from the term dictionary's")
    w("> role assignments. they show the overall shape of each chapter's")
    w("> semantic field. CORPUS-BASED numeric indices (frequency-weighted)")
    w("> require running the evidence ledger against the full corpus (task #35).")
    w()
    w("---")
    w()

    # load all chapters
    chapters = {}
    for ch in ["ch1", "ch2", "ch3", "ch4", "ch5"]:
        chapters[ch] = load_chapter(ch)

    markers = load_markers()

    # ─── chapter 2: SI ────────────────────────────────────────
    w("## chapter 2 — stance index (SI)")
    w()
    si_ch2 = compute_si("ch2", chapters["ch2"])
    if si_ch2:
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| engagement contributions | {si_ch2['engagement']} |")
        w(f"| opposition contributions | {si_ch2['opposition']} |")
        w(f"| both (split) | {si_ch2['both']} |")
        w(f"| total SI contributions | {si_ch2['total']} |")
        w(f"| **SI value** | **{si_ch2['si_value']}** |")
        w()
        w("**interpretation:** SI = 1.0 means pure engagement with vedic concepts;")
        w("SI = 0.0 means pure opposition. the buddha's stance is neither — he")
        w("selectively engages and opposes, which is the argument of ch2.")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | role | note |")
        w("|-------|------|------|")
        for eid, role, note in si_ch2["details"]:
            # truncate note for table readability
            short_note = note[:80] + "..." if len(note) > 80 else note
            w(f"| `{eid}` | {role} | {short_note} |")
        w()
    else:
        w("*no SI contributions found in ch2*")
        w()

    w("---")
    w()

    # ─── chapter 5: SI + H ────────────────────────────────────
    w("## chapter 5 — stance index (SI) + hardening index (H)")
    w()
    si_ch5 = compute_si("ch5", chapters["ch5"])
    h_ch5 = compute_h("ch5", chapters["ch5"])

    if si_ch5:
        w("### SI (stance toward creator-lord concept)")
        w()
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| engagement contributions | {si_ch5['engagement']} |")
        w(f"| opposition contributions | {si_ch5['opposition']} |")
        w(f"| both (split) | {si_ch5['both']} |")
        w(f"| total SI contributions | {si_ch5['total']} |")
        w(f"| **SI value** | **{si_ch5['si_value']}** |")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | role | note |")
        w("|-------|------|------|")
        for eid, role, note in si_ch5["details"]:
            short_note = note[:80] + "..." if len(note) > 80 else note
            w(f"| `{eid}` | {role} | {short_note} |")
        w()

    if h_ch5:
        w("### H (hardening: ethical rejection → logical refutation)")
        w()
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| numerator (hardened/ontic) | {h_ch5['numerator']} |")
        w(f"| denominator (therapeutic/release) | {h_ch5['denominator']} |")
        w(f"| primary (anchor term) | {h_ch5['primary']} |")
        w(f"| tracks hardening (qualitative) | {h_ch5['tracks_hardening']} |")
        w(f"| total H contributions | {h_ch5['total']} |")
        w(f"| **H value** | **{h_ch5['h_value']}** |")
        w()
        w("**interpretation:** H = 0.0 means all therapeutic/release language;")
        w("H = 1.0 means all ontic/systematic. for ch5, this tracks the shift")
        w("from 'the buddha declines the question' to 'the buddha logically refutes.'")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | role | note |")
        w("|-------|------|------|")
        for eid, role, note in h_ch5["details"]:
            short_note = note[:80] + "..." if len(note) > 80 else note
            w(f"| `{eid}` | {role} | {short_note} |")
        w()

    w("---")
    w()

    # ─── chapter 1: H ─────────────────────────────────────────
    w("## chapter 1 — hardening index (H)")
    w()
    h_ch1 = compute_h("ch1", chapters["ch1"])
    if h_ch1:
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| numerator (hardened/ontic) | {h_ch1['numerator']} |")
        w(f"| denominator (therapeutic/release) | {h_ch1['denominator']} |")
        w(f"| primary (anchor term) | {h_ch1['primary']} |")
        w(f"| tracks hardening (qualitative) | {h_ch1['tracks_hardening']} |")
        w(f"| total H contributions | {h_ch1['total']} |")
        w(f"| **H value** | **{h_ch1['h_value']}** |")
        w()
        w("**interpretation:** for ch1, this tracks the shift from 'anattā as")
        w("therapeutic instruction applied to aggregates' to 'anattā as universal")
        w("ontological claim about the non-existence of self.'")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | role | note |")
        w("|-------|------|------|")
        for eid, role, note in h_ch1["details"]:
            short_note = note[:80] + "..." if len(note) > 80 else note
            w(f"| `{eid}` | {role} | {short_note} |")
        w()
    else:
        w("*no H contributions found in ch1*")
        w()

    w("---")
    w()

    # ─── chapter 4: H ────────────────────────────────────────
    w("## chapter 4 — hardening index (H)")
    w()
    h_ch4 = compute_h("ch4", chapters["ch4"])
    if h_ch4:
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| numerator (hardened/ontic) | {h_ch4['numerator']} |")
        w(f"| denominator (therapeutic/release) | {h_ch4['denominator']} |")
        w(f"| primary (anchor term) | {h_ch4['primary']} |")
        w(f"| tracks hardening (qualitative) | {h_ch4['tracks_hardening']} |")
        w(f"| total H contributions | {h_ch4['total']} |")
        w(f"| **H value** | **{h_ch4['h_value']}** |")
        w()
        w("**interpretation:** for ch4, this tracks the shift from 'nibbāna as")
        w("fire-going-out (practice-register metaphor)' to 'nibbāna as asaṅkhata")
        w("dhamma (ontological category).' higher H = more reification of the goal.")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | role | note |")
        w("|-------|------|------|")
        for eid, role, note in h_ch4["details"]:
            short_note = note[:80] + "..." if len(note) > 80 else note
            w(f"| `{eid}` | {role} | {short_note} |")
        w()
    else:
        w("*no H contributions found in ch4*")
        w()

    w("---")
    w()

    # ─── chapter 3: MHI ───────────────────────────────────────
    w("## chapter 3 — method hardening index (MHI)")
    w()
    mhi = compute_mhi(chapters["ch3"])
    if mhi:
        w(f"| metric | value |")
        w(f"|--------|-------|")
        w(f"| practice register | {mhi['practice']} |")
        w(f"| system register | {mhi['system']} |")
        w(f"| practice → system (transition) | {mhi['transition']} |")
        w(f"| total terms | {mhi['total']} |")
        w(f"| **MHI value** | **{mhi['mhi_value']}** |")
        w()
        w("**interpretation:** MHI = 0.0 means all terms remain in practice")
        w("register; MHI = 1.0 means all have moved to system register.")
        w(f"MHI = {mhi['mhi_value']} reflects that most ch3 terms ({mhi['transition']}/12)")
        w("show the transition, while a few started or ended purely in one register.")
        w()
        w("**per-entry breakdown:**")
        w()
        w("| entry | register | drift direction | collocational markers |")
        w("|-------|----------|----------------|-----------------------|")
        for item in mhi["details"]:
            eid, reg, direction, mrk = item
            short_dir = direction[:60] + "..." if len(direction) > 60 else direction
            markers_str = ", ".join(mrk[:4]) if mrk else "—"
            w(f"| `{eid}` | {reg} | {short_dir} | {markers_str} |")
        w()
    else:
        w("*no MHI contributions found in ch3*")
        w()

    w("---")
    w()

    # ─── collocational markers summary ────────────────────────
    w("## collocational markers — register distribution")
    w()
    marker_summary = summarize_markers(markers)
    w("| register | count |")
    w("|----------|-------|")
    for reg in ["practice", "system", "ontic"]:
        w(f"| {reg} | {marker_summary.get(reg, 0)} |")
    w(f"| **total** | **{sum(marker_summary.values())}** |")
    w()
    w("these markers are used to DETECT register in corpus text.")
    w("when a primary term co-occurs with practice-register markers")
    w("(bhaveti, viharati, pajahati...), it signals method-shape language.")
    w("when it co-occurs with system-register markers (vibhajjati, lakkhana,")
    w("ganana...), it signals thesis-shape language. the MHI is the ratio.")
    w()

    w("---")
    w()

    # ─── cross-chapter summary ────────────────────────────────
    w("## cross-chapter summary")
    w()
    w("| chapter | index | value | interpretation |")
    w("|---------|-------|-------|----------------|")

    if si_ch2:
        w(f"| ch2 | SI | {si_ch2['si_value']} | "
          f"{si_ch2['engagement']}E / {si_ch2['opposition']}O / {si_ch2['both']}B — "
          f"{'balanced engagement-opposition' if 0.3 < si_ch2['si_value'] < 0.7 else 'skewed'} |")

    if h_ch1:
        w(f"| ch1 | H | {h_ch1['h_value']} | "
          f"{h_ch1['numerator']}N / {h_ch1['denominator']}D — "
          f"{'mostly therapeutic baseline' if h_ch1['h_value'] < 0.3 else 'significant hardening'} |")

    if h_ch4:
        w(f"| ch4 | H | {h_ch4['h_value']} | "
          f"{h_ch4['numerator']}N / {h_ch4['denominator']}D — "
          f"{'mostly practice-register' if h_ch4['h_value'] < 0.3 else 'significant hardening of the goal'} |")

    if mhi:
        w(f"| ch3 | MHI | {mhi['mhi_value']} | "
          f"{mhi['practice']}P / {mhi['system']}S / {mhi['transition']}T — "
          f"{'heavy transition' if mhi['transition'] > mhi['practice'] + mhi['system'] else 'mixed'} |")

    if si_ch5:
        w(f"| ch5 | SI | {si_ch5['si_value']} | "
          f"{si_ch5['engagement']}E / {si_ch5['opposition']}O / {si_ch5['both']}B |")
    if h_ch5:
        w(f"| ch5 | H | {h_ch5['h_value']} | "
          f"{h_ch5['numerator']}N / {h_ch5['denominator']}D — "
          f"{'ethical baseline preserved' if h_ch5['h_value'] < 0.3 else 'hardening toward logical refutation'} |")

    w()
    w("---")
    w()

    # ─── term lists for pipeline ──────────────────────────────
    w("## appendix: term lists for pipeline runner")
    w()
    w("these are the primary term forms to search for in the corpus,")
    w("grouped by chapter. the pipeline runner (task #35) uses these")
    w("as search inputs, weighted by their index_contribution roles.")
    w()

    for ch in ["ch1", "ch2", "ch3", "ch4", "ch5"]:
        w(f"### {ch}")
        w()
        terms = extract_search_terms(ch, chapters[ch])
        w("| entry | search forms |")
        w("|-------|-------------|")
        for eid, forms in terms:
            forms_str = ", ".join(forms[:6])
            if len(forms) > 6:
                forms_str += f" (+{len(forms)-6} more)"
            w(f"| `{eid}` | {forms_str} |")
        w()

    # ─── write output ─────────────────────────────────────────
    report = "\n".join(lines)
    outfile = OUTPUT_DIR / "index_summary.md"
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"index summary written to: {outfile}")
    print(f"total lines: {len(lines)}")

    # print quick summary
    if si_ch2:
        print(f"  ch2 SI = {si_ch2['si_value']} ({si_ch2['total']} contributions)")
    if h_ch1:
        print(f"  ch1 H  = {h_ch1['h_value']} ({h_ch1['total']} contributions)")
    if h_ch4:
        print(f"  ch4 H  = {h_ch4['h_value']} ({h_ch4['total']} contributions)")
    if mhi:
        print(f"  ch3 MHI = {mhi['mhi_value']} ({mhi['total']} terms)")
    if si_ch5:
        print(f"  ch5 SI = {si_ch5['si_value']} ({si_ch5['total']} contributions)")
    if h_ch5:
        print(f"  ch5 H  = {h_ch5['h_value']} ({h_ch5['total']} contributions)")


if __name__ == "__main__":
    generate_report()
