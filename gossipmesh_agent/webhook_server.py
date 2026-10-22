import os
import redis

HEARTBEAT_PREFIX = os.environ.get("HEARTBEAT_PREFIX", "heartbeat:")
CANCEL_PREFIX = os.environ.get("CANCEL_PREFIX", "cancel:")
GITHUB_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")

redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "localhost"), port=int(os.environ.get("REDIS_PORT", 6379)))


def verify_signature(headers: dict, payload: bytes) -> bool:
    if not GITHUB_SECRET:
        return True
    signature = headers.get("X-Hub-Signature-256")
    if not signature:
        return False
    import hmac, hashlib

    expected = "sha256=" + hmac.new(GITHUB_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def cancel_job(job_id: str):
    key = f"{HEARTBEAT_PREFIX}{job_id}"
    if not redis_client.exists(key):
        return {"status": "not_found", "job_id": job_id}, 404
    redis_client.set(f"{CANCEL_PREFIX}{job_id}", "true")
    return {"status": "cancelled", "job_id": job_id}, 200
