import json
import os

def main():
    base_dir = r"c:\Google discovery engine"
    filtered_path = os.path.join(base_dir, "processed_zone", "filtered_candidates.json")
    extracted_path = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
    failed_path = os.path.join(base_dir, "extracted_zone", "failed_records.json")
    
    with open(filtered_path, 'r', encoding='utf-8') as f:
        filtered_data = json.load(f)
        
    try:
        with open(extracted_path, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)
    except FileNotFoundError:
        extracted_data = []

    try:
        with open(failed_path, 'r', encoding='utf-8') as f:
            failed_data = json.load(f)
    except FileNotFoundError:
        failed_data = []
        
    total_eligible = len(filtered_data)
    total_extracted = len(extracted_data)
    total_failed = len(failed_data)
    total_pending = total_eligible - total_extracted - total_failed
    
    print("=== PHASE 4: EXTRACTION QUALITY AUDIT ===")
    print(f"Total eligible records: {total_eligible}")
    print(f"Genuine LLM extracted: {total_extracted}")
    print(f"Failed: {total_failed}")
    print(f"Pending: {total_pending}")
    
    if total_extracted == 0:
        return
        
    # Stats
    retrieval_failures = sum(1 for r in extracted_data if r.get('is_retrieval_failure') is True)
    memory_cue_records = sum(1 for r in extracted_data if r.get('memory_cues_present') or r.get('memory_cues_missing'))
    search_behavior_records = sum(1 for r in extracted_data if r.get('search_behavior'))
    failure_stage_records = sum(1 for r in extracted_data if r.get('failure_stage'))
    workaround_records = sum(1 for r in extracted_data if r.get('workaround_used'))
    photo_type_records = sum(1 for r in extracted_data if r.get('photo_type'))
    
    print(f"\nRetrieval-failure records: {retrieval_failures}")
    print(f"Memory-cue records: {memory_cue_records}")
    print(f"Search-behavior records: {search_behavior_records}")
    print(f"Failure-stage records: {failure_stage_records}")
    print(f"Workaround records: {workaround_records}")
    print(f"Photo-type records: {photo_type_records}")
    
    fields = [
        "is_retrieval_failure", "memory_cues_present", "memory_cues_missing",
        "search_behavior", "failure_stage", "workaround_used",
        "emotional_intensity", "outcome", "photo_type", "verbatim_quote"
    ]
    
    print("\nField population rates:")
    for field in fields:
        populated = sum(1 for r in extracted_data if r.get(field) is not None and r.get(field) != [] and r.get(field) != "")
        pct = (populated / total_extracted) * 100
        print(f"- {field}: {pct:.1f}% populated, {100-pct:.1f}% null/unknown")
        
    print("\n=== PHASE 5: DATA QUALITY CHECK ===")
    # Duplicates
    ids = [r.get('record_id') for r in extracted_data]
    unique_ids = set(ids)
    print(f"Duplicate record IDs: {len(ids) - len(unique_ids)}")
    
    # Missing IDs
    missing_ids = sum(1 for r in extracted_data if not r.get('record_id'))
    print(f"Missing record IDs: {missing_ids}")
    
    # Missing original text
    missing_text = sum(1 for r in extracted_data if not r.get('original_text'))
    print(f"Missing original text: {missing_text}")
    
    # Missing source
    missing_source = sum(1 for r in extracted_data if not r.get('source'))
    print(f"Records with no source: {missing_source}")
    
    # Fabricated quotes
    invalid_quotes = 0
    for r in extracted_data:
        quote = r.get('verbatim_quote')
        text = r.get('original_text')
        if quote and text:
            if quote not in text:
                invalid_quotes += 1
    print(f"Fabricated/non-verbatim quotes (quote not in original_text): {invalid_quotes}")
    
    # Heuristic records
    heuristic = sum(1 for r in extracted_data if r.get('model_name') not in ['openai/gpt-oss-20b', 'openai/gpt-oss-120b'])
    print(f"Heuristic/mock-generated records: {heuristic}")
    
    # Enums
    valid_photo_types = {"screenshot", "document_receipt", "candid_moment", "posed_person_group", "scenery_place", "food", "other"}
    invalid_enums = sum(1 for r in extracted_data if r.get('photo_type') and r.get('photo_type') not in valid_photo_types)
    print(f"Impossible enum values (photo_type): {invalid_enums}")
    
if __name__ == "__main__":
    main()
