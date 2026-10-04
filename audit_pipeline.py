import json
import os
import random
from collections import Counter

base_dir = r"c:\Google discovery engine"
zones = {
    "raw": os.path.join(base_dir, "landing_zone"),
    "preprocessed": os.path.join(base_dir, "processed_zone", "processed_records.json"),
    "deduplicated": os.path.join(base_dir, "processed_zone", "deduped_records.json"),
    "eligible": os.path.join(base_dir, "processed_zone", "filtered_candidates.json")
}

def get_raw_counts():
    counts = Counter()
    if os.path.exists(zones["raw"]):
        for root, dirs, files in os.walk(zones["raw"]):
            for fname in files:
                if fname.endswith(".json"):
                    # root is something like c:\Google discovery engine\landing_zone\play_store\2026-09-24
                    parts = os.path.relpath(root, zones["raw"]).split(os.sep)
                    source = parts[0] if parts else "unknown"
                    try:
                        with open(os.path.join(root, fname), "r", encoding="utf-8") as f:
                            data = json.load(f)
                            counts[source] += len(data)
                    except Exception as e:
                        print(f"Error loading {fname}: {e}")
    return counts

def get_json_counts(filepath):
    counts = Counter()
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                for r in data:
                    counts[r.get("source", "unknown")] += 1
        except:
            pass
    return counts

def sample_excluded():
    # Read deduped and eligible to find excluded
    deduped = {}
    if os.path.exists(zones["deduplicated"]):
        with open(zones["deduplicated"], "r", encoding="utf-8") as f:
            for r in json.load(f):
                deduped[r["id"]] = r
                
    eligible_ids = set()
    if os.path.exists(zones["eligible"]):
        with open(zones["eligible"], "r", encoding="utf-8") as f:
            for r in json.load(f):
                eligible_ids.add(r["id"])
                
    excluded = [r for rid, r in deduped.items() if rid not in eligible_ids]
    
    if not excluded:
        return []
        
    return random.sample(excluded, min(5, len(excluded)))

if __name__ == "__main__":
    raw_counts = get_raw_counts()
    prep_counts = get_json_counts(zones["preprocessed"])
    dedup_counts = get_json_counts(zones["deduplicated"])
    elig_counts = get_json_counts(zones["eligible"])
    
    print("=== SOURCE DISTRIBUTION ===")
    all_sources = set(raw_counts.keys()) | set(prep_counts.keys()) | set(dedup_counts.keys()) | set(elig_counts.keys())
    
    # Normalize source names
    # Sometimes raw files are named "play_store_..." and "help_community_..."
    # The JSON files use "play_store", "help_community", "reddit", etc.
    
    # Let's just print the raw mappings directly
    print(f"{'source':<20} | {'raw':<10} | {'preprocessed':<12} | {'deduplicated':<12} | {'eligible':<10} | {'eligibility_rate'}")
    
    # We will compute based on the keys in dedup_counts to unify
    unified_sources = set(prep_counts.keys())
    for src in unified_sources:
        r = raw_counts.get(src, 0)
        p = prep_counts.get(src, 0)
        d = dedup_counts.get(src, 0)
        e = elig_counts.get(src, 0)
        rate = f"{(e/d)*100:.2f}%" if d > 0 else "0.00%"
        print(f"{src:<20} | {r:<10} | {p:<12} | {d:<12} | {e:<10} | {rate}")
        
    # Also print any raw sources that didn't make it to preprocessed
    for src in set(raw_counts.keys()) - unified_sources:
        r = raw_counts.get(src, 0)
        print(f"{src:<20} | {r:<10} | {0:<12} | {0:<12} | {0:<10} | 0.00%")
        
    print("\n=== SAMPLE EXCLUDED ===")
    samples = sample_excluded()
    for s in samples:
        print(f"ID: {s['id']}, Source: {s['source']}")
        print(f"Text: {s['text'][:100]}...")
