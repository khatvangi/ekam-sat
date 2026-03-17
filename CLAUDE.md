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
# layer 1: terminological scan — use v2 nodes (123 nodes, exhaustive)
python scan_corpus.py --corpus /storage/mbh/bori/hk --nodes ../data/bg_nodes_v2.json --output ../output/v2/ --freq-map

# single node deep dive
python scan_corpus.py --corpus /storage/mbh/bori/hk --nodes ../data/bg_nodes_v2.json --node N006 --output ../output/N006/

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

- `data/bg_nodes_v2.json` — 123 BG doctrinal nodes (exhaustive, pre-sectarian lens), with HK term clusters, repetition tracking, echo hypotheses. Methodology: `protocols/node_extraction_methodology.md`
- `data/bg_nodes.json` — Original 35 nodes (superseded by v2)
- `scripts/scan_corpus.py` — Layer 1: regex search for HK terms across all 18 parvas, excludes BG itself (Bhishmaparva ch 23-40)
- `scripts/extract_speakers.py` — Layer 2: identifies `X uvAca` patterns to segment discourse by speaker, cross-references with echo results
- `scripts/semantic_search.py` — Layer 3: sentence-transformer embeddings for meaning-level matching beyond vocabulary

## Corpus (not in repo, kept locally)

The corpus lives at `bori/hk/` (symlink to `bori/ascii/`). Files: `MBh00.txt`–`MBh18.txt`. Format: `PPcccvvvx` verse IDs (PP=parva, ccc=chapter, vvv=verse, x=half-verse a/b/c/d/e). Book 00 is metadata only.

## Nīlakaṇṭha OCR (nilakantha/)

- `nilakantha/scripts/ocr_pipeline.py` — Gemini Vision OCR for Bhāratabhāvadīpa commentary PDFs
- Uses `google.genai` (new library), model `gemini-2.5-flash-lite` (default), API key via `GOOGLE_API_KEY` env var
- **SPENDING CAP: $22 already spent on Śāntiparva OCR. Do NOT run OCR or any paid API calls without explicit user approval. Cost estimates were 4x wrong — be extremely cautious.**
- 600 DPI PDFs at `nilakantha/600dpi/`, Chitrashala edition at `nilakantha/chitrashala/`
- Volume mapping: 8995=Ādi+Sabhā, 8996=Āraṇyaka+Virāṭa, 8997=Udyoga+Bhīṣma, 8998=Droṇa+Karṇa, 8999=Sauptika+Strī+Śānti(pp42-422), 9000=Anuśāsana+rest
- `nilakantha/scripts/ocr_surya.py` — Surya OCR (local GPU, FREE, ~10s/page, ~80% quality)
- **USE Surya for all future OCR. Gemini only with explicit user approval.**

## Key Details

- The multilingual MiniLM model finds mostly verbatim repetitions in Sanskrit. Use `--mode query` with English for true meaning-level echoes, or swap in an Indic model (`ai4bharat/indic-bert`)
- BG in BORI: Bhishmaparva ch 23-40 (BG ch1=06.023, ch18=06.040). Formula: BORI ch = BG ch + 22
- v3 scan results (post-bugfix): 43,303 total echoes, 2,352 strong (2+ core terms). Śāntiparva leads (9,153). Previous v2 numbers (98,658) were inflated by IGNORECASE bug.
- N006 (Indestructibility of Self) dominates at ~19K hits — `nitya`/`aja`/`avyaya` are extremely common in Sanskrit, so high-frequency nodes need the `--min-strength` filter
- Speaker detection relies on `X uvAca` pattern in HK text — works well but misses speakers introduced by other formulae
- User is writing a book on Ekam Sat — methodology must be publication-grade and defensible
