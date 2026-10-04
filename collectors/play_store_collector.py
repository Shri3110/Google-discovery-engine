import uuid
import datetime
from base_collector import BaseCollector
try:
    from google_play_scraper import reviews, Sort
except ImportError:
    pass

class PlayStoreCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="play_store", base_delay=2.0)
        self.app_id = "com.google.android.apps.photos"
        
    def run(self, count=50000):
        # We are pulling a large volume of raw reviews here. 
        # API limits for scraping Play Store are usually IP-based. 
        self.logger.info(f"Starting Play Store scrape for {count} reviews (mindful of rate limits)...")
        try:
            # Paginating automatically via the library
            result, continuation_token = reviews(
                self.app_id,
                lang='en', 
                country='us',
                sort=Sort.NEWEST,
                count=count
            )
        except Exception as e:
            self.logger.error(f"Failed to scrape: {e}")
            return
            
        normalized_records = []
        for r in result:
            # Phase 1: Only normalize, DO NOT aggressively filter here. 
            # Filtering belongs in Phase 2 to avoid dropping data prematurely.
            text = r.get("content", "")
            rating = r.get("score", 5)
            
            normalized_records.append({
                "id": f"play_{r.get('reviewId', uuid.uuid4().hex)}",
                "source": "play_store",
                "text": text,
                "timestamp": r.get("at", datetime.datetime.now()).isoformat() if hasattr(r.get("at"), "isoformat") else str(r.get("at")),
                "rating": rating,
                "thread_context": None,
                "url": None
            })
            
        # We save in batches of 5000 to simulate batch processing
        batch_size = 5000
        for i in range(0, len(normalized_records), batch_size):
            self.save_batch(normalized_records[i:i+batch_size])

if __name__ == "__main__":
    collector = PlayStoreCollector()
    # Pulling enough to ensure we hit the 2000+ processed goal after Phase 2 filters
    collector.run(count=100000)
