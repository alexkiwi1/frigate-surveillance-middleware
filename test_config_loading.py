#!/usr/bin/env python3
"""Test configuration loading."""

import os
from pydantic_settings import BaseSettings
from pydantic import Field

print("Environment variables:")
print(f"REDIS_HOST: {os.getenv('REDIS_HOST')}")
print(f"REDIS_PORT: {os.getenv('REDIS_PORT')}")
print()

class TestConfig(BaseSettings):
    host: str = Field(default='localhost', env='REDIS_HOST')
    port: int = Field(default=6379, env='REDIS_PORT')

print("Testing Pydantic settings loading:")
test_config = TestConfig()
print(f"TestConfig host: {test_config.host}")
print(f"TestConfig port: {test_config.port}")
print()

print("Testing with explicit env_file=None:")
test_config2 = TestConfig(_env_file=None)
print(f"TestConfig2 host: {test_config2.host}")
print(f"TestConfig2 port: {test_config2.port}")

