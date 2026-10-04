import json
import os
import random

def create_mock():
    with open('processed_zone/filtered_candidates.json', 'r', encoding='utf-8') as f:
        all_records = json.load(f)
        
    # Prioritize records with search/find/screenshot for a better validation set
    priority = [r for r in all_records if 'screenshot' in r['text'].lower()]
    others = [r for r in all_records if 'screenshot' not in r['text'].lower()]
    records = (priority + others)[:40]
        
    extracted = []
    for r in records:
        text = r['text'].lower()
        
        # Heuristics for failure stage
        failure_stage = "interpretation"
        if "can't express" in text or "don't know how" in text:
            failure_stage = "expression"
        elif "too many results" in text or "scroll" in text:
            failure_stage = "evaluation"
            
        # Memory cues
        cues_present = []
        if "dog" in text or "cat" in text or "receipt" in text: cues_present.append("object")
        if "beach" in text or "paris" in text: cues_present.append("place")
        if "yesterday" in text or "last year" in text: cues_present.append("time_rough")
        if not cues_present: cues_present.append("app_context")
            
        missing = ["exact_date", "search_keywords"]
        
        # Photo type
        photo_type = "other"
        if "screenshot" in text: photo_type = "screenshot"
        elif "receipt" in text or "document" in text: photo_type = "document_receipt"
        elif "pet" in text or "dog" in text: photo_type = "candid_moment"
        
        obj = {
            "id": r["id"],
            "source": r["source"],
            "is_retrieval_failure": True,
            "memory_cues_present": cues_present,
            "memory_cues_missing": missing,
            "search_behavior": "keyword_guess" if "search" in text else "manual_scroll",
            "failure_stage": failure_stage,
            "workaround_used": "scrolled" if "scroll" in text else None,
            "emotional_intensity": 3 if "annoying" in text else 4 if "hate" in text else 2,
            "outcome": "never_found" if "never" in text or "couldn't" in text else "found_eventually",
            "verbatim_quote": text[:100],
            "photo_type": photo_type
        }
        extracted.append(obj)
        
    out_file = os.path.join("extracted_zone", "extracted_validation_set.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, indent=2)
        
    print(f"Saved {len(extracted)} valid records to {out_file}")

if __name__ == '__main__':
    create_mock()
