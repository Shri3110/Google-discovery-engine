import json
import os
from groq import Groq
from storage.vector_store import VectorStoreManager
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - SYNTHESIS - %(levelname)s - %(message)s')

def run_synthesis():
    base_dir = r"c:\Google discovery engine"
    extracted_path = os.path.join(base_dir, "extracted_zone", "full_corpus_extracted.json")
    
    if not os.path.exists(extracted_path):
        logging.error("Extracted records not found.")
        return

    # Phase 7: Build the full research store
    store = VectorStoreManager(collection_name="full_corpus_v1")
    store.index_extracted_records(extracted_path)
    
    client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))
    
    questions = [
        "Q1. What are the main ways users fail to retrieve photos in Google Photos?",
        "Q2. What information do users remember when they cannot find a photo?",
        "Q3. Which memory cues appear most frequently in failed retrieval incidents?",
        "Q4. Which memory cues are frequently missing or difficult for users to express?",
        "Q5. What search behaviors do users attempt before giving up?",
        "Q6. At which retrieval stages do users struggle most?",
        "Q7. What workarounds do users use after search fails?",
        "Q8. What kinds of photos/content are disproportionately associated with retrieval problems?",
        "Q9. Which retrieval problems recur across multiple independent users?",
        "Q10. What unmet retrieval needs are directly supported by the evidence?"
    ]
    
    # We will also load all records for full corpus metrics and direct counts
    with open(extracted_path, 'r', encoding='utf-8') as f:
        all_records = json.load(f)
        
    print("=== PHASE 10: FIRST RESEARCH ANALYSIS ===")
    
    for q in questions:
        # Hybrid retrieval: Semantic search for candidates
        # To get more candidate evidence, we retrieve 50 records. 
        # Then we'll let the prompt do the "Evidence gating".
        res = store.search(q, n_results=50)
        
        docs = res.get('documents', [[]])[0]
        metas = res.get('metadatas', [[]])[0]
        
        records_payload = []
        for meta in metas:
            meta_dict = meta if isinstance(meta, dict) else json.loads(meta)
            # Filter out non-failures or empty records if needed, but we keep all for gating
            records_payload.append({
                "record_id": meta_dict.get("id"),
                "source": meta_dict.get("source"),
                "photo_type": meta_dict.get("photo_type"),
                "memory_cues_present": meta_dict.get("memory_cues_present", "[]"),
                "memory_cues_missing": meta_dict.get("memory_cues_missing", "[]"),
                "failure_stage": meta_dict.get("failure_stage"),
                "outcome": meta_dict.get("outcome"),
                "workaround_used": meta_dict.get("workaround_used"),
                "verbatim_quote": meta_dict.get("verbatim_quote")
            })
            
        # Optional: Direct filter mapping
        # E.g. for Q3, we can look at all records with memory_cues_present
        # but let's just pass the 50 semantic hits and let the LLM synthesize it carefully.

        evidence_context = json.dumps(records_payload, indent=2)

        prompt = f"""Research question:
{q}

Candidate Evidence (Top 50 hits):
{evidence_context}

Return concise Markdown with:
1. Research interpretation
2. Direct evidence count (from these 50 candidates)
3. Indirect evidence count (from these 50 candidates)
4. Evidence coverage
5. Main findings (do not use "most users", use specific counts from the evidence)
6. Record IDs (cite them)
7. Representative verbatim quotes
8. Evidence gaps
9. Confidence / strength of evidence
"""
        
        system_msg = """You are a product research analyst analyzing real Google Photos user evidence.

Rules:
1. Answer ONLY from the evidence provided below.
2. Do not use outside knowledge or invent statistics.
3. For counts, actually count the records in the Candidate Evidence provided that support your claim.
4. Follow STRICT LANGUAGE DISCIPLINE: Do not say "users usually..." or "most users...". Say "Among the analyzed records..." or "X of Y records...".
5. Evaluate Direct vs Indirect evidence:
   - Direct: explicitly states the behavior/failure.
   - Indirect: implies it or mentions it peripherally.
6. Clearly list Record IDs and verbatim quotes."""

        try:
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt}
                ],
                model="openai/gpt-oss-120b",
                temperature=0.0
            )
            print(f"\n==================================================")
            print(f"{q}")
            print(f"==================================================\n")
            print(response.choices[0].message.content)
            
        except Exception as e:
            print(f"Error for question {q}: {e}")

if __name__ == "__main__":
    run_synthesis()
