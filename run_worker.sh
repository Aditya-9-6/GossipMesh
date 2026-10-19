#!/usr/bin/env bash

# Ensure Redis URL is set (defaults to localhost)
REDIS_URL=${REDIS_URL:-redis://localhost:6379/0}

# Start RQ worker listening to the "github-events" queue
exec rq worker github-events --url "$REDIS_URL"
