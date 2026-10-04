import os
import sys
import logging
from collections import defaultdict

# Setup path so we can import from storage
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from storage.vector_store import VectorStoreManager
from groq import Groq
from dotenv import load_dotenv

try:
    from sklearn.cluster import KMeans
    import numpy as np
except ImportError:
    pass

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - CLUSTERING - %(levelname)s - %(message)s')

class OpportunitySynthesizer:
    def __init__(self):
        self.store = VectorStoreManager()
        # Tier 2 Model for Synthesis - Heavier reasoning model
        self.tier2_model = "openai/gpt-oss-120b"
        self.client = Groq(api_key=os.environ.get("GROQ_API_KEY", "mock_key"))
        
    def get_records_by_stage(self):
        """Pulls all embedded records grouped by failure_stage."""
        # ChromaDB allows getting all records if you don't supply a query
        results = self.store.collection.get(include=["embeddings", "metadatas", "documents"])
        
        stages = defaultdict(list)
        if not results or not results['embeddings']:
            return stages
            
        for i, meta in enumerate(results['metadatas']):
            stage = meta.get("failure_stage", "unknown")
            stages[stage].append({
                "id": results['ids'][i],
                "embedding": results['embeddings'][i],
                "document": results['documents'][i],
                "metadata": meta
            })
            
        return stages

    def cluster_within_stage(self, stage_records, n_clusters=3):
        """Uses K-Means to cluster records by their semantic embeddings."""
        if len(stage_records) < n_clusters:
            n_clusters = max(1, len(stage_records))
            
        embeddings = np.array([r['embedding'] for r in stage_records])
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        labels = kmeans.fit_predict(embeddings)
        
        clusters = defaultdict(list)
        for i, label in enumerate(labels):
            clusters[label].append(stage_records[i])
            
        return clusters

    def score_cluster(self, cluster_records):
        """Scores a cluster based on Frequency and Severity (Step 5.3)"""
        frequency = len(cluster_records)
        
        # Severity = mean emotional_intensity + (never_found rate)
        total_emotion = sum(r['metadata'].get('emotional_intensity', 3) for r in cluster_records)
        never_found_count = sum(1 for r in cluster_records if r['metadata'].get('outcome') == 'never_found')
        
        mean_emotion = total_emotion / frequency if frequency > 0 else 3
        never_found_rate = never_found_count / frequency if frequency > 0 else 0
        
        # Simple weighted severity score (max roughly 6)
        severity = mean_emotion + (never_found_rate * 2)
        
        return {
            "frequency": frequency,
            "severity": round(severity, 2),
            "mean_emotion": round(mean_emotion, 2),
            "never_found_rate": round(never_found_rate, 2)
        }

    def synthesize_cluster_label(self, cluster_records):
        """Uses Tier 2 LLM to generate a human-readable name and description."""
        # We sample up to 5 documents to save context window and avoid repetition
        samples = [r['document'] for r in cluster_records[:5]]
        
        prompt = f"""
        You are a product manager analyzing user feedback for Google Photos.
        I will provide a cluster of similar user complaints regarding search/retrieval failures.
        
        Analyze these samples and provide a short, highly descriptive JSON output:
        {{
            "cluster_name": "A 3-5 word name (e.g. 'Object-anchored memory, no place/time')",
            "description": "A 1 sentence explanation of what is breaking for the user."
        }}
        
        Samples:
        {chr(10).join(samples)}
        """
        
        try:
            res = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.tier2_model,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return json.loads(res.choices[0].message.content)
        except Exception as e:
            logging.error(f"Synthesis failed: {e}")
            return {"cluster_name": "Unnamed Cluster", "description": "Synthesis failed."}

    def run(self):
        logging.info("Starting Clustering & Opportunity Synthesis...")
        stages = self.get_records_by_stage()
        
        if not stages:
            logging.warning("No records found in vector store to cluster.")
            return
            
        final_opportunities = []
        
        for stage_name, records in stages.items():
            logging.info(f"Clustering {len(records)} records in stage: {stage_name}")
            clusters = self.cluster_within_stage(records)
            
            for cluster_id, cluster_records in clusters.items():
                scores = self.score_cluster(cluster_records)
                labels = self.synthesize_cluster_label(cluster_records)
                
                opportunity = {
                    "stage": stage_name,
                    "cluster_name": labels.get("cluster_name"),
                    "description": labels.get("description"),
                    "scores": scores,
                    "sample_quotes": [r['document'] for r in cluster_records[:3]]
                }
                final_opportunities.append(opportunity)
                
        # Sort by Severity * Frequency
        final_opportunities.sort(key=lambda x: x['scores']['severity'] * x['scores']['frequency'], reverse=True)
        
        # Save output
        out_file = os.path.join(self.store.base_dir, "analysis", "opportunity_report.json")
        with open(out_file, 'w', encoding='utf-8') as f:
            json.dump(final_opportunities, f, indent=2)
            
        logging.info(f"Synthesis complete! Saved {len(final_opportunities)} opportunity clusters to {out_file}")

if __name__ == "__main__":
    synthesizer = OpportunitySynthesizer()
    synthesizer.run()
