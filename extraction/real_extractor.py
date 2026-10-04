import json
import os
import time
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_genuine_sample():
    # Phase 1: 25 deterministic records
    with open('processed_zone/filtered_candidates.json', 'r', encoding='utf-8') as f:
        records = json.load(f)[:25]
        
    extracted_records = []
    
    system_prompt = """You are an expert product researcher. Extract structured data from the user feedback.
IMPORTANT: Only extract information that is EXPLICITLY SUPPORTED by the text.
If a field cannot be established from the text, return null (for strings/booleans) or [] (for arrays).
DO NOT INFER missing information. 
DO NOT guess failure stages or memory cues if they are not explicitly mentioned.

Output valid JSON matching this schema:
{
  "is_retrieval_failure": boolean,
  "memory_cues_present": [string],
  "memory_cues_missing": [string],
  "search_behavior": string,
  "failure_stage": string,
  "workaround_used": string,
  "emotional_intensity": integer (1-5),
  "outcome": string,
  "photo_type": string,
  "verbatim_quote": string (exact substring of the original text containing the evidence)
}"""

    for i, r in enumerate(records):
        print(f"Extracting record {i+1}/25: {r['id']}")
        original_text = r['text']
        
        user_prompt = f"User Feedback:\n\"{original_text}\""
        
        try:
            # We use openai/gpt-oss-20b for fast extraction
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="openai/gpt-oss-20b",
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            raw_response = response.choices[0].message.content
            parsed = json.loads(raw_response)
        except Exception as e:
            print(f"Error extracting {r['id']}: {e}")
            raw_response = str(e)
            parsed = {}
            
        extracted_records.append({
            "record_id": r["id"],
            "source": r["source"],
            "original_text": original_text,
            "verbatim_quote": parsed.get("verbatim_quote"),
            "is_retrieval_failure": parsed.get("is_retrieval_failure"),
            "memory_cues_present": parsed.get("memory_cues_present", []),
            "memory_cues_missing": parsed.get("memory_cues_missing", []),
            "search_behavior": parsed.get("search_behavior"),
            "failure_stage": parsed.get("failure_stage"),
            "workaround_used": parsed.get("workaround_used"),
            "emotional_intensity": parsed.get("emotional_intensity"),
            "outcome": parsed.get("outcome"),
            "photo_type": parsed.get("photo_type"),
            
            # Audit metadata
            "model_name": "openai/gpt-oss-20b",
            "extraction_timestamp": datetime.utcnow().isoformat() + "Z",
            "raw_model_response": raw_response,
            "parsed_extraction": parsed
        })
        
        # Sleep to respect rate limits if needed (optional but safe)
        time.sleep(1)
        
    out_path = os.path.join("extracted_zone", "genuine_validation_set.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(extracted_records, f, indent=2)
    print(f"Saved {len(extracted_records)} genuine extractions to {out_path}")

if __name__ == '__main__':
    extract_genuine_sample()
