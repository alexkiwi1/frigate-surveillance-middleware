#!/usr/bin/env python3
"""Debug Redis configuration."""

import os
from app.config import settings

print("Environment variables:")
print(f"REDIS_HOST: {os.getenv('REDIS_HOST', 'NOT SET')}")
print(f"REDIS_PORT: {os.getenv('REDIS_PORT', 'NOT SET')}")
print()

print("Settings:")
print(f"settings.cache.host: {settings.cache.host}")
print(f"settings.cache.port: {settings.cache.port}")
print(f"settings.redis_url: {settings.redis_url}")
print()

print("Cache config:")
print(f"settings.cache: {settings.cache}")
