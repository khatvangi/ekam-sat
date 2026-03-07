# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

**Ekam Sat Project** — three-layer analysis pipeline proving that the Bhagavad Gita's teachings are scattered across the entire Mahābhārata (~89,000 verses, BORI Critical Edition), spoken by different sages in different contexts but converging on one point.

## Setup

```bash
pip install sentence-transformers numpy pandas scikit-learn

# corpus must be at bori/hk/ (Harvard-Kyoto ASCII transliteration)
# if you have bori/ascii/, symlink it: ln -s bori/ascii bori/hk
```

## Pipeline (run from `scripts/`)

```bash
# layer 1: terminological scan (fast, ~2 min)
python scan_corpus.py --corpus /storage/mbh/bori/hk --nodes ../data/bg_nodes.json --output ../output/ --freq-map

# single node deep dive
python scan_corpus.py --corpus /storage/mbh/bori/hk --node N03 --output ../output/N03/

# layer 2: speaker/discourse extraction
python extract_speakers.py --corpus /storage/mbh/bori/hk --echoes ../output/echo_results.csv --output ../output/

# layer 3: build embeddings (slow, 30-90 min, run once)
python semantic_search.py --corpus /storage/mbh/bori/hk --mode build --output ../output/embeddings/

# semantic sweep (after embeddings built)
python semantic_search.py --mode sweep --output ../output/embeddings/

# search by meaning (English works better than Sanskrit for this model)
python semantic_search.py --mode query --text "the self is eternal" --output ../output/embeddings/
```

## Architecture

- `data/bg_nodes.json` — 35 BG doctrinal nodes with Harvard-Kyoto term clusters for grep matching
- `scripts/scan_corpus.py` — Layer 1: regex search for HK terms across all 18 parvas, excludes BG itself (Bhishmaparva ch 25-42)
- `scripts/extract_speakers.py` — Layer 2: identifies `X uvAca` patterns to segment discourse by speaker, cross-references with echo results
- `scripts/semantic_search.py` — Layer 3: sentence-transformer embeddings for meaning-level matching beyond vocabulary

## Corpus (not in repo, kept locally)

The corpus lives at `bori/hk/` (symlink to `bori/ascii/`). Files: `MBh00.txt`–`MBh18.txt`. Format: `PPcccvvvx` verse IDs (PP=parva, ccc=chapter, vvv=verse, x=half-verse a/b/c/d). Book 00 is metadata only.

## Key Details

- The multilingual MiniLM model finds mostly verbatim repetitions in Sanskrit. Use `--mode query` with English for true meaning-level echoes, or swap in an Indic model (`ai4bharat/indic-bert`)
- N01 (Indestructibility of Self) dominates at ~19K hits — `nitya`/`aja`/`avyaya` are extremely common in Sanskrit, so high-frequency nodes need the `--min-strength` filter
- Speaker detection relies on `X uvAca` pattern in HK text — works well but misses speakers introduced by other formulae
