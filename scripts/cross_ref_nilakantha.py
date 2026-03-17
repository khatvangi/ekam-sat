#!/usr/bin/env python3
"""
Nīlakaṇṭha Cross-Reference — Ekam Sat Project
================================================
Cross-references echo results with Nīlakaṇṭha's Bhāratabhāvadīpa commentary.
For each strong echo, searches the OCR'd commentary for the matched terms
and extracts surrounding context.

This answers: "what does the traditional commentator say about the verses
where BG doctrines echo across the MBH?"

Usage:
    python cross_ref_nilakantha.py \
        --echoes ../output/v3/echo_results.csv \
        --ocr-dir ../nilakantha/ocr_clean/ \
        --output ../output/nilakantha_xref/
"""

import re
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ─── volume-to-parva mapping ─────────────────────────────────────────────────
# each OCR volume covers specific parvas
VOLUME_PARVA_MAP = {
    "vol8995": ["01", "02"],           # Ādi, Sabhā
    "vol8996": ["03", "04"],           # Āraṇyaka, Virāṭa
    "vol8997": ["05", "06"],           # Udyoga, Bhīṣma
    "vol8998": ["07", "08"],           # Droṇa, Karṇa
    "vol8999": ["09", "10", "11"],     # Sauptika, Strī (pp1-41)
    "shanti":  ["12"],                 # Śāntiparva (Gemini OCR, separate dir)
    "vol9000": ["13", "14", "15", "16", "17", "18"],  # Anuśāsana + rest
}

# reverse map: parva -> volume
PARVA_VOLUME_MAP = {}
for vol, parvas in VOLUME_PARVA_MAP.items():
    for p in parvas:
        PARVA_VOLUME_MAP[p] = vol

PARVA_NAMES = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}

# context window: chars before/after a term match to extract
CONTEXT_CHARS = 200


def load_ocr_pages(ocr_dir, volume):
    """
    Load all HK transliteration text from an OCR volume's pages.
    Returns list of {page_num, hk_text} dicts.
    """
    ocr_path = Path(ocr_dir)

    if volume == "shanti":
        # Gemini OCR: pages are in ocr_dir/pages/ directly
        pages_dir = ocr_path / "pages"
    else:
        pages_dir = ocr_path / volume / "pages"

    if not pages_dir.exists():
        return []

    pages = []
    for page_file in sorted(pages_dir.glob("page_*.txt")):
        text = page_file.read_text(encoding="utf-8", errors="replace")

        # extract HK transliteration section (after marker)
        hk_marker = "--- HK TRANSLITERATION ---"
        if hk_marker in text:
            hk_text = text.split(hk_marker, 1)[1].strip()
        else:
            # Gemini OCR pages may not have HK section — use full text
            # strip the header line
            lines = text.split("\n")
            content = []
            for line in lines:
                if line.startswith("=== PAGE"):
                    continue
                content.append(line)
            hk_text = "\n".join(content).strip()

        page_num_str = page_file.stem.split("_")[1]
        pages.append({
            "page_num": int(page_num_str),
            "hk_text": hk_text,
            "volume": volume,
        })

    return pages


def search_terms_in_pages(pages, terms, min_terms=2):
    """
    Search for co-occurrence of terms in OCR pages.
    Returns list of matches with context.
    """
    matches = []

    for page in pages:
        text = page["hk_text"]
        if not text:
            continue

        found_terms = []
        for term in terms:
            if len(term) < 3:
                continue
            # search as substring (commentary text has no word boundaries)
            if term in text:
                found_terms.append(term)

        if len(found_terms) >= min_terms:
            # extract context around first found term
            first_term = found_terms[0]
            idx = text.find(first_term)
            start = max(0, idx - CONTEXT_CHARS)
            end = min(len(text), idx + len(first_term) + CONTEXT_CHARS)
            context = text[start:end]

            matches.append({
                "volume": page["volume"],
                "page_num": page["page_num"],
                "found_terms": found_terms,
                "found_count": len(found_terms),
                "context_hk": context.replace("\n", " ")[:400],
            })

    return matches


def main():
    parser = argparse.ArgumentParser(description="Nīlakaṇṭha Cross-Reference")
    parser.add_argument("--echoes", required=True, help="Echo results CSV from scan_corpus.py")
    parser.add_argument("--ocr-dir", default="../nilakantha/ocr_clean/", help="OCR output directory")
    parser.add_argument("--output", default="../output/nilakantha_xref/", help="Output directory")
    parser.add_argument("--min-strength", type=int, default=2, help="Minimum echo strength to cross-ref")
    parser.add_argument("--max-echoes", type=int, default=500, help="Max echoes to process (strongest first)")

    args = parser.parse_args()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # load node data for term lookup
    nodes_path = Path(args.echoes).parent.parent / "data" / "bg_nodes_v2.json"
    node_terms = {}
    if nodes_path.exists():
        with open(nodes_path) as f:
            node_data = json.load(f)
        for n in node_data["nodes"]:
            # combine all terms for richer searching
            all_t = list(set(n.get("hk_terms", []) + n.get("core_hk", [])))
            # filter to terms >= 4 chars (short terms match too broadly in OCR)
            node_terms[n["id"]] = [t for t in all_t if len(t) >= 3]
        print(f"Loaded term data for {len(node_terms)} nodes")

    # load echo results
    print("Loading echo results...")
    echoes = []
    with open(args.echoes, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            strength = int(row.get("match_strength", 0))
            if strength >= args.min_strength:
                # enrich with node terms
                nid = row.get("node_id", "")
                if nid in node_terms:
                    row["search_terms"] = node_terms[nid]
                else:
                    row["search_terms"] = [t for t in row.get("matched_terms", "").split("|") if len(t) >= 3]
                echoes.append(row)

    # sort by strength descending
    echoes.sort(key=lambda x: int(x.get("match_strength", 0)), reverse=True)
    echoes = echoes[:args.max_echoes]

    print(f"Strong echoes to cross-reference: {len(echoes)}")

    # group echoes by parva for efficient volume loading
    echoes_by_parva = defaultdict(list)
    for e in echoes:
        echoes_by_parva[e["parva_num"]].append(e)

    print(f"Parvas represented: {sorted(echoes_by_parva.keys())}")

    # load OCR pages per volume (cache to avoid reloading)
    volume_pages = {}
    all_xrefs = []
    parva_stats = defaultdict(lambda: {"echoes": 0, "with_commentary": 0, "pages_matched": 0})

    for parva_num in sorted(echoes_by_parva.keys()):
        volume = PARVA_VOLUME_MAP.get(parva_num)
        if not volume:
            print(f"  Parva {parva_num}: no volume mapping, skipping")
            continue

        # load pages if not cached
        if volume not in volume_pages:
            print(f"  Loading OCR pages for {volume}...")
            volume_pages[volume] = load_ocr_pages(args.ocr_dir, volume)
            print(f"    → {len(volume_pages[volume])} pages loaded")

        pages = volume_pages[volume]
        if not pages:
            print(f"  Parva {parva_num} ({volume}): no OCR pages found")
            continue

        parva_echoes = echoes_by_parva[parva_num]
        print(f"  Parva {parva_num} ({PARVA_NAMES.get(parva_num, '?')}): "
              f"{len(parva_echoes)} strong echoes to search in {len(pages)} pages...")

        for echo in parva_echoes:
            # get terms to search — prefer enriched node terms
            terms = echo.get("search_terms", [])
            terms_str = "|".join(terms)

            if len(terms) < 2:
                continue

            parva_stats[parva_num]["echoes"] += 1

            # search commentary pages for these terms
            page_matches = search_terms_in_pages(pages, terms, min_terms=2)

            if page_matches:
                parva_stats[parva_num]["with_commentary"] += 1
                parva_stats[parva_num]["pages_matched"] += len(page_matches)

                for pm in page_matches[:3]:  # top 3 pages per echo
                    all_xrefs.append({
                        "node_id": echo.get("node_id", ""),
                        "node_name": echo.get("node_name", ""),
                        "verse_id": echo.get("verse_id", ""),
                        "parva_num": parva_num,
                        "parva_name": PARVA_NAMES.get(parva_num, "?"),
                        "echo_strength": echo.get("match_strength", ""),
                        "echo_terms": terms_str,
                        "commentary_volume": pm["volume"],
                        "commentary_page": pm["page_num"],
                        "commentary_terms_found": "|".join(pm["found_terms"]),
                        "commentary_terms_count": pm["found_count"],
                        "commentary_context": pm["context_hk"],
                    })

    # ─── save outputs ─────────────────────────────────────────────────────

    # 1. cross-reference CSV
    xref_fields = ["node_id", "node_name", "verse_id", "parva_num", "parva_name",
                   "echo_strength", "echo_terms", "commentary_volume",
                   "commentary_page", "commentary_terms_found",
                   "commentary_terms_count", "commentary_context"]

    with open(output_dir / "nilakantha_xref.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=xref_fields)
        writer.writeheader()
        writer.writerows(all_xrefs)

    # 2. report
    total_with_commentary = sum(s["with_commentary"] for s in parva_stats.values())
    total_echoes = sum(s["echoes"] for s in parva_stats.values())
    total_pages = sum(s["pages_matched"] for s in parva_stats.values())

    lines = [
        "=" * 70,
        "EKAM SAT — NĪLAKAṆṬHA CROSS-REFERENCE REPORT",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
        f"Strong echoes searched: {total_echoes}",
        f"Echoes with commentary match: {total_with_commentary} "
        f"({100*total_with_commentary/total_echoes:.1f}% hit rate)" if total_echoes else "",
        f"Commentary pages matched: {total_pages}",
        f"Cross-reference entries: {len(all_xrefs)}",
        "",
        "-" * 70,
        "PER-PARVA CROSS-REFERENCE RESULTS",
        "-" * 70,
    ]

    for pnum in sorted(parva_stats.keys()):
        s = parva_stats[pnum]
        pname = PARVA_NAMES.get(pnum, "?")
        rate = 100 * s["with_commentary"] / s["echoes"] if s["echoes"] else 0
        lines.append(
            f"  P{pnum} {pname:<20} "
            f"echoes={s['echoes']:>4} "
            f"matched={s['with_commentary']:>4} ({rate:>5.1f}%) "
            f"pages={s['pages_matched']:>4}"
        )

    # top nodes by cross-reference hits
    node_xrefs = defaultdict(int)
    for xr in all_xrefs:
        node_xrefs[f"{xr['node_id']} {xr['node_name']}"] += 1

    lines += [
        "",
        "-" * 70,
        "TOP NODES BY COMMENTARY CROSS-REFERENCES",
        "-" * 70,
    ]
    for node, count in sorted(node_xrefs.items(), key=lambda x: x[1], reverse=True)[:20]:
        lines.append(f"  {node:<55} {count:>4} xrefs")

    # sample cross-references
    lines += [
        "",
        "-" * 70,
        "SAMPLE CROSS-REFERENCES (first 15)",
        "-" * 70,
    ]
    for xr in all_xrefs[:15]:
        lines.append(
            f"\n  [{xr['node_id']}] {xr['node_name']}"
            f"\n  Echo: {xr['verse_id']} (P{xr['parva_num']} {xr['parva_name']}) "
            f"strength={xr['echo_strength']}"
            f"\n  Commentary: {xr['commentary_volume']} p.{xr['commentary_page']} "
            f"| terms: {xr['commentary_terms_found']}"
            f"\n  Context: {xr['commentary_context'][:150]}..."
        )

    lines += ["", "=" * 70, "END OF REPORT", "=" * 70]

    with open(output_dir / "nilakantha_xref_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n" + "\n".join(lines[:45]))
    print(f"\nFull report: {output_dir / 'nilakantha_xref_report.txt'}")
    print(f"CSV: {output_dir / 'nilakantha_xref.csv'}")
    print(f"Done. {len(all_xrefs)} cross-references found.")


if __name__ == "__main__":
    main()
