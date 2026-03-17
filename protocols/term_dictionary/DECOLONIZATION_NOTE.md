# decolonization audit — abrahamic/eurocentric leak removal

**date:** 2026-02-10
**scope:** all 5 YAML files in entries/
**status:** applied

---

## why this matters

the term dictionary exists to show how buddhist terms drift from their
original senses. but if the dictionary ITSELF uses imported western/abrahamic
categories to describe those terms, it performs the very distortion it
claims to detect. the book loses credibility if it critiques PTS for
flattening temporal strata while simultaneously importing "god," "soul,"
"worship," and "prayer" into its own descriptions.

the issue is not sensitivity — it is ACCURACY. a deva is not a "god."
a jīva is not a "soul." yajña is not "worship." brahman is not "prayer."
each of these english words carries abrahamic assumptions that do not
apply to the indian concepts. using them is not just imprecise — it is
the exact category-error the book identifies in missionary-era scholarship
and perpetuated in standard dictionaries.

---

## what was found (2026-02-10 audit)

| category | count | examples | problem |
|----------|-------|----------|---------|
| "god" for deva/brahmā/indra | ~30 | "supreme warrior god," "creator god," "divine being / god" | imports abrahamic creator-omnipotent-transcendent associations onto cosmological beings within saṃsāra |
| "soul" for jīva/ātman | ~15 | "individual soul," "is the soul the same as the body" | imports abrahamic soul (created by god, judged after death) onto jīva (eternal individual in jain metaphysics) and ātman (universal absolute in upanishadic thought) |
| "worship" for yajña/deva-relation | ~6 | "objects of worship," "worship → subordination" | imports abrahamic adoration (power asymmetry, personal god) onto vedic ritual exchange (do ut des, reciprocal) |
| "prayer" for brahman | ~8 | "prayer-power," "lord of prayer" | imports abrahamic petition-to-god onto vedic sacred utterance with inherent power (mantra-force) |
| "heaven" for svarga/sagga | ~5 | "heaven" for celestial realms | imports abrahamic eternal-reward-dwelling onto impermanent cosmological realm within saṃsāra |
| "afterlife" | ~3 | "afterlife in ancestral realms" | imports abrahamic soul-after-death onto indian punarbhava/transmigration |
| "divine" for deva/agni | ~10 | "divine priest," "divine favor" | imports latin-christian divinus (of god/transcendent) onto vedic celestial function |
| "creator god" compound | ~12 | throughout ch5 | frames issaranimmāna debate in abrahamic terms, which is precisely the "wrong question" ch5 critiques |

---

## what was changed

| abrahamic import | replaced with | rationale |
|-----------------|---------------|-----------|
| "god" (for deva) | "deva" or "celestial being" | devas are beings within the cosmic order, subject to rebirth, not transcendent creators |
| "god" (for brahmā) | "brahmā" or "celestial deity" | brahmā is a specific cosmological being, first among devas, not the abrahamic god |
| "supreme god" (for indra) | "supreme deva" or "king of devas" | indra is the most powerful deva — still within saṃsāra |
| "creator god" | "creator-lord" or "issaranimmāna" | the buddhist critique targets issaranimmāna (creation-by-a-lord), not the abrahamic god-concept |
| "soul" (for jīva) | "life-principle" or "jīva" | jīva in jain metaphysics ≠ soul in abrahamic theology |
| "soul" (for ātman) | "self" or "ātman" | ātman = self/self-principle, not soul |
| "worship" (for yajña) | "ritual offering" or "sacrificial exchange" | vedic yajña is reciprocal exchange, not adoration |
| "prayer" (for brahman) | "sacred utterance" or "mantra-force" | vedic brahman = utterance with inherent power, not petition |
| "heaven" (for svarga) | "celestial realm" or native term | svarga is impermanent cosmological realm, not eternal reward |
| "afterlife" | "post-mortem continuation" or "transmigration" | no "after-life" in indian thought — only re-birth |
| "divine" (for deva/agni) | "celestial" or function-specific term | avoids latin-christian divinus associations |
| "divine favor" | "ritual reciprocity" | vedic ritual is exchange, not petition for favor |
| "divine communion" | "deva-communion" | soma ritual is reciprocal exchange with devas, not christian eucharist |
| "divine king" | "deva-king" | renders devānaminda accurately without latin-christian overtone |
| "divine ritualist" | "deva-ritualist" | agni as devam ṛtvijam — the term devam is already the correct descriptor |
| "divine fire" | "sacred fire" | avoids implying fire's sacredness derives from a transcendent god |
| "divine will" | "the lord's volition (īśvara-ceṣṭita)" | renders the actual sanskrit technical term rather than importing "divine" |
| "divine power/qualities" | "lordly power/qualities" | aiśvarya derives from īśvara (lord), not from latin divinus |

---

## the principle

when describing indian concepts, use INDIAN terms (with gloss if needed)
rather than english words that carry abrahamic baggage. the test:

> would a 5th-century-BCE indian recognize this description?
> or does it require knowledge of a religion that didn't exist yet?

if the description requires knowing what "god" means in the abrahamic
sense to understand the contrast being drawn, the description has failed.
the concepts must be described on their OWN terms first, and only then
compared cross-culturally.

---

## exceptions

some uses of these terms are ACCEPTABLE:

1. **quoting standard references** — "MW defines nāstika as 'atheist'" is
   fine because we are CRITIQUING the import, not performing it.

2. **explicit cross-cultural comparison** — "this is NOT what christians
   mean by 'god'" is fine because the comparison is marked.

3. **the jīva entry's undeclared-question quotes** — when citing MN 63's
   "is the jīva the same as the body?" — keeping the traditional translation
   "soul" in the quote itself is acceptable IF the surrounding text
   flags it as an imported translation.

---

## second-pass cleanup (2026-02-10)

the initial audit caught the major imports (god, soul, worship, prayer,
heaven, afterlife). a verification pass found 11 surviving "divine"
instances — 1 in MW quote (acceptable), 10 in our own voice. these were
replaced with "deva-communion," "deva-king," "deva-ritualist," "sacred
fire," "lordly power/qualities," and "the lord's volition (īśvara-ceṣṭita)."

final verification: ZERO leaks in our own voice. all remaining instances
of flagged terms are inside quoted PTS/MW references or in passages that
explicitly critique/flag those terms as western imports.

---

## guard going forward

any new entries or edits should be checked against this note.
the automated audit script should be updated to flag these terms
when they appear outside of quoted-reference contexts.
