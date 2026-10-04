import os
import sys
import logging
from play_store_collector import PlayStoreCollector
from reddit_collector import RedditCollector
from app_store_collector import AppStoreCollector
from help_community_collector import HelpCommunityCollector
from youtube_collector import YouTubeCollector

logging.basicConfig(level=logging.INFO, format='%(asctime)s - ORCHESTRATOR - %(levelname)s - %(message)s')

def run_all_collectors():
    """
    Simulates a daily/weekly Airflow DAG execution.
    Executes all source collectors independently. If one fails, the others continue.
    """
    logging.info("Starting ingestion orchestration...")
    
    collectors = [
        PlayStoreCollector(),
        AppStoreCollector(),
        HelpCommunityCollector(),
        RedditCollector(),
        YouTubeCollector()
    ]
    
    for collector in collectors:
        try:
            logging.info(f"Triggering {collector.source_name} collector...")
            collector.run()
        except Exception as e:
            logging.error(f"Collector {collector.source_name} failed: {e}")
            
    logging.info("Ingestion complete. Data is partitioned in the landing_zone.")

if __name__ == "__main__":
    # Ensure dependencies path is correct
    sys.path.append(os.path.dirname(__file__))
    run_all_collectors()
