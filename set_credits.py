import os, redis

# Connect to Redis (same URL used by the agent)
redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
r = redis.from_url(redis_url)

repo = 'githubtraining/hellogitworld'
# Give the repo an initial balance of 10 credits
r.hset(f'credits:{repo}', 'balance', 10)
print(f'Credits for {repo} set to 10')
