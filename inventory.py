import json
import os
import glob

def main():
    base_dir = r"c:\Google discovery engine"
    
    # Raw records
    raw_files = glob.glob(os.path.join(base_dir, "landing_zone", "**", "*.json"), recursive=True)
    total_raw = 0
    source_counts = {}
    for f in raw_files:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                data = json.load(file)
                total_raw += len(data)
                source = os.path.basename(os.path.dirname(f))
                source_counts[source] = source_counts.get(source, 0) + len(data)
        except Exception as e:
            pass

    print(f"Total raw records: {total_raw}")
    print(f"Source distribution: {source_counts}")
    
    # Eligible records
    filtered_path = os.path.join(base_dir, "processed_zone", "filtered_candidates.json")
    if os.path.exists(filtered_path):
        with open(filtered_path, 'r', encoding='utf-8') as f:
            filtered_data = json.load(f)
            print(f"Records after relevance filtering (eligible for extraction): {len(filtered_data)}")
            
            # Duplicates
            ids = [r.get('id') for r in filtered_data]
            unique_ids = set(ids)
            print(f"Duplicate count in eligible: {len(ids) - len(unique_ids)}")
    else:
        print("No filtered_candidates.json found.")
        
    # Extracted status
    extracted_path = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
    if os.path.exists(extracted_path):
        with open(extracted_path, 'r', encoding='utf-8') as f:
            extracted_data = json.load(f)
            print(f"Already genuinely extracted records: {len(extracted_data)}")
    else:
        print("Already genuinely extracted records: 0")

if __name__ == '__main__':
    main()
