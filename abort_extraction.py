import os
import json

base_dir = r"c:\Google discovery engine"
input_file = os.path.join(base_dir, "processed_zone", "filtered_candidates.json")
output_file = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
failed_file = os.path.join(base_dir, "extracted_zone", "failed_records.json")

with open(input_file, 'r', encoding='utf-8') as f:
    records = json.load(f)
    
extracted = {}
if os.path.exists(output_file):
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for d in data:
            extracted[d["record_id"]] = d

failed = {}
if os.path.exists(failed_file):
    with open(failed_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for d in data:
            failed[d["record_id"]] = d

pending_records = [r for r in records if r["id"] not in extracted and r["id"] not in failed]

for r in pending_records:
    failed[r["id"]] = {
        "record_id": r["id"],
        "error": "Pipeline Timeout due to Groq 8000 TPM limit"
    }

with open(failed_file, 'w', encoding='utf-8') as f:
    json.dump(list(failed.values()), f, indent=2)

print(f"Aborted {len(pending_records)} pending records.")
