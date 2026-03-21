#!/usr/bin/env python3
"""
Deep Reading Protocol — Ekam Sat Project
==========================================
The pipeline finds WHERE echoes are. This script prepares the material
for the human reader to find WHAT those echoes mean in context.

Procedure (derived from the Two Vishadas discovery):
  1. LOCATE: pipeline identifies high-density echo zones
  2. WHO SPEAKS: extract speakers in that zone
  3. WHAT DO THEY SAY: pull actual verse text for the densest passages
  4. COMPARE REGISTERS: how does the same teaching sound here vs in BG?
  5. WHAT'S DIFFERENT: what does this speaker add, transform, or refuse?
  6. WHAT'S SILENT: what's NOT said that the BG says, or vice versa?

This script automates steps 1-4 and prepares a "reading packet" for step 5-6.

Usage:
    # generate reading packet for a parva
    python deep_reading.py --parva 12 \
        --echoes ../output/v3/echo_results.csv \
        --corpus ../bori/hk \
        --nodes ../data/bg_nodes_v2.json \
        --discourses ../output/v3/discourses.json \
        --output ../output/deep_reading/

    # focus on a specific chapter range
    python deep_reading.py --parva 12 --ch-start 168 --ch-end 200 \
        --echoes ../output/v3/echo_results.csv \
        --corpus ../bori/hk \
        --nodes ../data/bg_nodes_v2.json \
        --output ../output/deep_reading/
"""

import re
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime


PARVAS = {
    "01": "Adi", "02": "Sabha", "03": "Aranyaka", "04": "Virata",
    "05": "Udyoga", "06": "Bhishma", "07": "Drona", "08": "Karna",
    "09": "Shalya", "10": "Sauptika", "11": "Stri", "12": "Shanti",
    "13": "Anushasana", "14": "Ashvamedha", "15": "Ashramavasika",
    "16": "Mausala", "17": "Mahaprasthanika", "18": "Svargarohana",
}

BG_CHAPTERS = set(range(23, 41))


def load_echoes_for_parva(echoes_path, parva_num, ch_start=None, ch_end=None):
    """load echoes filtered to a specific parva and optional chapter range."""
    echoes = []
    with open(echoes_path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["parva_num"] != parva_num:
                continue
            ch = int(row.get("chapter", 0))
            if ch_start and ch < ch_start:
                continue
            if ch_end and ch > ch_end:
                continue
            echoes.append(row)
    return echoes


def load_corpus_parva(corpus_dir, parva_num):
    """load all verses for a parva."""
    corpus_path = Path(corpus_dir)
    parva_file = corpus_path / f"MBh{parva_num}.txt"
    verses = {}
    if not parva_file.exists():
        return verses
    with open(parva_file, "r", encoding="utf-8", errors="replace") as f:
        current_id = None
        current_parts = []
        for line in f:
            line = line.rstrip()
            m = re.match(r'^(\d{8}[a-e]?)\s+(.*)', line)
            if m:
                if current_id and current_parts:
                    base = current_id[:8]
                    if base not in verses:
                        verses[base] = ""
                    verses[base] += " " + " ".join(current_parts)
                current_id = m.group(1)
                current_parts = [m.group(2)]
            elif current_id:
                current_parts.append(line.strip())
        if current_id and current_parts:
            base = current_id[:8]
            if base not in verses:
                verses[base] = ""
            verses[base] += " " + " ".join(current_parts)
    return {k: v.strip() for k, v in verses.items()}


def load_bg_verse_text(bg_dir, node_id, nodes):
    """load BG verse text for a node's anchor verses."""
    node = next((n for n in nodes if n["id"] == node_id), None)
    if not node:
        return []
    anchor = node.get("anchor_verses", [])
    bg_path = Path(bg_dir)
    results = []
    for ref in anchor[:3]:  # top 3 anchors
        parts = ref.split(".")
        if len(parts) != 2:
            continue
        ch, v = int(parts[0]), int(parts[1])
        bori_ch = ch + 22
        prefix = f"06{bori_ch:03d}{v:03d}"
        ch_file = bg_path / f"bg_ch{ch:02d}.txt"
        if ch_file.exists():
            with open(ch_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith(prefix):
                        m = re.match(r'^(\d{8}[a-e]?)\s+(.*)', line.strip())
                        if m:
                            results.append((m.group(1), m.group(2), ref))
    return results


def find_speakers_in_range(corpus_verses, ch_start=None, ch_end=None):
    """find X uvAca patterns in a chapter range."""
    speakers = []
    for vid, text in sorted(corpus_verses.items()):
        ch = int(vid[2:5])
        if ch_start and ch < ch_start:
            continue
        if ch_end and ch > ch_end:
            continue
        m = re.search(r'(\w+)\s+uvAca', text)
        if m:
            speakers.append({
                "verse_id": vid,
                "chapter": ch,
                "speaker_raw": m.group(1),
                "text": text[:100],
            })
    return speakers


def find_dense_zones(echoes, window=5):
    """
    find chapter ranges with highest echo density.
    returns list of (ch_start, ch_end, echo_count, node_count, top_nodes).
    """
    # group by chapter
    ch_echoes = defaultdict(list)
    for e in echoes:
        ch = int(e.get("chapter", 0))
        ch_echoes[ch].append(e)

    if not ch_echoes:
        return []

    chapters = sorted(ch_echoes.keys())

    # sliding window
    zones = []
    for i in range(len(chapters)):
        ch_start = chapters[i]
        ch_end = ch_start + window
        zone_echoes = []
        for ch in range(ch_start, ch_end + 1):
            zone_echoes.extend(ch_echoes.get(ch, []))

        if not zone_echoes:
            continue

        node_ids = set(e["node_id"] for e in zone_echoes)
        node_counts = Counter(e["node_id"] for e in zone_echoes)
        top = node_counts.most_common(5)

        zones.append({
            "ch_start": ch_start,
            "ch_end": ch_end,
            "echo_count": len(zone_echoes),
            "node_count": len(node_ids),
            "top_nodes": top,
        })

    # sort by density (echo_count * node_count)
    zones.sort(key=lambda z: z["echo_count"] * z["node_count"], reverse=True)

    # deduplicate overlapping zones
    used = set()
    unique_zones = []
    for z in zones:
        key = (z["ch_start"] // window)
        if key not in used:
            used.add(key)
            unique_zones.append(z)

    return unique_zones[:10]


def build_reading_packet(parva_num, echoes, corpus_verses, nodes, discourses,
                         bg_dir, ch_start=None, ch_end=None):
    """
    build a reading packet for critical analysis.
    this is what the human reader uses to discover register differences,
    metaphor transformations, silences, and inverse functions.
    """
    packet = {
        "parva": parva_num,
        "parva_name": PARVAS.get(parva_num, "?"),
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # step 1: LOCATE dense zones
    zones = find_dense_zones(echoes)
    packet["dense_zones"] = zones

    # step 2: WHO SPEAKS in the densest zones
    speakers = find_speakers_in_range(corpus_verses, ch_start, ch_end)
    # count speaker frequency
    speaker_counts = Counter(s["speaker_raw"] for s in speakers)
    packet["speakers"] = {
        "transitions": len(speakers),
        "unique_speakers": len(speaker_counts),
        "frequency": speaker_counts.most_common(15),
    }

    # step 3: for each dense zone, pull the actual echoed verses with context
    node_names = {n["id"]: n["name"] for n in nodes}
    zone_readings = []

    for zone in zones[:5]:  # top 5 zones
        zch_start = zone["ch_start"]
        zch_end = zone["ch_end"]

        # get echoes in this zone
        zone_echoes = [e for e in echoes
                       if zch_start <= int(e.get("chapter", 0)) <= zch_end]

        # group by node
        by_node = defaultdict(list)
        for e in zone_echoes:
            by_node[e["node_id"]].append(e)

        reading = {
            "zone": f"ch {zch_start}-{zch_end}",
            "total_echoes": len(zone_echoes),
            "nodes_present": len(by_node),
            "node_details": [],
        }

        for nid, node_echoes in sorted(by_node.items(),
                                        key=lambda x: len(x[1]), reverse=True)[:5]:
            # get BG anchor text for comparison
            bg_verses = load_bg_verse_text(bg_dir, nid, nodes)

            # get the actual MBH verse text (try base ID, then with half-verse stripped)
            mbh_samples = []
            for e in node_echoes[:5]:
                vid = e["verse_id"]
                text = corpus_verses.get(vid[:8], corpus_verses.get(vid, "[text not found]"))
                mbh_samples.append({
                    "verse_id": vid,
                    "chapter": e.get("chapter", ""),
                    "strength": e.get("match_strength", ""),
                    "terms": e.get("matched_terms", ""),
                    "text": text[:300],
                })

            reading["node_details"].append({
                "node_id": nid,
                "node_name": node_names.get(nid, "?"),
                "echo_count_in_zone": len(node_echoes),
                "bg_anchor_text": [{"ref": ref, "vid": vid, "text": text}
                                   for vid, text, ref in bg_verses],
                "mbh_samples": mbh_samples,
                "reading_prompts": [
                    f"COMPARE: how does the BG state this teaching vs how it appears here?",
                    f"REGISTER: is it abstract/metaphysical or grounded/practical?",
                    f"SPEAKER: who is speaking and to whom? what is their situation?",
                    f"TRANSFORM: does the teaching serve the same function here as in BG?",
                    f"SILENCE: what does the BG version include that is missing here, or vice versa?",
                ],
            })

        zone_readings.append(reading)

    packet["zone_readings"] = zone_readings

    # step 4: identify which BG nodes are ABSENT from this parva
    present_nodes = set(e["node_id"] for e in echoes)
    all_nodes = set(n["id"] for n in nodes)
    absent = all_nodes - present_nodes
    packet["absent_nodes"] = sorted(absent)
    packet["absent_count"] = len(absent)

    # step 5: identify which nodes are DENSE here but WEAK in BG
    node_density_here = Counter(e["node_id"] for e in echoes)
    dense_here = [(nid, count) for nid, count in node_density_here.most_common(10)]
    packet["densest_nodes_here"] = [
        {"node_id": nid, "name": node_names.get(nid, "?"), "count": count}
        for nid, count in dense_here
    ]

    return packet


def write_packet(packet, output_dir):
    """write the reading packet as both JSON and human-readable text."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    parva = packet["parva"]
    pname = packet["parva_name"]

    # JSON for programmatic use
    with open(output_dir / f"reading_packet_P{parva}.json", "w", encoding="utf-8") as f:
        json.dump(packet, f, ensure_ascii=False, indent=2)

    # human-readable text
    lines = [
        "=" * 70,
        f"DEEP READING PACKET: {pname} (Parva {parva})",
        f"Generated: {packet['generated']}",
        "=" * 70,
        "",
        "This packet prepares material for critical reading.",
        "The pipeline found the echoes. Your job: read the verses,",
        "compare registers, identify transformations, note silences.",
        "",
        "-" * 70,
        "STEP 1: DENSE ZONES (where to focus)",
        "-" * 70,
    ]

    for z in packet.get("dense_zones", [])[:5]:
        lines.append(
            f"  ch {z['ch_start']}-{z['ch_end']}: "
            f"{z['echo_count']} echoes, {z['node_count']} nodes"
        )
        for nid, count in z["top_nodes"][:3]:
            lines.append(f"    {nid}: {count}")

    lines += [
        "",
        "-" * 70,
        "STEP 2: WHO SPEAKS",
        "-" * 70,
    ]
    for speaker, count in packet.get("speakers", {}).get("frequency", []):
        lines.append(f"  {speaker:<25} {count:>3} speeches")

    lines += [
        "",
        "-" * 70,
        "STEP 3-4: VERSE COMPARISONS (BG vs here)",
        "-" * 70,
        "",
        "For each dense zone, the top echoed nodes are shown with:",
        "  - BG anchor verse (how krishna teaches it)",
        "  - MBH verses from this parva (how it appears here)",
        "  - reading prompts for critical analysis",
    ]

    for reading in packet.get("zone_readings", []):
        lines.append(f"\n{'─'*60}")
        lines.append(f"ZONE: {reading['zone']} ({reading['total_echoes']} echoes, "
                      f"{reading['nodes_present']} nodes)")
        lines.append(f"{'─'*60}")

        for nd in reading.get("node_details", []):
            lines.append(f"\n  [{nd['node_id']}] {nd['node_name']}")
            lines.append(f"  echoes in zone: {nd['echo_count_in_zone']}")

            lines.append(f"\n  BG ANCHOR (how krishna teaches this):")
            for bg in nd.get("bg_anchor_text", []):
                lines.append(f"    BG {bg['ref']}: {bg['text'][:120]}")

            lines.append(f"\n  HERE (how it appears in {pname}):")
            for mbh in nd.get("mbh_samples", []):
                lines.append(f"    {mbh['verse_id']} [str={mbh['strength']}]: "
                             f"{mbh['text'][:120]}")

            lines.append(f"\n  READING PROMPTS:")
            for prompt in nd.get("reading_prompts", []):
                lines.append(f"    ? {prompt}")

    lines += [
        "",
        "-" * 70,
        f"ABSENT NODES ({packet.get('absent_count', 0)} BG teachings NOT found here)",
        "-" * 70,
    ]
    for nid in packet.get("absent_nodes", [])[:20]:
        lines.append(f"  {nid}")

    lines += [
        "",
        "-" * 70,
        "DENSEST NODES (what this parva emphasizes most)",
        "-" * 70,
    ]
    for nd in packet.get("densest_nodes_here", []):
        lines.append(f"  {nd['node_id']} {nd['name'][:50]}: {nd['count']} echoes")

    lines += [
        "",
        "=" * 70,
        "WHAT TO LOOK FOR:",
        "",
        "1. REGISTER: is the teaching abstract or grounded?",
        "   (garment vs clay pot, axiom vs narrative, principle vs case)",
        "",
        "2. FUNCTION: does the teaching serve the same purpose as in BG?",
        "   (correction vs consolation, motivation vs explanation)",
        "",
        "3. SPEAKER VOICE: who speaks and how?",
        "   (divine authority vs human compassion vs witness)",
        "",
        "4. TRANSFORMATION: same doctrine but different form?",
        "   (compressed vs expanded, propositional vs parabolic)",
        "",
        "5. SILENCE: what is present in BG but absent here?",
        "   what is present here but absent in BG?",
        "",
        "6. CONSEQUENCE: does the teaching lead to action, acceptance,",
        "   or something else? (naSTho mohaH vs tUSNIM babhUva)",
        "=" * 70,
    ]

    with open(output_dir / f"reading_packet_P{parva}.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return output_dir / f"reading_packet_P{parva}.txt"


def main():
    parser = argparse.ArgumentParser(description="Deep Reading Protocol")
    parser.add_argument("--parva", required=True, help="Parva number (e.g. 12)")
    parser.add_argument("--echoes", required=True)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--nodes", required=True)
    parser.add_argument("--discourses", default=None)
    parser.add_argument("--bg-dir", default="../data/bg_chapters/")
    parser.add_argument("--output", default="../output/deep_reading/")
    parser.add_argument("--ch-start", type=int, default=None)
    parser.add_argument("--ch-end", type=int, default=None)

    args = parser.parse_args()

    parva_num = f"{int(args.parva):02d}"
    print(f"Preparing deep reading packet for {PARVAS.get(parva_num, '?')} (P{parva_num})")

    # load data
    with open(args.nodes) as f:
        nodes = json.load(f)["nodes"]

    discourses = []
    if args.discourses and Path(args.discourses).exists():
        with open(args.discourses) as f:
            discourses = json.load(f)

    echoes = load_echoes_for_parva(args.echoes, parva_num, args.ch_start, args.ch_end)
    print(f"  echoes in parva: {len(echoes)}")

    corpus_verses = load_corpus_parva(args.corpus, parva_num)
    print(f"  verses in parva: {len(corpus_verses)}")

    # build packet
    packet = build_reading_packet(
        parva_num, echoes, corpus_verses, nodes, discourses,
        args.bg_dir, args.ch_start, args.ch_end
    )

    # write
    txt_path = write_packet(packet, args.output)
    print(f"\nReading packet: {txt_path}")
    print("Now read the verses. The pipeline found where. You find what.")


if __name__ == "__main__":
    main()
