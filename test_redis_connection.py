#!/usr/bin/env python3
"""Test Redis connection from middleware container."""

import asyncio
import redis.asyncio as redis

async def test_redis_connection():
    """Test Redis connection."""
    try:
        r = redis.Redis(host='redis', port=6379)
        await r.ping()
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    finally:
        await r.aclose()

if __name__ == "__main__":
    asyncio.run(test_redis_connection())
