import json
import os
from groq import Groq
from storage.vector_store import VectorStoreManager
from dotenv import load_dotenv

load_dotenv()

def smoke_test():
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    key = os.environ.get("GROQ_API_KEY")
    
    print("=== SYNTHESIS SMOKE TEST DIAGNOSTICS ===")
    print(f"Key present: {'yes' if key else 'no'}")
    print(f"Key prefix: {key[:4] if key else 'none'}")
    print("Configured model: openai/gpt-oss-120b")
    print("Endpoint host: api.groq.com (implied by python SDK)")
    
    base_dir = r"c:\Google discovery engine"
    extracted_path = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
    
    with open(extracted_path, 'r', encoding='utf-8') as f:
        records = json.load(f)[:3] # Just 3 records
        
    records_payload = []
    for meta_dict in records:
        records_payload.append({
            "record_id": meta_dict.get("record_id"),
            "source": meta_dict.get("source"),
            "photo_type": meta_dict.get("photo_type"),
            "memory_cues_present": meta_dict.get("memory_cues_present", []),
            "memory_cues_missing": meta_dict.get("memory_cues_missing", []),
            "search_behavior": meta_dict.get("search_behavior"),
            "failure_stage": meta_dict.get("failure_stage"),
            "outcome": meta_dict.get("outcome"),
            "workaround_used": meta_dict.get("workaround_used"),
            "verbatim_quote": meta_dict.get("verbatim_quote")
        })

    evidence_context = json.dumps(records_payload, indent=2)

    prompt = f"""Research question:
What information do users remember when they cannot find a photo?

Candidate Evidence:
{evidence_context}

Return concise Markdown with:
1. Research interpretation
2. Direct evidence count (from candidates)
3. Indirect evidence count (from candidates)
4. Evidence coverage
5. Main findings
6. Record IDs
7. Representative verbatim quotes
8. Evidence gaps
9. Confidence / strength of evidence
"""
    
    system_msg = "You are a product research analyst analyzing real Google Photos user evidence.\n\nRules:\n1. Answer ONLY from the evidence provided below.\n2. Do not use outside knowledge or invent statistics.\n3. Follow STRICT LANGUAGE DISCIPLINE: Do not say 'users usually'. Say 'Among the analyzed records...'\n4. Clearly list Record IDs and verbatim quotes."

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ],
            model="openai/gpt-oss-120b",
            temperature=0.0
        )
        print("HTTP status: 200 OK")
        print("\n=== SMOKE TEST OUTPUT ===\n")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"Failed with exception: {e}")

if __name__ == "__main__":
    smoke_test()
