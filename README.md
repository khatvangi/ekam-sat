# Ekam Sat — Mahābhārata Corpus Analysis

> *ekam sad viprā bahudhā vadanti*
> "Truth is one; the wise call it by many names" — Ṛg Veda 1.164.46

A computational mapping of doctrinal recurrence across the entire Mahābhārata (~89,000 verses, BORI Critical Edition), demonstrating that the Bhagavad Gītā's teachings appear throughout the epic — spoken by different sages in different contexts, all converging on a single doctrinal core.

## the thesis

The Bhagavad Gītā is traditionally read as Kṛṣṇa's singular revelation to Arjuna. This project demonstrates computationally that:

1. **Every BG doctrine echoes elsewhere in the MBH.** 90.3% of the Gītā's 700 verses have terminological parallels across the epic.
2. **The same teachings come from different mouths.** Nārada echoes 80 of 123 BG doctrinal nodes — more than Kṛṣṇa himself (72). Bhīṣma, Vyāsa, Yājñavalkya, Parāśara all teach the same core.
3. **Śāntiparva dominates.** Bhīṣma's deathbed teachings (parva 12) produce the most echoes across every method — term overlap, semantic similarity, and hybrid analysis.
4. **The traditional commentator saw this too.** Nīlakaṇṭha's Bhāratabhāvadīpa commentary discusses the same echoed terms in 97.4% of cross-referenced cases.

The implication: the Gītā is not an interpolation or a standalone text grafted onto the epic. It is the densest expression of a doctrinal tradition that permeates the entire Mahābhārata. *Ekam sat* — one truth, many voices.

## results summary

| analysis layer | method | key result |
|---|---|---|
| layer 1a: node scan | 123 curated doctrinal nodes, HK term regex | 43,303 echoes, 2,352 strong (2+ core terms) |
| layer 1b: verse scan | all 700 BG verses, content word co-occurrence | 57,139 echoes, 632/700 verses have parallels |
| layer 1c: semantic | sentence-transformer embeddings (MiniLM) | 21,000 meaning-level echoes, all >0.7 similarity |
| layer 1d: hybrid | term + semantic merge | 77,848 pairs, 263 dual-evidence (strongest) |
| layer 1e: english | 28 english meaning queries cross-lingually | 840 matches across all parvas |
| layer 2: speakers | `X uvāca` discourse segmentation | 1,488 segments; Nārada echoes 80/123 nodes |
| layer 3: commentary | Nīlakaṇṭha OCR cross-reference | 1,001 xrefs at 97.4% hit rate |

### echo density by parva (all methods converge)

```
Śāntiparva (12)      ████████████████████████████████████████  9,153
Āraṇyaka (03)        ██████████████████████████               6,298
Anuśāsana (13)       ██████████████████                       4,574
Ādiparva (01)        █████████████████                        4,158
Droṇaparva (07)      ███████████████                          3,794
Udyogaparva (05)     ██████████████                           3,485
...all 18 non-BG parvas have echoes (including Mahāprasthānika: 51)
```

## methodology

### siddhānta, not sampradāya

all analysis reads the text at the level of siddhānta (established conclusion) rather than through any particular sampradāya (sectarian school). the 123 doctrinal nodes represent what the text itself states — not an Advaita, Dvaita, or Viśiṣṭādvaita reading. this is not a "neutral lens" in the Western academic sense where all positions are treated as equally interpretive. ekam sat (RV 1.164.46) is the Veda's own statement about the nature of truth. the various sampradāyas are themselves attempts to articulate this siddhānta — they acknowledge the divergence. we read at the level before the divergence, which is the level the Mahābhārata itself operates at. methodology documented in `protocols/node_extraction_methodology.md`.

### what we search

the BORI Critical Edition in Harvard-Kyoto (HK) ASCII transliteration. HK is case-sensitive by design: `A` = ā (long vowel), `a` = a (short); `S` = ṣ (retroflex), `s` = s (dental). this distinction is phonemically significant in Sanskrit — our pipeline respects it (no case-insensitive matching).

### what we exclude

the BG itself (parva 06, chapters 23-40 in BORI numbering; BG ch1 = BORI 06.023, ch18 = BORI 06.040). we search the MBH *outside* the Gītā for echoes of what the Gītā teaches.

### three-layer pipeline

```
Layer 1: TERMINOLOGICAL SCAN
  input:  123 BG nodes (hk_terms, core_hk) + 700 BG verses
  method: regex search across 72,744 non-BG verses
  output: verse-level echo database with strength scoring

Layer 2: SPEAKER EXTRACTION
  input:  echo database + full corpus
  method: "X uvāca" pattern detection → discourse segmentation
  output: who says what, annotated with BG node echoes

Layer 3: COMMENTARY CROSS-REFERENCE
  input:  echo database + Nīlakaṇṭha OCR (1,957 pages, 6 volumes)
  method: term co-occurrence search in HK transliterated commentary
  output: traditional commentator's discussion of echoed terms
```

## setup

### requirements

```bash
pip install sentence-transformers numpy pandas scikit-learn
```

for nīlakaṇṭha OCR (optional):
```bash
pip install pdf2image Pillow indic-transliteration
pip install surya-ocr  # local GPU OCR, free
```

### corpus

the BORI Critical Edition corpus is not included (copyrighted). place HK transliteration files at `bori/hk/`:
```
bori/hk/MBh00.txt   # metadata only
bori/hk/MBh01.txt   # Ādiparva
...
bori/hk/MBh18.txt   # Svargārohaṇaparva
```

verse ID format: `PPcccvvvx` (PP=parva, ccc=chapter, vvv=verse, x=half-verse a/b/c/d/e).

## running the pipeline

all commands from project root.

### layer 1a: node-based term scan

```bash
# full scan with 123 nodes (v2, exhaustive)
python scripts/scan_corpus.py \
    --corpus bori/hk \
    --nodes data/bg_nodes_v2.json \
    --output output/v3/ \
    --freq-map

# single node deep dive
python scripts/scan_corpus.py \
    --corpus bori/hk \
    --nodes data/bg_nodes_v2.json \
    --node N006 \
    --output output/N006/
```

### layer 1b: verse-level scan (all 700 BG verses)

```bash
python scripts/scan_bg_verses.py \
    --corpus bori/hk \
    --bg-dir data/bg_chapters/ \
    --output output/bg_verses/
```

### layer 1c: semantic embedding search

```bash
# build embeddings (slow, 30-90 min, run once)
python scripts/semantic_search.py \
    --corpus bori/hk \
    --mode build \
    --output output/embeddings/

# semantic sweep of all 700 BG verses
python scripts/scan_bg_semantic.py \
    --bg-dir data/bg_chapters/ \
    --embeddings output/embeddings/ \
    --output output/bg_semantic/

# search by meaning (english works best with this model)
python scripts/semantic_search.py \
    --mode query \
    --text "the self is eternal and indestructible" \
    --output output/embeddings/
```

### layer 1d+e: hybrid merge + english queries

```bash
python scripts/scan_bg_hybrid.py \
    --mode both \
    --term-echoes output/bg_verses/bg_verse_echoes.csv \
    --sem-echoes output/bg_semantic/bg_semantic_echoes.csv \
    --embeddings output/embeddings/ \
    --output output/bg_hybrid/
```

### layer 2: speaker/discourse extraction

```bash
python scripts/extract_speakers.py \
    --corpus bori/hk \
    --echoes output/v3/echo_results.csv \
    --output output/v3/
```

### layer 3: nīlakaṇṭha cross-reference

```bash
# requires OCR output at nilakantha/ocr_clean/
python scripts/cross_ref_nilakantha.py \
    --echoes output/v3/echo_results.csv \
    --ocr-dir nilakantha/ocr_clean/ \
    --output output/nilakantha_xref/

# build commentary alignment index
python scripts/build_commentary_index.py \
    --ocr-dir nilakantha/ocr_clean/ \
    --output output/commentary_index/
```

## repository structure

```
data/
├── bg_nodes_v2.json           # 123 BG doctrinal nodes (exhaustive, pre-sectarian)
├── bg_nodes.json              # original 35 nodes (superseded)
├── bg_nodes_ch1_6.json        # intermediate extraction files
├── bg_nodes_ch7_12.json
├── bg_nodes_ch13_18.json
└── bg_chapters/               # BG text in BORI HK format
    ├── bg_ch01.txt            # BG chapter 1 (= BORI 06.023)
    └── ...bg_ch18.txt         # BG chapter 18 (= BORI 06.040)

scripts/
├── scan_corpus.py             # layer 1a: node-based term scan
├── scan_bg_verses.py          # layer 1b: verse-level content word scan
├── semantic_search.py         # layer 1c: embedding build + query
├── scan_bg_semantic.py        # layer 1c: full 700-verse semantic sweep
├── scan_bg_hybrid.py          # layer 1d+e: hybrid merge + english queries
├── extract_speakers.py        # layer 2: speaker/discourse extraction
├── cross_ref_nilakantha.py    # layer 3: commentary cross-reference
└── build_commentary_index.py  # layer 3: page-chapter alignment index

nilakantha/
└── scripts/
    ├── ocr_pipeline.py        # Gemini Vision OCR (paid, high quality)
    ├── ocr_surya.py           # Surya OCR (local GPU, free, ~80% quality)
    └── run_surya_all.sh       # batch OCR for all 6 volumes

protocols/
├── node_extraction_methodology.md  # how the 123 nodes were derived
├── sanskrit_non_translatables.md   # terms kept untranslated and why
├── DECOLONIZATION_CHECKLIST.md     # epistemic decolonization framework
├── term_dictionary/                # structured term entries (from parallel project)
└── ...
```

## node data format

each of the 123 nodes in `bg_nodes_v2.json` contains:

```json
{
  "id": "N006",
  "name": "Indestructibility of the Self — Atman is Unborn and Undying",
  "proposition": "The atman is never born, never dies...",
  "anchor_verses": ["2.20"],
  "all_verses": ["2.17", "2.18", "2.19", "2.20", "2.21", "2.23", "2.24", "2.25"],
  "hk_terms": ["nitya", "aja", "avyaya", "avinAzin", "zarIrin", "dehin"],
  "core_hk": ["nitya", "aja", "avyaya"],
  "repetition_count": 6,
  "repetition_rationale": "Core atman-eternality terms...",
  "echo_hypothesis": "Expect strong echoes in Shantiparva..."
}
```

- `hk_terms`: all Harvard-Kyoto terms used for regex search
- `core_hk`: subset of terms whose co-occurrence defines a "strong" echo (match_strength >= 2)
- `echo_hypothesis`: pre-registered prediction about where echoes should appear (tested, not retrofitted)

## nilakantha OCR

Nilakantha Caturdhara's *Bharatabhavadipa* (17th c.) is the most comprehensive traditional commentary on the Mahabharata. we OCR'd 1,957 pages from the Archaeological Survey of India 600 DPI scans (6 volumes, catalog numbers 8995-9000).

| volume | parvas | pages | engine |
|--------|--------|-------|--------|
| 8995 | Adi + Sabha | 275 | Surya |
| 8996 | Aranyaka + Virata | 318 | Surya |
| 8997 | Udyoga + Bhishma | 312 | Surya |
| 8998 | Drona + Karna | 344 | Surya |
| 8999 | Sauptika + Stri (pp1-41) | 41 | Surya |
| 8999 | Shantiparva (pp42-422) | 380 | Gemini |
| 9000 | Anushasana + rest | 287 | Surya |

OCR output is not in the repo (too large). scripts to reproduce are in `nilakantha/scripts/`.

## bugs found and fixed

three critical bugs were discovered during a code audit on 2026-03-13. all have been fixed and results re-run:

| bug | impact | fix |
|-----|--------|-----|
| `re.IGNORECASE` on HK regex | conflated case-significant phonemes (A/a, S/s, R/r), inflating echoes by ~56% | removed; HK case is phonemically significant |
| BG exclusion range `range(23, 43)` | excluded 2 post-BG chapters (41-42) that should be searched | fixed to `range(23, 41)` |
| half-verse regex `[abcd]?` | missed 5,378 verses with half-verse marker `e` | fixed to `[a-e]?` |

pre-fix numbers (v2): 98,658 echoes — **stale, do not cite**
post-fix numbers (v3): 43,303 echoes — **current, publication-grade**

## limitations and future work

### current limitations

1. **no null baselines yet**: echo counts are not calibrated against random-term bundles or frequency-normalized expectations. a random-node control and a non-BG doctrinal control set (e.g., rājadharma terms) are needed to establish statistical significance. until then, raw counts demonstrate recurrence patterns but not their statistical unusualness.
2. **no morphological normalization**: Sanskrit is highly inflected and compound-rich. the current pipeline matches surface forms only — no stemming, compound decomposition, or sandhi resolution. philosophically identical teachings using different inflected forms may be missed; conversely, shared vocabulary in different argumentative contexts may trigger false matches.
3. **MiniLM on Sanskrit**: the multilingual sentence-transformer finds mostly verbatim repetitions in HK transliterated Sanskrit. true meaning-level echoes are better found via english queries (`--mode query --text "..."`). the semantic layer should be treated as exploratory, not evidential, until validated against manually annotated samples.
4. **speaker detection is a lower bound**: relies on `X uvAca` pattern. misses speakers introduced by other formulae (e.g., narrative description of who speaks). speaker-level results should be read as minimum counts.
5. **commentary alignment**: chapter numbers in Nīlakaṇṭha's commentary use vulgate (Chitrashala) edition numbering, not BORI. a full concordance between editions does not exist in machine-readable form.
6. **OCR quality**: Surya achieves ~80% character accuracy on Devanagari. ligature/spacing errors are common but key terms remain readable.

### planned controls

- random-node baseline: generate N random term bundles of equal size/frequency distribution and compare echo counts
- common-term baseline: measure echo density using high-frequency non-doctrinal terms to establish the noise floor
- non-BG control set: scan for a non-Gītā doctrinal cluster (e.g., rājadharma, arthaśāstra terms) to compare distribution
- manual adjudication: hand-verify a stratified sample of high-, medium-, and low-strength echoes for doctrinal relevance

## license

code: MIT. node data and analysis: CC-BY-4.0. corpus data (BORI) is not included and is subject to its own copyright.
