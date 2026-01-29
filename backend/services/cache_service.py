"""
Client-Specific Cache Service
Redis-based caching with client isolation
"""

import os
import logging
import json
from typing import Optional, Any, Dict
import redis
from datetime import timedelta

logger = logging.getLogger(__name__)


class CacheService:
    """
    Client-specific cache service using Redis.
    
    All cache keys are prefixed with client_id to ensure isolation.
    """
    
    def __init__(self, client_id: str):
        """
        Initialize cache service for a specific client.
        
        Args:
            client_id: Client UUID as string
        """
        self.client_id = client_id
        self.redis_client = self._init_redis()
        self.key_prefix = f"client:{client_id}:"
    
    def _init_redis(self) -> redis.Redis:
        """Initialize Redis client"""
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        try:
            client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            client.ping()
            logger.debug(f"Redis connected for client: {self.client_id}")
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Cache will be disabled.")
            return None
    
    def _get_key(self, key: str) -> str:
        """Get full cache key with client prefix"""
        return f"{self.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key (without client prefix)
            
        Returns:
            Cached value or None
        """
        if not self.redis_client:
            return None
        
        try:
            full_key = self._get_key(key)
            value = self.redis_client.get(full_key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600
    ) -> bool:
        """
        Set value in cache.
        
        Args:
            key: Cache key (without client prefix)
            value: Value to cache (must be JSON-serializable)
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            json_value = json.dumps(value)
            return self.redis_client.setex(full_key, ttl, json_value)
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key (without client prefix)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.delete(full_key))
        except Exception as e:
            logger.warning(f"Cache delete error: {e}")
            return False
    
    def clear_client_cache(self) -> bool:
        """
        Clear all cache entries for this client.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            pattern = f"{self.key_prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                return bool(self.redis_client.delete(*keys))
            return True
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key (without client prefix)
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis_client:
            return False
        
        try:
            full_key = self._get_key(key)
            return bool(self.redis_client.exists(full_key))
        except Exception as e:
            logger.warning(f"Cache exists check error: {e}")
            return False
    
    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key.
        
        Args:
            key: Cache key (without client prefix)
            
        Returns:
            TTL in seconds, or None if key doesn't exist
        """
        if not self.redis_client:
            return None
        
        try:
            full_key = self._get_key(key)
            ttl = self.redis_client.ttl(full_key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.warning(f"Cache TTL check error: {e}")
            return None
