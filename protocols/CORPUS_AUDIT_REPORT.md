# corpus audit report
## ab-initio buddha research project

**generated:** 2026-02-11
**pipeline version:** 5-chapter term dictionary pipeline
**methodology:** see `METHODOLOGY.md`

---

## corpus summary

| corpus | files | size | status | used by pipeline |
|--------|-------|------|--------|-----------------|
| pali_suttacentral | 112,181 | 929.8 MB | complete (SuttaCentral Bilara) | YES — 7 sources |
| chinese_cbeta | 21,989 | 2,390.8 MB | complete (CBETA XML) | YES — 4 sources |
| pali_commentary | 4 | 4.4 MB | reference only (visuddhimagga) | citations only |
| sanskrit | 23 | 10.7 MB | partial (mahāyāna texts) | citations only |
| vedic | 32 | 14.8 MB | partial (upanishads, ṛgveda) | citations only |
| jain | 3 | 0.6 MB | minimal (commentary notes) | citations only |
| **total** | **134,232** | **3,350.6 MB** | | |

---

## pipeline sources (11 active)

### pali sources (7)

| # | source | path | stratum | description |
|---|--------|------|---------|-------------|
| 1 | sutta_nipata_atthakavagga | `pali_suttacentral/.../snp/vagga4/` | earliest | Aṭṭhakavagga |
| 2 | sutta_nipata_parayanavagga | `pali_suttacentral/.../snp/vagga5/` | earliest | Pārāyanavagga |
| 3 | samyutta_nikaya | `pali_suttacentral/.../sn/` | early | Saṃyutta Nikāya |
| 4 | majjhima_nikaya | `pali_suttacentral/.../mn/` | early | Majjhima Nikāya |
| 5 | digha_nikaya | `pali_suttacentral/.../dn/` | early | Dīgha Nikāya |
| 6 | anguttara_nikaya | `pali_suttacentral/.../an/` | early | Aṅguttara Nikāya |
| 7 | sutta_nipata_full | `pali_suttacentral/.../snp/` | early | Sutta Nipāta (full) |

### chinese sources (4)

| # | source | path | stratum | description |
|---|--------|------|---------|-------------|
| 1 | dirgha_agama | `chinese_cbeta/.../T01/T01n0001_*` | early | 長阿含經 (parallel to DN) |
| 2 | madhyama_agama | `chinese_cbeta/.../T01/T01n0026_*` | early | 中阿含經 (parallel to MN) |
| 3 | samyukta_agama | `chinese_cbeta/.../T02/T02n0099_*` | early | 雜阿含經 (parallel to SN) |
| 4 | ekottara_agama | `chinese_cbeta/.../T02/T02n0125_*` | early | 增壹阿含經 (parallel to AN) |

---

## pipeline results (latest run: 2026-02-11)

| metric | value |
|--------|-------|
| total corpus hits | **110,873** |
| sources scanned | 11 |
| search terms | 67 (12 ch1, 16 ch2, 12 ch3, 12 ch4, 15 ch5) |
| collocational markers | 35 (15 practice, 15 system, 5 ontic) |
| scan time | ~105 seconds |

### per-chapter hit distribution

| chapter | terms | hits |
|---------|-------|------|
| ch2 (vedic baseline) | 16 | 52,973 |
| ch3 (method drift) | 12 | 20,290 |
| ch1 (anattā drift) | 12 | 19,346 |
| ch4 (nibbāna drift) | 12 | 12,065 |
| ch5 (wrong question) | 15 | 6,199 |

---

## term dictionary status

| file | entries | chapter | status |
|------|---------|---------|--------|
| `ch1_anatta_drift.yaml` | 12 | anattā drift | complete |
| `ch2_vedic_baseline.yaml` | 16 | vedic baseline | complete |
| `ch3_method_drift.yaml` | 12 | method drift | complete (harmonized 2026-02-11) |
| `ch4_nibbana_drift.yaml` | 12 | nibbāna drift | complete |
| `ch5_wrong_question.yaml` | 15 | wrong question | complete |
| `collocational_markers.yaml` | 35 | register markers | complete |
| **total** | **102** | | |

### audit results (2026-02-11)

- gaps/issues: **0**
- flagged items (standard reference disagreements): **13**
- broken family references: **0**

---

## structural indices

| chapter | index | value | contributions |
|---------|-------|-------|---------------|
| ch2 | SI | 0.52 | 25 (12E / 11O / 2B) |
| ch1 | H | 0.167 | 13 (1N / 5D / 2P / 5T) |
| ch4 | H | 0.375 | 12 (3N / 5D / 1P / 3T) |
| ch3 | MHI | 0.583 | 12 (1P / 3S / 8T) |
| ch5 | SI | 0.389 | 9 |
| ch5 | H | 0.4 | 9 |

### corpus-weighted indices

| chapter | index | structural | corpus-weighted | Δ |
|---------|-------|-----------|-----------------|---|
| ch2 | SI | 0.52 | 0.576 | +0.056 |
| ch1 | H | 0.167 | 0.063 | -0.104 |
| ch4 | H | 0.375 | 0.197 | -0.178 |
| ch3 | MHI | 0.583 | 0.156 | -0.427 |
| ch5 | SI | 0.389 | 0.455 | +0.066 |
| ch5 | H | 0.4 | 0.368 | -0.032 |

---

## not included (documented limitations)

| corpus | reason | plan |
|--------|--------|------|
| jain āgamas | core āgamas unavailable in machine-readable format | planned |
| gāndhārī manuscripts | fragmentary, not digitized for pipeline use | not planned |
| tibetan kangyur | late translations (7th c+), not early buddhist baseline | not planned |
| vedic/upanishadic texts | parser not yet built; manual citations used in ch2 | planned |
