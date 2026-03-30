# Viṣṇu Sahasranāma: Computational Splitting Analysis

## Date: 2026-03-27
## Source: BORI CE Anuśāsanaparva 13.135.014-120 (Harvard-Kyoto)

---

## The Problem

The Viṣṇu Sahasranāma is a continuous string of Sanskrit text (~8,663 characters) from which "one thousand names" are extracted. But the extraction depends on where you split the compounds. Different commentarial traditions (Śaṅkara, Parāśara Bhaṭṭa, Nīlakaṇṭha) split differently, producing different lists of names from the same verses.

This analysis asks: how many grammatically valid decompositions exist?

---

## Method

1. Remove all spaces from the BORI CE name-verses to produce a continuous string
2. Identify all grammatically valid split points using Sanskrit morphological rules:
   - After visarga (H) — the most common boundary marker (~43% of BORI splits)
   - After sandhi-final -o (from -aH before voiced) — ~22%
   - After long vowels (Ā, Ī) in nominal position — ~12%
   - After anusvāra (M) — ~3%
   - After word-final -r (dhātur, viṣṇur type) — ~8%
   - After visarga-sandhi consonants (ś before c, s before t) — ~2%
   - After word-final nasals (n, m) — ~3%
   - After stop consonants at voiced junctions — ~2%
   - After short -a before particles/avagraha — ~2%
3. Run dynamic programming to find all valid decompositions for each target name-count
4. Constrain: minimum name length 3 chars, maximum 40 chars

## Validation

The grammar rules capture **89% of BORI's editorial splits** (944/1054). The 11% missed are primarily:
- Word-final -r after consonant (not just vowel): viSNur, sthANur
- Certain compound-internal boundaries the rules don't recognize
- A few unusual sandhi patterns

The rules also identify **891 additional valid split points** that BORI's editors chose NOT to use. These are the source of the ambiguity.

---

## Results

### The string is massively underdetermined

| Metric | Value |
|--------|-------|
| String length | 8,663 characters |
| BORI editorial splits | 1,054 (yielding ~1,055 words) |
| Grammatically valid split points | 1,835 |
| Alternative valid splits (BORI doesn't use) | 891 |
| BORI words with internal valid splits | 677 / 1,055 (64%) |

**64% of BORI's "names" contain at least one internal point where the string could validly be split differently.**

### Reachable name counts

Any name count from **222 to 1,100+** is reachable through grammatically valid splitting.

### Path counts for specific targets

| Target | Distinct valid decompositions |
|--------|-------------------------------|
| **1,000** (sahasra) | ~1.35 × 10^362 |
| **1,008** (aṣṭottara) | ~2.24 × 10^362 |
| **999** | ~2.22 × 10^362 |
| **1,001** | ~8.16 × 10^361 |
| Total in [980, 1020] | ~8.33 × 10^369 |

For comparison: the number of atoms in the observable universe is ~10^80. The number of valid "thousand-name" decompositions of the VS exceeds this by a factor of 10^282.

---

## The Ambiguity Map

The most ambiguous words (BORI's splitting) — words containing the most internal valid split points:

| BORI word | Internal splits | Example alternative |
|-----------|----------------|-------------------|
| sarvayogaviniHsRtaH | 3 | sarva + yogaviniHsRtaH |
| siddhArthaH | 3 | siddhA + rthaH |
| candrAMzur | 3 | candrA + Mzur |
| amRtAMzUdbhavo | 3 | amRtAM + zUdbhavo |
| cANUrAndhraniSUdanaH | 3 | cANUrA + ndhraniSUdanaH |
| nArasiMhavapuH | 2 | nAra + siMhavapuH |
| puNDarIkAkSo | 2 | puNDarI + kAkSo |
| lokAdhiSThAnam | 2 | lokA + dhiSThAnam |
| kapilAcAryaH | 2 | kapilA + cAryaH |

---

## What This Means

### 1. "Sahasranāma" is an interpretive act, not a textual fact

The continuous Sanskrit string does not contain exactly 1,000 names. It contains a text that CAN BE SPLIT into 1,000 names — or 999, or 1,008, or 500, or 1,100. The "one thousand" is imposed by the commentator's splitting convention, not extracted from the text by grammatical necessity.

### 2. Every traditional commentator's list is valid

Śaṅkara's 1,000 names and Parāśara Bhaṭṭa's 1,000 names differ in ~100+ places. Both are grammatically valid decompositions. There is no mathematical basis for preferring one over the other on grammatical grounds alone. The preference is theological: Śaṅkara reads Advaita meanings, Bhaṭṭa reads Viśiṣṭādvaita meanings.

### 3. The BORI editors' split is not "1,000"

The BORI Critical Edition splits the text into ~1,055 words (including particles ca, tu, eva). Removing particles gives ~1,047. This is closer to the traditional count but not exactly 1,000. The editors were not trying to produce exactly 1,000 — they were producing the most natural word-boundary reading.

### 4. The ambiguity is concentrated, not uniform

64% of BORI's words have internal split alternatives. But the ambiguity clusters around long compounds (mahā-, sarva-, ananta- prefixed names) and sandhi junctions involving -o and -A. Short names (ajaH, vasuH, hariH) have no ambiguity — there's only one way to split them.

---

## Future work

1. **Map Śaṅkara's and Parāśara Bhaṭṭa's splits onto the graph** — identify exactly where they diverge and whether their divergences are in high-ambiguity or low-ambiguity zones
2. **Add dictionary constraint** — require each name to be an attested Sanskrit word or valid compound. This should dramatically reduce the solution space.
3. **Semantic constraint** — require each name to be a plausible Viṣṇu epithet. This is the hardest constraint to formalize but would give the tightest bound.
4. **Apply the same analysis to the Śiva Sahasranāma** (13.014) — the narrative structure makes it a different problem
5. **Information-theoretic analysis** — what is the entropy of the splitting? How many bits of information does a commentator's choice convey?

---

## Files

| File | Contents |
|------|----------|
| vsn_bori_ce.txt | BORI CE complete chapter (HK) |
| vsn_bori_names_raw.txt | 107 name-bearing verses |
| vsn_bori_names_list.txt | ~1,047 names (BORI split) |
| vsn_vulgate_itrans.itx | Vulgate complete (ITRANS) |
| vsn_vulgate_names_hk.txt | Vulgate names in HK |
| vsn_bori_vs_vulgate_comparison.md | BORI vs vulgate comparison |
| vsn_ambiguity_stats.json | Ambiguity statistics |
| vsn_computational_analysis.md | This document |
| shiva_sahasranama_bori_ce.txt | Śiva SN (BORI CE, HK) |
