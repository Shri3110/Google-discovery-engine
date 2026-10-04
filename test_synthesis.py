import os
import json
import chromadb
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def test_direct_synthesis():
    # 1. Fetch from Vector Store
    db_path = os.path.join(os.getcwd(), "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection(name="retrieval_failures")
    
    query = "Why do users fail to find screenshots?"
    results = collection.query(
        query_texts=[query],
        n_results=8
    )
    
    # Extract records
    evidence_records = []
    if results['metadatas'] and len(results['metadatas'][0]) > 0:
        for meta in results['metadatas'][0]:
            # Filter fields
            record = {
                "record_id": meta.get("id"),
                "source": meta.get("source"),
                "photo_type": meta.get("photo_type"),
                "memory_cues_present": json.loads(meta.get("memory_cues_present", "[]")),
                "memory_cues_missing": json.loads(meta.get("memory_cues_missing", "[]")),
                "search_behavior": meta.get("search_behavior"),
                "failure_stage": meta.get("failure_stage"),
                "outcome": meta.get("outcome"),
                "verbatim_quote": meta.get("verbatim_quote")
            }
            evidence_records.append(record)
            
    print(f"EVIDENCE RECORD COUNT: {len(evidence_records)}\n")
    for i, e in enumerate(evidence_records):
        print(f"RECORD {i+1}:\n{json.dumps(e, indent=2)}\n")
        
    # 2. Build Prompt
    system_prompt = """You are a product research analyst analyzing real Google Photos user evidence.

Answer ONLY from the evidence provided below.

Do not use outside knowledge.
Do not invent user complaints.
Do not invent quotes.
Do not invent statistics.

For each finding:
- explain what the evidence shows
- distinguish what users remember from what they forget
- identify the retrieval failure if supported
- cite the record IDs

If the evidence does not support a conclusion, explicitly say so."""

    user_prompt = f"""Research question:
{query}

Evidence:
{json.dumps(evidence_records, indent=2)}

Return concise Markdown with:

## Key Finding
## What Users Remember
## What They Forget
## Retrieval Failure
## Supporting Evidence
## Evidence Gaps"""

    token_estimate = len(system_prompt.split()) + len(user_prompt.split()) * 1.5
    print(f"INPUT TOKEN ESTIMATE: ~{int(token_estimate)}")
    print("MODEL: openai/gpt-oss-20b\n")
    
    # 3. Call LLM
    try:
        groq_client = Groq(api_key=os.environ.get('GROQ_API_KEY'))
        res = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="openai/gpt-oss-20b",
            temperature=0.0
        )
        print("RAW MODEL RESPONSE:\n")
        print(res.choices[0].message.content)
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    test_direct_synthesis()
