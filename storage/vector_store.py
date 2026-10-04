import os
import json
import logging
import chromadb
from chromadb.config import Settings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - STORAGE - %(levelname)s - %(message)s')

class VectorStoreManager:
    def __init__(self, collection_name="validation_genuine_v1"):
        self.base_dir = os.path.dirname(os.path.dirname(__file__))
        self.db_dir = os.path.join(self.base_dir, "chroma_db")
        os.makedirs(self.db_dir, exist_ok=True)
        
        # Initialize local vector database
        self.client = chromadb.PersistentClient(
            path=self.db_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection_name = collection_name
        
        # We use a fast, lightweight open encoder as per Phase 4.2
        self.encoder = None
        
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
    def _get_encoder(self):
        if not self.encoder:
            logging.info("Loading embedding model (all-MiniLM-L6-v2)...")
            self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        return self.encoder

    def index_extracted_records(self, json_filepath):
        """
        Reads structured records from Phase 3, embeds them, and stores them.
        """
        if not os.path.exists(json_filepath):
            logging.error(f"Cannot find extracted records at {json_filepath}")
            return
            
        with open(json_filepath, 'r', encoding='utf-8') as f:
            records = json.load(f)
            
        if not records:
            logging.warning("No records found to index.")
            return
            
        logging.info(f"Indexing {len(records)} records into Vector Store...")
        
        ids = []
        documents = []
        embeddings = []
        metadatas = []
        
        for r in records:
            record_id = r.get("record_id") or r.get("id")
            if not record_id:
                continue
                
            # Combine verbatim_quote + context for the embedding chunking strategy (Step 4.2)
            quote = r.get("verbatim_quote", "")
            failure_stage = r.get("failure_stage", "unknown")
            text_context = f"Failure Stage: {failure_stage}. User quote: {quote}"
            
            ids.append(record_id)
            documents.append(text_context)
            
            # Prepare metadata for structured filtering and frontend rendering
            # Chroma metadata must be primitive types (strings, ints, floats, bools)
            metadata = {
                "id": str(record_id),
                "source": str(r.get("source")),
                "is_retrieval_failure": bool(r.get("is_retrieval_failure")),
                "failure_stage": str(r.get("failure_stage")),
                "outcome": str(r.get("outcome")),
                "photo_type": str(r.get("photo_type")),
                "emotional_intensity": int(r.get("emotional_intensity") or 3),
                "search_behavior": str(r.get("search_behavior")),
                "workaround_used": str(r.get("workaround_used")),
                "verbatim_quote": str(r.get("verbatim_quote")),
                "memory_cues_present": json.dumps(r.get("memory_cues_present", [])),
                "memory_cues_missing": json.dumps(r.get("memory_cues_missing", []))
            }
            metadatas.append(metadata)
            
        # Generate embeddings
        encoder = self._get_encoder()
        logging.info("Generating vector embeddings...")
        vectors = encoder.encode(documents).tolist()
        
        # Upsert into ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=vectors,
            documents=documents,
            metadatas=metadatas
        )
        
        logging.info(f"Successfully indexed {len(ids)} records into local ChromaDB.")
        
    def search(self, query: str, n_results: int = 5, filter_stage: str = None):
        """
        Semantic search with optional structured filtering.
        """
        encoder = self._get_encoder()
        query_vector = encoder.encode([query]).tolist()
        
        where_clause = {}
        if filter_stage:
            where_clause = {"failure_stage": filter_stage}
            
        results = self.collection.query(
            query_embeddings=query_vector,
            n_results=n_results,
            where=where_clause if where_clause else None
        )
        
        return results

if __name__ == "__main__":
    store = VectorStoreManager(collection_name="validation_genuine_v1")
    extracted_path = os.path.join(store.base_dir, "extracted_zone", "genuine_validation_set.json")
    store.index_extracted_records(extracted_path)
