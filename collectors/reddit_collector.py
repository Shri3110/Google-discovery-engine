import os
import uuid
from datetime import datetime
from base_collector import BaseCollector

try:
    import praw
except ImportError:
    pass

class RedditCollector(BaseCollector):
    def __init__(self):
        super().__init__(source_name="reddit", base_delay=2.0)
        
        # Pulls auth from environment variables
        self.reddit = None
        try:
            self.reddit = praw.Reddit(
                client_id=os.environ.get("REDDIT_CLIENT_ID", "mock_id"),
                client_secret=os.environ.get("REDDIT_CLIENT_SECRET", "mock_secret"),
                user_agent="GooglePhotosDiscoveryEngine/1.0"
            )
        except Exception as e:
            self.logger.warning(f"Could not initialize PRAW: {e}")
            
    def run(self, subreddits=["googlephotos", "GooglePixel", "Android"], limit=100):
        if not self.reddit:
            self.logger.error("Reddit client not configured.")
            return
            
        self.logger.info(f"Starting Reddit scrape across {subreddits}...")
        
        query = "(search OR find OR remember OR missing OR lost) AND photo"
        
        normalized_records = []
        for sub in subreddits:
            try:
                subreddit = self.reddit.subreddit(sub)
                self.logger.info(f"Searching r/{sub}...")
                
                # We use search to pull relevant historical posts
                for submission in subreddit.search(query, sort="new", limit=limit):
                    text = f"{submission.title}\n{submission.selftext}"
                    
                    normalized_records.append({
                        "id": f"reddit_{submission.id}",
                        "source": "reddit",
                        "text": text.strip(),
                        "timestamp": datetime.fromtimestamp(submission.created_utc).isoformat(),
                        "rating": None,
                        "thread_context": "post",
                        "url": f"https://reddit.com{submission.permalink}"
                    })
                    
                    # We could optionally pull top-level comments as well here
                    
            except Exception as e:
                self.logger.error(f"Error scraping r/{sub}: {e}")
                
        self.save_batch(normalized_records)

if __name__ == "__main__":
    collector = RedditCollector()
    collector.run()
