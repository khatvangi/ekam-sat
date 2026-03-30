# Viṣṇu Sahasranāma: BORI Critical Edition vs Vulgate

## Sources
- **BORI CE**: Anuśāsanaparva 13.135.014-120 (Critical Edition, Poona)
- **Vulgate**: sanskritdocuments.org (Śaṅkara bhāṣya tradition, ch. 149 in vulgate numbering)
- **Nīlakaṇṭha**: Bhāratabhāvadīpa OCR (vol. 9000, pages 154-158, Surya ~80%)

## Overall Finding

**The two texts are ~88% identical at the character level** (spaces removed). The differences fall into four categories:

### Category 1: Orthographic / Sandhi variants (trivial)
Single-character differences due to sandhi resolution or scribal convention.
These do NOT affect the name list.

| Position | BORI | Vulgate | Type |
|----------|------|---------|------|
| multiple | -m (anusvāra) | -ṅ/-ñ (class nasal) | sandhi convention |
| v14 | vaSaTkAro | vaSaThkAro | extra aspirate in vulgate |
| multiple | final -H dropped | final -H retained | visarga handling |

### Category 2: Genuine name variants (significant)
These affect which names are in the list and their interpretation.

| BORI verse | BORI reading | Vulgate reading | Impact |
|------------|-------------|-----------------|--------|
| 13.135.037 | sahasramUrdhA | sahasramUrdhA | identical |
| 13.135.052 | vikSaraH | vikSaraH | identical |
| 13.135.053 | ...mahAbhAgo... | ...mahAbhAgo... | identical |
| 13.135.056 | rAmo virAmo viratoH | rAmo virAmo virajo | **virataH vs virajaH** — detached vs passionless |
| 13.135.082 | zUraH zauriH | zauriH zUraH | **word order swapped** |

### Category 3: Structural differences (significant)

1. **Vulgate has "OM" prefix** before verse 1. BORI does not.

2. **Vulgate has additional closing formula** after verse 107:
   "sarvapraharaṇāyudha OM nama iti" + "vanamālī gadī śārṅgī śaṅkhī cakrī ca nandakī / śrīmān nārāyaṇo viṣṇur vāsudevo 'bhirakṣatu"
   This closing verse is ABSENT from BORI CE (likely an interpolation or liturgical addition).

3. **Vulgate verse 108 (extra verse)**:
   The vulgate has 108 name-bearing verses; BORI has 107.
   The extra verse contains the closing names and the famous "sarvapraharaṇāyudhaḥ" as the final name.
   In BORI, this is the last name of verse 120 (= relative verse 107).

4. **Word boundary differences throughout**: The vulgate runs compounds together (bhUtakRdbhUtabhRdbhAvo) where BORI separates them (bhUtakRd bhUtabhRd bhAvo). This affects name-counting: the same text yields different name lists depending on where you split.

### Category 4: Vulgate additions not in BORI

1. **divaHspRk** — appears in vulgate (~v74) but may be absent or differently placed in BORI
2. **Closing dhyāna ślokas and nyāsa** — the vulgate text includes elaborate ritual apparatus (karanyāsa, aṅganyāsa, dhyāna ślokas) before the names begin. BORI has only the framing dialogue.

## Nīlakaṇṭha's Position

From the OCR (page 154), Nīlakaṇṭha states:
1. The names from "viśvaṃ viṣṇuḥ" onward are **spaṣṭārthaḥ** (self-evident in meaning)
2. For detailed etymological analysis: consult **Śrī Śaṅkarācārya's bhāṣya**
3. The VS is open to **all varṇas** including śūdras (*śūdraḥ sukham avāpnuyāt*)
4. The VS complements the Śiva Sahasranāma (which has 1,004 names vs VS's ~1,000)
5. Nīlakaṇṭha affirms the non-difference of Viṣṇu and Śiva (*viśvaṃ viṣṇur eva* — "the universe IS Viṣṇu")

## The Name-Count Problem

Both traditions claim 1,000 names. But:
- Simple space-delimited count on BORI: ~1,047 words
- The actual "1,000" depends on compound splitting conventions
- Śaṅkara's bhāṣya splits differently from Parāśara Bhaṭṭa's
- Same text → different 1,000 names depending on commentator

This is the most significant scholarly question: not which TEXT is original, but which SPLITTING is authoritative.

## Śiva Sahasranāma (for comparison)

Location in BORI: Anuśāsanaparva 13.014 (428 half-lines, ~214 verses)
- Nīlakaṇṭha's numbering: chapter 17
- Structure: COMPLETELY DIFFERENT from VS
  - VS: compact name-list (107 verses of dense epithets)
  - Śiva SN: narrative with devotee stories interspersed
  - Concentrated name-section: only verses 150-163 (~14 verses)
  - Remaining names scattered across 199 verses of narrative
- Nīlakaṇṭha notes: Śiva SN has 1,004 names (4 more than VS)

## Files in this directory

| File | Contents |
|------|----------|
| vsn_bori_ce.txt | Complete BORI CE ch. 13.135 (286 lines, HK) |
| vsn_bori_names_raw.txt | 107 name-bearing verses extracted (HK) |
| vsn_bori_names_list.txt | ~1,047 names parsed (rough, space-delimited) |
| vsn_vulgate_itrans.itx | Complete vulgate text (ITRANS, from sanskritdocuments.org) |
| vsn_vulgate_names_itrans.txt | Name verses only (ITRANS) |
| vsn_vulgate_names_hk.txt | Name verses converted to HK |
| shiva_sahasranama_bori_ce.txt | Complete BORI CE Śiva SN, ch. 13.014 (428 lines, HK) |
| nilakantha_vs_raw_pages154-158.txt | Nīlakaṇṭha OCR pages for VS commentary |
| vsn_bori_vs_vulgate_comparison.md | This file |
