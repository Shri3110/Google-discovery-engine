import os
import json
import time
import logging
from datetime import datetime
from abc import ABC, abstractmethod

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class BaseCollector(ABC):
    """
    Base class for all source collectors.
    Handles rate limiting, backoffs, and saving normalized data to the Landing Zone.
    """
    
    def __init__(self, source_name: str, base_delay: float = 1.0):
        self.source_name = source_name
        self.base_delay = base_delay
        self.logger = logging.getLogger(self.source_name)
        
        # Ensure landing zone exists for this source
        self.landing_zone = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "landing_zone",
            self.source_name
        )
        os.makedirs(self.landing_zone, exist_ok=True)
        
    def respect_rate_limit(self):
        """Implement basic rate limiting / politeness delay"""
        time.sleep(self.base_delay)
        
    def save_batch(self, records: list):
        """
        Saves a batch of normalized records to the Landing Zone.
        Normalized Schema: {id, source, text, timestamp, rating, thread_context, url}
        """
        if not records:
            self.logger.info("No records to save in this batch.")
            return
            
        # Partition by date as requested in Phase 1
        date_str = datetime.now().strftime("%Y-%m-%d")
        partition_dir = os.path.join(self.landing_zone, date_str)
        os.makedirs(partition_dir, exist_ok=True)
        
        batch_id = int(time.time() * 1000)
        filename = f"batch_{batch_id}.json"
        filepath = os.path.join(partition_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
            
        self.logger.info(f"Saved {len(records)} records to {partition_dir}/{filename}")

    @abstractmethod
    def run(self):
        """
        Main execution method. Must be implemented by specific collectors.
        Should fetch data, normalize it, and call self.save_batch(records)
        """
        pass
