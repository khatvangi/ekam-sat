#!/usr/bin/env python3
"""
MBH Speaker & Discourse Extractor
===================================
Identifies sage-discourses in the corpus: who speaks, to whom, in which context.
This is the meta-layer over raw term matching — we want to know not just THAT
a term appears, but WHO SAYS IT and IN WHAT SITUATION.

In BORI HK text, speaker labels typically appear as:
  vaiZaMpAyana uvAca   (Vaishampayana said)
  yudhiShThira uvAca   (Yudhishthira said)
  kRShNa uvAca         (Krishna said)
  markaNeya uvAca      (Markandeya said)
  etc.

This script extracts all discourse segments with their speakers,
then cross-references with the echo database.

Usage:
    python extract_speakers.py --corpus /storage/mbh/bori/hk --output ../output/
"""

import os
import re
import json
import csv
from pathlib import Path
from collections import defaultdict

# ─── Known sage/speaker names in Harvard-Kyoto ────────────────────────────────
# Format: (hk_pattern, canonical_name, role)
SPEAKERS = [
    # Narrators
    (r"vaiZaMpAyana|vaisampAyana", "Vaishampayana", "narrator"),
    (r"sUta|sauti|zaunaka", "Suta/Shaunaka", "narrator"),
    (r"vyAsa|kRShNadvaipAyana", "Vyasa", "narrator/sage"),
    
    # Main Characters
    (r"kRShNa|vAsudeva|govinda|kezava", "Krishna", "avatar"),
    (r"arjuna|pArtha|dhanaMjaya|kirITin", "Arjuna", "warrior"),
    (r"yudhiShThira|dharmarAja|ajAtazatru", "Yudhishthira", "king"),
    (r"bhIShma|gAMgeyA|pitAmaha", "Bhishma", "grandsire"),
    (r"dhRtarAShTra", "Dhritarashtra", "king"),
    (r"duryodhana|suyodhana", "Duryodhana", "antagonist"),
    (r"vidura", "Vidura", "minister/sage"),
    (r"draupadI|pAMcAlI|kRShNA", "Draupadi", "queen"),
    (r"karNa|rAdheyA|sUtraputra", "Karna", "warrior"),
    (r"droNa|droNAcArya", "Drona", "teacher"),
    (r"kRpA|kRpAcArya", "Kripa", "teacher"),
    (r"zikhaM|zikhaNDin", "Shikhandi", "warrior"),
    
    # Forest Sages (Vanaparva)
    (r"markaNeya|mArkaNeya", "Markandeya", "sage"),
    (r"lomaza|lomazA", "Lomasha", "sage"),
    (r"nArada", "Narada", "celestial sage"),
    (r"agastya", "Agastya", "sage"),
    (r"pulastya", "Pulastya", "sage"),
    (r"bRhadazva", "Brihadashva", "sage"),
    (r"vRShNi|vRShNimant", "Vrishni", "sage"),
    (r"dhaumya", "Dhaumya", "family priest"),
    
    # Shanti/Anushasana Parva Sages
    (r"sanatsujAta", "Sanatsujata", "sage"),
    (r"sanat|sanaka|sanandana", "Sanaka/Sanandana", "eternal sage"),
    (r"bRhaspati", "Brihaspati", "divine teacher"),
    (r"zukaH|zuka|vedavyAsa", "Shuka", "sage"),
    (r"janaka", "Janaka", "philosopher-king"),
    (r"sulabhA", "Sulabha", "female philosopher"),
    (r"paMcazikha", "Panchashikha", "Sankhya sage"),
    (r"yAjJavalkya", "Yajnavalkya", "sage"),
    (r"kapila", "Kapila", "Sankhya founder"),
    (r"parAzara", "Parashara", "sage"),
    (r"manu", "Manu", "progenitor"),
    (r"indra", "Indra", "king of gods"),
    
    # Misc
    (r"gAndhArI", "Gandhari", "queen"),
    (r"kuntI", "Kunti", "mother"),
    (r"zaMjaya|saMjaya", "Sanjaya", "narrator"),
    (r"azvattAmA|azmattAman", "Ashvatthaman", "warrior"),
]

UVACA_PATTERN = re.compile(
    r'(' + '|'.join(p for p, _, _ in SPEAKERS) + r')\s+uvAca'
)


def extract_discourses(corpus_dir):
    """
    Walk through the corpus files in order, identify speaker transitions,
    and segment the text into discourse blocks.
    
    Returns list of discourse objects:
    {
        start_verse: str,
        end_verse: str,
        speaker: str,
        speaker_role: str,
        parva: str,
        verse_count: int,
        verses: [verse_id, ...]
    }
    """
    print(f"Extracting discourse segments from: {corpus_dir}")
    
    corpus_path = Path(corpus_dir)
    files = sorted([f for f in corpus_path.iterdir() if f.is_file()])
    
    discourses = []
    current_discourse = None
    
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"  Error reading {filepath}: {e}")
            continue
        
        for line in lines:
            line = line.rstrip()
            if not line:
                continue
            
            # Check for verse ID
            m = re.match(r'^(\d{8}[a-e]?)\s*(.*)', line)
            if not m:
                continue
            
            verse_id = m.group(1)
            text = m.group(2)
            
            # Check for speaker change
            speaker_match = UVACA_PATTERN.search(text)
            if speaker_match:
                # Save current discourse
                if current_discourse and current_discourse["verses"]:
                    discourses.append(current_discourse)
                
                # Identify speaker (HK is case-sensitive — don't lowercase)
                matched_name = speaker_match.group(1)
                speaker_name = "Unknown"
                speaker_role = "unknown"
                for pattern, name, role in SPEAKERS:
                    if re.search(pattern, matched_name):
                        speaker_name = name
                        speaker_role = role
                        break
                
                parva = verse_id[0:2]
                current_discourse = {
                    "start_verse": verse_id,
                    "end_verse": verse_id,
                    "speaker": speaker_name,
                    "speaker_role": speaker_role,
                    "parva": parva,
                    "verse_count": 1,
                    "verses": [verse_id],
                }
            elif current_discourse:
                current_discourse["end_verse"] = verse_id
                current_discourse["verse_count"] += 1
                current_discourse["verses"].append(verse_id)
    
    # Don't forget last discourse
    if current_discourse and current_discourse["verses"]:
        discourses.append(current_discourse)
    
    print(f"Found {len(discourses)} discourse segments")
    return discourses


def annotate_with_echoes(discourses, echo_results):
    """
    Cross-reference discourse segments with echo results.
    Returns discourses enriched with node-echo data.
    """
    # Build echo lookup: verse_id -> [node_ids]
    echo_map = defaultdict(list)
    for echo in echo_results:
        echo_map[echo["verse_id"]].append(echo["node_id"])
    
    for discourse in discourses:
        echoed_nodes = set()
        for v in discourse["verses"]:
            echoed_nodes.update(echo_map.get(v, []))
        discourse["echoed_nodes"] = list(echoed_nodes)
        discourse["echo_count"] = len(echoed_nodes)
    
    return discourses


def save_discourses(discourses, output_path):
    """Save discourse inventory to CSV."""
    if not discourses:
        return
    
    fieldnames = ["start_verse", "end_verse", "parva", "speaker", "speaker_role",
                  "verse_count", "echo_count", "echoed_nodes"]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for d in discourses:
            row = {k: d.get(k, "") for k in fieldnames}
            row["echoed_nodes"] = "|".join(d.get("echoed_nodes", []))
            row = {k: v for k, v in row.items() if k in fieldnames}
            writer.writerow(row)
    
    print(f"Saved discourse inventory to {output_path}")


def generate_discourse_report(discourses, output_path):
    """Generate summary report of sage discourses."""
    # Count by speaker
    speaker_counts = defaultdict(lambda: {"discourses": 0, "verses": 0, "echo_nodes": set()})
    
    for d in discourses:
        s = d["speaker"]
        speaker_counts[s]["discourses"] += 1
        speaker_counts[s]["verses"] += d["verse_count"]
        speaker_counts[s]["echo_nodes"].update(d.get("echoed_nodes", []))
    
    lines = [
        "=" * 70,
        "SAGE DISCOURSE INVENTORY",
        "=" * 70,
        "",
        f"Total discourse segments: {len(discourses)}",
        "",
        "─" * 70,
        f"{'SPEAKER':<25} {'DISCOURSES':>10} {'VERSES':>8} {'BG NODES ECHOED':>16}",
        "─" * 70,
    ]
    
    for speaker, data in sorted(speaker_counts.items(), key=lambda x: x[1]["verses"], reverse=True):
        lines.append(
            f"  {speaker:<23} {data['discourses']:>10} {data['verses']:>8} {len(data['echo_nodes']):>16}"
        )
    
    lines += [
        "",
        "─" * 70,
        "HIGH-DENSITY DISCOURSES (most BG node echoes, non-BG, non-Krishna)",
        "─" * 70,
    ]
    
    # Filter out Krishna discourses (those ARE the BG analog) — focus on other voices
    other_discourses = [d for d in discourses if d["speaker"] not in ["Krishna", "Unknown"]]
    other_discourses.sort(key=lambda x: x.get("echo_count", 0), reverse=True)
    
    for d in other_discourses[:30]:
        nodes = ", ".join(d.get("echoed_nodes", [])[:5])
        lines.append(
            f"\n  {d['speaker']} [{d['start_verse']}–{d['end_verse']}]"
        )
        lines.append(f"  Parva: {d['parva']} | Verses: {d['verse_count']} | BG nodes: {d.get('echo_count',0)}")
        lines.append(f"  Nodes: {nodes}")
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Discourse report saved to {output_path}")
    print("\n".join(lines[:30]))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MBH Speaker/Discourse Extractor")
    parser.add_argument("--corpus", required=True, help="Path to BORI HK corpus directory")
    parser.add_argument("--echoes", default=None, help="Path to echo_results.csv from scan_corpus.py")
    parser.add_argument("--output", default="../output/", help="Output directory")
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract discourses
    discourses = extract_discourses(args.corpus)
    
    # Load echoes if available
    if args.echoes and Path(args.echoes).exists():
        import csv as _csv
        echo_results = []
        with open(args.echoes, "r", encoding="utf-8") as f:
            reader = _csv.DictReader(f)
            echo_results = list(reader)
        discourses = annotate_with_echoes(discourses, echo_results)
        print(f"Annotated discourses with {len(echo_results)} echo results")
    
    save_discourses(discourses, output_dir / "discourse_inventory.csv")
    generate_discourse_report(discourses, output_dir / "discourse_report.txt")
    
    # Also save as JSON for downstream processing
    for d in discourses:
        d["verses"] = d.get("verses", [])[:5]  # trim to save space
    
    with open(output_dir / "discourses.json", "w", encoding="utf-8") as f:
        json.dump(discourses, f, ensure_ascii=False, indent=2)
    
    print(f"\nDone. Discourse data in {output_dir}")


if __name__ == "__main__":
    main()
