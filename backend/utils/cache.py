"""
Simple in-memory cache for API responses
"""
import time
from typing import Dict, Any, Optional
import hashlib

class SimpleCache:
    """Simple in-memory cache with TTL"""
    
    def __init__(self, ttl_seconds: int = 300):  # 5 minutes default
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl_seconds
    
    def _get_key(self, data: Dict) -> str:
        """Create cache key from data"""
        json_str = str(sorted(data.items()))
        return hashlib.md5(json_str.encode()).hexdigest()
    
    def get(self, data: Dict) -> Optional[Any]:
        """Get cached result if exists and not expired"""
        key = self._get_key(data)
        
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached["timestamp"] < self.ttl:
                return cached["data"]
            else:
                # Expired
                del self.cache[key]
        
        return None
    
    def set(self, data: Dict, result: Any):
        """Cache a result"""
        key = self._get_key(data)
        self.cache[key] = {
            "data": result,
            "timestamp": time.time()
        }
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()

# Global cache instance
generation_cache = SimpleCache(ttl_seconds=600)  # 10 minutes for generations