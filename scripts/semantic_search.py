#!/usr/bin/env python3
"""
MBH Semantic Embedding Pipeline
=================================
Uses sentence-transformer embeddings to find non-obvious doctrinal echoes —
verses that MEAN the same thing as a BG teaching without using the same terms.

This catches the minor sages, the narrative asides, the half-verses in
conversation that no grep would surface.

Usage:
    # Install dependencies first:
    pip install sentence-transformers numpy pandas scikit-learn

    # Build embeddings (slow, run once):
    python semantic_search.py --corpus /storage/mbh/bori/hk --mode build --output ../output/

    # Search for BG verse echoes:
    python semantic_search.py --mode search --bg-verse "2.47" --output ../output/

    # Search custom Sanskrit query:
    python semantic_search.py --mode query --text "action without attachment to results" --output ../output/

    # Full BG node sweep:
    python semantic_search.py --mode sweep --output ../output/
"""

import os
import re
import json
import argparse
import numpy as np
from pathlib import Path
from collections import defaultdict


# BG verses in Roman transliteration (Harvard-Kyoto) — key verses as query anchors
BG_KEY_VERSES = {
    "2.47": "karmaṇy evādhikāras te mā phaleṣu kadācana mā karmaphalahetur bhūr mā te saṅgo 'stv akarmaṇi",
    "2.20": "na jāyate mriyate vā kadācin nāyaṁ bhūtvā bhavitā vā na bhūyaḥ ajo nityaḥ śāśvato 'yaṁ purāṇo na hanyate hanyamāne śarīre",
    "6.29": "sarvabhūtastham ātmānaṁ sarvabhūtāni cātmani īkṣate yogayuktātmā sarvatra samadarśanaḥ",
    "13.27": "samaṁ sarveṣu bhūteṣu tiṣṭhantaṁ parameśvaram vinaśyatsv avinaśyantaṁ yaḥ paśyati sa paśyati",
    "18.66": "sarvadharmān parityajya mām ekaṁ śaraṇaṁ vraja ahaṁ tvāṁ sarvapāpebhyo mokṣayiṣyāmi mā śucaḥ",
    "2.55": "prajahāti yadā kāmān sarvān pārtha manogatān ātmany evātmanā tuṣṭaḥ sthitaprajñas tadocyate",
    "3.37": "kāma eṣa krodha eṣa rajoguṇasamudbhavaḥ mahāśano mahāpāpmā viddhy enam iha vairiṇam",
    "4.18": "karmaṇy akarma yaḥ paśyed akarmaṇi ca karma yaḥ sa buddhimān manuṣyeṣu sa yuktaḥ kṛtsnakarmakṛt",
    "11.32": "kālo 'smi lokakṣayakṛt pravṛddho lokān samāhartum iha pravṛttaḥ ṛte 'pi tvāṁ na bhaviṣyanti sarve ye 'vasthitāḥ pratyanīkeṣu yodhāḥ",
}

# HK versions of the same for corpus matching
BG_KEY_VERSES_HK = {
    "2.47": "karmaNy evAdhikAras te mA phaleshu kadAcana mA karmaphalaheturbhUr mA te saMgo stvakarmaRAi",
    "2.20": "na jAyate mriyate vA kadAcin nAyaM bhUtvA bhavitA vA na bhUyaH ajo nityaH zAzvato yaM purANo na hanyate hanyamAne zarIre",
    "6.29": "sarvabhUtastham AtmAnaM sarvabhUtAni cAtmani Ikzate yogayuktAtmA sarvatra samadarzanaH",
    "13.27": "samaM sarveshu bhUteshu tiShThantaM paramezvaram vinazyatsvA vinazyantaM yaH pazyati sa pazyati",
    "18.66": "sarvAdharmAn parityajya mAm ekaM zaraNaM vraja ahaM tvAM sarvapApebhyo mokzayiShyAmi mA zucaH",
}


def load_corpus_verses(corpus_dir, max_verses=None):
    """Load corpus into list of (verse_id, text) tuples."""
    corpus_path = Path(corpus_dir)
    verses = []
    
    for filepath in sorted(corpus_path.iterdir()):
        if not filepath.is_file():
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.rstrip()
                    m = re.match(r'^(\d{8}[abcd]?)\s+(.*)', line)
                    if m:
                        verse_id = m.group(1)
                        text = m.group(2).strip()
                        if text:
                            verses.append((verse_id, text))
                            if max_verses and len(verses) >= max_verses:
                                return verses
        except Exception as e:
            print(f"Error: {filepath}: {e}")
    
    return verses


def build_embeddings(corpus_dir, output_dir, model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    """
    Build and save embeddings for entire corpus.
    
    Uses multilingual MiniLM — handles transliterated Sanskrit reasonably well.
    For better Sanskrit support, consider: ai4bharat/indic-bert or
    arvindrajan92/indic-sentence-bert-nli
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: sentence-transformers not installed.")
        print("Run: pip install sentence-transformers")
        return
    
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    print("Loading corpus...")
    verses = load_corpus_verses(corpus_dir)
    print(f"Loaded {len(verses)} verses")
    
    verse_ids = [v[0] for v in verses]
    texts = [v[1] for v in verses]
    
    print("Building embeddings (this will take 30-60 minutes for full corpus)...")
    print("Consider running overnight. Progress will be shown.")
    
    # Batch encode with progress
    batch_size = 256
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embs = model.encode(batch, show_progress_bar=False)
        all_embeddings.append(embs)
        if i % 5000 == 0:
            print(f"  Encoded {i}/{len(texts)} verses...")
    
    embeddings = np.vstack(all_embeddings)
    
    # Save
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    np.save(output_dir / "embeddings.npy", embeddings)
    
    with open(output_dir / "verse_ids.json", "w") as f:
        json.dump(verse_ids, f)
    
    print(f"Embeddings saved: {embeddings.shape} at {output_dir}")
    print("Now run with --mode search or --mode sweep")


def search_similar(query_text, output_dir, top_k=50, exclude_parva=None,
                   model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
    """Find verses most semantically similar to query text."""
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("ERROR: pip install sentence-transformers")
        return []
    
    output_dir = Path(output_dir)
    emb_path = output_dir / "embeddings.npy"
    ids_path = output_dir / "verse_ids.json"
    
    if not emb_path.exists():
        print("ERROR: Embeddings not found. Run --mode build first.")
        return []
    
    print("Loading embeddings...")
    embeddings = np.load(emb_path)
    with open(ids_path) as f:
        verse_ids = json.load(f)
    
    print(f"Loading model: {model_name}")
    model = SentenceTransformer(model_name)
    
    query_emb = model.encode([query_text])
    
    # Cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1
    normalized = embeddings / norms
    query_norm = query_emb / np.linalg.norm(query_emb)
    
    similarities = (normalized @ query_norm.T).flatten()
    
    # Get top-k
    top_indices = np.argsort(similarities)[::-1][:top_k * 3]  # get extra to filter
    
    results = []
    for idx in top_indices:
        vid = verse_ids[idx]
        parva = vid[0:2]
        
        if exclude_parva and parva in exclude_parva:
            continue
        
        results.append({
            "verse_id": vid,
            "parva": parva,
            "similarity": float(similarities[idx]),
        })
        
        if len(results) >= top_k:
            break
    
    return results


def sweep_bg_nodes(output_dir, top_k=20):
    """Search for semantic echoes of each BG key verse."""
    output_dir = Path(output_dir)
    all_semantic_echoes = []
    
    print("Sweeping BG key verses for semantic echoes across MBH...")
    
    for bg_ref, text in BG_KEY_VERSES.items():
        print(f"\n  BG {bg_ref}:")
        print(f"  '{text[:80]}...'")
        
        # Exclude Bhishmaparva (parva 06) where BG itself lives
        results = search_similar(text, output_dir, top_k=top_k, exclude_parva={"06"})
        
        for r in results:
            r["bg_verse"] = bg_ref
            r["bg_text"] = text[:100]
            all_semantic_echoes.append(r)
        
        print(f"  → {len(results)} semantic echoes found")
    
    # Save
    import csv
    with open(output_dir / "semantic_echoes.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["bg_verse", "verse_id", "parva", "similarity", "bg_text"])
        writer.writeheader()
        writer.writerows(all_semantic_echoes)
    
    print(f"\nSaved {len(all_semantic_echoes)} semantic echoes to {output_dir / 'semantic_echoes.csv'}")
    return all_semantic_echoes


def main():
    parser = argparse.ArgumentParser(description="MBH Semantic Search")
    parser.add_argument("--corpus", help="Path to corpus (needed for --mode build)")
    parser.add_argument("--output", default="../output/", help="Output directory")
    parser.add_argument("--mode", choices=["build", "search", "query", "sweep"], required=True)
    parser.add_argument("--bg-verse", default="2.47", help="BG verse ref for --mode search")
    parser.add_argument("--text", default=None, help="Query text for --mode query")
    parser.add_argument("--top-k", type=int, default=30)
    parser.add_argument("--model", default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                        help="Embedding model. For better Sanskrit: ai4bharat/indic-bert")
    
    args = parser.parse_args()
    
    if args.mode == "build":
        if not args.corpus:
            print("ERROR: --corpus required for --mode build")
            return
        build_embeddings(args.corpus, args.output, args.model)
    
    elif args.mode == "search":
        text = BG_KEY_VERSES.get(args.bg_verse)
        if not text:
            print(f"BG verse {args.bg_verse} not in key verse list. Use --mode query with --text instead.")
            return
        results = search_similar(text, args.output, args.top_k, exclude_parva={"06"})
        print(f"\nTop {len(results)} echoes of BG {args.bg_verse}:")
        for r in results[:20]:
            print(f"  [{r['verse_id']}] P{r['parva']}  sim={r['similarity']:.3f}")
    
    elif args.mode == "query":
        if not args.text:
            print("ERROR: --text required for --mode query")
            return
        results = search_similar(args.text, args.output, args.top_k)
        print(f"\nTop results for: '{args.text}'")
        for r in results[:20]:
            print(f"  [{r['verse_id']}] P{r['parva']}  sim={r['similarity']:.3f}")
    
    elif args.mode == "sweep":
        sweep_bg_nodes(args.output, args.top_k)


if __name__ == "__main__":
    main()
