# code audit report
## current workspace review

**generated:** 2026-03-13
**scope:** current modified and newly added executable code in `/storage/mbh`
**method:** static review plus targeted execution of non-destructive scripts

---

## findings

### 1. high — `scan_corpus.py` now drops non-Gita material

**file:** `/storage/mbh/scripts/scan_corpus.py`

The scanner now excludes Bhishmaparva chapters `23-42`:

```python
BG_CHAPTERS_IN_BHISHMA = set(range(23, 43))
```

But the surrounding comment states that chapters `41-42` are post-Gita narrative. Since the stated goal is to search the Mahabharata outside the Bhagavad Gita, this change introduces false negatives by omitting legitimate non-BG material.

**impact:** echo counts and downstream analysis can be understated, especially in Bhishmaparva.

**relevant lines:** `47-50`, `67-72`

---

### 2. high — `compute_indices.py` is not runnable from the repo layout

**file:** `/storage/mbh/protocols/compute_indices.py`

The script resolves its term-dictionary directory from the repository root:

```python
ROOT = Path(__file__).parent.parent
ENTRIES_DIR = ROOT / "term_dictionary" / "entries"
```

However the YAML files actually live under:

```text
/storage/mbh/protocols/term_dictionary/entries
```

Running the script confirms the breakage:

```text
FileNotFoundError: [Errno 2] No such file or directory:
'/storage/mbh/term_dictionary/entries/ch1_anatta_drift.yaml'
```

**impact:** the structural index report cannot currently be regenerated.

**relevant lines:** `24-26`, `41-45`

---

### 3. high — `pipeline_runner.py` fails before it can execute

**file:** `/storage/mbh/protocols/pipeline_runner.py`

Two separate issues make the pipeline runner non-functional as committed:

1. It imports local modules that are not present in this repository:

```python
from corpus_config import get_primary_sources, CorpusSource
from parsers import get_parser
```

2. It points `ENTRIES_DIR` at the same nonexistent root-level `term_dictionary` path used by `compute_indices.py`.

Running the script confirms the first failure immediately:

```text
ModuleNotFoundError: No module named 'corpus_config'
```

**impact:** the corpus-weighted pipeline cannot be executed or validated from this checkout.

**relevant lines:** `28-31`, `42-44`

---

### 4. medium — resumed OCR runs can overwrite aggregate outputs with partial data

**files:** `/storage/mbh/nilakantha/scripts/ocr_pipeline.py`, `/storage/mbh/nilakantha/scripts/ocr_surya.py`

Both OCR scripts skip per-page files that already exist, but still rebuild the combined JSON and concatenated text outputs from the in-memory `results` list, which only contains pages processed during the current invocation.

That means a resumed run can rewrite:

- `*_ocr_results.json` / `*_surya_results.json`
- `*_clean_devanagari.txt`
- `*_clean_hk.txt` (Gemini script)

with only the newly processed subset, silently truncating the aggregate outputs.

**impact:** resumed OCR jobs can corrupt the final assembled artifacts even when page-level files are preserved.

**relevant lines:**
- `ocr_pipeline.py`: `192-201`, `255-305`
- `ocr_surya.py`: `113-121`, `158-189`

---

### 5. medium — structural comparison in `pipeline_runner.py` is hardcoded

**file:** `/storage/mbh/protocols/pipeline_runner.py`

The report comparison section says it is loading structural indices, but the values are hardcoded directly in the script:

```python
structural = {
    "ch2_si": 0.52,
    "ch1_h": 0.167,
    "ch3_mhi": 0.583,
    "ch4_h": 0.375,
    "ch5_si": 0.389,
    "ch5_h": 0.4,
}
```

Any update to the term dictionary or structural index method will make this comparison stale while still presenting it as current.

**impact:** report deltas can look precise while being out of sync with the source data.

**relevant lines:** `491-499`

---

## verification performed

- Ran `python protocols/compute_indices.py`
  - Result: immediate `FileNotFoundError` on missing term-dictionary path.
- Ran `python protocols/pipeline_runner.py`
  - Result: immediate `ModuleNotFoundError: corpus_config`.

I did not execute the OCR scripts because they are either paid (`Gemini`) or GPU-intensive (`Surya`); those findings are based on control-flow review.

---

## review boundary

This report focuses on the executable code currently changed or added in the workspace:

- `scripts/scan_corpus.py`
- `protocols/compute_indices.py`
- `protocols/pipeline_runner.py`
- `nilakantha/scripts/ocr_pipeline.py`
- `nilakantha/scripts/ocr_surya.py`

It does not attempt a full factual audit of the large JSON/text data files added in this workspace.
