import redis
from gossipmesh.core.config import settings

redis_client = redis.from_url(settings.REDIS_URI, decode_responses=True)
