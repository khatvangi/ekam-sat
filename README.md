# Ekam Sat Project — MBH Corpus Analysis Pipeline
## "One truth, many voices across 89,000 verses"

---

## What This Does

Three-layer analysis of the BORI Critical Edition to prove that the teaching Krishna
crystallizes in the Bhagavad Gita is scattered across the entire Mahabharata —
spoken by different sages, in different contexts, to different people, but converging
on one point.

### Layer 1: Terminological (grep-based)
`scan_corpus.py` — Searches all 18 parvas for 35 BG doctrinal nodes using Harvard-Kyoto
term clusters. Finds: every verse containing core BG terminology *outside* the BG itself.

### Layer 2: Discourse (structural)
`extract_speakers.py` — Identifies who is speaking in each discourse segment. Maps
sage-discourses across the corpus, then cross-references with Layer 1 results. Answers:
which sages carry the most concentrated BG teaching? Who echoes Krishna without being Krishna?

### Layer 3: Semantic (embedding-based)
`semantic_search.py` — Uses sentence embeddings to find *meaning-level* echoes — verses
that express the same idea without the same vocabulary. Surfaces the hidden, minor,
unnoticed passages.

---

## Setup

```bash
# Install Python dependencies
pip install sentence-transformers numpy pandas scikit-learn

# Verify corpus exists
ls /storage/mbh/bori/hk/   # Should show .hk or .txt files with verse IDs
```

---

## Run Order

### Step 1: Terminological scan (fast, run first)
```bash
cd scripts/

# Full scan, all 35 nodes
python scan_corpus.py \
    --corpus /storage/mbh/bori/hk \
    --nodes ../data/bg_nodes.json \
    --output ../output/ \
    --freq-map

# Output:
#   ../output/echo_results.csv     — every echo, cited by BORI verse ID
#   ../output/frequency_map.csv   — heat map: nodes × parvas
#   ../output/scan_report.txt     — human-readable summary
```

### Step 2: Single node deep dive
```bash
# Example: trace N03 (Nishkama Karma) across entire MBH
python scan_corpus.py \
    --corpus /storage/mbh/bori/hk \
    --node N03 \
    --output ../output/N03/
```

### Step 3: Speaker/discourse extraction
```bash
python extract_speakers.py \
    --corpus /storage/mbh/bori/hk \
    --echoes ../output/echo_results.csv \
    --output ../output/

# Output:
#   ../output/discourse_inventory.csv  — every speaker segment
#   ../output/discourse_report.txt    — who echoes BG most
#   ../output/discourses.json         — machine-readable
```

### Step 4: Build semantic embeddings (slow — run overnight)
```bash
python semantic_search.py \
    --corpus /storage/mbh/bori/hk \
    --mode build \
    --output ../output/embeddings/

# This takes 30-90 minutes. Only needs to run once.
# Saves embeddings.npy (~500MB) and verse_ids.json
```

### Step 5: Semantic sweep (after embeddings are built)
```bash
# Sweep all key BG verses for semantic echoes
python semantic_search.py \
    --mode sweep \
    --output ../output/embeddings/

# Search for a specific BG verse's echoes
python semantic_search.py \
    --mode search \
    --bg-verse 2.47 \
    --output ../output/embeddings/

# Search by meaning (English or transliterated Sanskrit)
python semantic_search.py \
    --mode query \
    --text "the self is eternal, it does not die when the body dies" \
    --output ../output/embeddings/
```

---

## Output Files

| File | Contents |
|------|----------|
| `echo_results.csv` | All verse-level echoes, BORI cited |
| `frequency_map.csv` | Node × Parva heat map |
| `scan_report.txt` | Human summary of findings |
| `discourse_inventory.csv` | Sage discourse segments |
| `discourse_report.txt` | Which sages carry the teaching |
| `embeddings/semantic_echoes.csv` | Meaning-level echoes beyond grep |

---

## The 35 BG Nodes

| ID | Teaching |
|----|----------|
| N01 | Indestructibility of the Self |
| N02 | Self vs Body Distinction |
| N03 | Nishkama Karma — Action Without Fruit-Attachment |
| N04 | Equanimity — Sama in Pleasure and Pain |
| N05 | The Sthitaprajna — Portrait of the Realized |
| N06 | Three Gunas — Sattva Rajas Tamas |
| N07 | Field and Knower of the Field |
| N08 | Brahman Pervades All |
| N09 | Self is the Same in All Beings |
| N10 | Renunciation vs Abandonment |
| N11 | Yoga as Equanimity in Action |
| N12 | Desire as Root of All Bondage |
| N13 | Duty According to One's Nature — Svadharma |
| N14 | Knowledge Destroys Ignorance |
| N15 | Brahman as Origin and End of All |
| N16 | The Imperishable Beyond All Dualities |
| N17 | Surrender — Sarva Dharman Parityajya |
| N18 | Devotion — Bhakti as Highest Path |
| N19 | The Wise Grieve for Neither Living nor Dead |
| N20 | Non-Attachment — Nirmama Nirahankara |
| N21 | Silence and Self-Control |
| N22 | Impermanence of the World |
| N23 | The Cosmic Person — Vishwarupa |
| N24 | Time as the Destroyer — Kala |
| N25 | Liberation — Moksha as Highest Goal |
| N26 | Friend of All Beings |
| N27 | The Witness Self — Sakshi |
| N28 | True Sacrifice — Yajna as Inner Fire |
| N29 | He Who Sees Inaction in Action |
| N30 | The Divine and Demonic Natures |
| N31 | Ishvara as Inner Ruler of All Hearts |
| N32 | Practice and Dispassion — Abhyasa Vairagya |
| N33 | Purification of Mind |
| N34 | Not the Doer — Ahamkara as False Agent |
| N35 | Brahmavidya — Knowledge of Brahman as Supreme |

---

## What the Data Will Tell You

The scan reveals:

1. **Which parvas are densest** — Shantiparva (12) and Aranyakaparva (03) will likely
   dominate, but the *surprises* will be in Adiparva, Sabhaparva, Striparva.

2. **Which sages carry the most concentrated teaching** — Markandeya, Vidura, Bhishma
   are known. But who are the minor voices? The scan finds them.

3. **Which nodes are most broadly distributed** — N01 (Indestructibility), N03
   (Nishkama Karma), N04 (Equanimity) will likely appear in every parva. Track which
   nodes appear in *unexpected* parvas.

4. **The hidden minor passages** — Semantic search finds these. A 3-verse exchange
   between a forest sage and Yudhishthira that contains the core of BG 13.27 in
   different vocabulary. These are your strongest proofs.

---

## For the Book

Each chapter of the book corresponds to one or more BG nodes. The data provides:
- Primary BORI citations (verse IDs → full text from corpus)
- Speaker context (who says it, to whom, in what situation)
- Distribution map (how widely this teaching appears across the epic)
- The minor/hidden passages that academic scholarship has missed

The argument: not just the famous discourses, but the texture of the entire epic
converges on ekam sat.
