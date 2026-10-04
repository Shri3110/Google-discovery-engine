import os
import json
import re

class PreprocessingPipeline:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.landing_zone = os.path.join(self.base_dir, "landing_zone")
        self.processed_zone = os.path.join(self.base_dir, "processed_zone")
        os.makedirs(self.processed_zone, exist_ok=True)
        
    def load_raw_data(self):
        records = []
        for source in os.listdir(self.landing_zone):
            source_dir = os.path.join(self.landing_zone, source)
            if not os.path.isdir(source_dir): continue
            
            for date_partition in os.listdir(source_dir):
                part_dir = os.path.join(source_dir, date_partition)
                if not os.path.isdir(part_dir): continue
                
                for filename in os.listdir(part_dir):
                    if not filename.endswith('.json'): continue
                    with open(os.path.join(part_dir, filename), 'r', encoding='utf-8') as f:
                        records.extend(json.load(f))
        return records
        
    def dedup(self, records):
        seen_texts = set()
        unique = []
        for r in records:
            raw_text = r.get("text")
            text = (raw_text or "").strip().lower()
            if not text or text in seen_texts:
                continue
            seen_texts.add(text)
            unique.append(r)
        return unique
        
    def pre_filter(self, records):
        """
        Cheap rules-based classifier to enforce cost control before LLM phase.
        We only want records that *might* contain a retrieval failure.
        """
        # Keywords indicating a search/retrieval attempt or memory
        keywords = re.compile(r'\b(search|find|remember|missing|lost|looking for|where is|disappeared|scroll)\b', re.IGNORECASE)
        
        filtered = []
        for r in records:
            raw_text = r.get("text")
            text = raw_text or ""
            rating = r.get("rating")
            
            # Keep negative/neutral reviews that mention target keywords
            if rating is not None and rating <= 3:
                if keywords.search(text):
                    filtered.append(r)
            # If no rating is present (e.g. Reddit), just check keywords
            elif keywords.search(text):
                filtered.append(r)
                
        return filtered

    def run(self):
        print("Starting preprocessing pipeline...")
        
        raw_records = self.load_raw_data()
        print(f"Loaded {len(raw_records)} raw records from Landing Zone.")
        
        deduped = self.dedup(raw_records)
        print(f"Removed {len(raw_records) - len(deduped)} duplicates. {len(deduped)} remaining.")
        
        filtered = self.pre_filter(deduped)
        print(f"Relevance pre-filter discarded {len(deduped) - len(filtered)} records.")
        print(f"FINAL PROCESSED VOLUME: {len(filtered)} records.")
        
        # Save to processed zone in a single batch (or multiple if huge)
        out_file = os.path.join(self.processed_zone, "filtered_candidates.json")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(filtered, f, indent=2, ensure_ascii=False)
            
        print(f"Saved to {out_file}")

if __name__ == "__main__":
    pipeline = PreprocessingPipeline()
    pipeline.run()
