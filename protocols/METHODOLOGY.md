# methodology — abinitio audit pipeline

## pipeline architecture

the pipeline reads PRIMARY CORPUS FILES directly — it does NOT depend on the WisdomLib database.

```
data/raw/                          ← corpus files (3.6 GB)
├── pali_suttacentral/             ← SuttaCentral Bilara JSON (7 sources)
├── chinese_cbeta/                 ← CBETA XML (4 Āgama sources)
├── pali_commentary/               ← visuddhimagga (reference only)
└── sanskrit/, vedic/, jain/       ← future expansion (not yet active)

term_dictionary/entries/           ← hand-authored YAML (55 entries)
├── ch1_anatta_drift.yaml          ← 12 terms (anattā drift)
├── ch2_vedic_baseline.yaml        ← 16 terms (vedic baseline)
├── ch3_method_drift.yaml          ← 12 terms (method drift)
├── ch5_wrong_question.yaml        ← 15 terms (wrong question)
└── collocational_markers.yaml     ← 35 register markers

src/
├── corpus_config.py               ← declares 11 primary sources + paths
├── parsers.py                     ← text extraction (Bilara JSON, CBETA XML)
├── pipeline_runner.py             ← corpus scan: forms → hits → register → indices
├── compute_indices.py             ← structural indices from YAML role assignments
└── evidence_ledger.py             ← earlier evidence scanner (18,251 entries)
```

### data flow

```
corpus_config.py  →  parsers.py  →  pipeline_runner.py
(11 sources)         (text out)      (search term forms from YAML)
                                          ↓
                                     98,808 hits
                                          ↓
                                collocational marker co-occurrence
                                          ↓
                                frequency-weighted SI, H, MHI
```

the pipeline reads `forms` fields from each YAML entry (pali, sanskrit, chinese terms),
builds regex patterns, and scans every corpus file for matches. for each hit, it checks
a ±100 character context window for collocational markers (35 markers classified as
practice/system/ontic register) and computes register profiles per term.

**the database (`buddha_research/database/`) is a separate system.** it stores
WisdomLib reference data for dictionary lookups. database issues (scraping provenance,
duplicate entries) do not affect pipeline claims because the pipeline never reads the database.

---

## source provenance

### pali corpus (7 sources)

all from SuttaCentral Bilara — segmented, root Pāli, Mahāsaṅgīti edition.

| source | path | stratum | description |
|--------|------|---------|-------------|
| sutta_nipata_atthakavagga | `pali_suttacentral/.../snp/vagga4/` | earliest | Aṭṭhakavagga (oldest stratum) |
| sutta_nipata_parayanavagga | `pali_suttacentral/.../snp/vagga5/` | earliest | Pārāyanavagga (oldest stratum) |
| samyutta_nikaya | `pali_suttacentral/.../sn/` | early | Saṃyutta Nikāya (~2,904 suttas) |
| majjhima_nikaya | `pali_suttacentral/.../mn/` | early | Majjhima Nikāya (152 suttas) |
| digha_nikaya | `pali_suttacentral/.../dn/` | early | Dīgha Nikāya (34 suttas) |
| anguttara_nikaya | `pali_suttacentral/.../an/` | early | Aṅguttara Nikāya (~8,777 suttas) |
| sutta_nipata_full | `pali_suttacentral/.../snp/` | early | full Sutta Nipāta |

### chinese corpus (4 sources)

all from CBETA (Chinese Buddhist Electronic Text Association) — XML format.

| source | path | text | description |
|--------|------|------|-------------|
| dirgha_agama | `chinese_cbeta/.../T01/T01n0001_*` | 長阿含經 | parallel to Dīgha Nikāya |
| madhyama_agama | `chinese_cbeta/.../T01/T01n0026_*` | 中阿含經 | parallel to Majjhima Nikāya |
| samyukta_agama | `chinese_cbeta/.../T02/T02n0099_*` | 雜阿含經 | parallel to Saṃyutta Nikāya |
| ekottara_agama | `chinese_cbeta/.../T02/T02n0125_*` | 增壹阿含經 | parallel to Aṅguttara Nikāya |

### total: 11 primary sources → 98,808 corpus hits

---

## scope rationale

### why Pāli + Chinese

Pāli sutta piṭaka and Chinese Āgama translations are the standard comparative
corpus for early Buddhist studies. where both traditions preserve the same passage,
it provides independent attestation of pre-sectarian material. this is the
methodology used by Anālayo, Sujāto, Bucknell, and others in comparative early
Buddhist textual studies.

### what is NOT included (and why)

| tradition | status | reason |
|-----------|--------|--------|
| Jain Āgamas | planned | core Āgamas unavailable in machine-readable format; commentary notes extracted |
| Gāndhārī manuscripts | not included | fragmentary; Salomon corpus not yet digitized for pipeline use |
| Tibetan Kangyur | not included | translations are late (7th c+); useful for mahāyāna cross-reference but not early Buddhist baseline |
| Vedic/Upanishadic | planned | GRETIL sources identified but parser not yet built; used for manual citations in ch2 entries |

these are documented limitations, not oversights. the pipeline is designed to be
extensible — adding new sources requires only a `CorpusSource` entry in `corpus_config.py`
and a parser in `parsers.py`.

---

## index formulas

### SI — stance index (ch2, ch5)

```
SI = engagement / (engagement + opposition + both)
```

- engagement: term retains vedic usage (brahmavihāra, brahmacariya)
- opposition: term challenges vedic usage (brahmā demoted, sacrifice rejected)
- both: term shows both stances (counts 0.5 to each side)
- range: 0.0 (pure opposition) to 1.0 (pure engagement)

**structural SI** counts YAML `index_contribution` role assignments.
**corpus-weighted SI** weights each term's contribution by its occurrence count.

### H — hardening index (ch1, ch5)

```
H = numerator / (numerator + denominator)
```

- numerator: evidence of hardening (ontic, systematic, definitional language)
- denominator: baseline (therapeutic, release-oriented, practice language)
- range: 0.0 (pure therapeutic) to 1.0 (pure ontic)
- `primary` and `tracks_hardening` roles are qualitative anchors, not counted

### MHI — method hardening index (ch3)

```
MHI = (system + 0.5 × transition) / total
```

- practice: term remains in experiential/doing register
- system: term has moved to enumerative/categorical register
- transition: term shows the shift (practice → system)
- range: 0.0 (pure practice) to 1.0 (pure system)

**corpus-weighted MHI** uses collocational marker co-occurrence density:

```
MHI_corpus = Σ(system_density × count) / Σ((practice_density + system_density) × count)
```

---

## key result: structural vs corpus-weighted gap

| chapter | index | structural | corpus-weighted | Δ |
|---------|-------|-----------|-----------------|---|
| ch2 | SI | 0.52 | 0.576 | +0.056 |
| ch1 | H | 0.167 | 0.063 | -0.104 |
| ch3 | MHI | 0.583 | 0.156 | -0.427 |
| ch5 | SI | 0.389 | 0.455 | +0.066 |
| ch5 | H | 0.4 | 0.368 | -0.032 |

the ch3 MHI gap (Δ = -0.427) is the strongest signal: structurally, 8/12 terms
show practice→system transition, but in the actual early corpus, practice-register
markers outnumber system-register ~5:1. the hardening happens in commentarial texts
OUTSIDE the early corpus window — confirming the book's thesis that method-drift
is a post-canonical development.

---

## DB vs pipeline: separate systems

| system | reads | purpose | issues |
|--------|-------|---------|--------|
| pipeline | `data/raw/` corpus files | frequency counts, register detection, weighted indices | none |
| database | WisdomLib scraping + manual | dictionary lookups, reference definitions | 98% WisdomLib provenance |

the database stores reference data (PTS dictionary entries, Monier-Williams definitions,
WisdomLib cross-references). it is NOT used by the pipeline for any claims about
term frequency, register distribution, or semantic drift. database provenance issues
(predominantly WisdomLib scraping) are a documentation concern, not a validity concern
for the pipeline's quantitative claims.

the database has been split into:
- `buddha_research_primary.db` — curated, high-confidence entries
- `buddha_research_secondary.db` — scraped reference data (WisdomLib etc.)

---

## decolonization principles

the term dictionary and pipeline follow decolonization principles:

1. **source language primacy**: pāli/sanskrit/chinese terms are primary; english translations are secondary glosses
2. **no christian framing**: terms like "divine," "sacred," "soul" are avoided; we use tradition-native vocabulary
3. **temporal honesty**: each term is tracked across strata with dating confidence levels, not presented as having a single stable meaning
4. **dictionary critique**: standard references (PTS, Monier-Williams, WisdomLib) are compared against our temporal-strata analysis; disagreements are flagged with `[!]` markers
5. **colonial language awareness**: translation-induced drift is documented (e.g., jhāna → "meditation," bhāvanā → "meditation," sīla → "morality")
