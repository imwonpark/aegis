import os
import pytest
from unittest.mock import patch, AsyncMock

# env vars for tests
os.environ["VALID_API_KEYS"] = ""  # disable auth
os.environ["REDIS_HOST"] = "localhost"
os.environ["REDIS_PORT"] = "6379"
os.environ["LOG_LEVEL"] = "WARNING"

# mock redis
@pytest.fixture(autouse=True)
def mock_redis():
    """mock redis for tests"""
    with patch('redis.asyncio.Redis') as mock_redis:
        mock_redis.return_value.ping = AsyncMock()
        yield mock_redis
