import uuid
from datetime import datetime
from base_collector import BaseCollector
try:
    from app_store_scraper import AppStore
except ImportError:
    pass

class AppStoreCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="app_store", base_delay=3.0)
        self.app_name = "google-photos"
        self.app_id = 962194608
        
    def run(self, count=1000):
        self.logger.info(f"Starting App Store scrape for {self.app_name}...")
        try:
            scraper = AppStore(country="us", app_name=self.app_name, app_id=self.app_id)
            scraper.review(how_many=count)
        except Exception as e:
            self.logger.error(f"Failed to scrape: {e}")
            return
            
        normalized_records = []
        for r in scraper.reviews:
            text = r.get("review", "").lower()
            rating = r.get("rating", 5)
            
            if rating > 3:
                continue
                
            keywords = ["search", "find", "remember", "looking for", "missing", "lost"]
            if not any(kw in text for kw in keywords):
                continue
                
            normalized_records.append({
                "id": f"app_{uuid.uuid4().hex}",
                "source": "app_store",
                "text": r.get("review", ""),
                "timestamp": str(r.get("date", datetime.now())),
                "rating": rating,
                "thread_context": None,
                "url": None
            })
            
        self.save_batch(normalized_records)

if __name__ == "__main__":
    collector = AppStoreCollector()
    collector.run(count=1000)
