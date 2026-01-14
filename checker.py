"""Core checker orchestrator with concurrent checking and result tracking."""

import asyncio
from typing import List, Dict, Optional
from datetime import datetime
import config
from browser_checker import BrowserChecker


class ContentChecker:
    """Orchestrates content checking with result tracking."""
    
    def __init__(self, timeout: int = None, max_concurrent: int = 3):
        """
        Initialize the content checker.
        
        Args:
            timeout: Timeout per check in seconds
            max_concurrent: Maximum concurrent checks (default: 3 for balance)
        """
        self.timeout = timeout or config.DEFAULT_TIMEOUT
        self.max_concurrent = max_concurrent
        self.results: List[Dict] = []
    
    async def check_single_item(self, content_item: Dict, retry_count: int = 0) -> Dict:
        """Check a single content item with retry logic."""
        name = content_item.get("name", "Unknown")
        content_type = content_item.get("type", "unknown")
        
        try:
            async with BrowserChecker(timeout=self.timeout) as checker:
                result = await checker.check_content(content_item)
                return result
        except Exception as e:
            # Retry logic
            if retry_count < config.MAX_RETRIES:
                print(f"  Retrying {name} ({content_type})...")
                await asyncio.sleep(config.RETRY_DELAY)
                return await self.check_single_item(content_item, retry_count + 1)
            
            return {
                "name": name,
                "type": content_type,
                "url": content_item.get("url", ""),
                "status": "broken",
                "error_message": f"Exception during check: {str(e)}",
                "check_time": datetime.now().isoformat()
            }
    
    async def check_items_concurrent(self, content_items: List[Dict]) -> List[Dict]:
        """Check multiple items with controlled concurrency."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def check_with_semaphore(item: Dict) -> Dict:
            async with semaphore:
                return await self.check_single_item(item)
        
        tasks = [check_with_semaphore(item) for item in content_items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                item = content_items[i]
                processed_results.append({
                    "name": item.get("name", "Unknown"),
                    "type": item.get("type", "unknown"),
                    "url": item.get("url", ""),
                    "status": "broken",
                    "error_message": f"Exception: {str(result)}",
                    "check_time": datetime.now().isoformat()
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def check_all(self, content_items: List[Dict]) -> List[Dict]:
        """
        Check all content items.
        
        Args:
            content_items: List of content items to check
            
        Returns:
            List of check results
        """
        total = len(content_items)
        print(f"\nChecking {total} items...")
        print(f"Using {self.max_concurrent} concurrent checks\n")
        
        # Group by type for better progress tracking
        by_type = {}
        for item in content_items:
            item_type = item.get("type", "unknown")
            if item_type not in by_type:
                by_type[item_type] = []
            by_type[item_type].append(item)
        
        all_results = []
        
        # Check each type
        for item_type, items in by_type.items():
            print(f"Checking {len(items)} {item_type} items...")
            
            for i, item in enumerate(items, 1):
                name = item.get("name", "Unknown")
                print(f"  [{i}/{len(items)}] {name}...", end=" ", flush=True)
                
                result = await self.check_single_item(item)
                all_results.append(result)
                
                status = result.get("status", "unknown")
                if status == "working":
                    print("✓ Working")
                else:
                    error = result.get("error_message", "Unknown error")
                    print(f"✗ {status}: {error}")
        
        self.results = all_results
        return all_results
    
    def get_results_by_type(self) -> Dict[str, List[Dict]]:
        """Group results by content type."""
        by_type = {}
        for result in self.results:
            result_type = result.get("type", "unknown")
            if result_type not in by_type:
                by_type[result_type] = []
            by_type[result_type].append(result)
        return by_type
    
    def get_summary(self) -> Dict:
        """Get summary statistics."""
        total = len(self.results)
        working = sum(1 for r in self.results if r.get("status") == "working")
        broken = sum(1 for r in self.results if r.get("status") == "broken")
        
        by_type = {}
        for result in self.results:
            result_type = result.get("type", "unknown")
            if result_type not in by_type:
                by_type[result_type] = {"total": 0, "working": 0, "broken": 0}
            by_type[result_type]["total"] += 1
            if result.get("status") == "working":
                by_type[result_type]["working"] += 1
            else:
                by_type[result_type]["broken"] += 1
        
        return {
            "total": total,
            "working": working,
            "broken": broken,
            "by_type": by_type,
            "check_time": datetime.now().isoformat()
        }
