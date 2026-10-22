import os, json, redis

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
job = {"type": "issue_opened", "repo": "githubtraining/hellogitworld", "issue_number": 1, "id": "test123"}
r.rpush("gossipmesh:jobs", json.dumps(job))
print("enqueued")
