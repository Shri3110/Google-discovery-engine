import os
import sys
import collections

sys.path.append(r"c:\Google discovery engine")
from preprocessing.pipeline import PreprocessingPipeline

p = PreprocessingPipeline()
raw = p.load_raw_data()
raw_counts = collections.Counter(r.get("source", "unknown") for r in raw)

deduped = p.dedup(raw)
dedup_counts = collections.Counter(r.get("source", "unknown") for r in deduped)

filtered = p.pre_filter(deduped)
filtered_counts = collections.Counter(r.get("source", "unknown") for r in filtered)

print("=== SOURCE DISTRIBUTION ===")
print(f"{'source':<20} | {'raw':<10} | {'deduplicated':<12} | {'eligible':<10} | {'eligibility_rate'}")
for src in sorted(list(raw_counts.keys())):
    r = raw_counts[src]
    d = dedup_counts.get(src, 0)
    e = filtered_counts.get(src, 0)
    rate = f"{(e/d)*100:.2f}%" if d > 0 else "0.00%"
    print(f"{src:<20} | {r:<10} | {d:<12} | {e:<10} | {rate}")

import random
excluded = [r for r in deduped if r not in filtered]
print("\n=== SAMPLE EXCLUDED ===")
for r in random.sample(excluded, min(5, len(excluded))):
    print(f"ID: {r.get('id')}, Source: {r.get('source')}, Rating: {r.get('rating')}")
    print(f"Text: {r.get('text')}")
    print(f"Reason: Rating > 3 (was {r.get('rating')})" if r.get('rating') and r.get('rating') > 3 else "Reason: Keyword mismatch")
    print("---")

