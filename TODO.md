# ekam sat — master todo list

## status key
- [ ] not started
- [~] in progress
- [x] done

---

## phase 0: the eighteen vishadas (BOOK STRUCTURE) — DONE 2026-03-21

- [x] framework document: docs/eighteen_vishadas.md
- [x] P01 Adi: inherited curse
- [x] P02 Sabha: witnessed humiliation
- [x] P03 Aranyaka: chronic exile
- [x] P04 Virata: forced concealment
- [x] P05 Udyoga: failed peace
- [x] P06 Bhishma: anticipatory grief (the one the Gita resolves)
- [x] P07 Drona: moral injury (the lie)
- [x] P08 Karna: retroactive fratricide
- [x] P09 Shalya: determined endgame
- [x] P10 Sauptika: vengeance / doctrine weaponized
- [x] P11 Stri: accomplished loss (three registers)
- [x] P12 Shanti: burden of governance
- [x] P13 Anushasana: dying teacher
- [x] P14 Ashvamedha: atonement
- [x] P15 Ashramavasika: aging and departure
- [x] P16 Mausala: self-destruction / curse fulfilled
- [x] P17 Mahaprasthanika: the last walk / the dog
- [x] P18 Svargarohana: cosmic injustice
- [ ] review all 18 essays for Sanskrit accuracy and verse references
- [ ] rename P10/P11/P16/P17/P18 essay files for consistent naming (p10_, p11_, etc.)
- [ ] write book introduction using 18 vishadas as spine

---

## phase 1: paraphrase family curation

### per-node curation (output/paraphrase/paraphrase_families.json)
for each node, review expansion words and mark keep/drop/add.

- [ ] N006 (atman indestructible) — review 20 expansion candidates
- [ ] N009 (sat/asat) — review expansions
- [ ] N016 (desire chain) — review expansions
- [ ] N017 (nishkama karma) — review expansions
- [ ] N015 (sthitaprajna) — review expansions
- [ ] N011 (svadharma) — review expansions
- [ ] N047 (two prakritis) — review expansions
- [ ] N058 (aksara brahman) — review expansions
- [ ] N095 (brahman womb) — review expansions
- [ ] N022 (desire enemy) — review expansions
- [ ] N075 (equal vision) — review expansions
- [ ] N033 (sannyasa = yoga) — review expansions
- [ ] N048 (divine origin/dissolution) — review expansions
- [ ] N093 (purusha-prakriti) — review expansions
- [ ] N108 (three tapas) — review expansions
- [ ] remaining 108 nodes — batch review after gold set

### synonym group review
- [ ] review atman_self stems — add missing synonyms
- [ ] review brahman_absolute stems
- [ ] review karma_action stems
- [ ] review jnana_knowledge stems
- [ ] review bhakti_devotion stems
- [ ] review yoga_discipline stems
- [ ] review dharma_order stems
- [ ] review moksha_liberation stems
- [ ] review kama_desire stems
- [ ] review guna_quality stems
- [ ] review tyaga_renunciation stems
- [ ] review maya_illusion stems
- [ ] add new groups: kala (time), deva (divine), loka (world-order)

---

## phase 2: semantic meaning families (node_semantics.yaml)

### gold standard nodes (15-20 priority)
populate full semantic profiles in data/node_semantics.yaml:

- [~] N006 (atman indestructible) — starter done, needs hard_positive/false_positive
- [~] N009 (sat/asat) — starter done
- [~] N017 (nishkama karma) — starter done
- [~] N016 (desire chain) — starter done
- [~] N015 (sthitaprajna) — starter done
- [~] N075 (equal vision) — starter done
- [~] N047 (two prakritis) — starter done
- [~] N033 (sannyasa = yoga) — starter done
- [~] N011 (svadharma) — starter done
- [ ] N058 (aksara brahman) — create semantic profile
- [ ] N095 (brahman womb) — create semantic profile
- [ ] N048 (divine origin/dissolution) — create semantic profile
- [ ] N093 (purusha-prakriti) — create semantic profile
- [ ] N108 (three tapas) — create semantic profile
- [ ] N069 (divine cosmic relations) — create semantic profile
- [ ] N022 (desire enemy) — create semantic profile
- [ ] N060 (om imperishable) — create semantic profile

### per-node validation annotation
for each gold node, annotate 10 passages:
- 3 strong positives (clearly teaches this)
- 3 moderate (partially teaches this)
- 2 false positives (term overlap but wrong doctrine)
- 2 edge cases

- [ ] N006 validation set
- [ ] N009 validation set
- [ ] N017 validation set
- [ ] (continue for all gold nodes)

---

## phase 3: inverse map (BG ↔ MBH)

### bottom-up MBH node discovery (data/mbh_extra_nodes.yaml)
extract teachings from high-density non-BG passages:

- [~] X001 rajadharma burden — placeholder created, needs passage refs
- [~] X002 dandaniti statecraft — placeholder created
- [~] X003 grief dharma — placeholder created
- [~] X004 tirtha pilgrimage — placeholder created
- [~] X005 narrative dharma — placeholder created
- [ ] pitR-dharma (ancestor obligations)
- [ ] strI-dharma (dharma of women)
- [ ] vanaprastha (forest asceticism)
- [ ] kAla as independent force (beyond guna)
- [ ] ritual yajña (literal, not BG's metaphorical)
- [ ] political alliance theory (sandhi-vigraha)
- [ ] ecological/animal dharma
- [ ] (discover more from Shanti/Anushasana scan)

### build inverse map scripts
- [ ] write scripts/semantic_mapper.py — score passages against meaning families
- [ ] write scripts/inverse_map.py — BG-vs-MBH matrix, selection index, types A-E
- [ ] write scripts/cluster_asymmetry.py — compare doctrinal packages BG vs outside

### compute inverse metrics
- [ ] selection_index per node: (outside_density - bg_density) / (outside + bg + ε)
- [ ] classify all nodes as type A/B/C/D/E
- [ ] assign inverse_relation tags: omitted / muted / transformed / absorbed / opposed / backgrounded

---

## phase 4: deeper structural layers

### tattva-sadhana-phala triadic coding
- [ ] classify each of 123 BG nodes into tattva / sadhana / phala
- [ ] classify MBH extra nodes similarly
- [ ] compare triadic shape of BG vs MBH teaching

### narrative situation tagging
- [ ] tag discourse contexts: battle_crisis, kingship_instruction, grief_consolation,
      ascetic_instruction, cosmological_teaching, post_war_reflection, exile_counsel
- [ ] test whether certain nodes cluster in certain narrative pressures

### discourse sequence similarity
- [ ] encode node order within major speeches
- [ ] compare teaching-progression between BG and other discourses
- [ ] build teaching-sequence similarity metric

### internal witness layer
- [ ] detect self-referential passages (MBH interprets itself)
- [ ] find passages where speakers summarize/recontextualize earlier teachings
- [ ] map these cross-references to node architecture

---

## phase 5: technical upgrades

### morphology-aware matching
- [ ] integrate curated paraphrase families into scan pipeline
- [ ] add compound decomposition (basic)
- [ ] add sandhi resolution (basic)
- [ ] re-run full scan with morphology-aware matching

### word boundary handling
- [ ] add \b or whitespace matching to scan_corpus.py regex
- [ ] re-run and compare counts

### manual adjudication sample
- [ ] randomly sample 100 echoes (33 high, 33 medium, 34 low strength)
- [ ] manually classify: true echo / partial echo / false positive
- [ ] compute precision at each strength level
- [ ] report as calibration for all automated counts

### rebuild embeddings with fixed regex
- [ ] re-run semantic_search.py --mode build with [a-e] regex
- [ ] compare embedding counts before/after

---

## phase 6: publication preparation

### writing
- [ ] draft methodology chapter (node extraction, pipeline, controls)
- [ ] draft results chapter (echo topology, speaker signatures, compression)
- [ ] draft inverse chapter (what BG selects, compresses, omits)
- [ ] draft siddhanta framing chapter (not sectarian, not "lens")

### figures
- [ ] parva heatmap (node × parva frequency)
- [ ] co-occurrence network graph (PMI clusters)
- [ ] speaker doctrinal profiles (radar charts)
- [ ] BG-vs-MBH selection index histogram
- [ ] compression comparison (BG vs top MBH discourses)

### push to github
- [x] initial commit
- [x] v3 pipeline + all scripts
- [x] dharma topology
- [x] paraphrase families
- [ ] curated semantic families
- [ ] inverse map results
- [ ] final publication data
