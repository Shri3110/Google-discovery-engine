import json
import os

def validate_and_fix(records):
    enums = {
        "photo_type": {"screenshot", "document_receipt", "candid_moment", "posed_person_group", "scenery_place", "food", "other"},
        "search_behavior": {"keyword_guess", "manual_scroll", "album_browse", "date_range_guess", "person_filter", "gave_up"},
        "failure_stage": {"expression", "interpretation", "evaluation", "recovery"},
        "outcome": {"found_eventually", "never_found", "unclear"}
    }
    
    valid_count = 0
    invalid_count = 0
    invalid_fields_count = {}
    
    for r in records:
        is_valid = True
        for field, allowed in enums.items():
            val = r.get(field)
            if val is not None and val not in allowed:
                # Issue detected
                r[field] = None
                r[f"{field}_validation_issue"] = True
                
                is_valid = False
                invalid_fields_count[field] = invalid_fields_count.get(field, 0) + 1
        
        if is_valid:
            valid_count += 1
        else:
            invalid_count += 1
            
    return valid_count, invalid_count, invalid_fields_count

if __name__ == "__main__":
    base_dir = r"c:\Google discovery engine"
    file_path = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        records = json.load(f)
        
    valid, invalid, fields_count = validate_and_fix(records)
    
    print("=== SCHEMA VALIDATION REPORT ===")
    print(f"Valid records: {valid}")
    print(f"Invalid records: {invalid}")
    print(f"Invalid fields: {fields_count}")
    print(f"Corrected records: {invalid}")
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2)
