# Node Extraction Methodology — Ekam Sat Project

## 1. Purpose

This document describes the method used to extract an exhaustive set of doctrinal
propositions ("nodes") from the Bhagavad Gita (BORI Critical Edition), for use as
search targets against the full Mahabharata corpus (~89,000 verses).

The goal: demonstrate computationally that the BG's teachings recur across the
entire MBH, spoken by different sages in different contexts, converging
on one point (ekam sat).

## 2. What Is a Node?

A node is a **distinct philosophical claim** — not a topic, not a verse, not a keyword.

Formally: two propositions P and Q are the same node if no sage within the MBH
tradition could coherently affirm P while denying Q. If they could, P and Q are
separate nodes.

Each node has:

| Field | Description |
|-------|-------------|
| `id` | Sequential identifier (N001-N123) |
| `name` | Short label |
| `proposition` | The claim in one sentence |
| `anchor_verses` | The 2-4 verses that most directly state the claim |
| `all_verses` | Every BG verse that participates in this claim |
| `hk_terms` | Harvard-Kyoto search terms for grep against BORI corpus |
| `core_hk` | High-precision subset of hk_terms |
| `repetition_count` | How many times the BG restates this claim |
| `repetition_rationale` | Why the BG returns to this point |
| `echo_hypothesis` | What to search for in the MBH |

## 3. Lens: Pre-Sectarian

The extraction uses no commentarial lens. Not Advaita, not Dvaita, not
Vishishtadvaita. The framework is the BG's own, read through the Rg Vedic
principle "ekam sat vipra bahudha vadanti" (RV 1.164.46) — the one truth,
sages call by many names.

This predates all post-BG schools by millennia. Nodes are stated in the BG's
own vocabulary. Where commentators disagree on a verse's meaning, the node
records the verse's literal claim without adjudicating the dispute.

## 4. Extraction Method

### Step 1: Chapter-by-Chapter Reading

The BORI Critical Edition text (Harvard-Kyoto transliteration) was read
verse-by-verse across all 18 chapters.

Source: `bori/hk/MBh06.txt`, chapters 06.023 (BG ch1) through 06.040 (BG ch18).

### Step 2: Verse-Level Proposition Extraction

For each verse, the philosophical claim was identified:
- What does this verse assert, deny, command, or describe?
- Is this the same claim as a nearby verse, or a new one?

Most verses participate in multi-verse arguments. A single node typically
spans 3-10 verses that make the same claim from different angles.

### Step 3: Clustering

Verses making the same claim were grouped into a single node. The clustering
criterion: "Could a sage affirm one verse's claim while denying the other's?"
If no, same node. If yes, different nodes.

### Step 4: Repetition as Signal

When the BG states the same claim in multiple chapters (e.g., "the atman is
eternal" in ch2, ch13, ch15), this is recorded as a repetition — not collapsed.

Each repetition has a rationale: different context, different objection being
addressed, deepening of the claim. The `repetition_count` field records how
many times the BG returns to this teaching.

This is methodologically important: a teaching repeated 7 times (N006,
indestructibility of self) carries different weight than one stated once
(N010, the marvellous nature of the self). The MBH echo search should
reflect this weighting.

### Step 5: Narrative and Frame Nodes

The BG is not a standalone text — it is a discourse within the MBH, spoken
on a battlefield, embedded in a war narrative. Narrative elements are nodes too:

- Arjuna's vishada (moral paralysis) — N002
- The army catalogue and conch-blowing — N004
- Sanjaya's witness frame — N123
- The dharma-sankata (moral impasse) — N001

These are included because the thesis is: **BG = MBH and MBH = BG**.
Arjuna's paralysis echoes every MBH scene where a warrior faces an
impossible choice. Excluding narrative nodes would weaken the echo argument.

### Step 6: Term Extraction

For each node, search terms were identified in Harvard-Kyoto transliteration:

- `hk_terms`: all relevant forms including sandhi variants
- `core_hk`: 2-3 most distinctive terms for high-precision grep

Terms were selected for grep-ability against the BORI corpus format
(PPcccvvvx verse IDs followed by HK text).

### Step 7: Completeness Validation

Every BG verse was checked against the node list. The target: every verse
maps to at least one node.

Current coverage: 550/700 verses (78.6%). The uncovered verses are primarily:
- Question/transition verses (Arjuna asking, chapter openings)
- Enumeration details (food types, sub-classifications)
- Connecting tissue between arguments

These are mapped to existing nodes in a second pass (see Section 7).

## 5. Results

| Metric | v1 (original) | v2 (this extraction) |
|--------|---------------|----------------------|
| Total nodes | 35 | 123 |
| Chapters with nodes | 14/18 | 18/18 |
| Verse coverage | unmeasured | 550/700 (78.6%) |
| Narrative nodes | 0 | 4 |
| Repetition tracking | no | yes |
| Echo hypotheses | no | yes |

### Distribution by chapter:

| Chapter | Yoga | Nodes |
|---------|------|-------|
| 1 | Arjuna Vishada | 4 |
| 2 | Sankhya | 13 |
| 3 | Karma | 7 |
| 4 | Jnana | 9 |
| 5 | Sannyasa | 5 |
| 6 | Dhyana | 9 |
| 7 | Jnana-Vijnana | 11 |
| 8 | Akshara-Brahma | 7 |
| 9 | Rajavidya | 13 |
| 10 | Vibhuti | 5 |
| 11 | Vishvarupa | 4 |
| 12 | Bhakti | 4 |
| 13 | Kshetra-Kshetrajna | 4 |
| 14 | Gunatraya | 5 |
| 15 | Purushottama | 4 |
| 16 | Daivasura | 3 |
| 17 | Shraddhatraya | 4 |
| 18 | Moksha-Sannyasa | 13 |

## 6. How Nodes Are Used

Each node generates a search query against the full MBH corpus:

1. **Terminological scan** (`scan_corpus.py`): grep for `hk_terms` across all
   18 parvas, excluding BG itself (Bhishmaparva ch23-42). Produces hit counts,
   verse citations, and parva distribution.

2. **Speaker attribution** (`extract_speakers.py`): cross-reference echo
   locations with speaker markers (`X uvAca`) to identify who in the MBH
   teaches the same claim.

3. **Semantic search** (`semantic_search.py`): use sentence-transformer
   embeddings to find meaning-level echoes beyond vocabulary match.

The three layers together build the case at increasing levels of rigor:
vocabulary match → discourse context → semantic equivalence.

## 7. Known Limitations and Future Work

### Verse coverage gap (78.6% → target 95%+)

150 verses are unmapped. Most are transitional. A second pass will assign
them to existing nodes or create 5-10 additional nodes for:
- Ch16 asuri sampad details (16.6-16.20)
- Ch17 ahara-traya classification (17.7-17.13)
- Ch10 Arjuna's response to vibhutis (10.12-10.18)

### Term precision

High-frequency terms like `nitya`, `aja`, `dharma` generate thousands of
hits, most noise. The `core_hk` field mitigates this, but a `--min-strength`
filter is needed for nodes with common terms.

### Commentarial cross-reference

Future versions should note where Shankara, Ramanuja, and Madhva identify
specific teachings — not as validation of the node list (that would import
their biases) but as an additional data layer.

### MBH feedback loop

After the initial scan, if a term cluster lights up across parvas but doesn't
map to any node, that is a **missing node** — the MBH itself tells us the BG
node list was incomplete. This makes the analysis self-correcting.

## 8. File Locations

| File | Description |
|------|-------------|
| `data/bg_nodes_v2.json` | The 123-node taxonomy |
| `data/bg_nodes.json` | Original 35-node taxonomy (superseded) |
| `scripts/scan_corpus.py` | Layer 1: terminological scan |
| `scripts/extract_speakers.py` | Layer 2: speaker attribution |
| `scripts/semantic_search.py` | Layer 3: semantic search |
| `protocols/node_extraction_methodology.md` | This document |
